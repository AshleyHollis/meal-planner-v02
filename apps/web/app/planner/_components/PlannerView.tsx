'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  confirmDraft,
  getAISuggestion,
  getConfirmedPlan,
  getDraft,
  openDraftFromSuggestion,
  requestAISuggestion,
  requestSlotRegen,
} from '../../_lib/planner-api';
import type {
  AISuggestionResult,
  ConfirmedPlan,
  DraftPlan,
  PlanSlot,
  SyncStatus,
} from '../../_lib/types';
import { useSession } from '../../_hooks/useSession';
import { LoadingState } from '../../_components/LoadingState';
import { ErrorState } from '../../_components/ErrorState';
import { EmptyState } from '../../_components/EmptyState';
import { SyncStatusBadge } from '../../_components/SyncStatusBadge';
import { randomUUID } from '../../_lib/uuid';
import { AISuggestionBanner } from './AISuggestionBanner';
import { StaleDraftWarning } from './StaleDraftWarning';
import { WeeklyGrid } from './WeeklyGrid';
import { SlotEditor } from './SlotEditor';
import styles from './PlannerView.module.css';

function isoMonday(offset = 0): string {
  const d = new Date();
  const day = d.getDay();
  const diff = (day === 0 ? -6 : 1 - day) + offset * 7;
  d.setDate(d.getDate() + diff);
  return d.toISOString().slice(0, 10);
}

const MEAL_TYPES: PlanSlot['mealType'][] = ['breakfast', 'lunch', 'dinner'];

type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'ok'; data: T }
  | { status: 'error'; message: string };

function createSlot(dayOfWeek: number, mealType: PlanSlot['mealType']): PlanSlot {
  return {
    slotId: `${dayOfWeek}-${mealType}`,
    dayOfWeek,
    mealType,
    mealTitle: null,
    mealSummary: null,
    origin: 'manually_added',
    reasonCodes: [],
    explanation: null,
    slotState: 'idle',
    originalSuggestion: null,
    slotMessage: null,
  };
}

function createManualDraft(householdId: string, planPeriodStart: string): DraftPlan {
  return {
    draftId: `local-draft-${planPeriodStart}`,
    householdId,
    planPeriodStart,
    slots: Array.from({ length: 7 }, (_, dayOfWeek) =>
      MEAL_TYPES.map((mealType) => createSlot(dayOfWeek, mealType))
    ).flat(),
    staleWarning: false,
    staleWarningAcknowledged: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    suggestionRequestId: null,
  };
}

function ensureSlotSnapshots(slots: PlanSlot[]): PlanSlot[] {
  return slots.map((slot) => ({
    ...slot,
    originalSuggestion:
      slot.originalSuggestion ??
      (slot.origin === 'ai_suggested' && slot.mealTitle
        ? {
            mealTitle: slot.mealTitle,
            mealSummary: slot.mealSummary,
            reasonCodes: slot.reasonCodes,
            explanation: slot.explanation,
          }
        : null),
    slotMessage: slot.slotMessage ?? null,
  }));
}

function normalizeDraft(draft: DraftPlan): DraftPlan {
  return {
    ...draft,
    slots: ensureSlotSnapshots(draft.slots),
  };
}

function normalizeConfirmed(plan: ConfirmedPlan): ConfirmedPlan {
  return {
    ...plan,
    slots: ensureSlotSnapshots(plan.slots).map((slot) => ({
      ...slot,
      slotState: 'idle',
      slotMessage: null,
    })),
  };
}

function buildLocalDraftFromSuggestion(
  suggestion: AISuggestionResult,
  householdId: string,
  planPeriodStart: string
): DraftPlan {
  return {
    draftId: `local-draft-${suggestion.suggestionId}`,
    householdId,
    planPeriodStart,
    slots: ensureSlotSnapshots(suggestion.slots),
    staleWarning: suggestion.isStale,
    staleWarningAcknowledged: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    suggestionRequestId: suggestion.requestId,
  };
}

export function PlannerView() {
  const { user, session, refresh } = useSession();
  const [periodStart] = useState(() => isoMonday());
  const [suggestion, setSuggestion] = useState<AsyncState<AISuggestionResult | null>>({
    status: 'loading',
  });
  const [draft, setDraft] = useState<AsyncState<DraftPlan | null>>({
    status: 'loading',
  });
  const [confirmedPlan, setConfirmedPlan] = useState<AsyncState<ConfirmedPlan | null>>({
    status: 'loading',
  });
  const [plannerStatus, setPlannerStatus] = useState<SyncStatus>('idle');
  const [requestMessage, setRequestMessage] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [editorSlotId, setEditorSlotId] = useState<string | null>(null);
  const [staleAcknowledged, setStaleAcknowledged] = useState(false);

  const loadAll = useCallback(async () => {
    if (!user) {
      setSuggestion({ status: 'ok', data: null });
      setDraft({ status: 'ok', data: null });
      setConfirmedPlan({ status: 'ok', data: null });
      return;
    }

    setSuggestion({ status: 'loading' });
    setDraft({ status: 'loading' });
    setConfirmedPlan({ status: 'loading' });

    try {
      const [suggestionResult, draftResult, confirmedResult] = await Promise.all([
        getAISuggestion(user.householdId, periodStart),
        getDraft(user.householdId, periodStart),
        getConfirmedPlan(user.householdId, periodStart),
      ]);

      setSuggestion({ status: 'ok', data: suggestionResult });
      setDraft({ status: 'ok', data: draftResult ? normalizeDraft(draftResult) : null });
      setConfirmedPlan({
        status: 'ok',
        data: confirmedResult ? normalizeConfirmed(confirmedResult) : null,
      });
    } catch {
      const message = 'Could not load planner data.';
      setSuggestion({ status: 'error', message });
      setDraft({ status: 'error', message });
      setConfirmedPlan({ status: 'error', message });
    }
  }, [user, periodStart]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const activeDraft = draft.status === 'ok' ? draft.data : null;
  const activeSuggestion = suggestion.status === 'ok' ? suggestion.data : null;
  const activeConfirmedPlan = confirmedPlan.status === 'ok' ? confirmedPlan.data : null;

  useEffect(() => {
    setStaleAcknowledged(Boolean(activeDraft?.staleWarningAcknowledged));
  }, [activeDraft?.draftId, activeDraft?.staleWarningAcknowledged]);

  useEffect(() => {
    if (!user || suggestion.status !== 'ok' || suggestion.data?.status !== 'generating') {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      void loadAll();
    }, 2500);

    return () => window.clearTimeout(timeoutId);
  }, [suggestion, loadAll, user]);

  const editorSlot = useMemo(
    () => activeDraft?.slots.find((slot) => slot.slotId === editorSlotId) ?? null,
    [activeDraft, editorSlotId]
  );

  const hasSuggestionToReview = Boolean(
    activeSuggestion &&
      (activeSuggestion.status === 'ready' || activeSuggestion.status === 'fallback_used') &&
      activeSuggestion.slots.length > 0
  );

  function updateDraftSlot(slotId: string, updater: (slot: PlanSlot) => PlanSlot) {
    setDraft((previous) => {
      if (previous.status !== 'ok' || !previous.data) {
        return previous;
      }

      return {
        status: 'ok',
        data: {
          ...previous.data,
          updatedAt: new Date().toISOString(),
          slots: previous.data.slots.map((slot) =>
            slot.slotId === slotId ? updater(slot) : slot
          ),
        },
      };
    });
  }

  async function handleRequestSuggestion() {
    if (!user) return;

    setPlannerStatus('syncing');
    setRequestMessage(null);
    setSuggestion({
      status: 'ok',
      data: {
        suggestionId: `pending-${periodStart}`,
        requestId: null,
        householdId: user.householdId,
        planPeriodStart: periodStart,
        status: 'generating',
        slots: [],
        isStale: false,
        fallbackMode: 'none',
        createdAt: new Date().toISOString(),
      },
    });

    try {
      const result = await requestAISuggestion(
        user.householdId,
        periodStart,
        randomUUID()
      );
      setSuggestion({ status: 'ok', data: result });
      setPlannerStatus('idle');
    } catch {
      setSuggestion({
        status: 'ok',
        data: {
          suggestionId: `failed-${periodStart}`,
          requestId: null,
          householdId: user.householdId,
          planPeriodStart: periodStart,
          status: 'failed',
          slots: [],
          isStale: false,
          fallbackMode: 'manual_guidance',
          createdAt: new Date().toISOString(),
        },
      });
      setPlannerStatus('error');
      setRequestMessage(
        'AI suggestion requests are unavailable right now. You can still create and edit a manual draft.'
      );
    }
  }

  async function handleOpenDraft() {
    if (!user || !activeSuggestion) return;

    if (activeDraft && !window.confirm('Replace the draft already in progress?')) {
      return;
    }

    try {
      const openedDraft = await openDraftFromSuggestion(
        user.householdId,
        activeSuggestion.suggestionId
      );
      setDraft({ status: 'ok', data: normalizeDraft(openedDraft) });
    } catch {
      setDraft({
        status: 'ok',
        data: buildLocalDraftFromSuggestion(activeSuggestion, user.householdId, periodStart),
      });
      setRequestMessage(
        'Opened a local draft from the suggestion. Confirmation still depends on the backend plan contract.'
      );
    }
  }

  function handleCreateManualDraft() {
    if (!user) return;

    if (activeDraft && !window.confirm('Replace the draft already in progress?')) {
      return;
    }

    setDraft({
      status: 'ok',
      data: createManualDraft(user.householdId, periodStart),
    });
    setRequestMessage(null);
    setEditorSlotId(null);
  }

  function handleSaveSlot(slotId: string, mealTitle: string, mealSummary: string) {
    updateDraftSlot(slotId, (slot) => {
      const normalizedTitle = mealTitle.trim();
      const normalizedSummary = mealSummary.trim() || null;

      if (
        slot.originalSuggestion &&
        normalizedTitle === (slot.originalSuggestion.mealTitle ?? '') &&
        normalizedSummary === slot.originalSuggestion.mealSummary
      ) {
        return {
          ...slot,
          mealTitle: slot.originalSuggestion.mealTitle,
          mealSummary: slot.originalSuggestion.mealSummary,
          reasonCodes: slot.originalSuggestion.reasonCodes,
          explanation: slot.originalSuggestion.explanation,
          origin: 'ai_suggested',
          slotState: 'idle',
          slotMessage: 'Restored the original AI suggestion.',
        };
      }

      return {
        ...slot,
        mealTitle: normalizedTitle || null,
        mealSummary: normalizedSummary,
        origin: slot.originalSuggestion ? 'user_edited' : 'manually_added',
        reasonCodes: [],
        explanation: null,
        slotState: 'idle',
        slotMessage: normalizedTitle
          ? 'Manual edit saved.'
          : 'Slot cleared. You can regenerate or restore it later.',
      };
    });

    setEditorSlotId(null);
  }

  function handleRestoreOriginal(slotId: string) {
    updateDraftSlot(slotId, (slot) => {
      if (!slot.originalSuggestion) {
        return slot;
      }

      return {
        ...slot,
        mealTitle: slot.originalSuggestion.mealTitle,
        mealSummary: slot.originalSuggestion.mealSummary,
        reasonCodes: slot.originalSuggestion.reasonCodes,
        explanation: slot.originalSuggestion.explanation,
        origin: 'ai_suggested',
        slotState: 'idle',
        slotMessage: 'Restored the original AI suggestion.',
      };
    });

    setEditorSlotId(null);
  }

  async function handleRegenerateSlot(slotId: string) {
    if (!user || draft.status !== 'ok' || !draft.data) return;

    const currentSlot = draft.data.slots.find((slot) => slot.slotId === slotId);
    if (!currentSlot) return;

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      updateDraftSlot(slotId, (slot) => ({
        ...slot,
        slotState: 'regen_failed',
        slotMessage: 'Reconnect to request a new suggestion for this slot.',
      }));
      setPlannerStatus('offline');
      return;
    }

    updateDraftSlot(slotId, (slot) => ({
      ...slot,
      slotState: 'pending_regen',
      slotMessage: null,
    }));
    setPlannerStatus('syncing');

    try {
      await requestSlotRegen(user.householdId, draft.data.draftId, slotId, randomUUID());
      updateDraftSlot(slotId, (slot) => ({
        ...slot,
        slotState: 'regenerating',
        slotMessage: 'Waiting for the updated suggestion…',
      }));

      const refreshedDraft = await getDraft(user.householdId, periodStart);
      if (refreshedDraft) {
        setDraft({ status: 'ok', data: normalizeDraft(refreshedDraft) });
        setPlannerStatus('idle');
        return;
      }

      throw new Error('No refreshed draft available yet.');
    } catch {
      updateDraftSlot(slotId, (slot) => ({
        ...slot,
        mealTitle: slot.originalSuggestion?.mealTitle ?? slot.mealTitle,
        mealSummary: slot.originalSuggestion?.mealSummary ?? slot.mealSummary,
        reasonCodes: slot.originalSuggestion?.reasonCodes ?? slot.reasonCodes,
        explanation: slot.originalSuggestion?.explanation ?? slot.explanation,
        origin: slot.originalSuggestion ? 'ai_suggested' : slot.origin,
        slotState: 'regen_failed',
        slotMessage: 'Could not regenerate this slot. Retry or edit it manually.',
      }));
      setPlannerStatus('error');
    }
  }

  async function handleConfirm() {
    if (!user || draft.status !== 'ok' || !draft.data) return;

    if (draft.data.staleWarning && !staleAcknowledged) {
      setConfirmError(
        'Acknowledge the stale-draft warning before confirming this plan.'
      );
      return;
    }

    setConfirming(true);
    setConfirmError(null);
    setPlannerStatus('syncing');

    try {
      await confirmDraft(user.householdId, draft.data.draftId, {
        clientMutationId: randomUUID(),
        staleWarningAcknowledged: draft.data.staleWarning ? staleAcknowledged : false,
      });
      await loadAll();
      setPlannerStatus('idle');
    } catch {
      setPlannerStatus('error');
      setConfirmError('Could not confirm the plan. Please try again.');
    } finally {
      setConfirming(false);
    }
  }

  if (session.status === 'loading') {
    return <LoadingState label="Loading planner…" />;
  }

  if (session.status === 'error') {
    return <ErrorState message={session.message} onRetry={refresh} />;
  }

  if (!user) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Meal Planner</h1>
          <span className={styles.period}>Week of {periodStart}</span>
        </div>
        <EmptyState
          icon="🔐"
          title="Sign in to plan meals"
          description="Planner session state comes from the API bootstrap endpoint. Once the backend session is active, this screen will load suggestions, drafts, and confirmed plans."
        />
      </div>
    );
  }

  const isLoading =
    suggestion.status === 'loading' ||
    draft.status === 'loading' ||
    confirmedPlan.status === 'loading';
  const hasError =
    suggestion.status === 'error' ||
    draft.status === 'error' ||
    confirmedPlan.status === 'error';

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Meal Planner</h1>
          <span className={styles.period}>Week of {periodStart}</span>
        </div>
        <SyncStatusBadge status={plannerStatus} />
      </div>

      {isLoading && <LoadingState label="Loading planner…" />}

      {hasError && !isLoading && (
        <ErrorState
          message={
            (suggestion.status === 'error' && suggestion.message) ||
            (draft.status === 'error' && draft.message) ||
            (confirmedPlan.status === 'error' && confirmedPlan.message) ||
            'Error loading planner.'
          }
          onRetry={loadAll}
        />
      )}

      {!isLoading && !hasError && (
        <>
          <AISuggestionBanner
            status={activeSuggestion?.status ?? 'idle'}
            isStale={activeSuggestion?.isStale}
            onOpenDraft={hasSuggestionToReview ? handleOpenDraft : undefined}
            onRequestNew={handleRequestSuggestion}
          />

          {requestMessage && <p className={styles.note}>{requestMessage}</p>}

          {activeConfirmedPlan && !activeDraft && (
            <section className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Confirmed plan</h2>
                <span className={styles.sectionMeta}>
                  Confirmed {new Date(activeConfirmedPlan.confirmedAt).toLocaleString()}
                </span>
              </div>
              <WeeklyGrid plan={activeConfirmedPlan} showOriginBadges={false} />
            </section>
          )}

          {activeDraft ? (
            <>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Editable draft</h2>
                <span className={styles.sectionMeta}>Mix AI suggestions with manual edits.</span>
              </div>

              <StaleDraftWarning
                visible={activeDraft.staleWarning}
                acknowledged={staleAcknowledged}
                onAcknowledgeChange={setStaleAcknowledged}
              />

              <WeeklyGrid
                plan={activeDraft}
                editable
                onEditSlot={setEditorSlotId}
                onRegenerateSlot={handleRegenerateSlot}
              />

              <div className={styles.confirmRow}>
                {confirmError && <p className={styles.confirmError}>{confirmError}</p>}
                <button
                  className={styles.secondaryButton}
                  onClick={handleCreateManualDraft}
                  type="button"
                >
                  Start over manually
                </button>
                <button
                  className={styles.confirmButton}
                  onClick={handleConfirm}
                  disabled={confirming}
                  type="button"
                >
                  {confirming ? 'Confirming…' : 'Confirm plan'}
                </button>
              </div>
            </>
          ) : (
            <EmptyState
              icon="📅"
              title="No draft plan yet"
              description="Request a fresh AI suggestion or start a manual draft. Existing confirmed plans stay protected until you explicitly confirm a replacement."
              action={
                <div className={styles.emptyActions}>
                  <button className={styles.secondaryButton} onClick={handleCreateManualDraft} type="button">
                    Start manual draft
                  </button>
                  <button className={styles.confirmButton} onClick={handleRequestSuggestion} type="button">
                    Request AI suggestion
                  </button>
                </div>
              }
            />
          )}

          <SlotEditor
            slot={editorSlot}
            open={Boolean(editorSlot)}
            onClose={() => setEditorSlotId(null)}
            onSave={handleSaveSlot}
            onRestoreOriginal={handleRestoreOriginal}
          />
        </>
      )}
    </div>
  );
}
