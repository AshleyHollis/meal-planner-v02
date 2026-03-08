'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  confirmDraft,
  getAISuggestion,
  getConfirmedPlan,
  getDraft,
  openDraftFromSuggestion,
  pollAISuggestionRequest,
  revertDraftSlot,
  requestAISuggestion,
  requestSlotRegen,
  updateDraftSlot,
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
import {
  getConfirmButtonLabel,
  getRegenerationFailureMessage,
} from '../../_lib/planner-ui';
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

type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'ok'; data: T }
  | { status: 'error'; message: string };

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
            usesOnHand: slot.usesOnHand,
            missingHints: slot.missingHints,
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
        getAISuggestion(user.activeHouseholdId, periodStart),
        getDraft(user.activeHouseholdId, periodStart),
        getConfirmedPlan(user.activeHouseholdId, periodStart),
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
    if (
      !user ||
      suggestion.status !== 'ok' ||
      suggestion.data?.status !== 'generating' ||
      !suggestion.data.requestId
    ) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      void pollAISuggestionRequest(user.activeHouseholdId, suggestion.data!.requestId!, {
        maxAttempts: 1,
        planPeriodStart: periodStart,
      })
        .then((result) => {
          setSuggestion({ status: 'ok', data: result });
          if (result.status !== 'generating') {
            setPlannerStatus('idle');
            void loadAll();
          }
        })
        .catch(() => {
          setPlannerStatus('error');
          setSuggestion({
            status: 'error',
            message: 'Could not refresh planner request status.',
          });
        });
    }, 1500);

    return () => window.clearTimeout(timeoutId);
  }, [suggestion, loadAll, periodStart, user]);

  const editorSlot = useMemo(
    () => activeDraft?.slots.find((slot) => slot.slotId === editorSlotId) ?? null,
    [activeDraft, editorSlotId]
  );

  const hasSuggestionToReview = Boolean(
    activeSuggestion &&
      (activeSuggestion.status === 'ready' || activeSuggestion.status === 'fallback_used') &&
      activeSuggestion.slots.length > 0
  );

  function replaceDraftSlot(slotId: string, nextSlot: PlanSlot) {
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
            slot.slotId === slotId ? nextSlot : slot
          ),
        },
      };
    });
  }

  async function handleRequestSuggestion() {
    if (!user) return;

    setPlannerStatus('syncing');
    setRequestMessage(null);

    try {
      const result = await requestAISuggestion(
        user.activeHouseholdId,
        periodStart,
        randomUUID()
      );
      setSuggestion({ status: 'ok', data: result });
      setPlannerStatus(result.status === 'generating' ? 'syncing' : 'idle');
    } catch {
      setSuggestion({
        status: 'ok',
        data: {
          suggestionId: `failed-${periodStart}`,
          requestId: null,
          householdId: user.activeHouseholdId,
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
        'AI suggestion requests are unavailable right now. Please retry once the planner service is reachable.'
      );
    }
  }

  async function handleOpenDraft() {
    if (!user || !activeSuggestion) return;

    const replaceExisting =
      Boolean(activeDraft) && window.confirm('Replace the draft already in progress?');
    if (activeDraft && !replaceExisting) {
      return;
    }

    try {
      const openedDraft = await openDraftFromSuggestion(
        user.activeHouseholdId,
        activeSuggestion.suggestionId,
        { replaceExisting }
      );
      setDraft({ status: 'ok', data: normalizeDraft(openedDraft) });
      setRequestMessage(null);
    } catch {
      setRequestMessage(
        'Could not open the planner draft from the latest suggestion. Please refresh and try again.'
      );
    }
  }

  async function handleSaveSlot(slotId: string, mealTitle: string, mealSummary: string) {
    if (!user || draft.status !== 'ok' || !draft.data) {
      return;
    }

    setPlannerStatus('syncing');
    try {
      const slot = await updateDraftSlot(user.activeHouseholdId, draft.data.draftId, slotId, {
        mealTitle: mealTitle.trim() || null,
        mealSummary: mealSummary.trim() || null,
      });
      replaceDraftSlot(slotId, slot);
      setEditorSlotId(null);
      setRequestMessage(null);
      setPlannerStatus('idle');
    } catch {
      setPlannerStatus('error');
      setRequestMessage('Could not save that slot. Please try again.');
    }
  }

  async function handleRestoreOriginal(slotId: string) {
    if (!user || draft.status !== 'ok' || !draft.data) {
      return;
    }

    setPlannerStatus('syncing');
    try {
      const slot = await revertDraftSlot(user.activeHouseholdId, draft.data.draftId, slotId);
      replaceDraftSlot(slotId, slot);
      setEditorSlotId(null);
      setRequestMessage(null);
      setPlannerStatus('idle');
    } catch {
      setPlannerStatus('error');
      setRequestMessage('Could not restore the original suggestion for that slot.');
    }
  }

  async function handleRegenerateSlot(slotId: string) {
    if (!user || draft.status !== 'ok' || !draft.data) return;

    const currentSlot = draft.data.slots.find((slot) => slot.slotId === slotId);
    if (!currentSlot) return;

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      replaceDraftSlot(slotId, {
        ...currentSlot,
        slotState: 'regen_failed',
        slotMessage: 'Reconnect to request a new suggestion for this slot.',
      });
      setPlannerStatus('offline');
      return;
    }

    replaceDraftSlot(slotId, {
      ...currentSlot,
      slotState: 'pending_regen',
      slotMessage: null,
    });
    setPlannerStatus('syncing');

    try {
      const regenRequest = await requestSlotRegen(
        user.activeHouseholdId,
        draft.data.draftId,
        slotId,
        randomUUID()
      );
      replaceDraftSlot(slotId, {
        ...currentSlot,
        slotState: 'regenerating',
        slotMessage: 'Waiting for the updated suggestion…',
      });

      const regenResult = await pollAISuggestionRequest(
        user.activeHouseholdId,
        regenRequest.requestId ?? regenRequest.suggestionId,
        {
          maxAttempts: 10,
          delayMs: 150,
          planPeriodStart: periodStart,
        }
      );

      const refreshedDraft = await getDraft(user.activeHouseholdId, periodStart);
      if (refreshedDraft) {
        const normalizedDraft = normalizeDraft(refreshedDraft);
        setDraft({ status: 'ok', data: normalizedDraft });

        if (
          regenResult.status === 'failed' ||
          regenResult.status === 'insufficient_context' ||
          regenResult.fallbackMode === 'manual_guidance'
        ) {
          const recoveredSlot =
            normalizedDraft.slots.find((slot) => slot.slotId === slotId) ?? currentSlot;
          replaceDraftSlot(slotId, {
            ...recoveredSlot,
            slotState: 'regen_failed',
            slotMessage: `${getRegenerationFailureMessage(recoveredSlot)} AI could not produce a better replacement from the current context.`,
          });
          setPlannerStatus(regenResult.status === 'failed' ? 'error' : 'idle');
          return;
        }

        setPlannerStatus('idle');
        return;
      }

      throw new Error('No refreshed draft available yet.');
    } catch {
      replaceDraftSlot(slotId, {
        ...currentSlot,
        slotState: 'regen_failed',
        slotMessage: getRegenerationFailureMessage(currentSlot),
      });
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
      await confirmDraft(user.activeHouseholdId, draft.data.draftId, {
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
            fallbackMode={activeSuggestion?.fallbackMode}
            hasConfirmedPlan={Boolean(activeConfirmedPlan)}
            isStale={activeSuggestion?.isStale}
            onOpenDraft={hasSuggestionToReview ? handleOpenDraft : undefined}
            onRequestNew={handleRequestSuggestion}
          />

          {requestMessage && <p className={styles.note}>{requestMessage}</p>}

          {activeConfirmedPlan && (
            <section className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>
                  {activeDraft || hasSuggestionToReview ? 'Current confirmed plan' : 'Confirmed plan'}
                </h2>
                <span className={styles.sectionMeta}>
                  {activeDraft || hasSuggestionToReview
                    ? 'Still active until you explicitly confirm a replacement.'
                    : `Confirmed ${new Date(activeConfirmedPlan.confirmedAt).toLocaleString()}`}
                </span>
              </div>
              <WeeklyGrid
                plan={activeConfirmedPlan}
                showOriginBadges={false}
                showSuggestionMeta={false}
              />
            </section>
          )}

          {!activeDraft && hasSuggestionToReview && activeSuggestion && (
            <section className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Latest AI suggestion</h2>
                <span className={styles.sectionMeta}>
                  Review the proposed meals before opening an editable draft.
                </span>
              </div>
              <WeeklyGrid plan={activeSuggestion} />
            </section>
          )}

          {activeDraft ? (
            <section className={styles.section}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Editable draft</h2>
                <span className={styles.sectionMeta}>
                  {activeConfirmedPlan
                    ? 'Confirming this draft will replace the current confirmed plan.'
                    : 'Mix AI suggestions with manual edits.'}
                </span>
              </div>

              <StaleDraftWarning visible={activeDraft.staleWarning} />

              <WeeklyGrid
                plan={activeDraft}
                editable
                onEditSlot={setEditorSlotId}
                onRegenerateSlot={handleRegenerateSlot}
              />

              <div className={styles.confirmRow}>
                <div className={styles.confirmCopy}>
                  {activeDraft.staleWarning && (
                    <StaleDraftWarning
                      visible
                      acknowledged={staleAcknowledged}
                      onAcknowledgeChange={setStaleAcknowledged}
                    />
                  )}
                  {confirmError && <p className={styles.confirmError}>{confirmError}</p>}
                </div>
                <button
                  className={styles.confirmButton}
                  onClick={handleConfirm}
                  disabled={confirming}
                  type="button"
                >
                  {getConfirmButtonLabel(Boolean(activeConfirmedPlan), confirming)}
                </button>
              </div>
            </section>
          ) : (
            <EmptyState
              icon="📅"
              title="No draft plan yet"
              description="Request a fresh AI suggestion to open a backend draft for this week. Existing confirmed plans stay protected until you explicitly confirm a replacement."
              action={
                <div className={styles.emptyActions}>
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
