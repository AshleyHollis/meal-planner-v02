import { api, ApiError } from './api';
import type {
  AISuggestionResult,
  AISuggestionStatus,
  ConfirmedPlan,
  DraftPlan,
  FallbackMode,
  PlanSlot,
  PlanSlotOrigin,
  PlanSlotSuggestionSnapshot,
} from './types';

function parseCsvList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((entry): entry is string => typeof entry === 'string');
  }
  if (typeof value === 'string' && value.trim()) {
    return value
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);
  }
  return [];
}

function createOriginalSuggestion(slot: {
  mealTitle: string | null;
  mealSummary: string | null;
  reasonCodes: string[];
  explanation: string | null;
  origin: PlanSlotOrigin;
}): PlanSlotSuggestionSnapshot | null {
  if (slot.origin !== 'ai_suggested' || !slot.mealTitle) {
    return null;
  }

  return {
    mealTitle: slot.mealTitle,
    mealSummary: slot.mealSummary,
    reasonCodes: slot.reasonCodes,
    explanation: slot.explanation,
  };
}

function mapSlot(raw: Record<string, unknown>, fallbackOrigin: PlanSlotOrigin): PlanSlot {
  const reasonCodes = parseCsvList(raw.reasonCodes ?? raw.reason_codes);
  const explanationEntries = parseCsvList(
    raw.explanationEntries ?? raw.explanation_entries
  );
  const explanationCandidate =
    (raw.explanation as string | null | undefined) ?? explanationEntries.join(' ').trim();

  const slot: PlanSlot = {
    slotId: String(
      raw.slotId ?? raw.id ?? `${raw.dayOfWeek ?? raw.day_of_week}-${raw.mealType ?? raw.meal_type}`
    ),
    dayOfWeek: Number(raw.dayOfWeek ?? raw.day_of_week ?? 0),
    mealType: (raw.mealType ?? raw.meal_type ?? 'dinner') as PlanSlot['mealType'],
    mealTitle: (raw.mealTitle ?? raw.meal_title ?? null) as string | null,
    mealSummary: (raw.mealSummary ?? raw.meal_summary ?? null) as string | null,
    origin: (raw.origin ?? raw.slot_origin ?? fallbackOrigin) as PlanSlotOrigin,
    reasonCodes,
    explanation: explanationCandidate || null,
    slotState: (raw.slotState ?? raw.slot_state ?? 'idle') as PlanSlot['slotState'],
    originalSuggestion: null,
    slotMessage: (raw.slotMessage ?? raw.slot_message ?? null) as string | null,
  };

  return {
    ...slot,
    originalSuggestion: createOriginalSuggestion(slot),
  };
}

function mapSuggestionStatus(
  status: unknown,
  fallbackMode: FallbackMode,
  slots: PlanSlot[]
): AISuggestionStatus {
  if (status === 'pending' || status === 'generating') {
    return 'generating';
  }
  if (status === 'completed') {
    if (slots.length === 0 || fallbackMode === 'manual_guidance') {
      return 'insufficient_context';
    }
    return fallbackMode === 'none' ? 'ready' : 'fallback_used';
  }
  if (status === 'failed' || status === 'expired') {
    return 'failed';
  }
  return (status as AISuggestionStatus | undefined) ?? 'idle';
}

function mapFallbackMode(raw: unknown): FallbackMode {
  if (raw === true) {
    return 'curated_fallback';
  }
  if (typeof raw === 'string') {
    if (raw === 'curated_fallback' || raw === 'manual_guidance') {
      return raw;
    }
  }
  return 'none';
}

function mapDraftPlan(raw: Record<string, unknown>): DraftPlan {
  const slots = Array.isArray(raw.slots)
    ? raw.slots.map((slot) => mapSlot(slot as Record<string, unknown>, 'manually_added'))
    : [];

  return {
    draftId: String(raw.draftId ?? raw.id ?? raw.meal_plan_id ?? ''),
    householdId: String(raw.householdId ?? raw.household_id ?? ''),
    planPeriodStart: String(raw.planPeriodStart ?? raw.period_start ?? ''),
    slots,
    staleWarning: Boolean(raw.staleWarning ?? raw.stale_warning ?? raw.stale_flag),
    staleWarningAcknowledged: Boolean(
      raw.staleWarningAcknowledged ?? raw.stale_warning_acknowledged
    ),
    createdAt: String(raw.createdAt ?? raw.created_at ?? new Date().toISOString()),
    updatedAt: String(raw.updatedAt ?? raw.updated_at ?? new Date().toISOString()),
    suggestionRequestId: (raw.suggestionRequestId ??
      raw.ai_suggestion_request_id ??
      null) as string | null,
  };
}

function mapConfirmedPlan(raw: Record<string, unknown>): ConfirmedPlan {
  const slots = Array.isArray(raw.slots)
    ? raw.slots.map((slot) => mapSlot(slot as Record<string, unknown>, 'manually_added'))
    : [];

  return {
    planId: String(raw.planId ?? raw.id ?? ''),
    householdId: String(raw.householdId ?? raw.household_id ?? ''),
    planPeriodStart: String(raw.planPeriodStart ?? raw.period_start ?? ''),
    slots,
    confirmedAt: String(raw.confirmedAt ?? raw.confirmed_at ?? new Date().toISOString()),
    aiSuggestionRequestId: (raw.aiSuggestionRequestId ??
      raw.ai_suggestion_request_id ??
      null) as string | null,
    staleWarningAcknowledged: Boolean(
      raw.staleWarningAcknowledged ?? raw.stale_warning_acknowledged
    ),
  };
}

export async function getAISuggestion(
  householdId: string,
  planPeriodStart: string
): Promise<AISuggestionResult | null> {
  try {
    const raw = await api.get<Record<string, unknown>>(
      `/api/v1/households/${householdId}/plans/suggestion?period=${planPeriodStart}`
    );
    const slots = Array.isArray(raw.slots)
      ? raw.slots.map((slot) => mapSlot(slot as Record<string, unknown>, 'ai_suggested'))
      : [];
    const fallbackMode = mapFallbackMode(raw.fallbackMode ?? raw.fallback_mode);

    return {
      suggestionId: String(raw.suggestionId ?? raw.id ?? raw.result_id ?? ''),
      requestId: (raw.requestId ?? raw.request_id ?? null) as string | null,
      householdId: String(raw.householdId ?? raw.household_id ?? householdId),
      planPeriodStart: String(
        raw.planPeriodStart ?? raw.plan_period_start ?? planPeriodStart
      ),
      status: mapSuggestionStatus(raw.status, fallbackMode, slots),
      slots,
      isStale: Boolean(raw.isStale ?? raw.stale_flag ?? false),
      fallbackMode,
      createdAt: String(raw.createdAt ?? raw.created_at ?? new Date().toISOString()),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function requestAISuggestion(
  householdId: string,
  planPeriodStart: string,
  clientMutationId: string,
  slotId?: string
): Promise<AISuggestionResult> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/plans/suggestion`,
    {
      planPeriodStart,
      targetSlotId: slotId ?? null,
      requestIdempotencyKey: clientMutationId,
    }
  );

  const slots = Array.isArray(raw.slots)
    ? raw.slots.map((slot) => mapSlot(slot as Record<string, unknown>, 'ai_suggested'))
    : [];
  const fallbackMode = mapFallbackMode(raw.fallbackMode ?? raw.fallback_mode);

  return {
    suggestionId: String(raw.suggestionId ?? raw.id ?? raw.result_id ?? clientMutationId),
    requestId: (raw.requestId ?? raw.request_id ?? clientMutationId) as string,
    householdId,
    planPeriodStart,
    status: mapSuggestionStatus(raw.status, fallbackMode, slots),
    slots,
    isStale: Boolean(raw.isStale ?? raw.stale_flag ?? false),
    fallbackMode,
    createdAt: String(raw.createdAt ?? raw.created_at ?? new Date().toISOString()),
  };
}

export async function getDraft(
  householdId: string,
  planPeriodStart: string
): Promise<DraftPlan | null> {
  try {
    const raw = await api.get<Record<string, unknown>>(
      `/api/v1/households/${householdId}/plans/draft?period=${planPeriodStart}`
    );
    return mapDraftPlan(raw);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function openDraftFromSuggestion(
  householdId: string,
  suggestionId: string
): Promise<DraftPlan> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/plans/draft`,
    { suggestionId }
  );
  return mapDraftPlan(raw);
}

export async function confirmDraft(
  householdId: string,
  draftId: string,
  options: { clientMutationId: string; staleWarningAcknowledged: boolean }
): Promise<ConfirmedPlan> {
  const raw = await api.post<Record<string, unknown>>(
    `/api/v1/households/${householdId}/plans/draft/${draftId}/confirm`,
    options
  );
  return mapConfirmedPlan(raw);
}

export async function getConfirmedPlan(
  householdId: string,
  planPeriodStart: string
): Promise<ConfirmedPlan | null> {
  try {
    const raw = await api.get<Record<string, unknown>>(
      `/api/v1/households/${householdId}/plans/confirmed?period=${planPeriodStart}`
    );
    return mapConfirmedPlan(raw);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function requestSlotRegen(
  householdId: string,
  draftId: string,
  slotId: string,
  clientMutationId: string
): Promise<void> {
  return api.post(
    `/api/v1/households/${householdId}/plans/draft/${draftId}/slots/${slotId}/regenerate`,
    { clientMutationId }
  );
}
