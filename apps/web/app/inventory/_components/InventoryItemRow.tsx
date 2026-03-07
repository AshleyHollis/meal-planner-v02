'use client';

import type { InventoryItem } from '../../_lib/types';
import { describeItemFreshness, formatStorageLocation } from '../../_lib/inventory-trust';
import styles from './InventoryItemRow.module.css';

type Props = {
  item: InventoryItem;
  onArchive?: (item: InventoryItem) => void;
  onReview?: (item: InventoryItem) => void;
  isSelected?: boolean;
};

function freshnessClass(item: InventoryItem) {
  if (item.freshnessBasis === 'known') {
    if (item.expiryDate) {
      const days = Math.ceil((new Date(item.expiryDate).getTime() - Date.now()) / 86_400_000);
      if (days < 0) return styles.expired;
      if (days <= 3) return styles.expiringSoon;
    }
    return styles.known;
  }

  if (item.freshnessBasis === 'estimated') {
    return styles.estimated;
  }

  return styles.unknown;
}

export function InventoryItemRow({ item, onArchive, onReview, isSelected }: Props) {
  const freshnessLabel = describeItemFreshness(item);

  return (
    <li className={`${styles.row} ${isSelected ? styles.selected : ''}`}>
      <div className={styles.main}>
        <div className={styles.titleRow}>
          <span className={styles.name}>{item.name}</span>
          <span className={styles.version}>v{item.serverVersion}</span>
        </div>
        <span className={styles.qty}>
          {item.quantityOnHand} {item.primaryUnit}
        </span>
        <span className={styles.location}>{formatStorageLocation(item.storageLocation)}</span>
      </div>
      <div className={styles.meta}>
        <span className={`${styles.badge} ${freshnessClass(item)}`}>{freshnessLabel}</span>
        {onReview && (
          <button
            className={styles.reviewBtn}
            onClick={() => onReview(item)}
            aria-label={`${isSelected ? 'Hide' : 'Review'} trust details for ${item.name}`}
            type="button"
          >
            {isSelected ? 'Hide details' : 'Review details'}
          </button>
        )}
        {onArchive && (
          <button
            className={styles.archiveBtn}
            onClick={() => onArchive(item)}
            aria-label={`Archive ${item.name}`}
            type="button"
          >
            Archive
          </button>
        )}
      </div>
    </li>
  );
}
