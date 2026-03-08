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

export type FallbackMode = 'none' | 'curated_fallback' | 'manual_guidance';

export type PlanSlotSuggestionSnapshot = {
  mealTitle: string | null;
  mealSummary: string | null;
  reasonCodes: string[];
  explanation: string | null;
  usesOnHand: string[];
  missingHints: string[];
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
  fallbackMode: FallbackMode | null;
  usesOnHand: string[];
  missingHints: string[];
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

export type GroceryLineOrigin = 'derived' | 'ad_hoc';

export type GroceryListStatus =
  | 'no_plan_confirmed'
  | 'deriving'
  | 'draft'
  | 'stale_draft'
  | 'confirming'
  | 'confirmed'
  | 'trip_in_progress'
  | 'trip_complete_pending_reconciliation';

export type GroceryTripState =
  | 'confirmed_list_ready'
  | 'trip_in_progress'
  | 'trip_complete_pending_reconciliation';

export type GroceryMealSource = {
  mealSlotId: string;
  mealName: string | null;
  contributedQuantity: number;
};

export type GroceryIncompleteSlotWarning = {
  mealSlotId: string;
  mealName: string | null;
  reason: string;
  message: string | null;
};

export type GroceryLine = {
  groceryLineId: string;
  groceryListId: string;
  groceryListVersionId: string;
  name: string;
  ingredientRefId: string | null;
  quantityNeeded: number;
  unit: string;
  quantityCoveredByInventory: number;
  quantityToBuy: number;
  origin: GroceryLineOrigin;
  mealSources: GroceryMealSource[];
  offsetInventoryItemId: string | null;
  offsetInventoryItemVersion: number | null;
  userAdjustedQuantity: number | null;
  userAdjustmentNote: string | null;
  userAdjustmentFlagged: boolean;
  adHocNote: string | null;
  active: boolean;
  createdAt: string;
  updatedAt: string;
};

export type GroceryList = {
  groceryListId: string;
  householdId: string;
  planPeriodStart: string;
  planPeriodEnd: string | null;
  lines: GroceryLine[];
  derivedFromPlanId: string | null;
  lastDerivedAt: string | null;
  confirmedAt: string | null;
  tripState: GroceryTripState;
  isStale: boolean;
  status: GroceryListStatus;
  currentVersionNumber: number;
  currentVersionId: string | null;
  confirmedPlanVersion: number | null;
  inventorySnapshotReference: string | null;
  incompleteSlotWarnings: GroceryIncompleteSlotWarning[];
};

// ─── Sync queue ──────────────────────────────────────────────────────────────

export type SyncAggregateType = 'grocery_list' | 'grocery_line' | 'inventory_item';

export type SyncAggregateRef = {
  aggregateType: SyncAggregateType;
  aggregateId: string;
  aggregateVersion: number | null;
  provisionalAggregateId: string | null;
};

export type QueueableSyncMutation = {
  clientMutationId: string;
  householdId: string;
  actorId: string;
  aggregateType: SyncAggregateType;
  aggregateId: string | null;
  provisionalAggregateId: string | null;
  mutationType: string;
  payload: Record<string, unknown>;
  baseServerVersion: number | null;
  deviceTimestamp: string;
  localQueueStatus: SyncStatus;
};

export type SyncOutcome =
  | 'applied'
  | 'duplicate_retry'
  | 'auto_merged_non_overlapping'
  | 'failed_retryable'
  | 'review_required_quantity'
  | 'review_required_deleted_or_archived'
  | 'review_required_freshness_or_location'
  | 'review_required_other_unsafe';

export type SyncResolutionAction = 'keep_mine' | 'use_server';

export type SyncResolutionStatus = 'pending' | 'resolved_keep_mine' | 'resolved_use_server';

export type SyncMutationOutcome = {
  clientMutationId: string;
  mutationType: string;
  aggregate: SyncAggregateRef;
  outcome: SyncOutcome;
  authoritativeServerVersion: number | null;
  conflictId: string | null;
  retryable: boolean;
  duplicateOfClientMutationId: string | null;
  autoMergeReason: string | null;
};

export type SyncConflictSummary = {
  conflictId: string;
  householdId: string;
  aggregate: SyncAggregateRef;
  localMutationId: string;
  mutationType: string;
  outcome: SyncOutcome;
  baseServerVersion: number | null;
  currentServerVersion: number;
  requiresReview: boolean;
  summary: string;
  localQueueStatus: SyncStatus;
  allowedResolutionActions: SyncResolutionAction[];
  resolutionStatus: SyncResolutionStatus;
  createdAt: string;
  resolvedAt: string | null;
  resolvedByActorId: string | null;
};

export type SyncConflictDetail = SyncConflictSummary & {
  localIntentSummary: Record<string, unknown>;
  baseStateSummary: Record<string, unknown>;
  serverStateSummary: Record<string, unknown>;
};

export type GroceryConfirmedListBootstrap = {
  householdId: string;
  groceryListId: string;
  groceryListVersionId: string;
  groceryListStatus: GroceryListStatus;
  tripState: GroceryTripState;
  aggregate: SyncAggregateRef;
  confirmedAt: string;
  confirmedPlanVersion: number | null;
  inventorySnapshotReference: string | null;
  incompleteSlotWarnings: GroceryIncompleteSlotWarning[];
  lines: GroceryLine[];
};

export type SyncConflictKeepMineCommand = {
  conflictId: string;
  householdId: string;
  clientMutationId: string;
  baseServerVersion: number | null;
};

export type SyncConflictUseServerCommand = {
  conflictId: string;
  householdId: string;
  clientMutationId: string;
};

export type SyncStatus =
  | 'idle'
  | 'queued_offline'
  | 'syncing'
  | 'synced'
  | 'retrying'
  | 'failed_retryable'
  | 'conflict'
  | 'review_required'
  | 'resolving'
  | 'resolved_keep_mine'
  | 'resolved_use_server'
  | 'error'
  | 'offline';

export type OfflineSyncScope = {
  householdId: string;
  groceryListId: string;
  groceryListVersionId: string;
  planPeriodStart: string;
  tripState: GroceryTripState;
  aggregate: SyncAggregateRef;
};

export type OfflineMealPlanContext = {
  snapshotKey: string;
  householdId: string;
  groceryListId: string;
  groceryListVersionId: string;
  planPeriodStart: string;
  planPeriodEnd: string | null;
  derivedFromPlanId: string | null;
  confirmedPlanVersion: number | null;
  savedAt: string;
};

export type OfflineInventorySnapshot = {
  snapshotKey: string;
  householdId: string;
  groceryListId: string;
  groceryListVersionId: string;
  inventorySnapshotReference: string | null;
  savedAt: string;
};

export type OfflineConfirmedListSnapshot = {
  snapshotKey: string;
  scope: OfflineSyncScope;
  savedAt: string;
  bootstrap: GroceryConfirmedListBootstrap;
  groceryList: GroceryList;
  mealPlanContext: OfflineMealPlanContext;
  inventorySnapshot: OfflineInventorySnapshot;
};

export type OfflineSyncMutationRecord = QueueableSyncMutation & {
  scope: OfflineSyncScope;
  snapshotKey: string;
  retryCount: number;
  lastAttemptAt: string | null;
  nextRetryAt: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
};

export type OfflineConflictRecord = {
  conflict: SyncConflictDetail;
  scope: OfflineSyncScope;
  snapshotKey: string;
  localMutation: OfflineSyncMutationRecord | null;
  storedAt: string;
  updatedAt: string;
};

export type OfflineQueueState = {
  queuedCount: number;
  retryingCount: number;
  failedRetryableCount: number;
  reviewRequiredCount: number;
  conflictCount: number;
  latestSnapshotSavedAt: string | null;
};
