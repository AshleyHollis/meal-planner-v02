'use client';

import type { PlanSlot } from '../../_lib/types';
import styles from './PlanSlotCard.module.css';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const ORIGIN_LABELS: Record<PlanSlot['origin'], string> = {
  ai_suggested: 'AI',
  user_edited: 'Edited',
  manually_added: 'Manual',
};

type Props = {
  slot: PlanSlot;
  editable?: boolean;
  showOriginBadge?: boolean;
  onEdit?: (slotId: string) => void;
  onRegenerate?: (slotId: string) => void;
};

export function PlanSlotCard({
  slot,
  editable = false,
  showOriginBadge = true,
  onEdit,
  onRegenerate,
}: Props) {
  const isRegenerating =
    slot.slotState === 'regenerating' || slot.slotState === 'pending_regen';

  return (
    <div
      className={`${styles.card} ${isRegenerating ? styles.regenerating : ''}`}
      aria-label={`${DAY_LABELS[slot.dayOfWeek]} ${slot.mealType}`}
    >
      <div className={styles.header}>
        <span className={styles.mealType}>{slot.mealType}</span>
        {showOriginBadge && (
          <span className={`${styles.originBadge} ${styles[slot.origin]}`}>
            {ORIGIN_LABELS[slot.origin]}
          </span>
        )}
      </div>

      {isRegenerating ? (
        <p className={styles.regenLabel}>Refreshing suggestion…</p>
      ) : slot.mealTitle ? (
        <>
          <p className={styles.mealTitle}>{slot.mealTitle}</p>
          {slot.mealSummary && <p className={styles.mealSummary}>{slot.mealSummary}</p>}
          {slot.explanation && (
            <details className={styles.explanation}>
              <summary>Why this meal?</summary>
              <p>{slot.explanation}</p>
            </details>
          )}
        </>
      ) : (
        <p className={styles.emptySlot}>No meal planned</p>
      )}

      {slot.slotMessage && (
        <p
          className={`${styles.slotMessage} ${
            slot.slotState === 'regen_failed' ? styles.slotError : ''
          }`}
        >
          {slot.slotMessage}
        </p>
      )}

      {editable && (
        <div className={styles.actions}>
          {onEdit && (
            <button
              className={styles.actionBtn}
              onClick={() => onEdit(slot.slotId)}
              type="button"
              aria-label={`Edit ${slot.mealType} on ${DAY_LABELS[slot.dayOfWeek]}`}
            >
              Edit
            </button>
          )}
          {onRegenerate && !isRegenerating && (
            <button
              className={styles.actionBtn}
              onClick={() => onRegenerate(slot.slotId)}
              type="button"
              aria-label={`Regenerate ${slot.mealType} on ${DAY_LABELS[slot.dayOfWeek]}`}
            >
              {slot.mealTitle ? 'Regenerate' : 'Suggest'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
