from enum import Enum


class StorageLocation(str, Enum):
    pantry = "pantry"
    fridge = "fridge"
    freezer = "freezer"
    leftovers = "leftovers"


class FreshnessBasis(str, Enum):
    known = "known"
    estimated = "estimated"
    unknown = "unknown"


class MutationType(str, Enum):
    create_item = "create_item"
    set_metadata = "set_metadata"
    increase_quantity = "increase_quantity"
    decrease_quantity = "decrease_quantity"
    set_quantity = "set_quantity"
    move_location = "move_location"
    archive_item = "archive_item"
    correction = "correction"


class ReasonCode(str, Enum):
    manual_create = "manual_create"
    manual_edit = "manual_edit"
    manual_count_reset = "manual_count_reset"
    shopping_apply = "shopping_apply"
    shopping_skip_or_reduce = "shopping_skip_or_reduce"
    cooking_consume = "cooking_consume"
    leftovers_create = "leftovers_create"
    spoilage_or_discard = "spoilage_or_discard"
    location_move = "location_move"
    correction = "correction"
    system_replay_duplicate = "system_replay_duplicate"


class MealPlanStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"


class SlotOrigin(str, Enum):
    ai_suggested = "ai_suggested"
    user_edited = "user_edited"
    manually_added = "manually_added"


class PlanSlotRegenStatus(str, Enum):
    idle = "idle"
    pending_regen = "pending_regen"
    regenerating = "regenerating"
    regen_failed = "regen_failed"


class GroceryListStatus(str, Enum):
    no_plan_confirmed = "no_plan_confirmed"
    deriving = "deriving"
    draft = "draft"
    stale_draft = "stale_draft"
    confirming = "confirming"
    confirmed = "confirmed"
    trip_in_progress = "trip_in_progress"
    trip_complete_pending_reconciliation = "trip_complete_pending_reconciliation"


class GroceryItemOrigin(str, Enum):
    derived = "derived"
    ad_hoc = "ad_hoc"


class ReconciliationStatus(str, Enum):
    ready_for_review = "ready_for_review"
    review_draft = "review_draft"
    apply_pending_online = "apply_pending_online"
    applying = "applying"
    applied = "applied"
    apply_failed_retryable = "apply_failed_retryable"
    apply_failed_review_required = "apply_failed_review_required"
    corrected_later = "corrected_later"


class ShoppingOutcome(str, Enum):
    bought = "bought"
    bought_adjusted = "bought_adjusted"
    skipped = "skipped"
    not_purchased = "not_purchased"
    ad_hoc = "ad_hoc"


class CookingEventStatus(str, Enum):
    cooking_draft = "cooking_draft"
    ready_to_apply = "ready_to_apply"
    apply_pending_online = "apply_pending_online"
    applying = "applying"
    applied = "applied"
    apply_failed_retryable = "apply_failed_retryable"
    apply_failed_review_required = "apply_failed_review_required"
    corrected_later = "corrected_later"


class CookingOutcome(str, Enum):
    used = "used"
    used_adjusted = "used_adjusted"
    skipped = "skipped"
    substitute = "substitute"


class AISuggestionStatus(str, Enum):
    queued = "queued"
    pending = "pending"
    generating = "generating"
    completed = "completed"
    completed_with_fallback = "completed_with_fallback"
    failed = "failed"
    stale = "stale"
    superseded = "superseded"
    expired = "expired"
