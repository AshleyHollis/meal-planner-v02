from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GroceryDiagnosticFixture:
    client_mutation_id: str
    correlation_id: str


@dataclass(frozen=True)
class SyncDiagnosticFixture:
    client_mutation_id: str
    correlation_id: str
    device_timestamp: str
    base_server_version: int | None = None
    provisional_aggregate_id: str | None = None


DERIVATION_DIAGNOSTIC_FIXTURE = GroceryDiagnosticFixture(
    client_mutation_id="derive-diagnostics-001",
    correlation_id="derive-diagnostics-001",
)

STALE_DETECTION_FIXTURE = GroceryDiagnosticFixture(
    client_mutation_id="inventory-stale-diagnostics-001",
    correlation_id="inventory-stale-diagnostics-001",
)

CONFIRMATION_DIAGNOSTIC_FIXTURE = GroceryDiagnosticFixture(
    client_mutation_id="confirm-diagnostics-001",
    correlation_id="confirm-diagnostics-001",
)

SYNC_DUPLICATE_RETRY_FIXTURE = SyncDiagnosticFixture(
    client_mutation_id="sync-duplicate-retry-diagnostics-001",
    correlation_id="sync-duplicate-retry-diagnostics-001",
    device_timestamp="2026-03-09T14:00:00Z",
    base_server_version=1,
    provisional_aggregate_id="local-duplicate-water-001",
)

SYNC_AUTO_MERGE_FIXTURE = SyncDiagnosticFixture(
    client_mutation_id="sync-auto-merge-diagnostics-001",
    correlation_id="sync-auto-merge-diagnostics-001",
    device_timestamp="2026-03-09T14:05:00Z",
    base_server_version=1,
    provisional_aggregate_id="local-auto-merge-water-001",
)

SYNC_REVIEW_REQUIRED_FIXTURE = SyncDiagnosticFixture(
    client_mutation_id="sync-review-required-diagnostics-001",
    correlation_id="sync-review-required-diagnostics-001",
    device_timestamp="2026-03-09T14:10:00Z",
    base_server_version=1,
)

SYNC_KEEP_MINE_RESOLUTION_FIXTURE = GroceryDiagnosticFixture(
    client_mutation_id="sync-keep-mine-diagnostics-001",
    correlation_id="sync-keep-mine-diagnostics-001",
)

SYNC_USE_SERVER_RESOLUTION_FIXTURE = GroceryDiagnosticFixture(
    client_mutation_id="sync-use-server-diagnostics-001",
    correlation_id="sync-use-server-diagnostics-001",
)


def build_sync_add_ad_hoc_mutation(
    fixture: SyncDiagnosticFixture,
    *,
    household_id: str,
    actor_id: str,
    grocery_list_id: str,
    ingredient_name: str,
    shopping_quantity: str,
    unit: str,
    ad_hoc_note: str | None = None,
    aggregate_id: str | None = None,
    local_queue_status: str = "queued_offline",
) -> dict[str, Any]:
    return {
        "client_mutation_id": fixture.client_mutation_id,
        "household_id": household_id,
        "actor_id": actor_id,
        "aggregate_type": "grocery_list",
        "aggregate_id": aggregate_id or grocery_list_id,
        "provisional_aggregate_id": fixture.provisional_aggregate_id,
        "mutation_type": "add_ad_hoc",
        "payload": {
            "grocery_list_id": grocery_list_id,
            "ingredient_name": ingredient_name,
            "shopping_quantity": shopping_quantity,
            "unit": unit,
            **({"ad_hoc_note": ad_hoc_note} if ad_hoc_note is not None else {}),
        },
        "base_server_version": fixture.base_server_version,
        "device_timestamp": fixture.device_timestamp,
        "local_queue_status": local_queue_status,
    }


def build_sync_adjust_line_mutation(
    fixture: SyncDiagnosticFixture,
    *,
    household_id: str,
    actor_id: str,
    grocery_list_id: str,
    grocery_line_id: str,
    quantity_to_buy: str,
    user_adjustment_note: str | None = None,
    local_queue_status: str = "queued_offline",
) -> dict[str, Any]:
    return {
        "client_mutation_id": fixture.client_mutation_id,
        "household_id": household_id,
        "actor_id": actor_id,
        "aggregate_type": "grocery_line",
        "aggregate_id": grocery_line_id,
        "provisional_aggregate_id": fixture.provisional_aggregate_id,
        "mutation_type": "adjust_line",
        "payload": {
            "grocery_list_id": grocery_list_id,
            "quantity_to_buy": quantity_to_buy,
            **(
                {"user_adjustment_note": user_adjustment_note}
                if user_adjustment_note is not None
                else {}
            ),
        },
        "base_server_version": fixture.base_server_version,
        "device_timestamp": fixture.device_timestamp,
        "local_queue_status": local_queue_status,
    }


def build_sync_remove_line_mutation(
    fixture: SyncDiagnosticFixture,
    *,
    household_id: str,
    actor_id: str,
    grocery_list_id: str,
    grocery_line_id: str,
    local_queue_status: str = "queued_offline",
) -> dict[str, Any]:
    return {
        "client_mutation_id": fixture.client_mutation_id,
        "household_id": household_id,
        "actor_id": actor_id,
        "aggregate_type": "grocery_line",
        "aggregate_id": grocery_line_id,
        "provisional_aggregate_id": fixture.provisional_aggregate_id,
        "mutation_type": "remove_line",
        "payload": {
            "grocery_list_id": grocery_list_id,
        },
        "base_server_version": fixture.base_server_version,
        "device_timestamp": fixture.device_timestamp,
        "local_queue_status": local_queue_status,
    }
