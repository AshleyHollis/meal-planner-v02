'use client';

import { useEffect, useState } from 'react';
import type { PlanSlot } from '../../_lib/types';
import styles from './SlotEditor.module.css';

type Props = {
  slot: PlanSlot | null;
  open: boolean;
  onClose: () => void;
  onSave: (slotId: string, mealTitle: string, mealSummary: string) => void;
  onRestoreOriginal?: (slotId: string) => void;
};

export function SlotEditor({ slot, open, onClose, onSave, onRestoreOriginal }: Props) {
  const [mealTitle, setMealTitle] = useState('');
  const [mealSummary, setMealSummary] = useState('');

  useEffect(() => {
    setMealTitle(slot?.mealTitle ?? '');
    setMealSummary(slot?.mealSummary ?? '');
  }, [slot]);

  if (!open || !slot) {
    return null;
  }

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-labelledby="slot-editor-title">
      <div className={styles.dialog}>
        <div className={styles.header}>
          <div>
            <h2 id="slot-editor-title" className={styles.title}>
              Edit {slot.mealType}
            </h2>
            <p className={styles.subtitle}>Update this slot manually or restore the original AI suggestion.</p>
          </div>
          <button className={styles.closeButton} onClick={onClose} type="button">
            ✕
          </button>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label} htmlFor="slot-meal-title">
            Meal title
          </label>
          <input
            id="slot-meal-title"
            className={styles.input}
            value={mealTitle}
            onChange={(event) => setMealTitle(event.target.value)}
            placeholder="e.g. Chicken fajitas"
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label} htmlFor="slot-meal-summary">
            Summary
          </label>
          <textarea
            id="slot-meal-summary"
            className={styles.textarea}
            value={mealSummary}
            onChange={(event) => setMealSummary(event.target.value)}
            placeholder="Optional note or prep reminder"
            rows={4}
          />
        </div>

        <div className={styles.actions}>
          {slot.originalSuggestion && onRestoreOriginal && (
            <button
              className={styles.secondaryButton}
              onClick={() => onRestoreOriginal(slot.slotId)}
              type="button"
            >
              Restore AI suggestion
            </button>
          )}
          <button className={styles.secondaryButton} onClick={onClose} type="button">
            Cancel
          </button>
          <button
            className={styles.primaryButton}
            onClick={() => onSave(slot.slotId, mealTitle, mealSummary)}
            type="button"
          >
            Save slot
          </button>
        </div>
      </div>
    </div>
  );
}
