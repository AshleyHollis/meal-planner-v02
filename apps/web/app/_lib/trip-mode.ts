import { getActiveLines, hasQuantityOverride } from './grocery-ui';
import type { GroceryLine, GroceryList } from './types';

export type TripProgressSummary = {
  totalLineCount: number;
  remainingLineCount: number;
  completedLineCount: number;
  adHocLineCount: number;
  adjustedLineCount: number;
};

function nextTripStatus(list: GroceryList): GroceryList['status'] {
  return list.status === 'confirmed' ? 'trip_in_progress' : list.status;
}

export function getTripProgressSummary(list: GroceryList): TripProgressSummary {
  const totalLineCount = list.lines.length;
  const remainingLineCount = getActiveLines(list).length;
  const completedLineCount = Math.max(totalLineCount - remainingLineCount, 0);
  const adHocLineCount = list.lines.filter((line) => line.origin === 'ad_hoc' && line.active).length;
  const adjustedLineCount = list.lines.filter((line) => line.active && hasQuantityOverride(line)).length;

  return {
    totalLineCount,
    remainingLineCount,
    completedLineCount,
    adHocLineCount,
    adjustedLineCount,
  };
}

export function applyOptimisticTripQuantity(
  list: GroceryList,
  groceryLineId: string,
  quantity: number,
  note?: string,
  updatedAt = new Date().toISOString()
): GroceryList {
  return {
    ...list,
    status: nextTripStatus(list),
    tripState: 'trip_in_progress',
    lines: list.lines.map((line) =>
      line.groceryLineId === groceryLineId
        ? {
            ...line,
            userAdjustedQuantity: quantity,
            userAdjustmentNote: note?.trim() ? note.trim() : line.userAdjustmentNote,
            userAdjustmentFlagged: quantity !== line.quantityToBuy,
            updatedAt,
          }
        : line
    ),
  };
}

export function applyOptimisticTripCompletion(
  list: GroceryList,
  groceryLineId: string,
  updatedAt = new Date().toISOString()
): GroceryList {
  return {
    ...list,
    status: nextTripStatus(list),
    tripState: 'trip_in_progress',
    lines: list.lines.map((line) =>
      line.groceryLineId === groceryLineId
        ? {
            ...line,
            active: false,
            updatedAt,
          }
        : line
    ),
  };
}

export function applyOptimisticTripAdHocLine(
  list: GroceryList,
  input: {
    provisionalLineId: string;
    name: string;
    quantity: number;
    unit: string;
    note?: string;
  },
  updatedAt = new Date().toISOString()
): GroceryList {
  const nextLine: GroceryLine = {
    groceryLineId: input.provisionalLineId,
    groceryListId: list.groceryListId,
    groceryListVersionId: list.currentVersionId ?? 'local-trip-version',
    name: input.name,
    ingredientRefId: null,
    quantityNeeded: input.quantity,
    unit: input.unit,
    quantityCoveredByInventory: 0,
    quantityToBuy: input.quantity,
    origin: 'ad_hoc',
    mealSources: [],
    offsetInventoryItemId: null,
    offsetInventoryItemVersion: null,
    userAdjustedQuantity: null,
    userAdjustmentNote: null,
    userAdjustmentFlagged: false,
    adHocNote: input.note?.trim() ? input.note.trim() : null,
    active: true,
    createdAt: updatedAt,
    updatedAt,
  };

  return {
    ...list,
    status: nextTripStatus(list),
    tripState: 'trip_in_progress',
    lines: [...list.lines, nextLine],
  };
}
