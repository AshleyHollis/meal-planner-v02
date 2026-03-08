import type {
  FreshnessBasis,
  FreshnessInfo,
  InventoryAdjustment,
  InventoryItem,
  InventoryReasonCode,
  MutationType,
  StorageLocation,
} from './types';

const quantityFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 4,
});

export function toDateInputValue(value: string | null | undefined): string {
  if (!value) {
    return '';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.split('T')[0] ?? '';
  }

  return date.toISOString().split('T')[0] ?? '';
}

export function formatStorageLocation(location: StorageLocation): string {
  switch (location) {
    case 'pantry':
      return 'Pantry';
    case 'fridge':
      return 'Fridge';
    case 'freezer':
      return 'Freezer';
    case 'leftovers':
      return 'Leftovers';
    default:
      return location;
  }
}

export function formatMutationType(mutationType: MutationType): string {
  switch (mutationType) {
    case 'create_item':
      return 'Created item';
    case 'set_metadata':
      return 'Updated metadata';
    case 'increase_quantity':
      return 'Increased quantity';
    case 'decrease_quantity':
      return 'Decreased quantity';
    case 'set_quantity':
      return 'Set quantity';
    case 'move_location':
      return 'Moved location';
    case 'archive_item':
      return 'Archived item';
    case 'correction':
      return 'Applied correction';
    default:
      return mutationType;
  }
}

export function formatReasonCode(reasonCode: InventoryReasonCode): string {
  switch (reasonCode) {
    case 'manual_create':
      return 'Manual create';
    case 'manual_edit':
      return 'Manual edit';
    case 'manual_count_reset':
      return 'Manual count reset';
    case 'shopping_apply':
      return 'Shopping apply';
    case 'shopping_skip_or_reduce':
      return 'Shopping skip or reduce';
    case 'cooking_consume':
      return 'Cooking consume';
    case 'leftovers_create':
      return 'Leftovers create';
    case 'spoilage_or_discard':
      return 'Spoilage or discard';
    case 'location_move':
      return 'Location move';
    case 'correction':
      return 'Correction';
    case 'system_replay_duplicate':
      return 'Duplicate replay';
    default:
      return reasonCode;
  }
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return 'Unknown time';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function formatQuantity(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }

  return quantityFormatter.format(value);
}

export function formatSignedQuantity(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }

  const formatted = formatQuantity(Math.abs(value));
  if (value > 0) {
    return `+${formatted}`;
  }
  if (value < 0) {
    return `-${formatted}`;
  }
  return formatted;
}

export function formatQuantityWithUnit(
  value: number | null | undefined,
  unit: string | null | undefined
): string {
  const formatted = formatQuantity(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

export function formatFreshnessBasis(basis: FreshnessBasis): string {
  switch (basis) {
    case 'known':
      return 'Known freshness';
    case 'estimated':
      return 'Estimated freshness';
    case 'unknown':
      return 'Unknown freshness';
    default:
      return basis;
  }
}

export function describeFreshnessInfo(freshness: FreshnessInfo | null | undefined): string {
  const basis = freshness?.basis ?? 'unknown';
  const basisLabel = formatFreshnessBasis(basis);
  const bestBefore = toDateInputValue(freshness?.bestBefore);

  if (basis === 'known' && bestBefore) {
    return `${basisLabel} · ${bestBefore}`;
  }

  if (basis === 'estimated' && bestBefore) {
    return `${basisLabel} · ${bestBefore}`;
  }

  if (basis === 'estimated' && freshness?.estimatedNote) {
    return `${basisLabel} · ${freshness.estimatedNote}`;
  }

  return basisLabel;
}

export function describeItemFreshness(item: Pick<
  InventoryItem,
  'freshnessBasis' | 'expiryDate' | 'estimatedExpiryDate' | 'freshnessNote'
>): string {
  return describeFreshnessInfo({
    basis: item.freshnessBasis,
    bestBefore:
      item.freshnessBasis === 'known'
        ? item.expiryDate
        : item.freshnessBasis === 'estimated'
          ? item.estimatedExpiryDate
          : null,
    estimatedNote: item.freshnessBasis === 'estimated' ? item.freshnessNote : null,
  });
}

export function describeAdjustmentSummary(adjustment: InventoryAdjustment | null): string {
  if (!adjustment) {
    return 'No committed adjustments yet.';
  }

  const action = formatMutationType(adjustment.mutationType);
  const time = formatTimestamp(adjustment.createdAt);
  return `${action} · ${time}`;
}
