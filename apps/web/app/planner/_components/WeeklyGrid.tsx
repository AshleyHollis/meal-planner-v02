'use client';

import { Fragment } from 'react';
import type { DraftPlan, ConfirmedPlan } from '../../_lib/types';
import { PlanSlotCard } from './PlanSlotCard';
import styles from './WeeklyGrid.module.css';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MEAL_TYPES = ['breakfast', 'lunch', 'dinner'] as const;

type Props = {
  plan: Pick<DraftPlan, 'slots'> | Pick<ConfirmedPlan, 'slots'>;
  editable?: boolean;
  showOriginBadges?: boolean;
  onEditSlot?: (slotId: string) => void;
  onRegenerateSlot?: (slotId: string) => void;
};

export function WeeklyGrid({
  plan,
  editable = false,
  showOriginBadges = true,
  onEditSlot,
  onRegenerateSlot,
}: Props) {
  function slotFor(dayOfWeek: number, mealType: string) {
    return plan.slots.find(
      (slot) => slot.dayOfWeek === dayOfWeek && slot.mealType === mealType
    );
  }

  return (
    <div className={styles.grid} role="grid" aria-label="Weekly meal plan">
      <div className={styles.cornerCell} />
      {DAY_LABELS.map((day) => (
        <div key={day} className={styles.dayHeader} role="columnheader">
          {day}
        </div>
      ))}

      {MEAL_TYPES.map((mealType) => (
        <Fragment key={mealType}>
          <div className={styles.mealLabel} role="rowheader">
            {mealType.charAt(0).toUpperCase() + mealType.slice(1)}
          </div>
          {DAY_LABELS.map((_, dayIdx) => {
            const slot = slotFor(dayIdx, mealType);
            return (
              <div key={`${mealType}-${dayIdx}`} className={styles.cell} role="gridcell">
                {slot ? (
                  <PlanSlotCard
                    slot={slot}
                    editable={editable}
                    showOriginBadge={showOriginBadges}
                    onEdit={editable ? onEditSlot : undefined}
                    onRegenerate={editable ? onRegenerateSlot : undefined}
                  />
                ) : (
                  <div className={styles.emptyCell} />
                )}
              </div>
            );
          })}
        </Fragment>
      ))}
    </div>
  );
}
