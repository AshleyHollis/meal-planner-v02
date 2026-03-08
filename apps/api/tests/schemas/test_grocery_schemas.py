from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.grocery import (
    GroceryConfirmedListBootstrapRead,
    GroceryListConfirmCommand,
    GroceryListDeriveCommand,
    GroceryListItemAdHocCreate,
    GroceryListItemRead,
    GroceryListRead,
    GroceryListQuantityAdjustCommand,
    GroceryListRemoveLineCommand,
    GroceryMutationResult,
    GroceryListVersionRead,
    QueueableSyncMutation,
    SyncConflictDetailRead,
    SyncConflictKeepMineCommand,
    SyncConflictUseServerCommand,
    SyncMutationOutcomeRead,
)


def test_ad_hoc_item_create_valid():
    item = GroceryListItemAdHocCreate(
        grocery_list_id="gl-001",
        household_id="hh-001",
        ingredient_name="Sparkling Water",
        shopping_quantity=Decimal("2.0"),
        unit="liters",
        client_mutation_id="grocery-create-001",
    )
    assert item.ingredient_name == "Sparkling Water"
    assert item.shopping_quantity == Decimal("2.0")


def test_ad_hoc_item_create_accepts_legacy_quantity_alias():
    item = GroceryListItemAdHocCreate.model_validate(
        {
            "grocery_list_id": "gl-001",
            "household_id": "hh-001",
            "ingredient_name": "Sparkling Water",
            "quantity_needed": "2.0",
            "unit": "liters",
            "client_mutation_id": "grocery-create-legacy",
        }
    )

    assert item.shopping_quantity == Decimal("2.0")


def test_ad_hoc_item_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        GroceryListItemAdHocCreate(
            grocery_list_id="gl-001",
            household_id="hh-001",
            ingredient_name="Sparkling Water",
            shopping_quantity=Decimal("0.0"),
            unit="liters",
            client_mutation_id="grocery-create-002",
        )


def test_ad_hoc_item_rejects_empty_name():
    with pytest.raises(ValidationError):
        GroceryListItemAdHocCreate(
            grocery_list_id="gl-001",
            household_id="hh-001",
            ingredient_name="",
            shopping_quantity=Decimal("1.0"),
            unit="liters",
            client_mutation_id="grocery-create-003",
        )


def test_grocery_confirm_command_requires_idempotency_key():
    cmd = GroceryListConfirmCommand(
        grocery_list_id="gl-001",
        household_id="hh-001",
        client_mutation_id="grocery-confirm-001",
    )
    assert cmd.client_mutation_id == "grocery-confirm-001"


def test_grocery_quantity_adjust_command_captures_adjustment_note():
    cmd = GroceryListQuantityAdjustCommand(
        grocery_list_item_id="gli-001",
        household_id="hh-001",
        user_adjusted_quantity=Decimal("3.0"),
        user_adjustment_note="Need extra for guests",
        client_mutation_id="grocery-adjust-001",
    )
    assert cmd.user_adjustment_note == "Need extra for guests"


def test_grocery_remove_line_command_requires_idempotency_key():
    cmd = GroceryListRemoveLineCommand(
        grocery_list_item_id="gli-001",
        household_id="hh-001",
        client_mutation_id="grocery-remove-001",
    )
    assert cmd.client_mutation_id == "grocery-remove-001"


def test_grocery_derive_command_accepts_camel_case_payload():
    cmd = GroceryListDeriveCommand.model_validate(
        {
            "household_id": "hh-001",
            "planPeriodStart": "2025-01-06",
            "clientMutationId": "grocery-derive-001",
        }
    )

    assert str(cmd.plan_period_start) == "2025-01-06"
    assert cmd.client_mutation_id == "grocery-derive-001"


def test_grocery_list_item_read_parses_meal_sources_and_active_state():
    item = GroceryListItemRead.model_validate(
        {
            "id": "gli-001",
            "stable_line_id": "line-001",
            "grocery_list_id": "gl-001",
            "grocery_list_version_id": "glv-001",
            "ingredient_name": "Pasta",
            "required_quantity": "400.0",
            "unit": "grams",
            "offset_quantity": "100.0",
            "offset_inventory_item_id": "inv-001",
            "offset_inventory_item_version": 3,
            "shopping_quantity": "300.0",
            "origin": "derived",
            "meal_sources": '[{"meal_plan_slot_id": "slot-001", "meal_name": "Pasta Night", "quantity": "400.0"}]',
            "user_adjusted_quantity": None,
            "user_adjustment_note": None,
            "user_adjustment_flagged": False,
            "ad_hoc_note": None,
            "active": True,
            "removed_at": None,
            "created_client_mutation_id": None,
            "removed_client_mutation_id": None,
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:00:00Z",
        }
    )

    assert item.meal_sources[0].meal_slot_id == "slot-001"
    assert item.meal_sources[0].contributed_quantity == Decimal("400.0")
    assert item.grocery_line_id == "line-001"
    assert item.active is True


def test_grocery_list_version_read_parses_incomplete_slot_warnings():
    version = GroceryListVersionRead.model_validate(
        {
            "id": "glv-001",
            "grocery_list_id": "gl-001",
            "version_number": 2,
            "plan_period_reference": "2025-01-06/2025-01-12",
            "confirmed_plan_id": "plan-001",
            "derived_at": "2025-01-01T12:00:00Z",
            "confirmed_plan_version": 4,
            "inventory_snapshot_reference": "inventory-v7",
            "invalidated_at": None,
            "incomplete_slot_warnings": '[{"meal_plan_slot_id": "slot-007", "meal_name": "Friday Soup"}]',
        }
    )

    assert version.incomplete_slot_warnings[0].meal_slot_id == "slot-007"


def test_grocery_list_read_exposes_current_version_metadata():
    grocery_list = GroceryListRead.model_validate(
        {
            "id": "gl-001",
            "household_id": "hh-001",
            "meal_plan_id": "plan-001",
            "status": "draft",
            "current_version_number": 2,
            "current_version_id": "glv-002",
            "confirmed_at": None,
            "confirmation_client_mutation_id": None,
            "last_derived_at": "2025-01-01T12:00:00Z",
            "incomplete_slot_warnings": '[{"meal_plan_slot_id": "slot-009"}]',
            "created_at": "2025-01-01T12:00:00Z",
            "updated_at": "2025-01-01T12:05:00Z",
        }
    )

    assert grocery_list.grocery_list_version_id == "glv-002"
    assert grocery_list.current_version_id == "glv-002"
    assert grocery_list.incomplete_slot_warnings[0].meal_slot_id == "slot-009"
    assert grocery_list.trip_state == "confirmed_list_ready"


def test_queueable_sync_mutation_captures_offline_metadata():
    mutation = QueueableSyncMutation.model_validate(
        {
            "client_mutation_id": "offline-001",
            "household_id": "hh-001",
            "actor_id": "user-001",
            "aggregate_type": "grocery_line",
            "aggregate_id": "line-123",
            "mutation_type": "adjust_quantity",
            "payload": {"quantity_to_buy": "3.0"},
            "base_server_version": 4,
            "device_timestamp": "2025-01-01T12:00:00Z",
            "local_queue_status": "queued_offline",
        }
    )

    assert mutation.aggregate_type == "grocery_line"
    assert mutation.aggregate_id == "line-123"
    assert mutation.base_server_version == 4


def test_confirmed_list_bootstrap_read_locks_confirmed_snapshot_contract():
    bootstrap = GroceryConfirmedListBootstrapRead.model_validate(
        {
            "household_id": "hh-001",
            "grocery_list_id": "gl-001",
            "grocery_list_version_id": "glv-002",
            "status": "confirmed",
            "trip_state": "confirmed_list_ready",
            "aggregate": {
                "aggregate_type": "grocery_list",
                "aggregate_id": "gl-001",
                "aggregate_version": 2,
            },
            "confirmed_at": "2025-01-01T12:00:00Z",
            "confirmed_plan_version": 4,
            "inventory_snapshot_reference": "inventory-v7",
            "incomplete_slot_warnings": '[{"meal_plan_slot_id": "slot-009"}]',
            "lines": [
                {
                    "id": "gli-001",
                    "grocery_line_id": "line-001",
                    "grocery_list_id": "gl-001",
                    "grocery_list_version_id": "glv-002",
                    "ingredient_name": "Milk",
                    "required_quantity": "2.0",
                    "unit": "liters",
                    "offset_quantity": "0",
                    "shopping_quantity": "2.0",
                    "origin": "ad_hoc",
                    "meal_sources": [],
                    "user_adjustment_flagged": False,
                    "active": True,
                    "created_at": "2025-01-01T12:00:00Z",
                    "updated_at": "2025-01-01T12:00:00Z",
                }
            ],
        }
    )

    assert bootstrap.grocery_list_status == "confirmed"
    assert bootstrap.trip_state == "confirmed_list_ready"
    assert bootstrap.aggregate.aggregate_version == 2
    assert bootstrap.incomplete_slot_warnings[0].meal_slot_id == "slot-009"


def test_sync_mutation_outcome_read_supports_duplicate_and_conflict_metadata():
    outcome = SyncMutationOutcomeRead.model_validate(
        {
            "client_mutation_id": "offline-001",
            "mutation_type": "adjust_quantity",
            "aggregate": {
                "aggregate_type": "grocery_line",
                "aggregate_id": "line-123",
                "current_server_version": 7,
            },
            "outcome": "duplicate_retry",
            "authoritative_server_version": 7,
            "duplicate_of_client_mutation_id": "offline-000",
        }
    )

    assert outcome.aggregate.aggregate_version == 7
    assert outcome.outcome == "duplicate_retry"
    assert outcome.duplicate_of_client_mutation_id == "offline-000"


def test_sync_conflict_detail_read_exposes_resolution_actions_and_state_summaries():
    detail = SyncConflictDetailRead.model_validate(
        {
            "conflict_id": "conflict-001",
            "household_id": "hh-001",
            "aggregate": {
                "aggregate_type": "grocery_line",
                "aggregate_id": "line-123",
                "aggregate_version": 8,
            },
            "local_mutation_id": "offline-001",
            "mutation_type": "adjust_quantity",
            "outcome": "review_required_quantity",
            "base_server_version": 6,
            "current_server_version": 8,
            "requires_review": True,
            "summary": "Quantity changed on both devices.",
            "allowed_resolution_actions": ["keep_mine", "use_server"],
            "resolution_status": "pending",
            "created_at": "2025-01-01T12:00:00Z",
            "local_intent_summary": {"quantity_to_buy": "3.0"},
            "base_state_summary": {"quantity_to_buy": "2.0"},
            "server_state_summary": {"quantity_to_buy": "4.0"},
        }
    )

    assert detail.allowed_resolution_actions == ["keep_mine", "use_server"]
    assert detail.server_state_summary["quantity_to_buy"] == "4.0"


def test_sync_conflict_resolution_commands_accept_camel_case_payloads():
    keep_mine = SyncConflictKeepMineCommand.model_validate(
        {
            "conflictId": "conflict-001",
            "household_id": "hh-001",
            "clientMutationId": "resolve-keep-001",
            "baseServerVersion": 8,
        }
    )
    use_server = SyncConflictUseServerCommand.model_validate(
        {
            "conflictId": "conflict-001",
            "household_id": "hh-001",
            "clientMutationId": "resolve-server-001",
        }
    )

    assert keep_mine.base_server_version == 8
    assert use_server.client_mutation_id == "resolve-server-001"


def test_grocery_mutation_result_wraps_updated_list_and_item():
    result = GroceryMutationResult.model_validate(
        {
            "mutation_kind": "add_ad_hoc",
            "grocery_list": {
                "id": "gl-001",
                "household_id": "hh-001",
                "meal_plan_id": "plan-001",
                "status": "draft",
                "current_version_number": 2,
                "current_version_id": "glv-002",
                "confirmed_at": None,
                "confirmation_client_mutation_id": None,
                "last_derived_at": "2025-01-01T12:00:00Z",
                "plan_period_start": "2025-01-06",
                "plan_period_end": "2025-01-12",
                "confirmed_plan_version": 4,
                "inventory_snapshot_reference": "inventory-v7",
                "is_stale": False,
                "incomplete_slot_warnings": [],
                "lines": [],
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:05:00Z",
            },
            "item": {
                "id": "gli-099",
                "grocery_line_id": "line-099",
                "grocery_list_id": "gl-001",
                "grocery_list_version_id": "glv-002",
                "ingredient_name": "Sparkling Water",
                "required_quantity": "2.0",
                "unit": "liters",
                "offset_quantity": "0.0",
                "shopping_quantity": "2.0",
                "origin": "ad_hoc",
                "meal_sources": [],
                "user_adjusted_quantity": None,
                "user_adjustment_note": None,
                "user_adjustment_flagged": False,
                "ad_hoc_note": "Party drinks",
                "active": True,
                "removed_at": None,
                "created_client_mutation_id": "mut-001",
                "removed_client_mutation_id": None,
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:05:00Z",
            },
            "is_duplicate": False,
        }
    )

    assert isinstance(result.grocery_list, GroceryListRead)
    assert result.item is not None
    assert result.item.grocery_line_id == "line-099"
    assert result.item.ingredient_name == "Sparkling Water"
