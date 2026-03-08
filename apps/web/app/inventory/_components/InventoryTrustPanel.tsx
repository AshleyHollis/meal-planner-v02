'use client';

import { useEffect, useMemo, useState } from 'react';
import { ErrorState } from '../../_components/ErrorState';
import { LoadingState } from '../../_components/LoadingState';
import {
  describeAdjustmentSummary,
  describeFreshnessInfo,
  describeItemFreshness,
  formatMutationType,
  formatQuantityWithUnit,
  formatReasonCode,
  formatSignedQuantity,
  formatStorageLocation,
  formatTimestamp,
  toDateInputValue,
} from '../../_lib/inventory-trust';
import type {
  FreshnessBasis,
  InventoryAdjustment,
  InventoryHistoryPage,
  InventoryItemDetail,
  InventoryReasonCode,
  MutationType,
  StorageLocation,
} from '../../_lib/types';
import styles from './InventoryTrustPanel.module.css';

type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'ok'; data: T }
  | { status: 'error'; message: string };

type QuantityMutationType = 'increase_quantity' | 'decrease_quantity' | 'set_quantity';

type QuantityMutationValues = {
  mutationType: QuantityMutationType;
  quantity: number;
  reasonCode: InventoryReasonCode;
  note: string;
};

type MetadataMutationValues = {
  name: string;
  freshnessBasis: FreshnessBasis;
  expiryDate: string;
  estimatedExpiryDate: string;
  freshnessNote: string;
  note: string;
};

type MoveMutationValues = {
  storageLocation: StorageLocation;
  note: string;
};

type CorrectionMutationValues = {
  correctsAdjustmentId: string;
  deltaQuantity: number;
  note: string;
};

type Props = {
  item: InventoryItemDetail;
  historyState: AsyncState<InventoryHistoryPage>;
  onRetryHistory: () => void;
  onLoadMoreHistory: () => void;
  onQuantitySubmit: (values: QuantityMutationValues) => void | Promise<void>;
  onMetadataSubmit: (values: MetadataMutationValues) => void | Promise<void>;
  onMoveSubmit: (values: MoveMutationValues) => void | Promise<void>;
  onCorrectionSubmit: (values: CorrectionMutationValues) => void | Promise<void>;
  disabled?: boolean;
  loadingMoreHistory?: boolean;
};

const increaseReasons: InventoryReasonCode[] = [
  'manual_edit',
  'shopping_apply',
  'leftovers_create',
  'correction',
];

const decreaseReasons: InventoryReasonCode[] = [
  'cooking_consume',
  'spoilage_or_discard',
  'shopping_skip_or_reduce',
  'manual_edit',
  'correction',
];

const setReasons: InventoryReasonCode[] = ['manual_count_reset', 'manual_edit'];

function defaultReasonForMutation(mutationType: QuantityMutationType): InventoryReasonCode {
  switch (mutationType) {
    case 'increase_quantity':
      return 'manual_edit';
    case 'decrease_quantity':
      return 'cooking_consume';
    case 'set_quantity':
      return 'manual_count_reset';
    default:
      return 'manual_edit';
  }
}

function reasonOptionsForMutation(mutationType: QuantityMutationType): InventoryReasonCode[] {
  switch (mutationType) {
    case 'increase_quantity':
      return increaseReasons;
    case 'decrease_quantity':
      return decreaseReasons;
    case 'set_quantity':
      return setReasons;
    default:
      return increaseReasons;
  }
}

function quantityFieldLabel(mutationType: QuantityMutationType): string {
  switch (mutationType) {
    case 'increase_quantity':
      return 'Increase by';
    case 'decrease_quantity':
      return 'Decrease by';
    case 'set_quantity':
      return 'Set total to';
    default:
      return 'Quantity';
  }
}

function precisionReductionRequiresIntent(
  currentBasis: FreshnessBasis,
  nextBasis: FreshnessBasis
): boolean {
  return (
    (currentBasis === 'known' && nextBasis !== 'known') ||
    (currentBasis === 'estimated' && nextBasis === 'unknown')
  );
}

function quantityChanged(entry: InventoryAdjustment): boolean {
  return Boolean(entry.quantityTransition?.changed);
}

function correctionOptionLabel(entry: InventoryAdjustment): string {
  const delta = formatSignedQuantity(entry.quantityTransition?.delta ?? entry.deltaQuantity);
  return `${formatMutationType(entry.mutationType)} · ${formatTimestamp(entry.createdAt)} · ${delta}`;
}

export function InventoryTrustPanel({
  item,
  historyState,
  onRetryHistory,
  onLoadMoreHistory,
  onQuantitySubmit,
  onMetadataSubmit,
  onMoveSubmit,
  onCorrectionSubmit,
  disabled,
  loadingMoreHistory,
}: Props) {
  const [quantityType, setQuantityType] = useState<QuantityMutationType>('increase_quantity');
  const [quantityValue, setQuantityValue] = useState('');
  const [quantityReason, setQuantityReason] = useState<InventoryReasonCode>('manual_edit');
  const [quantityNote, setQuantityNote] = useState('');

  const [metadataName, setMetadataName] = useState(item.name);
  const [metadataBasis, setMetadataBasis] = useState<FreshnessBasis>(item.freshnessBasis);
  const [metadataExpiryDate, setMetadataExpiryDate] = useState(toDateInputValue(item.expiryDate));
  const [metadataEstimatedDate, setMetadataEstimatedDate] = useState(
    toDateInputValue(item.estimatedExpiryDate)
  );
  const [metadataFreshnessNote, setMetadataFreshnessNote] = useState(item.freshnessNote ?? '');
  const [metadataNote, setMetadataNote] = useState('');
  const [confirmReducedPrecision, setConfirmReducedPrecision] = useState(false);

  const [moveLocation, setMoveLocation] = useState<StorageLocation>(item.storageLocation);
  const [moveNote, setMoveNote] = useState('');

  const [correctionTargetId, setCorrectionTargetId] = useState('');
  const [correctionDelta, setCorrectionDelta] = useState('');
  const [correctionNote, setCorrectionNote] = useState('');

  useEffect(() => {
    setQuantityType('increase_quantity');
    setQuantityValue('');
    setQuantityReason(defaultReasonForMutation('increase_quantity'));
    setQuantityNote('');
    setMetadataName(item.name);
    setMetadataBasis(item.freshnessBasis);
    setMetadataExpiryDate(toDateInputValue(item.expiryDate));
    setMetadataEstimatedDate(toDateInputValue(item.estimatedExpiryDate));
    setMetadataFreshnessNote(item.freshnessNote ?? '');
    setMetadataNote('');
    setConfirmReducedPrecision(false);
    setMoveLocation(item.storageLocation);
    setMoveNote('');
  }, [item]);

  useEffect(() => {
    setQuantityReason(defaultReasonForMutation(quantityType));
  }, [quantityType]);

  const quantityReasons = useMemo(
    () => reasonOptionsForMutation(quantityType),
    [quantityType]
  );

  const correctionCandidates = useMemo(() => {
    if (historyState.status !== 'ok') {
      return [];
    }

    return historyState.data.entries.filter(quantityChanged);
  }, [historyState]);

  useEffect(() => {
    if (correctionCandidates.length === 0) {
      setCorrectionTargetId('');
      setCorrectionDelta('');
      return;
    }

    const fallbackTarget =
      correctionCandidates.find((entry) => entry.inventoryAdjustmentId === correctionTargetId) ??
      correctionCandidates[0];

    setCorrectionTargetId(fallbackTarget.inventoryAdjustmentId);
    const suggestedDelta = fallbackTarget.quantityTransition?.delta ?? fallbackTarget.deltaQuantity;
    setCorrectionDelta(suggestedDelta ? String(-suggestedDelta) : '');
  }, [correctionCandidates, correctionTargetId]);

  const selectedCorrectionTarget =
    correctionCandidates.find((entry) => entry.inventoryAdjustmentId === correctionTargetId) ?? null;

  const requiresReducedPrecisionConfirm = precisionReductionRequiresIntent(
    item.freshnessBasis,
    metadataBasis
  );

  function handleQuantitySubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = Number(quantityValue);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return;
    }

    void onQuantitySubmit({
      mutationType: quantityType,
      quantity: parsed,
      reasonCode: quantityReason,
      note: quantityNote.trim(),
    });

    setQuantityValue('');
    setQuantityNote('');
  }

  function handleMetadataSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!metadataName.trim()) {
      return;
    }

    if (requiresReducedPrecisionConfirm && !confirmReducedPrecision) {
      return;
    }

    void onMetadataSubmit({
      name: metadataName.trim(),
      freshnessBasis: metadataBasis,
      expiryDate: metadataBasis === 'known' ? metadataExpiryDate : '',
      estimatedExpiryDate: metadataBasis === 'estimated' ? metadataEstimatedDate : '',
      freshnessNote: metadataFreshnessNote.trim(),
      note: metadataNote.trim(),
    });

    setMetadataNote('');
    setConfirmReducedPrecision(false);
  }

  function handleMoveSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    void onMoveSubmit({
      storageLocation: moveLocation,
      note: moveNote.trim(),
    });

    setMoveNote('');
  }

  function handleCorrectionSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = Number(correctionDelta);
    if (!correctionTargetId || !Number.isFinite(parsed) || parsed === 0 || !correctionNote.trim()) {
      return;
    }

    void onCorrectionSubmit({
      correctsAdjustmentId: correctionTargetId,
      deltaQuantity: parsed,
      note: correctionNote.trim(),
    });

    setCorrectionNote('');
  }

  return (
    <section className={styles.panel} aria-label={`${item.name} trust review`}>
      <div className={styles.summaryHeader}>
        <div>
          <p className={styles.eyebrow}>Trust review</p>
          <h2 className={styles.itemTitle}>{item.name}</h2>
          <p className={styles.summaryText}>
            {formatQuantityWithUnit(item.quantityOnHand, item.primaryUnit)} in{' '}
            {formatStorageLocation(item.storageLocation)}
          </p>
        </div>
        <div className={styles.summaryMeta}>
          <span>v{item.serverVersion}</span>
          <span>Updated {formatTimestamp(item.updatedAt)}</span>
        </div>
      </div>

      <div className={styles.snapshotGrid}>
        <article className={styles.snapshotCard}>
          <span className={styles.cardLabel}>Current freshness</span>
          <strong>{describeItemFreshness(item)}</strong>
        </article>
        <article className={styles.snapshotCard}>
          <span className={styles.cardLabel}>History summary</span>
          <strong>
            {item.historySummary?.committedAdjustmentCount ?? 0} events ·{' '}
            {item.historySummary?.correctionCount ?? 0} corrections
          </strong>
        </article>
        <article className={styles.snapshotCard}>
          <span className={styles.cardLabel}>Latest committed event</span>
          <strong>{describeAdjustmentSummary(item.latestAdjustment)}</strong>
        </article>
      </div>

      <p className={styles.auditNotice}>
        History is append-only. Corrections add balancing events and keep earlier changes visible for
        review.
      </p>

      <div className={styles.actionGrid}>
        <form className={styles.card} onSubmit={handleQuantitySubmit}>
          <div className={styles.cardHeader}>
            <div>
              <h3>Adjust quantity</h3>
              <p>Increase, decrease, or set a counted total with a version-safe retryable mutation.</p>
            </div>
          </div>
          <label className={styles.fieldLabel}>
            Action
            <select
              className={styles.input}
              value={quantityType}
              onChange={(event) => setQuantityType(event.target.value as QuantityMutationType)}
              disabled={disabled}
            >
              <option value="increase_quantity">Increase quantity</option>
              <option value="decrease_quantity">Decrease quantity</option>
              <option value="set_quantity">Set exact quantity</option>
            </select>
          </label>
          <div className={styles.formRow}>
            <label className={styles.fieldLabel}>
              {quantityFieldLabel(quantityType)}
              <input
                className={styles.input}
                type="number"
                min="0"
                step="0.01"
                value={quantityValue}
                onChange={(event) => setQuantityValue(event.target.value)}
                placeholder={item.primaryUnit}
                disabled={disabled}
              />
            </label>
            <label className={styles.fieldLabel}>
              Reason
              <select
                className={styles.input}
                value={quantityReason}
                onChange={(event) => setQuantityReason(event.target.value as InventoryReasonCode)}
                disabled={disabled}
              >
                {quantityReasons.map((reason) => (
                  <option key={reason} value={reason}>
                    {formatReasonCode(reason)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className={styles.fieldLabel}>
            Note
            <textarea
              className={styles.textarea}
              value={quantityNote}
              onChange={(event) => setQuantityNote(event.target.value)}
              placeholder="Optional context for the audit trail"
              disabled={disabled}
            />
          </label>
          {quantityType === 'set_quantity' && (
            <p className={styles.helper}>
              Set quantity records the new counted total while preserving the earlier value in
              history.
            </p>
          )}
          <button className={styles.primaryButton} type="submit" disabled={disabled}>
            Save quantity change
          </button>
        </form>

        <form className={styles.card} onSubmit={handleMetadataSubmit}>
          <div className={styles.cardHeader}>
            <div>
              <h3>Edit metadata</h3>
              <p>Update the item name and freshness basis while keeping each trust-sensitive change auditable.</p>
            </div>
          </div>
          <label className={styles.fieldLabel}>
            Item name
            <input
              className={styles.input}
              value={metadataName}
              onChange={(event) => setMetadataName(event.target.value)}
              disabled={disabled}
            />
          </label>
          <div className={styles.formRow}>
            <label className={styles.fieldLabel}>
              Freshness basis
              <select
                className={styles.input}
                value={metadataBasis}
                onChange={(event) => setMetadataBasis(event.target.value as FreshnessBasis)}
                disabled={disabled}
              >
                <option value="known">Known freshness</option>
                <option value="estimated">Estimated freshness</option>
                <option value="unknown">Unknown freshness</option>
              </select>
            </label>
            {metadataBasis === 'known' && (
              <label className={styles.fieldLabel}>
                Exact expiry date
                <input
                  className={styles.input}
                  type="date"
                  value={metadataExpiryDate}
                  onChange={(event) => setMetadataExpiryDate(event.target.value)}
                  disabled={disabled}
                />
              </label>
            )}
            {metadataBasis === 'estimated' && (
              <label className={styles.fieldLabel}>
                Estimated expiry date
                <input
                  className={styles.input}
                  type="date"
                  value={metadataEstimatedDate}
                  onChange={(event) => setMetadataEstimatedDate(event.target.value)}
                  disabled={disabled}
                />
              </label>
            )}
          </div>
          <label className={styles.fieldLabel}>
            Freshness note
            <input
              className={styles.input}
              value={metadataFreshnessNote}
              onChange={(event) => setMetadataFreshnessNote(event.target.value)}
              placeholder="Optional detail for estimated or newly confirmed freshness"
              disabled={disabled}
            />
          </label>
          <label className={styles.fieldLabel}>
            Audit note
            <textarea
              className={styles.textarea}
              value={metadataNote}
              onChange={(event) => setMetadataNote(event.target.value)}
              placeholder="Optional reason for this metadata update"
              disabled={disabled}
            />
          </label>
          {requiresReducedPrecisionConfirm && (
            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={confirmReducedPrecision}
                onChange={(event) => setConfirmReducedPrecision(event.target.checked)}
                disabled={disabled}
              />
              <span>
                I understand this reduces freshness precision and should stay visible in history.
              </span>
            </label>
          )}
          <button className={styles.primaryButton} type="submit" disabled={disabled}>
            Save metadata
          </button>
        </form>

        <form className={styles.card} onSubmit={handleMoveSubmit}>
          <div className={styles.cardHeader}>
            <div>
              <h3>Move location</h3>
              <p>Record where the item lives now without changing its identity or rewriting history.</p>
            </div>
          </div>
          <label className={styles.fieldLabel}>
            New storage location
            <select
              className={styles.input}
              value={moveLocation}
              onChange={(event) => setMoveLocation(event.target.value as StorageLocation)}
              disabled={disabled}
            >
              <option value="pantry">Pantry</option>
              <option value="fridge">Fridge</option>
              <option value="freezer">Freezer</option>
              <option value="leftovers">Leftovers</option>
            </select>
          </label>
          <label className={styles.fieldLabel}>
            Note
            <textarea
              className={styles.textarea}
              value={moveNote}
              onChange={(event) => setMoveNote(event.target.value)}
              placeholder="Optional explanation for the move"
              disabled={disabled}
            />
          </label>
          <button className={styles.primaryButton} type="submit" disabled={disabled}>
            Save location move
          </button>
        </form>

        <form className={styles.card} onSubmit={handleCorrectionSubmit}>
          <div className={styles.cardHeader}>
            <div>
              <h3>Compensating correction</h3>
              <p>Link a balancing quantity event to an earlier adjustment. The original event stays visible.</p>
            </div>
          </div>
          <label className={styles.fieldLabel}>
            Correction target
            <select
              className={styles.input}
              value={correctionTargetId}
              onChange={(event) => setCorrectionTargetId(event.target.value)}
              disabled={disabled || correctionCandidates.length === 0}
            >
              {correctionCandidates.length === 0 ? (
                <option value="">No quantity-changing history loaded yet</option>
              ) : (
                correctionCandidates.map((entry) => (
                  <option key={entry.inventoryAdjustmentId} value={entry.inventoryAdjustmentId}>
                    {correctionOptionLabel(entry)}
                  </option>
                ))
              )}
            </select>
          </label>
          {selectedCorrectionTarget && (
            <p className={styles.helper}>
              Correcting: {correctionOptionLabel(selectedCorrectionTarget)}
            </p>
          )}
          <div className={styles.formRow}>
            <label className={styles.fieldLabel}>
              Delta quantity
              <input
                className={styles.input}
                type="number"
                step="0.01"
                value={correctionDelta}
                onChange={(event) => setCorrectionDelta(event.target.value)}
                placeholder="Use positive to restore, negative to reduce"
                disabled={disabled || correctionCandidates.length === 0}
              />
            </label>
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Current item total</span>
              <strong>{formatQuantityWithUnit(item.quantityOnHand, item.primaryUnit)}</strong>
            </div>
          </div>
          <label className={styles.fieldLabel}>
            Why is a correction needed?
            <textarea
              className={styles.textarea}
              value={correctionNote}
              onChange={(event) => setCorrectionNote(event.target.value)}
              placeholder="Required so later readers understand the correction chain"
              disabled={disabled || correctionCandidates.length === 0}
            />
          </label>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={disabled || correctionCandidates.length === 0}
          >
            Record correction
          </button>
        </form>
      </div>

      <section className={styles.historySection} aria-label="Inventory history">
        <div className={styles.historyHeader}>
          <div>
            <h3>History</h3>
            <p>
              Review committed changes, freshness transitions, location moves, and correction links
              without rebuilding the audit trail in the browser.
            </p>
          </div>
          {historyState.status === 'ok' && (
            <span className={styles.historyMeta}>
              {historyState.data.summary.committedAdjustmentCount} committed events
            </span>
          )}
        </div>

        {historyState.status === 'loading' && <LoadingState label="Loading item history…" />}
        {historyState.status === 'error' && (
          <ErrorState message={historyState.message} onRetry={onRetryHistory} />
        )}
        {historyState.status === 'ok' && (
          <>
            <div className={styles.historyList}>
              {historyState.data.entries.map((entry) => (
                <article className={styles.historyCard} key={entry.inventoryAdjustmentId}>
                  <div className={styles.historyCardHeader}>
                    <div>
                      <h4>{formatMutationType(entry.mutationType)}</h4>
                      <p>
                        {formatTimestamp(entry.createdAt)} · {formatReasonCode(entry.reasonCode)}
                      </p>
                    </div>
                    <div className={styles.tagGroup}>
                      {entry.correctionLinks.isCorrection && (
                        <span className={styles.tag}>Correction event</span>
                      )}
                      {entry.correctionLinks.isCorrected && (
                        <span className={styles.tag}>Corrected later</span>
                      )}
                      {entry.clientMutationId && <span className={styles.tag}>Retry-safe</span>}
                    </div>
                  </div>

                  <dl className={styles.historyDetails}>
                    <div>
                      <dt>Actor</dt>
                      <dd>{entry.actorUserId}</dd>
                    </div>

                    {entry.quantityTransition?.changed && (
                      <div>
                        <dt>Quantity</dt>
                        <dd>
                          {formatQuantityWithUnit(
                            entry.quantityTransition.before,
                            entry.quantityTransition.unit
                          )}{' '}
                          →{' '}
                          {formatQuantityWithUnit(
                            entry.quantityTransition.after,
                            entry.quantityTransition.unit
                          )}{' '}
                          ({formatSignedQuantity(entry.quantityTransition.delta)})
                        </dd>
                      </div>
                    )}

                    {entry.locationTransition?.changed && (
                      <div>
                        <dt>Location</dt>
                        <dd>
                          {entry.locationTransition.before
                            ? formatStorageLocation(entry.locationTransition.before)
                            : 'Unknown'}{' '}
                          →{' '}
                          {entry.locationTransition.after
                            ? formatStorageLocation(entry.locationTransition.after)
                            : 'Unknown'}
                        </dd>
                      </div>
                    )}

                    {entry.freshnessTransition?.changed && (
                      <div>
                        <dt>Freshness</dt>
                        <dd>
                          {describeFreshnessInfo(entry.freshnessTransition.before)} →{' '}
                          {describeFreshnessInfo(entry.freshnessTransition.after)}
                        </dd>
                      </div>
                    )}

                    {entry.correctionLinks.correctsAdjustmentId && (
                      <div>
                        <dt>Corrects</dt>
                        <dd>{entry.correctionLinks.correctsAdjustmentId}</dd>
                      </div>
                    )}

                    {entry.correctionLinks.correctedByAdjustmentIds.length > 0 && (
                      <div>
                        <dt>Corrected by</dt>
                        <dd>{entry.correctionLinks.correctedByAdjustmentIds.join(', ')}</dd>
                      </div>
                    )}

                    {(entry.workflowReference?.causalWorkflowId ||
                      entry.workflowReference?.causalWorkflowType ||
                      entry.workflowReference?.correlationId) && (
                      <div>
                        <dt>Workflow reference</dt>
                        <dd>
                          {entry.workflowReference?.causalWorkflowType ?? 'workflow'}
                          {entry.workflowReference?.causalWorkflowId
                            ? ` · ${entry.workflowReference.causalWorkflowId}`
                            : ''}
                          {entry.workflowReference?.correlationId
                            ? ` · correlation ${entry.workflowReference.correlationId}`
                            : ''}
                        </dd>
                      </div>
                    )}

                    {entry.note && (
                      <div className={styles.fullWidth}>
                        <dt>Note</dt>
                        <dd>{entry.note}</dd>
                      </div>
                    )}
                  </dl>
                </article>
              ))}
            </div>

            {historyState.data.hasMore && (
              <button
                className={styles.secondaryButton}
                type="button"
                onClick={onLoadMoreHistory}
                disabled={disabled || loadingMoreHistory}
              >
                {loadingMoreHistory ? 'Loading older events…' : 'Load older history'}
              </button>
            )}
          </>
        )}
      </section>
    </section>
  );
}
