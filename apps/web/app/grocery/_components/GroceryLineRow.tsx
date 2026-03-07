'use client';

import type { GroceryLine } from '../../_lib/types';
import styles from './GroceryLineRow.module.css';

type Props = {
  line: GroceryLine;
  onToggle?: (id: string, checked: boolean) => void;
};

export function GroceryLineRow({ line, onToggle }: Props) {
  return (
    <li className={`${styles.row} ${line.checked ? styles.checked : ''}`}>
      <label className={styles.label}>
        <input
          type="checkbox"
          className={styles.checkbox}
          checked={line.checked}
          onChange={(e) => onToggle?.(line.groceryLineId, e.target.checked)}
          aria-label={`${line.name} — ${line.quantityToBuy} ${line.unit}`}
        />
        <div className={styles.textColumn}>
          <span className={styles.name}>{line.name}</span>
          {line.sourceMeals.length > 0 && (
            <span className={styles.trace}>From {line.sourceMeals.join(', ')}</span>
          )}
          {line.userAdjustmentFlagged && (
            <span className={styles.flagged}>Review override — derived quantity changed.</span>
          )}
        </div>
      </label>

      <div className={styles.right}>
        <span className={styles.qty}>
          {line.quantityToBuy} {line.unit}
        </span>
        {line.origin === 'meal_derived' && line.sourceMealIds.length > 0 && (
          <span className={styles.source} title={`From ${line.sourceMealIds.length} meal(s)`}>
            🍽️ {line.sourceMealIds.length}
          </span>
        )}
        {line.origin === 'ad_hoc' && <span className={styles.adHoc}>Ad hoc</span>}
        {line.quantityCoveredByInventory > 0 && (
          <span className={styles.covered} title="Partially covered by inventory">
            −{line.quantityCoveredByInventory} {line.unit} on hand
          </span>
        )}
        {line.offsetInventoryItemId && (
          <span className={styles.offset}>Linked to inventory</span>
        )}
      </div>
    </li>
  );
}
