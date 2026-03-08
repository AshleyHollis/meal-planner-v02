'use client';

import { Fragment } from 'react';
import type { PlanSlot } from '../../_lib/types';
import { PlanSlotCard } from './PlanSlotCard';
import styles from './WeeklyGrid.module.css';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const FULL_DAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const MEAL_TYPES = ['breakfast', 'lunch', 'dinner'] as const;

type Props = {
  plan: { slots: PlanSlot[] };
  editable?: boolean;
  showOriginBadges?: boolean;
  showSuggestionMeta?: boolean;
  onEditSlot?: (slotId: string) => void;
  onRegenerateSlot?: (slotId: string) => void;
};

export function WeeklyGrid({
  plan,
  editable = false,
  showOriginBadges = true,
  showSuggestionMeta = showOriginBadges,
  onEditSlot,
  onRegenerateSlot,
}: Props) {
  function slotFor(dayOfWeek: number, mealType: string) {
    return plan.slots.find(
      (slot) => slot.dayOfWeek === dayOfWeek && slot.mealType === mealType
    );
  }

  return (
    <>
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
                        showSuggestionMeta={showSuggestionMeta}
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

      <div className={styles.mobileSections} aria-label="Weekly meal plan by meal type">
        {MEAL_TYPES.map((mealType) => (
          <section key={`mobile-${mealType}`} className={styles.mobileSection}>
            <div className={styles.mobileSectionHeader}>
              <h3 className={styles.mobileSectionTitle}>
                {mealType.charAt(0).toUpperCase() + mealType.slice(1)}
              </h3>
              <span className={styles.mobileSectionHint}>Swipe to review each day</span>
            </div>
            <div className={styles.mobileScroller}>
              {DAY_LABELS.map((day, dayIdx) => {
                const slot = slotFor(dayIdx, mealType);
                return (
                  <div key={`mobile-${mealType}-${dayIdx}`} className={styles.mobileDay}>
                    <span className={styles.mobileDayLabel} aria-label={FULL_DAY_LABELS[dayIdx]}>
                      {day}
                    </span>
                    <div className={styles.mobileCard}>
                      {slot ? (
                        <PlanSlotCard
                          slot={slot}
                          editable={editable}
                          showOriginBadge={showOriginBadges}
                          showSuggestionMeta={showSuggestionMeta}
                          onEdit={editable ? onEditSlot : undefined}
                          onRegenerate={editable ? onRegenerateSlot : undefined}
                        />
                      ) : (
                        <div className={styles.emptyCell} />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
