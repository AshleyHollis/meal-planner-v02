'use client';

import { useEffect, useMemo, useState } from 'react';
import type { GroceryLine, SyncStatus } from '../../_lib/types';
import { getEffectiveQuantity, getMealTraceLabel, hasQuantityOverride } from '../../_lib/grocery-ui';
import { SyncStatusBadge } from '../../_components/SyncStatusBadge';
import styles from './GroceryLineRow.module.css';

type Props = {
  line: GroceryLine;
  editable?: boolean;
  disabled?: boolean;
  mode?: 'review' | 'trip';
  syncStatus?: SyncStatus | null;
  pendingCopy?: string | null;
  onAdjust?: (line: GroceryLine, quantity: number, note?: string) => Promise<void> | void;
  onQuickAdjust?: (line: GroceryLine, quantity: number) => Promise<void> | void;
  onRemove?: (line: GroceryLine) => Promise<void> | void;
  onComplete?: (line: GroceryLine) => Promise<void> | void;
};

export function GroceryLineRow({
  line,
  editable = false,
  disabled = false,
  mode = 'review',
  syncStatus = null,
  pendingCopy = null,
  onAdjust,
  onQuickAdjust,
  onRemove,
  onComplete,
}: Props) {
  const trace = getMealTraceLabel(line);
  const effectiveQuantity = getEffectiveQuantity(line);
  const overrideActive = hasQuantityOverride(line);
  const [showDetails, setShowDetails] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);
  const [overrideQuantity, setOverrideQuantity] = useState(String(effectiveQuantity));
  const [overrideNote, setOverrideNote] = useState(line.userAdjustmentNote ?? '');
  const detailId = useMemo(() => `line-detail-${line.groceryLineId}`, [line.groceryLineId]);
  const tripMode = mode === 'trip';

  useEffect(() => {
    setOverrideQuantity(String(effectiveQuantity));
    setOverrideNote(line.userAdjustmentNote ?? '');
  }, [effectiveQuantity, line.groceryLineId, line.userAdjustmentNote]);

  async function handleAdjustSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = Number(overrideQuantity);
    if (!Number.isFinite(parsed) || parsed <= 0 || !onAdjust) {
      return;
    }

    await onAdjust(line, parsed, overrideNote.trim() || undefined);
    setEditing(false);
  }

  async function handleQuickAdjust(delta: number) {
    const nextQuantity = Number((effectiveQuantity + delta).toFixed(2));
    if (nextQuantity <= 0 || !onQuickAdjust) {
      return;
    }

    await onQuickAdjust(line, nextQuantity);
  }

  async function handleRemoveConfirm() {
    const action = tripMode ? onComplete : onRemove;
    if (!action) {
      return;
    }

    await action(line);
    setConfirmingRemoval(false);
  }

  return (
    <li className={`${styles.row} ${!line.active ? styles.inactive : ''} ${tripMode ? styles.tripRow : ''}`}>
      <div className={styles.label}>
        <div className={styles.textColumn}>
          <div className={styles.nameRow}>
            <span className={styles.name}>{line.name}</span>
            {line.origin === 'ad_hoc' && <span className={styles.adHoc}>Ad hoc</span>}
            {!line.active && <span className={styles.removed}>{tripMode ? 'Done' : 'Removed'}</span>}
            {syncStatus && <SyncStatusBadge status={syncStatus} />}
          </div>
          {trace && <span className={styles.trace}>{trace}</span>}
          {overrideActive && (
            <span className={styles.override}>
              {tripMode
                ? `Remaining amount changed to ${effectiveQuantity} ${line.unit}.`
                : `Review quantity override — shopping quantity is ${effectiveQuantity} ${line.unit}.`}
            </span>
          )}
          {line.userAdjustmentFlagged && (
            <span className={styles.flagged}>
              {tripMode
                ? 'Trip amount differs from the confirmed snapshot.'
                : 'Review override — derived quantity changed.'}
            </span>
          )}
          {line.adHocNote && <span className={styles.trace}>Note: {line.adHocNote}</span>}
          {line.userAdjustmentNote && <span className={styles.trace}>Override note: {line.userAdjustmentNote}</span>}
          {pendingCopy && <span className={styles.pending}>{pendingCopy}</span>}
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.quantityCluster}>
          <span className={styles.qty}>{effectiveQuantity} {line.unit}</span>
          <span className={styles.quantityLabel}>
            {tripMode ? 'Left to buy' : 'Shopping quantity'}
          </span>
          {overrideActive && (
            <span className={styles.derivedQty}>Confirmed {line.quantityToBuy} {line.unit}</span>
          )}
        </div>
        {line.origin === 'derived' && line.mealSources.length > 0 && (
          <span className={styles.source} title={`Consolidated from ${line.mealSources.length} meal source(s)`}>
            🍽️ {line.mealSources.length}
          </span>
        )}
        {line.quantityCoveredByInventory > 0 && (
          <span className={styles.covered} title="Partially covered by inventory">
            −{line.quantityCoveredByInventory} {line.unit} on hand
          </span>
        )}
        {line.offsetInventoryItemId && <span className={styles.offset}>Linked inventory</span>}
        <div className={styles.actions}>
          <button
            className={styles.actionButton}
            type="button"
            aria-expanded={showDetails}
            aria-controls={detailId}
            onClick={() => setShowDetails((value) => !value)}
          >
            {showDetails ? 'Hide details' : 'Show details'}
          </button>
          {tripMode && editable && line.active && onQuickAdjust && (
            <>
              <button
                className={styles.quickButton}
                type="button"
                disabled={disabled || effectiveQuantity <= 1}
                onClick={() => void handleQuickAdjust(-1)}
              >
                −1
              </button>
              <button
                className={styles.quickButton}
                type="button"
                disabled={disabled}
                onClick={() => void handleQuickAdjust(1)}
              >
                +1
              </button>
            </>
          )}
          {editable && line.active && onAdjust && (
            <button
              className={styles.actionButton}
              type="button"
              disabled={disabled}
              onClick={() => {
                setEditing((value) => !value);
                setConfirmingRemoval(false);
              }}
            >
              {editing ? 'Cancel edit' : tripMode ? 'Set amount' : 'Edit quantity'}
            </button>
          )}
          {editable && line.active && (tripMode ? onComplete : onRemove) && (
            <button
              className={tripMode ? styles.completeButton : styles.actionButton}
              type="button"
              disabled={disabled}
              onClick={() => {
                setConfirmingRemoval((value) => !value);
                setEditing(false);
              }}
            >
              {confirmingRemoval
                ? tripMode
                  ? 'Cancel done'
                  : 'Cancel remove'
                : tripMode
                  ? 'Mark done'
                  : 'Remove'}
            </button>
          )}
        </div>
      </div>

      {(showDetails || editing || confirmingRemoval) && (
        <div className={styles.detailPanel} id={detailId}>
          <div className={styles.detailGrid}>
            <div className={styles.detailCard}>
              <h3 className={styles.detailTitle}>{tripMode ? 'Trip amount' : 'Quantity review'}</h3>
              <p className={styles.detailCopy}>
                Required {line.quantityNeeded} {line.unit}
                {line.quantityCoveredByInventory > 0
                  ? ` • on hand ${line.quantityCoveredByInventory} ${line.unit}`
                  : ' • no inventory offset'}
                {` • target ${line.quantityToBuy} ${line.unit}`}
              </p>
              {line.offsetInventoryItemId && (
                <p className={styles.detailCopy}>
                  Inventory match: {line.offsetInventoryItemId}
                  {line.offsetInventoryItemVersion !== null
                    ? ` (snapshot v${line.offsetInventoryItemVersion})`
                    : ''}
                </p>
              )}
            </div>

            {line.origin === 'derived' && line.mealSources.length > 0 && (
              <div className={styles.detailCard}>
                <h3 className={styles.detailTitle}>Meal traceability</h3>
                <ul className={styles.detailList}>
                  {line.mealSources.map((source) => (
                    <li key={`${line.groceryLineId}-${source.mealSlotId}`} className={styles.detailListItem}>
                      <span>{source.mealName ?? `Meal slot ${source.mealSlotId}`}</span>
                      <span>
                        {source.contributedQuantity} {line.unit}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {editable && line.active && editing && onAdjust && (
            <form className={styles.editor} onSubmit={(event) => void handleAdjustSubmit(event)}>
              <label className={styles.editorField}>
                <span className={styles.editorLabel}>
                  {tripMode ? 'Remaining amount to buy' : 'Shopping quantity'}
                </span>
                <input
                  className={styles.editorInput}
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={overrideQuantity}
                  onChange={(event) => setOverrideQuantity(event.target.value)}
                  disabled={disabled}
                />
              </label>
              <label className={styles.editorField}>
                <span className={styles.editorLabel}>
                  {tripMode ? 'Optional trip note' : 'Review note'}
                </span>
                <textarea
                  className={styles.editorInput}
                  rows={2}
                  value={overrideNote}
                  onChange={(event) => setOverrideNote(event.target.value)}
                  disabled={disabled}
                />
              </label>
              <div className={styles.editorActions}>
                <button className={styles.saveButton} type="submit" disabled={disabled}>
                  {tripMode ? 'Save amount' : 'Save quantity'}
                </button>
              </div>
            </form>
          )}

          {editable && line.active && confirmingRemoval && (tripMode ? onComplete : onRemove) && (
            <div className={styles.removePanel}>
              <p className={styles.detailCopy}>
                {tripMode
                  ? 'Mark this line done on this device. It will stay in the trip history section and sync when the connection is available.'
                  : 'Remove this line from the current draft? Refreshing later can bring derived lines back if they are still needed.'}
              </p>
              <button
                className={tripMode ? styles.completeButton : styles.removeButton}
                type="button"
                disabled={disabled}
                onClick={() => void handleRemoveConfirm()}
              >
                {tripMode ? 'Confirm done' : 'Confirm remove'}
              </button>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
