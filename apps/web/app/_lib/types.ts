// Domain types for the meal planner web client.
// The API remains authoritative; these shapes normalize backend contracts for UI use.

// ─── Session ─────────────────────────────────────────────────────────────────

export type HouseholdRole = 'owner' | 'member';

export type HouseholdMembership = {
  householdId: string;
  householdName: string;
  role: HouseholdRole;
};

export type SessionUser = {
  userId: string;
  email: string;
  displayName: string;
  activeHouseholdId: string;
  activeHouseholdName: string | null;
  activeHouseholdRole: HouseholdRole | null;
  householdId: string;
  householdName: string | null;
  role: HouseholdRole | null;
  households: HouseholdMembership[];
};

export type SessionResponse = {
  authenticated: boolean;
  user: SessionUser | null;
};

export type SessionState =
  | { status: 'loading' }
  | { status: 'retrying' }
  | { status: 'authenticated'; user: SessionUser }
  | { status: 'unauthenticated'; message: string }
  | { status: 'unauthorized'; message: string }
  | { status: 'error'; message: string };

// ─── Inventory ───────────────────────────────────────────────────────────────

export type StorageLocation = 'pantry' | 'fridge' | 'freezer' | 'leftovers';

export type FreshnessBasis = 'known' | 'estimated' | 'unknown';

export type FreshnessInfo = {
  basis: FreshnessBasis;
  bestBefore: string | null;
  estimatedNote: string | null;
};

export type InventoryReasonCode =
  | 'manual_create'
  | 'manual_edit'
  | 'manual_count_reset'
  | 'shopping_apply'
  | 'shopping_skip_or_reduce'
  | 'cooking_consume'
  | 'leftovers_create'
  | 'spoilage_or_discard'
  | 'location_move'
  | 'correction'
  | 'system_replay_duplicate';

export type InventoryItem = {
  inventoryItemId: string;
  householdId: string;
  name: string;
  storageLocation: StorageLocation;
  quantityOnHand: number;
  primaryUnit: string;
  freshnessBasis: FreshnessBasis;
  expiryDate: string | null;
  estimatedExpiryDate: string | null;
  freshnessNote: string | null;
  freshnessUpdatedAt: string | null;
  isActive: boolean;
  serverVersion: number;
  updatedAt: string;
};

export type InventoryQuantityTransition = {
  before: number | null;
  after: number | null;
  delta: number | null;
  unit: string | null;
  changed: boolean;
};

export type InventoryLocationTransition = {
  before: StorageLocation | null;
  after: StorageLocation | null;
  changed: boolean;
};

export type InventoryFreshnessTransition = {
  before: FreshnessInfo | null;
  after: FreshnessInfo | null;
  changed: boolean;
};

export type InventoryWorkflowReference = {
  correlationId: string | null;
  causalWorkflowId: string | null;
  causalWorkflowType: string | null;
};

export type InventoryCorrectionLinks = {
  correctsAdjustmentId: string | null;
  correctedByAdjustmentIds: string[];
  isCorrection: boolean;
  isCorrected: boolean;
};

export type InventoryAdjustment = {
  inventoryAdjustmentId: string;
  inventoryItemId: string;
  householdId: string;
  mutationType: MutationType;
  deltaQuantity: number | null;
  quantityBefore: number | null;
  quantityAfter: number | null;
  storageLocationBefore: StorageLocation | null;
  storageLocationAfter: StorageLocation | null;
  freshnessBefore: FreshnessInfo | null;
  freshnessAfter: FreshnessInfo | null;
  reasonCode: InventoryReasonCode;
  actorUserId: string;
  correlationId: string | null;
  clientMutationId: string | null;
  causalWorkflowId: string | null;
  causalWorkflowType: string | null;
  correctsAdjustmentId: string | null;
  note: string | null;
  createdAt: string;
  primaryUnit: string | null;
  quantityTransition: InventoryQuantityTransition | null;
  locationTransition: InventoryLocationTransition | null;
  freshnessTransition: InventoryFreshnessTransition | null;
  workflowReference: InventoryWorkflowReference | null;
  correctionLinks: InventoryCorrectionLinks;
};

export type InventoryHistorySummary = {
  committedAdjustmentCount: number;
  correctionCount: number;
  latestAdjustmentId: string | null;
  latestMutationType: MutationType | null;
  latestActorUserId: string | null;
  latestCreatedAt: string | null;
};

export type InventoryHistoryPage = {
  entries: InventoryAdjustment[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  summary: InventoryHistorySummary;
};

export type InventoryItemDetail = InventoryItem & {
  historySummary: InventoryHistorySummary | null;
  latestAdjustment: InventoryAdjustment | null;
};

export type MutationType =
  | 'create_item'
  | 'set_metadata'
  | 'increase_quantity'
  | 'decrease_quantity'
  | 'set_quantity'
  | 'move_location'
  | 'archive_item'
  | 'correction';

export type InventoryMutationRequest = {
  clientMutationId: string;
  mutationType: MutationType;
  inventoryItemId?: string;
  lastKnownVersion?: number;
  payload: Record<string, unknown>;
};

export type MutationReceipt = {
  clientMutationId: string;
  inventoryAdjustmentId: string;
  inventoryItemId: string;
  mutationType: MutationType;
  quantityAfter: number | null;
  versionAfter: number;
  isDuplicate: boolean;
  message?: string;
};

export type InventoryConflictDetail = {
  code: 'stale_inventory_version';
  message: string;
  expectedVersion?: number;
  currentVersion?: number;
};

// ─── Planner ─────────────────────────────────────────────────────────────────

export type PlanSlotOrigin = 'ai_suggested' | 'user_edited' | 'manually_added';

export type PlanSlotState =
  | 'idle'
  | 'pending_regen'
  | 'regenerating'
  | 'regen_failed';

export type PlanSlotSuggestionSnapshot = {
  mealTitle: string | null;
  mealSummary: string | null;
  reasonCodes: string[];
  explanation: string | null;
};

export type PlanSlot = {
  slotId: string;
  dayOfWeek: number;
  mealType: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  mealTitle: string | null;
  mealSummary: string | null;
  origin: PlanSlotOrigin;
  reasonCodes: string[];
  explanation: string | null;
  slotState: PlanSlotState;
  originalSuggestion: PlanSlotSuggestionSnapshot | null;
  slotMessage: string | null;
};

export type DraftPlan = {
  draftId: string;
  householdId: string;
  planPeriodStart: string;
  slots: PlanSlot[];
  staleWarning: boolean;
  staleWarningAcknowledged: boolean;
  createdAt: string;
  updatedAt: string;
  suggestionRequestId: string | null;
};

export type AISuggestionStatus =
  | 'idle'
  | 'generating'
  | 'ready'
  | 'fallback_used'
  | 'insufficient_context'
  | 'failed';

export type FallbackMode = 'none' | 'curated_fallback' | 'manual_guidance';

export type AISuggestionResult = {
  suggestionId: string;
  requestId: string | null;
  householdId: string;
  planPeriodStart: string;
  status: AISuggestionStatus;
  slots: PlanSlot[];
  isStale: boolean;
  fallbackMode: FallbackMode;
  createdAt: string;
};

export type ConfirmedPlan = {
  planId: string;
  householdId: string;
  planPeriodStart: string;
  slots: PlanSlot[];
  confirmedAt: string;
  aiSuggestionRequestId: string | null;
  staleWarningAcknowledged: boolean;
};

// ─── Grocery ─────────────────────────────────────────────────────────────────

export type GroceryLineOrigin = 'meal_derived' | 'ad_hoc';

export type GroceryListStatus = 'deriving' | 'current' | 'shopping' | 'completed';

export type GroceryReviewState = 'draft' | 'confirmed';

export type GroceryLine = {
  groceryLineId: string;
  groceryListId: string;
  name: string;
  quantityNeeded: number;
  unit: string;
  quantityCoveredByInventory: number;
  quantityToBuy: number;
  origin: GroceryLineOrigin;
  sourceMealIds: string[];
  sourceMeals: string[];
  checked: boolean;
  offsetInventoryItemId: string | null;
  userAdjustedQuantity: number | null;
  userAdjustmentFlagged: boolean;
};

export type GroceryList = {
  groceryListId: string;
  householdId: string;
  planPeriodStart: string;
  lines: GroceryLine[];
  derivedFromPlanId: string | null;
  lastDerivedAt: string | null;
  isStale: boolean;
  status: GroceryListStatus;
  reviewState: GroceryReviewState;
  currentVersionNumber: number;
};

// ─── Sync queue ──────────────────────────────────────────────────────────────

export type SyncStatus =
  | 'idle'
  | 'syncing'
  | 'conflict'
  | 'error'
  | 'offline';
