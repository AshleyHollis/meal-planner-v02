from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import app.models  # noqa: F401
from sqlalchemy import URL, Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.ai_planning import AISuggestionRequest, AISuggestionResult, AISuggestionSlot
from app.models.base import Base
from app.models.grocery import GroceryList, GroceryListItem, GroceryListVersion, GroceryMutationReceipt, GrocerySyncConflict
from app.models.household import Household, HouseholdMembership
from app.models.inventory import InventoryAdjustment, InventoryItem, MutationReceipt
from app.models.meal_plan import MealPlan, MealPlanSlot, MealPlanSlotHistory

REVIEWER_USER_ID = "reviewer-user-001"
REVIEWER_USER_EMAIL = "reviewer@example.com"
REVIEWER_USER_NAME = "Riley Reviewer"
REVIEWER_MEMBER_ID = "11111111-1111-1111-1111-111111111101"
REVIEWER_HOUSEHOLD_ID = "11111111-1111-1111-1111-111111111111"
REVIEWER_HOUSEHOLD_NAME = "Riley & Sam Household"
REVIEWER_COLLABORATOR_ID = "reviewer-user-002"
REVIEWER_COLLABORATOR_EMAIL = "sam.reviewer@example.com"
REVIEWER_COLLABORATOR_NAME = "Sam Reviewer"
REVIEWER_COLLABORATOR_MEMBER_ID = "11111111-1111-1111-1111-111111111102"
SECONDARY_HOUSEHOLD_ID = "22222222-2222-2222-2222-222222222222"
SECONDARY_HOUSEHOLD_NAME = "Cabin Pantry"
SECONDARY_MEMBER_ID = "22222222-2222-2222-2222-222222222201"
REVIEWER_PLAN_ID = "33333333-3333-3333-3333-333333333333"
REVIEWER_PLAN_PERIOD_START = date(2026, 3, 9)
REVIEWER_PLAN_PERIOD_END = REVIEWER_PLAN_PERIOD_START + timedelta(days=6)
REVIEWER_GROCERY_LIST_ID = "44444444-4444-4444-4444-444444444444"
REVIEWER_GROCERY_VERSION_ID = "44444444-4444-4444-4444-444444444445"
REVIEWER_AI_REQUEST_ID = "55555555-5555-5555-5555-555555555555"
REVIEWER_AI_RESULT_ID = "55555555-5555-5555-5555-555555555556"

SUPPORTED_SCENARIOS = ("sync-conflict-review", "trip-in-progress")
SUPPORTED_ENVIRONMENTS = ("local", "preview", "test")

_SEED_CREATED_AT = datetime(2026, 3, 9, 8, 0, 0)
_PLAN_CONFIRMED_AT = datetime(2026, 3, 9, 8, 45, 0)
_GROCERY_CONFIRMED_AT = datetime(2026, 3, 9, 9, 15, 0)
_SYNC_CONFLICT_AT = datetime(2026, 3, 9, 10, 0, 0)
_ZERO = Decimal("0.0000")


@dataclass(frozen=True)
class ReviewerSeedSummary:
    database_url: str
    household_id: str
    secondary_household_id: str
    confirmed_plan_id: str
    grocery_list_id: str
    grocery_list_version_id: str
    scenario_names: tuple[str, ...]
    inventory_item_ids: dict[str, str]
    dev_env: dict[str, str]


@dataclass(frozen=True)
class SeedBootstrapResult:
    dataset: str
    environment: str
    scenario: str
    period_start: date
    inventory_items: int
    confirmed_plan_slots: int
    grocery_lines: int


@dataclass(frozen=True)
class SeedDatasetResult:
    dataset: str
    environment: str
    scenario: str
    period_start: date
    inventory_items: int
    confirmed_plan_slots: int
    grocery_lines: int


class SeedSafetyError(RuntimeError):
    """Raised when reviewer seed data is requested for an unsafe environment."""


@dataclass(frozen=True)
class _InventorySeed:
    key: str
    item_id: str
    name: str
    storage_location: str
    quantity_on_hand: Decimal
    primary_unit: str
    freshness_basis: str
    expiry_date: date | None = None
    estimated_expiry_date: date | None = None
    freshness_note: str | None = None
    version: int = 1
    created_at: datetime = _SEED_CREATED_AT
    updated_at: datetime = _SEED_CREATED_AT
    freshness_updated_at: datetime | None = None
    adjustments: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class _PlannerSlotSeed:
    slot_id: str
    slot_key: str
    day_of_week: int
    meal_type: str
    meal_title: str
    meal_summary: str
    meal_reference_id: str | None
    slot_origin: str
    is_user_locked: bool = False
    reason_codes: tuple[str, ...] = ()
    explanation_entries: tuple[str, ...] = ()
    uses_on_hand: tuple[str, ...] = ()
    missing_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class _GroceryLineSeed:
    item_id: str
    stable_line_id: str
    ingredient_name: str
    required_quantity: Decimal
    unit: str
    offset_quantity: Decimal
    shopping_quantity: Decimal
    origin: str
    meal_sources: tuple[dict[str, object], ...]
    ingredient_ref_id: str | None = None
    offset_inventory_key: str | None = None
    user_adjusted_quantity: Decimal | None = None
    user_adjustment_note: str | None = None
    user_adjustment_flagged: bool = False
    ad_hoc_note: str | None = None
    created_client_mutation_id: str | None = None


def default_database_url() -> URL:
    build_dir = Path(__file__).resolve().parents[2] / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    return URL.create("sqlite+pysqlite", database=str((build_dir / "inventory.sqlite").resolve()))


def seed_reviewer_data(
    *,
    database_url: str | URL | None = None,
    scenario_names: Iterable[str] = (),
    reset: bool = True,
    environment: str | None = None,
) -> ReviewerSeedSummary:
    if environment is not None:
        validate_seed_environment(environment)
    normalized_scenarios = tuple(sorted(dict.fromkeys(scenario_names)))
    unsupported = sorted(set(normalized_scenarios) - set(SUPPORTED_SCENARIOS))
    if unsupported:
        raise ValueError(f"Unsupported reviewer seed scenario(s): {', '.join(unsupported)}")

    db_url = database_url or default_database_url()
    engine = _create_engine(db_url)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with session_factory.begin() as session:
            _seed_households(session)
            inventory_by_key = _seed_inventory(session)
            _seed_planner(session)
            grocery_version_id = _seed_grocery(session, inventory_by_key)
            if "trip-in-progress" in normalized_scenarios:
                grocery_version_id = _apply_trip_in_progress(session)
            if "sync-conflict-review" in normalized_scenarios:
                grocery_version_id = _apply_sync_conflict_review(session, inventory_by_key)
    finally:
        engine.dispose()

    return ReviewerSeedSummary(
        database_url=str(db_url),
        household_id=REVIEWER_HOUSEHOLD_ID,
        secondary_household_id=SECONDARY_HOUSEHOLD_ID,
        confirmed_plan_id=REVIEWER_PLAN_ID,
        grocery_list_id=REVIEWER_GROCERY_LIST_ID,
        grocery_list_version_id=grocery_version_id,
        scenario_names=normalized_scenarios,
        inventory_item_ids={seed.key: seed.item_id for seed in _inventory_seeds()},
        dev_env=_dev_env(),
    )


def format_seed_summary(summary: ReviewerSeedSummary) -> str:
    scenario_label = ", ".join(summary.scenario_names) if summary.scenario_names else "baseline only"
    lines = [
        f"Seeded reviewer dataset into {summary.database_url}",
        f"- Household: {summary.household_id} ({REVIEWER_HOUSEHOLD_NAME})",
        f"- Confirmed plan: {summary.confirmed_plan_id} for {REVIEWER_PLAN_PERIOD_START.isoformat()}",
        f"- Grocery snapshot: {summary.grocery_list_id} @ {summary.grocery_list_version_id}",
        f"- Scenarios: {scenario_label}",
        "- Suggested web dev env:",
    ]
    lines.extend(f"  {key}={value}" for key, value in summary.dev_env.items())
    return "\n".join(lines)


def current_smoke_week() -> date:
    return REVIEWER_PLAN_PERIOD_START


def seed_dataset(
    *,
    environment: str,
    scenario: str = "baseline",
    reset: bool = True,
    database_url: str | URL | None = None,
) -> SeedDatasetResult:
    normalized_environment = validate_seed_environment(environment)

    seed_reviewer_data(
        database_url=database_url,
        scenario_names=_scenario_names_from_label(scenario),
        reset=reset,
    )
    return SeedDatasetResult(
        dataset="reviewer-baseline",
        environment=normalized_environment,
        scenario=scenario,
        period_start=REVIEWER_PLAN_PERIOD_START,
        inventory_items=len(_inventory_seeds()),
        confirmed_plan_slots=len(_planner_slots()),
        grocery_lines=len(_grocery_line_seeds()),
    )


def bootstrap_from_environment(database_url: str | URL | None = None) -> SeedBootstrapResult | None:
    config = _bootstrap_config_from_environment()
    if config is None:
        return None

    environment, scenario, if_empty_only = config
    if if_empty_only and not _database_is_empty(database_url):
        return None

    result = seed_dataset(
        environment=environment,
        scenario=scenario,
        reset=True,
        database_url=database_url,
    )
    return SeedBootstrapResult(
        dataset=result.dataset,
        environment=result.environment,
        scenario=result.scenario,
        period_start=result.period_start,
        inventory_items=result.inventory_items,
        confirmed_plan_slots=result.confirmed_plan_slots,
        grocery_lines=result.grocery_lines,
    )


def _bootstrap_config_from_environment() -> tuple[str, str, bool] | None:
    legacy_dataset = os.getenv("MEAL_PLANNER_BOOTSTRAP_DATASET", "").strip()
    if legacy_dataset:
        if legacy_dataset != "reviewer-baseline":
            raise SeedSafetyError(f"Unsupported bootstrap dataset: {legacy_dataset}")
        return (
            os.getenv("MEAL_PLANNER_BOOTSTRAP_ENV", "local").strip() or "local",
            os.getenv("MEAL_PLANNER_BOOTSTRAP_SCENARIO", "baseline").strip() or "baseline",
            os.getenv("MEAL_PLANNER_BOOTSTRAP_IF_EMPTY", "").strip().lower() in {"1", "true", "yes", "on"},
        )

    enabled = os.getenv("MEAL_PLANNER_REVIEWER_SEED", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return None

    return (
        os.getenv("MEAL_PLANNER_BOOTSTRAP_ENV", os.getenv("ASPIRE_ENV", "local")).strip() or "local",
        os.getenv(
            "MEAL_PLANNER_BOOTSTRAP_SCENARIO",
            os.getenv("MEAL_PLANNER_REVIEWER_SEED_SCENARIO", "baseline"),
        ).strip()
        or "baseline",
        True,
    )


def _database_is_empty(database_url: str | URL | None) -> bool:
    db_url = database_url or default_database_url()
    engine = _create_engine(db_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with session_factory() as session:
            return session.scalar(select(Household.id).limit(1)) is None
    finally:
        engine.dispose()


def _scenario_names_from_label(scenario: str) -> tuple[str, ...]:
    normalized = scenario.strip().lower()
    if normalized in {"", "baseline"}:
        return ()
    if normalized in SUPPORTED_SCENARIOS:
        return (normalized,)
    raise ValueError(f"Unsupported reviewer seed scenario: {scenario}")


def validate_seed_environment(environment: str) -> str:
    normalized_environment = (environment or "local").strip().lower()
    if normalized_environment in SUPPORTED_ENVIRONMENTS:
        return normalized_environment
    if normalized_environment == "production":
        raise SeedSafetyError("Reviewer seed data must not run against production environments.")
    allowed = ", ".join(SUPPORTED_ENVIRONMENTS)
    raise SeedSafetyError(
        f"Reviewer seed data only supports {allowed} environments; got {normalized_environment!r}."
    )


def _create_engine(database_url: str | URL) -> Engine:
    engine = create_engine(database_url, connect_args={"check_same_thread": False}, future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _seed_households(session: Session) -> None:
    households = [
        Household(
            id=REVIEWER_HOUSEHOLD_ID,
            name=REVIEWER_HOUSEHOLD_NAME,
            created_at=_SEED_CREATED_AT,
            updated_at=_SEED_CREATED_AT,
        ),
        Household(
            id=SECONDARY_HOUSEHOLD_ID,
            name=SECONDARY_HOUSEHOLD_NAME,
            created_at=_SEED_CREATED_AT,
            updated_at=_SEED_CREATED_AT,
        ),
    ]
    memberships = [
        HouseholdMembership(
            id=REVIEWER_MEMBER_ID,
            household_id=REVIEWER_HOUSEHOLD_ID,
            user_id=REVIEWER_USER_ID,
            user_email=REVIEWER_USER_EMAIL,
            user_display_name=REVIEWER_USER_NAME,
            role="owner",
            created_at=_SEED_CREATED_AT,
            updated_at=_SEED_CREATED_AT,
        ),
        HouseholdMembership(
            id=REVIEWER_COLLABORATOR_MEMBER_ID,
            household_id=REVIEWER_HOUSEHOLD_ID,
            user_id=REVIEWER_COLLABORATOR_ID,
            user_email=REVIEWER_COLLABORATOR_EMAIL,
            user_display_name=REVIEWER_COLLABORATOR_NAME,
            role="member",
            created_at=_SEED_CREATED_AT,
            updated_at=_SEED_CREATED_AT,
        ),
        HouseholdMembership(
            id=SECONDARY_MEMBER_ID,
            household_id=SECONDARY_HOUSEHOLD_ID,
            user_id=REVIEWER_USER_ID,
            user_email=REVIEWER_USER_EMAIL,
            user_display_name=REVIEWER_USER_NAME,
            role="owner",
            created_at=_SEED_CREATED_AT,
            updated_at=_SEED_CREATED_AT,
        ),
    ]
    session.add_all([*households, *memberships])


def _inventory_seeds() -> tuple[_InventorySeed, ...]:
    return (
        _InventorySeed(
            key="pasta",
            item_id="66666666-6666-6666-6666-666666666601",
            name="Pasta",
            storage_location="pantry",
            quantity_on_hand=Decimal("500.0000"),
            primary_unit="grams",
            freshness_basis="unknown",
            freshness_note=None,
            version=1,
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777701",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("500.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("500.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-pasta-create",
                    "created_at": _SEED_CREATED_AT,
                    "note": "Pantry staple kept on hand for quick dinners.",
                },
            ),
        ),
        _InventorySeed(
            key="oats",
            item_id="66666666-6666-6666-6666-666666666602",
            name="Oats",
            storage_location="pantry",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="bag",
            freshness_basis="unknown",
            version=1,
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777702",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("1.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-oats-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=1),
                    "note": "Breakfast backup for the smoke household.",
                },
            ),
        ),
        _InventorySeed(
            key="olive-oil",
            item_id="66666666-6666-6666-6666-666666666603",
            name="Olive Oil",
            storage_location="pantry",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="bottle",
            freshness_basis="known",
            expiry_date=date(2026, 9, 1),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=2),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=2),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777703",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("1.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-oil-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=2),
                    "note": "Bottle unit intentionally avoids silent ml conversion.",
                },
            ),
        ),
        _InventorySeed(
            key="milk",
            item_id="66666666-6666-6666-6666-666666666604",
            name="Milk",
            storage_location="fridge",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="liter",
            freshness_basis="known",
            expiry_date=date(2026, 3, 12),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(hours=1, minutes=45),
            version=4,
            updated_at=_SEED_CREATED_AT + timedelta(hours=1, minutes=45),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777704",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("2.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("2.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-milk-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=3),
                    "note": "Baseline fridge stock for breakfasts.",
                },
                {
                    "id": "77777777-7777-7777-7777-777777777705",
                    "mutation_type": "set_metadata",
                    "delta_quantity": None,
                    "quantity_before": Decimal("2.0000"),
                    "quantity_after": Decimal("2.0000"),
                    "reason_code": "manual_edit",
                    "client_mutation_id": "seed-reviewer-inventory-milk-expiry",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=20),
                    "expiry_date_before": date(2026, 3, 11),
                    "expiry_date_after": date(2026, 3, 12),
                    "note": "Reviewer updated the carton label after unpacking groceries.",
                },
                {
                    "id": "77777777-7777-7777-7777-777777777706",
                    "mutation_type": "decrease_quantity",
                    "delta_quantity": Decimal("-1.5000"),
                    "quantity_before": Decimal("2.0000"),
                    "quantity_after": Decimal("0.5000"),
                    "reason_code": "cooking_consume",
                    "client_mutation_id": "seed-reviewer-inventory-milk-consume",
                    "created_at": _SEED_CREATED_AT + timedelta(hours=1),
                    "note": "Breakfast smoothie used more milk than expected.",
                },
                {
                    "id": "77777777-7777-7777-7777-777777777707",
                    "mutation_type": "correction",
                    "delta_quantity": Decimal("0.5000"),
                    "quantity_before": Decimal("0.5000"),
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "correction",
                    "client_mutation_id": "seed-reviewer-inventory-milk-correction",
                    "created_at": _SEED_CREATED_AT + timedelta(hours=1, minutes=45),
                    "corrects_adjustment_id": "77777777-7777-7777-7777-777777777706",
                    "note": "Half a carton was still unopened on the lower shelf.",
                },
            ),
        ),
        _InventorySeed(
            key="eggs",
            item_id="66666666-6666-6666-6666-666666666605",
            name="Eggs",
            storage_location="fridge",
            quantity_on_hand=Decimal("8.0000"),
            primary_unit="count",
            freshness_basis="known",
            expiry_date=date(2026, 3, 15),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=5),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=5),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777708",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("8.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("8.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-eggs-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=5),
                    "note": "Eight eggs left after weekend baking.",
                },
            ),
        ),
        _InventorySeed(
            key="tomatoes",
            item_id="66666666-6666-6666-6666-666666666606",
            name="Tomatoes",
            storage_location="fridge",
            quantity_on_hand=Decimal("2.0000"),
            primary_unit="count",
            freshness_basis="known",
            expiry_date=date(2026, 3, 11),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=6),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=6),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777709",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("2.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("2.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-tomatoes-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=6),
                    "note": "Fresh tomatoes should be used first this week.",
                },
            ),
        ),
        _InventorySeed(
            key="spinach",
            item_id="66666666-6666-6666-6666-666666666607",
            name="Spinach",
            storage_location="fridge",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="bag",
            freshness_basis="estimated",
            estimated_expiry_date=date(2026, 3, 10),
            freshness_note="Farmer's market bundle estimated to last through Tuesday.",
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=7),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=7),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777710",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("1.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-spinach-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=7),
                    "note": "Estimated freshness keeps the review surface honest.",
                },
            ),
        ),
        _InventorySeed(
            key="greek-yogurt",
            item_id="66666666-6666-6666-6666-666666666608",
            name="Greek Yogurt",
            storage_location="fridge",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="tub",
            freshness_basis="known",
            expiry_date=date(2026, 3, 18),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=8),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=8),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777711",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("1.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-yogurt-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=8),
                    "note": "Protein-friendly breakfast option already on hand.",
                },
            ),
        ),
        _InventorySeed(
            key="ground-beef",
            item_id="66666666-6666-6666-6666-666666666609",
            name="Ground Beef",
            storage_location="freezer",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="pack",
            freshness_basis="known",
            expiry_date=date(2026, 9, 15),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=9),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=9),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777712",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("1.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-beef-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=9),
                    "note": "Freezer backup for taco night or emergency pasta sauce.",
                },
            ),
        ),
        _InventorySeed(
            key="mixed-vegetables",
            item_id="66666666-6666-6666-6666-666666666610",
            name="Mixed Vegetables",
            storage_location="freezer",
            quantity_on_hand=Decimal("2.0000"),
            primary_unit="bag",
            freshness_basis="known",
            expiry_date=date(2026, 12, 1),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=10),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=10),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777713",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("2.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("2.0000"),
                    "reason_code": "manual_create",
                    "client_mutation_id": "seed-reviewer-inventory-veg-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=10),
                    "note": "Reliable freezer option for quick weeknight sides.",
                },
            ),
        ),
        _InventorySeed(
            key="leftover-soup",
            item_id="66666666-6666-6666-6666-666666666611",
            name="Leftover Vegetable Soup",
            storage_location="leftovers",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="container",
            freshness_basis="known",
            expiry_date=date(2026, 3, 10),
            freshness_updated_at=_SEED_CREATED_AT + timedelta(minutes=11),
            version=1,
            updated_at=_SEED_CREATED_AT + timedelta(minutes=11),
            adjustments=(
                {
                    "id": "77777777-7777-7777-7777-777777777714",
                    "mutation_type": "create_item",
                    "delta_quantity": Decimal("1.0000"),
                    "quantity_before": _ZERO,
                    "quantity_after": Decimal("1.0000"),
                    "reason_code": "leftovers_create",
                    "client_mutation_id": "seed-reviewer-inventory-leftovers-create",
                    "created_at": _SEED_CREATED_AT + timedelta(minutes=11),
                    "note": "Shows leftovers as first-class inventory.",
                },
            ),
        ),
    )


def _seed_inventory(session: Session) -> dict[str, _InventorySeed]:
    inventory_by_key: dict[str, _InventorySeed] = {}
    receipt_counter = 1
    for seed in _inventory_seeds():
        item = InventoryItem(
            id=seed.item_id,
            household_id=REVIEWER_HOUSEHOLD_ID,
            name=seed.name,
            storage_location=seed.storage_location,
            quantity_on_hand=seed.quantity_on_hand,
            primary_unit=seed.primary_unit,
            freshness_basis=seed.freshness_basis,
            expiry_date=seed.expiry_date,
            estimated_expiry_date=seed.estimated_expiry_date,
            freshness_note=seed.freshness_note,
            freshness_updated_at=seed.freshness_updated_at,
            is_active=True,
            version=seed.version,
            created_at=seed.created_at,
            updated_at=seed.updated_at,
        )
        session.add(item)
        inventory_by_key[seed.key] = seed
        for adjustment in seed.adjustments:
            is_create = str(adjustment["mutation_type"]) == "create_item"
            adjustment_model = InventoryAdjustment(
                id=str(adjustment["id"]),
                inventory_item_id=seed.item_id,
                household_id=REVIEWER_HOUSEHOLD_ID,
                mutation_type=str(adjustment["mutation_type"]),
                delta_quantity=adjustment.get("delta_quantity"),
                quantity_before=adjustment.get("quantity_before"),
                quantity_after=adjustment.get("quantity_after"),
                storage_location_before=adjustment.get(
                    "storage_location_before",
                    None if is_create else seed.storage_location,
                ),
                storage_location_after=adjustment.get("storage_location_after", seed.storage_location),
                freshness_basis_before=adjustment.get(
                    "freshness_basis_before",
                    None if is_create else seed.freshness_basis,
                ),
                expiry_date_before=adjustment.get("expiry_date_before", None if is_create else seed.expiry_date),
                estimated_expiry_date_before=adjustment.get("estimated_expiry_date_before"),
                freshness_basis_after=adjustment.get("freshness_basis_after", seed.freshness_basis),
                expiry_date_after=adjustment.get("expiry_date_after", seed.expiry_date),
                estimated_expiry_date_after=adjustment.get("estimated_expiry_date_after", seed.estimated_expiry_date),
                reason_code=str(adjustment["reason_code"]),
                actor_id=REVIEWER_USER_ID,
                client_mutation_id=str(adjustment["client_mutation_id"]),
                correlation_id=str(adjustment["client_mutation_id"]),
                corrects_adjustment_id=adjustment.get("corrects_adjustment_id"),
                notes=adjustment.get("note"),
                created_at=adjustment["created_at"],
            )
            session.add(adjustment_model)
            session.add(
                MutationReceipt(
                    id=f"dddddddd-dddd-dddd-dddd-{receipt_counter:012d}",
                    household_id=REVIEWER_HOUSEHOLD_ID,
                    client_mutation_id=str(adjustment["client_mutation_id"]),
                    accepted_at=adjustment["created_at"],
                    result_summary=f"{seed.name} {adjustment_model.mutation_type}",
                    inventory_adjustment_id=adjustment_model.id,
                )
            )
            receipt_counter += 1

    session.add(
        InventoryItem(
            id="66666666-6666-6666-6666-666666666699",
            household_id=SECONDARY_HOUSEHOLD_ID,
            name="Cabin Flour",
            storage_location="pantry",
            quantity_on_hand=Decimal("1.0000"),
            primary_unit="bag",
            freshness_basis="unknown",
            version=1,
            created_at=_SEED_CREATED_AT,
            updated_at=_SEED_CREATED_AT,
        )
    )
    return inventory_by_key


def _planner_slots() -> tuple[_PlannerSlotSeed, ...]:
    return (
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888801",
            slot_key="0:breakfast",
            day_of_week=0,
            meal_type="breakfast",
            meal_title="Overnight Oats",
            meal_summary="Prep-ahead oats with banana and yogurt.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888802",
            slot_key="0:lunch",
            day_of_week=0,
            meal_type="lunch",
            meal_title="Leftover Vegetable Soup",
            meal_summary="Use the container already in leftovers before it expires.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888803",
            slot_key="0:dinner",
            day_of_week=0,
            meal_type="dinner",
            meal_title="Pasta Bake",
            meal_summary="Pantry pasta dinner that uses tomatoes already in the fridge.",
            meal_reference_id="meal-pasta-bake",
            slot_origin="ai_suggested",
            reason_codes=("USES_ON_HAND", "EXPIRY_PRIORITY"),
            explanation_entries=("Uses pantry pasta and near-expiry tomatoes first.",),
            uses_on_hand=("Pasta", "Tomatoes"),
            missing_hints=(),
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888804",
            slot_key="1:breakfast",
            day_of_week=1,
            meal_type="breakfast",
            meal_title="Greek Yogurt Parfait",
            meal_summary="Quick protein breakfast with fruit and oats.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888805",
            slot_key="1:lunch",
            day_of_week=1,
            meal_type="lunch",
            meal_title="Spinach Egg Wraps",
            meal_summary="Simple lunch that uses the spinach before Tuesday ends.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888806",
            slot_key="1:dinner",
            day_of_week=1,
            meal_type="dinner",
            meal_title="Taco Night",
            meal_summary="Family taco night with freezer beef as backup.",
            meal_reference_id="meal-taco-night",
            slot_origin="ai_suggested",
            reason_codes=("FAMILY_FAVORITE",),
            explanation_entries=("Keeps Tuesday realistic with a familiar low-friction dinner.",),
            uses_on_hand=("Ground Beef",),
            missing_hints=("Cilantro",),
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888807",
            slot_key="2:breakfast",
            day_of_week=2,
            meal_type="breakfast",
            meal_title="Banana Smoothies",
            meal_summary="Fast breakfast using milk and yogurt before the next shop.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888808",
            slot_key="2:lunch",
            day_of_week=2,
            meal_type="lunch",
            meal_title="Chicken Salad Sandwiches",
            meal_summary="Midweek lunch that still feels like a real household plan.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888809",
            slot_key="2:dinner",
            day_of_week=2,
            meal_type="dinner",
            meal_title="Salad Night",
            meal_summary="Lighter dinner that spends the last fresh tomatoes and spinach.",
            meal_reference_id="meal-salad-night",
            slot_origin="ai_suggested",
            reason_codes=("EXPIRY_PRIORITY", "LOW_EFFORT"),
            explanation_entries=("Keeps midweek lighter while using produce close to expiry.",),
            uses_on_hand=("Tomatoes", "Spinach"),
            missing_hints=("Lettuce",),
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888810",
            slot_key="3:breakfast",
            day_of_week=3,
            meal_type="breakfast",
            meal_title="Eggs on Toast",
            meal_summary="Classic breakfast that makes the household feel lived in.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888811",
            slot_key="3:lunch",
            day_of_week=3,
            meal_type="lunch",
            meal_title="Yogurt & Fruit Bowls",
            meal_summary="Quick lunch on a meeting-heavy day.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888812",
            slot_key="3:dinner",
            day_of_week=3,
            meal_type="dinner",
            meal_title="Pesto Pasta",
            meal_summary="Balances convenience with the basil line still needed on the list.",
            meal_reference_id="meal-pesto-pasta",
            slot_origin="ai_suggested",
            reason_codes=("USES_ON_HAND",),
            explanation_entries=("Reuses pantry pasta while keeping the grocery need traceable.",),
            uses_on_hand=("Pasta"),
            missing_hints=("Basil",),
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888813",
            slot_key="4:breakfast",
            day_of_week=4,
            meal_type="breakfast",
            meal_title="Overnight Oats",
            meal_summary="Repeat breakfast that keeps the week believable.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888814",
            slot_key="4:lunch",
            day_of_week=4,
            meal_type="lunch",
            meal_title="Tomato Toasties",
            meal_summary="Uses simple ingredients without feeling like a canned demo.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888815",
            slot_key="4:dinner",
            day_of_week=4,
            meal_type="dinner",
            meal_title="Taco Night",
            meal_summary="Second taco night is deliberate: kids asked for it again.",
            meal_reference_id="meal-taco-night",
            slot_origin="ai_suggested",
            reason_codes=("FAMILY_FAVORITE",),
            explanation_entries=("Repeats a family favorite to show that plans need not be perfectly novel.",),
            uses_on_hand=("Ground Beef",),
            missing_hints=("Cilantro",),
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888816",
            slot_key="5:breakfast",
            day_of_week=5,
            meal_type="breakfast",
            meal_title="Pancakes",
            meal_summary="Weekend breakfast that makes the household feel real.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888817",
            slot_key="5:lunch",
            day_of_week=5,
            meal_type="lunch",
            meal_title="Leftover Taco Bowls",
            meal_summary="Makes use of whatever is left from Friday dinner.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888818",
            slot_key="5:dinner",
            day_of_week=5,
            meal_type="dinner",
            meal_title="Salad Night",
            meal_summary="Keeps Saturday dinner lighter after a bigger breakfast.",
            meal_reference_id="meal-salad-night",
            slot_origin="ai_suggested",
            reason_codes=("LOW_EFFORT",),
            explanation_entries=("Weekend dinner stays light and quick.",),
            uses_on_hand=("Tomatoes"),
            missing_hints=("Lettuce",),
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888819",
            slot_key="6:breakfast",
            day_of_week=6,
            meal_type="breakfast",
            meal_title="Smoothie Bowls",
            meal_summary="Uses the remaining yogurt and milk before the next shop.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888820",
            slot_key="6:lunch",
            day_of_week=6,
            meal_type="lunch",
            meal_title="Soup & Toast",
            meal_summary="Simple Sunday lunch that leaves room for dinner prep.",
            meal_reference_id=None,
            slot_origin="manually_added",
        ),
        _PlannerSlotSeed(
            slot_id="88888888-8888-8888-8888-888888888821",
            slot_key="6:dinner",
            day_of_week=6,
            meal_type="dinner",
            meal_title="Pasta Bake",
            meal_summary="Repeatable end-of-week dinner that still feels household-authentic.",
            meal_reference_id="meal-pasta-bake",
            slot_origin="ai_suggested",
            reason_codes=("USES_ON_HAND",),
            explanation_entries=("Ends the week with a reliable pantry dinner.",),
            uses_on_hand=("Pasta", "Tomatoes"),
            missing_hints=(),
        ),
    )


def _seed_planner(session: Session) -> None:
    plan = MealPlan(
        id=REVIEWER_PLAN_ID,
        household_id=REVIEWER_HOUSEHOLD_ID,
        period_start=REVIEWER_PLAN_PERIOD_START,
        period_end=REVIEWER_PLAN_PERIOD_END,
        status="confirmed",
        version=3,
        created_at=_SEED_CREATED_AT + timedelta(minutes=35),
        updated_at=_PLAN_CONFIRMED_AT,
        confirmed_at=_PLAN_CONFIRMED_AT,
        confirmation_client_mutation_id="seed-reviewer-plan-confirm",
        ai_suggestion_request_id=REVIEWER_AI_REQUEST_ID,
        ai_suggestion_result_id=REVIEWER_AI_RESULT_ID,
        stale_warning_acknowledged=False,
    )
    session.add(plan)
    session.flush()
    request = AISuggestionRequest(
        id=REVIEWER_AI_REQUEST_ID,
        household_id=REVIEWER_HOUSEHOLD_ID,
        actor_id=REVIEWER_USER_ID,
        plan_period_start=REVIEWER_PLAN_PERIOD_START,
        plan_period_end=REVIEWER_PLAN_PERIOD_END,
        target_slot_id=None,
        meal_plan_id=REVIEWER_PLAN_ID,
        meal_plan_slot_id=None,
        status="completed",
        request_idempotency_key="seed-reviewer-ai-request",
        prompt_family="weekly_meal_plan",
        prompt_version="1.0.0",
        policy_version="1.0.0",
        context_contract_version="1.0.0",
        result_contract_version="1.0.0",
        grounding_hash=hashlib.sha256(b"reviewer-seed-grounding").hexdigest(),
        created_at=_SEED_CREATED_AT + timedelta(minutes=30),
        completed_at=_PLAN_CONFIRMED_AT - timedelta(minutes=5),
    )
    result = AISuggestionResult(
        id=REVIEWER_AI_RESULT_ID,
        request_id=REVIEWER_AI_REQUEST_ID,
        meal_plan_id=REVIEWER_PLAN_ID,
        fallback_mode="none",
        stale_flag=False,
        result_contract_version="1.0.0",
        created_at=_PLAN_CONFIRMED_AT - timedelta(minutes=4),
    )
    session.add_all([request, result])
    for index, slot_seed in enumerate(_planner_slots(), start=1):
        session.add(
            MealPlanSlot(
                id=slot_seed.slot_id,
                meal_plan_id=REVIEWER_PLAN_ID,
                slot_key=slot_seed.slot_key,
                day_of_week=slot_seed.day_of_week,
                meal_type=slot_seed.meal_type,
                meal_title=slot_seed.meal_title,
                meal_summary=slot_seed.meal_summary,
                meal_reference_id=slot_seed.meal_reference_id,
                slot_origin=slot_seed.slot_origin,
                ai_suggestion_request_id=(
                    REVIEWER_AI_REQUEST_ID if slot_seed.slot_origin == "ai_suggested" else None
                ),
                ai_suggestion_result_id=(
                    REVIEWER_AI_RESULT_ID if slot_seed.slot_origin == "ai_suggested" else None
                ),
                reason_codes=_json_list(slot_seed.reason_codes) if slot_seed.reason_codes else None,
                explanation_entries=(
                    _json_list(slot_seed.explanation_entries) if slot_seed.explanation_entries else None
                ),
                prompt_family="weekly_meal_plan" if slot_seed.slot_origin == "ai_suggested" else None,
                prompt_version="1.0.0" if slot_seed.slot_origin == "ai_suggested" else None,
                fallback_mode="none" if slot_seed.slot_origin == "ai_suggested" else None,
                regen_status="idle",
                pending_regen_request_id=None,
                is_user_locked=slot_seed.is_user_locked,
                notes=None,
                created_at=_PLAN_CONFIRMED_AT - timedelta(minutes=2),
                updated_at=_PLAN_CONFIRMED_AT - timedelta(minutes=1),
            )
        )
        session.add(
            MealPlanSlotHistory(
                id=f"eeeeeeee-eeee-eeee-eeee-{index:012d}",
                meal_plan_slot_id=slot_seed.slot_id,
                meal_plan_id=REVIEWER_PLAN_ID,
                slot_key=slot_seed.slot_key,
                slot_origin=slot_seed.slot_origin,
                ai_suggestion_request_id=(
                    REVIEWER_AI_REQUEST_ID if slot_seed.slot_origin == "ai_suggested" else None
                ),
                ai_suggestion_result_id=(
                    REVIEWER_AI_RESULT_ID if slot_seed.slot_origin == "ai_suggested" else None
                ),
                reason_codes=_json_list(slot_seed.reason_codes) if slot_seed.reason_codes else None,
                explanation_entries=(
                    _json_list(slot_seed.explanation_entries) if slot_seed.explanation_entries else None
                ),
                prompt_family="weekly_meal_plan" if slot_seed.slot_origin == "ai_suggested" else None,
                prompt_version="1.0.0" if slot_seed.slot_origin == "ai_suggested" else None,
                fallback_mode="none" if slot_seed.slot_origin == "ai_suggested" else None,
                stale_warning_present_at_confirmation=False,
                confirmed_at=_PLAN_CONFIRMED_AT,
                created_at=_PLAN_CONFIRMED_AT,
            )
        )
        if slot_seed.slot_origin == "ai_suggested":
            session.add(
                AISuggestionSlot(
                    id=f"ffffffff-ffff-ffff-ffff-{index:012d}",
                    result_id=REVIEWER_AI_RESULT_ID,
                    slot_key=slot_seed.slot_key,
                    day_of_week=slot_seed.day_of_week,
                    meal_type=slot_seed.meal_type,
                    meal_title=slot_seed.meal_title,
                    meal_summary=slot_seed.meal_summary,
                    reason_codes=_json_list(slot_seed.reason_codes),
                    explanation_entries=_json_list(slot_seed.explanation_entries),
                    uses_on_hand=_json_list(slot_seed.uses_on_hand),
                    missing_hints=_json_list(slot_seed.missing_hints),
                    is_fallback=False,
                    created_at=_PLAN_CONFIRMED_AT - timedelta(minutes=3),
                )
            )


def _grocery_line_seeds() -> tuple[_GroceryLineSeed, ...]:
    return (
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999901",
            stable_line_id="99999999-9999-9999-9999-999999999911",
            ingredient_name="Milk",
            ingredient_ref_id="ingredient-milk",
            required_quantity=Decimal("3.0000"),
            unit="liter",
            offset_quantity=Decimal("1.0000"),
            shopping_quantity=Decimal("2.0000"),
            origin="derived",
            offset_inventory_key="milk",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888801",
                    "meal_name": "Overnight Oats",
                    "contributed_quantity": "1.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888807",
                    "meal_name": "Banana Smoothies",
                    "contributed_quantity": "1.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888819",
                    "meal_name": "Smoothie Bowls",
                    "contributed_quantity": "1.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999902",
            stable_line_id="99999999-9999-9999-9999-999999999912",
            ingredient_name="Pasta",
            ingredient_ref_id="ingredient-pasta",
            required_quantity=Decimal("1300.0000"),
            unit="grams",
            offset_quantity=Decimal("500.0000"),
            shopping_quantity=Decimal("800.0000"),
            origin="derived",
            offset_inventory_key="pasta",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888803",
                    "meal_name": "Pasta Bake",
                    "contributed_quantity": "500.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888812",
                    "meal_name": "Pesto Pasta",
                    "contributed_quantity": "300.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888821",
                    "meal_name": "Pasta Bake",
                    "contributed_quantity": "500.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999903",
            stable_line_id="99999999-9999-9999-9999-999999999913",
            ingredient_name="Tomatoes",
            ingredient_ref_id="ingredient-tomatoes",
            required_quantity=Decimal("8.0000"),
            unit="count",
            offset_quantity=Decimal("2.0000"),
            shopping_quantity=Decimal("6.0000"),
            origin="derived",
            offset_inventory_key="tomatoes",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888803",
                    "meal_name": "Pasta Bake",
                    "contributed_quantity": "4.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888809",
                    "meal_name": "Salad Night",
                    "contributed_quantity": "2.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888818",
                    "meal_name": "Salad Night",
                    "contributed_quantity": "2.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999904",
            stable_line_id="99999999-9999-9999-9999-999999999914",
            ingredient_name="Tortillas",
            ingredient_ref_id="ingredient-tortillas",
            required_quantity=Decimal("16.0000"),
            unit="count",
            offset_quantity=_ZERO,
            shopping_quantity=Decimal("16.0000"),
            origin="derived",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888806",
                    "meal_name": "Taco Night",
                    "contributed_quantity": "8.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888815",
                    "meal_name": "Taco Night",
                    "contributed_quantity": "8.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999905",
            stable_line_id="99999999-9999-9999-9999-999999999915",
            ingredient_name="Salsa",
            ingredient_ref_id="ingredient-salsa",
            required_quantity=Decimal("1.0000"),
            unit="jar",
            offset_quantity=_ZERO,
            shopping_quantity=Decimal("1.0000"),
            origin="derived",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888806",
                    "meal_name": "Taco Night",
                    "contributed_quantity": "1.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999906",
            stable_line_id="99999999-9999-9999-9999-999999999916",
            ingredient_name="Basil",
            ingredient_ref_id="ingredient-basil",
            required_quantity=Decimal("1.0000"),
            unit="bunch",
            offset_quantity=_ZERO,
            shopping_quantity=Decimal("1.0000"),
            origin="derived",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888812",
                    "meal_name": "Pesto Pasta",
                    "contributed_quantity": "1.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999907",
            stable_line_id="99999999-9999-9999-9999-999999999917",
            ingredient_name="Greek Yogurt",
            ingredient_ref_id="ingredient-greek-yogurt",
            required_quantity=Decimal("1.0000"),
            unit="tub",
            offset_quantity=Decimal("1.0000"),
            shopping_quantity=_ZERO,
            origin="derived",
            offset_inventory_key="greek-yogurt",
            user_adjusted_quantity=Decimal("2.0000"),
            user_adjustment_note="Pick up two tubs so breakfasts last through Sunday.",
            user_adjustment_flagged=True,
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888804",
                    "meal_name": "Greek Yogurt Parfait",
                    "contributed_quantity": "1.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999908",
            stable_line_id="99999999-9999-9999-9999-999999999918",
            ingredient_name="Bananas",
            ingredient_ref_id="ingredient-bananas",
            required_quantity=Decimal("6.0000"),
            unit="count",
            offset_quantity=_ZERO,
            shopping_quantity=Decimal("6.0000"),
            origin="derived",
            meal_sources=(
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888801",
                    "meal_name": "Overnight Oats",
                    "contributed_quantity": "2.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888807",
                    "meal_name": "Banana Smoothies",
                    "contributed_quantity": "2.0000",
                },
                {
                    "meal_slot_id": "88888888-8888-8888-8888-888888888819",
                    "meal_name": "Smoothie Bowls",
                    "contributed_quantity": "2.0000",
                },
            ),
        ),
        _GroceryLineSeed(
            item_id="99999999-9999-9999-9999-999999999909",
            stable_line_id="99999999-9999-9999-9999-999999999919",
            ingredient_name="Cilantro",
            required_quantity=Decimal("1.0000"),
            unit="bunch",
            offset_quantity=_ZERO,
            shopping_quantity=Decimal("1.0000"),
            origin="ad_hoc",
            meal_sources=(),
            ad_hoc_note="Optional taco topping the family always grabs at the store.",
            created_client_mutation_id="seed-reviewer-grocery-add-cilantro",
        ),
    )


def _seed_grocery(session: Session, inventory_by_key: dict[str, _InventorySeed]) -> str:
    snapshot_reference = _inventory_snapshot_reference(
        [
            session.get(InventoryItem, seed.item_id)
            for seed in inventory_by_key.values()
            if session.get(InventoryItem, seed.item_id) is not None
        ]
    )
    grocery_list = GroceryList(
        id=REVIEWER_GROCERY_LIST_ID,
        household_id=REVIEWER_HOUSEHOLD_ID,
        meal_plan_id=REVIEWER_PLAN_ID,
        status="confirmed",
        current_version_number=1,
        confirmed_at=_GROCERY_CONFIRMED_AT,
        confirmation_client_mutation_id="seed-reviewer-grocery-confirm",
        created_at=_PLAN_CONFIRMED_AT + timedelta(minutes=10),
        updated_at=_GROCERY_CONFIRMED_AT,
    )
    version = GroceryListVersion(
        id=REVIEWER_GROCERY_VERSION_ID,
        grocery_list_id=REVIEWER_GROCERY_LIST_ID,
        version_number=1,
        plan_period_reference=f"{REVIEWER_PLAN_PERIOD_START.isoformat()}/{REVIEWER_PLAN_PERIOD_END.isoformat()}",
        confirmed_plan_id=REVIEWER_PLAN_ID,
        derived_at=_PLAN_CONFIRMED_AT + timedelta(minutes=20),
        confirmed_plan_version=3,
        inventory_snapshot_reference=snapshot_reference,
        invalidated_at=None,
        incomplete_slot_warnings=json.dumps([]),
    )
    session.add_all([grocery_list, version])
    for line_seed in _grocery_line_seeds():
        offset_item = inventory_by_key.get(line_seed.offset_inventory_key) if line_seed.offset_inventory_key else None
        session.add(
            GroceryListItem(
                id=line_seed.item_id,
                stable_line_id=line_seed.stable_line_id,
                grocery_list_id=REVIEWER_GROCERY_LIST_ID,
                grocery_list_version_id=REVIEWER_GROCERY_VERSION_ID,
                ingredient_name=line_seed.ingredient_name,
                ingredient_ref_id=line_seed.ingredient_ref_id,
                required_quantity=line_seed.required_quantity,
                unit=line_seed.unit,
                offset_quantity=line_seed.offset_quantity,
                offset_inventory_item_id=offset_item.item_id if offset_item is not None else None,
                offset_inventory_item_version=offset_item.version if offset_item is not None else None,
                shopping_quantity=line_seed.shopping_quantity,
                origin=line_seed.origin,
                meal_sources=_json_list(line_seed.meal_sources) if line_seed.meal_sources else None,
                user_adjusted_quantity=line_seed.user_adjusted_quantity,
                user_adjustment_note=line_seed.user_adjustment_note,
                user_adjustment_flagged=line_seed.user_adjustment_flagged,
                ad_hoc_note=line_seed.ad_hoc_note,
                active=True,
                removed_at=None,
                is_purchased=False,
                created_client_mutation_id=line_seed.created_client_mutation_id,
                removed_client_mutation_id=None,
                created_at=_GROCERY_CONFIRMED_AT - timedelta(minutes=2),
                updated_at=_GROCERY_CONFIRMED_AT - timedelta(minutes=1),
            )
        )

    session.add_all(
        [
            GroceryMutationReceipt(
                id="aaaaaaa1-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
                household_id=REVIEWER_HOUSEHOLD_ID,
                grocery_list_id=REVIEWER_GROCERY_LIST_ID,
                grocery_list_item_id=None,
                client_mutation_id="seed-reviewer-grocery-confirm",
                mutation_kind="confirm",
                accepted_at=_GROCERY_CONFIRMED_AT,
                result_summary="Confirmed reviewer grocery snapshot.",
            ),
            GroceryMutationReceipt(
                id="aaaaaaa1-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
                household_id=REVIEWER_HOUSEHOLD_ID,
                grocery_list_id=REVIEWER_GROCERY_LIST_ID,
                grocery_list_item_id="99999999-9999-9999-9999-999999999909",
                client_mutation_id="seed-reviewer-grocery-add-cilantro",
                mutation_kind="add_ad_hoc",
                accepted_at=_GROCERY_CONFIRMED_AT - timedelta(minutes=3),
                result_summary="Added ad hoc cilantro line before confirming the list.",
            ),
            GroceryMutationReceipt(
                id="aaaaaaa1-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
                household_id=REVIEWER_HOUSEHOLD_ID,
                grocery_list_id=REVIEWER_GROCERY_LIST_ID,
                grocery_list_item_id="99999999-9999-9999-9999-999999999907",
                client_mutation_id="seed-reviewer-grocery-adjust-yogurt",
                mutation_kind="adjust_line",
                accepted_at=_GROCERY_CONFIRMED_AT - timedelta(minutes=4),
                result_summary="Reviewer boosted the yogurt quantity for extra breakfasts.",
            ),
        ]
    )
    return version.id


def _apply_trip_in_progress(session: Session) -> str:
    grocery_list = session.get(GroceryList, REVIEWER_GROCERY_LIST_ID)
    if grocery_list is None:
        raise ValueError("Reviewer grocery baseline must exist before applying trip overlay.")
    grocery_list.status = "trip_in_progress"
    grocery_list.updated_at = _SYNC_CONFLICT_AT
    return REVIEWER_GROCERY_VERSION_ID


def _apply_sync_conflict_review(session: Session, inventory_by_key: dict[str, _InventorySeed]) -> str:
    current_version = session.get(GroceryListVersion, REVIEWER_GROCERY_VERSION_ID)
    grocery_list = session.get(GroceryList, REVIEWER_GROCERY_LIST_ID)
    if current_version is None or grocery_list is None:
        raise ValueError("Reviewer grocery baseline must exist before applying conflict overlay.")

    current_version.invalidated_at = _SYNC_CONFLICT_AT
    grocery_list.current_version_number = 2
    grocery_list.status = "trip_in_progress"
    grocery_list.updated_at = _SYNC_CONFLICT_AT

    next_version = GroceryListVersion(
        id="44444444-4444-4444-4444-444444444446",
        grocery_list_id=REVIEWER_GROCERY_LIST_ID,
        version_number=2,
        plan_period_reference=current_version.plan_period_reference,
        confirmed_plan_id=current_version.confirmed_plan_id,
        derived_at=current_version.derived_at,
        confirmed_plan_version=current_version.confirmed_plan_version,
        inventory_snapshot_reference=current_version.inventory_snapshot_reference,
        invalidated_at=None,
        incomplete_slot_warnings=current_version.incomplete_slot_warnings,
    )
    session.add(next_version)

    for index, item in enumerate(
        session.query(GroceryListItem)
        .filter(GroceryListItem.grocery_list_version_id == REVIEWER_GROCERY_VERSION_ID)
        .order_by(GroceryListItem.created_at.asc(), GroceryListItem.id.asc())
        .all(),
        start=1,
    ):
        cloned = GroceryListItem(
            id=f"bbbbbbbb-bbbb-bbbb-bbbb-{index:012d}",
            stable_line_id=item.stable_line_id,
            grocery_list_id=item.grocery_list_id,
            grocery_list_version_id=next_version.id,
            ingredient_name=item.ingredient_name,
            ingredient_ref_id=item.ingredient_ref_id,
            required_quantity=item.required_quantity,
            unit=item.unit,
            offset_quantity=item.offset_quantity,
            offset_inventory_item_id=item.offset_inventory_item_id,
            offset_inventory_item_version=item.offset_inventory_item_version,
            shopping_quantity=item.shopping_quantity,
            origin=item.origin,
            meal_sources=item.meal_sources,
            user_adjusted_quantity=item.user_adjusted_quantity,
            user_adjustment_note=item.user_adjustment_note,
            user_adjustment_flagged=item.user_adjustment_flagged,
            ad_hoc_note=item.ad_hoc_note,
            active=item.active,
            removed_at=item.removed_at,
            is_purchased=item.is_purchased,
            created_client_mutation_id=item.created_client_mutation_id,
            removed_client_mutation_id=item.removed_client_mutation_id,
            created_at=item.created_at,
            updated_at=_SYNC_CONFLICT_AT,
        )
        if item.stable_line_id == "99999999-9999-9999-9999-999999999911":
            cloned.user_adjusted_quantity = Decimal("1.5000")
            cloned.user_adjustment_note = "Server copy reflects a partial store run from another phone."
            cloned.user_adjustment_flagged = True
        session.add(cloned)

    session.add(
        GrocerySyncConflict(
            id="cccccccc-cccc-cccc-cccc-ccccccccccc1",
            household_id=REVIEWER_HOUSEHOLD_ID,
            grocery_list_id=REVIEWER_GROCERY_LIST_ID,
            aggregate_type="grocery_line",
            aggregate_id="99999999-9999-9999-9999-999999999911",
            local_mutation_id="seed-reviewer-sync-conflict-001",
            mutation_type="adjust_line",
            outcome="review_required_quantity",
            base_server_version=1,
            current_server_version=2,
            requires_review=True,
            summary="Milk quantity changed on another device while this phone was offline.",
            local_queue_status="review_required",
            allowed_resolution_actions=json.dumps(["keep_mine", "use_server"]),
            resolution_status="pending",
            local_intent_summary=json.dumps(
                {
                    "aggregate_type": "grocery_line",
                    "aggregate_id": "99999999-9999-9999-9999-999999999911",
                    "mutation_type": "adjust_line",
                    "payload": {
                        "grocery_list_id": REVIEWER_GROCERY_LIST_ID,
                        "quantity_to_buy": "2.5000",
                        "user_adjustment_note": "Keep enough milk for smoothies through Sunday.",
                    },
                }
            ),
            base_state_summary=json.dumps(
                {
                    "grocery_list_id": REVIEWER_GROCERY_LIST_ID,
                    "grocery_list_status": "confirmed",
                    "trip_state": "confirmed_list_ready",
                    "line": {
                        "grocery_line_id": "99999999-9999-9999-9999-999999999911",
                        "ingredient_name": "Milk",
                        "shopping_quantity": "2.0000",
                        "user_adjusted_quantity": None,
                    },
                }
            ),
            server_state_summary=json.dumps(
                {
                    "grocery_list_id": REVIEWER_GROCERY_LIST_ID,
                    "grocery_list_status": "trip_in_progress",
                    "trip_state": "trip_in_progress",
                    "line": {
                        "grocery_line_id": "99999999-9999-9999-9999-999999999911",
                        "ingredient_name": "Milk",
                        "shopping_quantity": "2.0000",
                        "user_adjusted_quantity": "1.5000",
                    },
                }
            ),
            created_at=_SYNC_CONFLICT_AT,
            resolved_at=None,
            resolved_by_actor_id=None,
        )
    )
    return next_version.id


def _inventory_snapshot_reference(items: list[InventoryItem | None]) -> str:
    digest = hashlib.sha1()
    for item in sorted(
        [item for item in items if item is not None and item.is_active],
        key=lambda current: (current.created_at, current.id),
    ):
        digest.update(
            "|".join(
                [
                    item.id,
                    _normalized_name(item.name),
                    item.primary_unit,
                    str(item.quantity_on_hand),
                    str(item.version),
                    str(int(item.is_active)),
                ]
            ).encode("utf-8")
        )
        digest.update(b";")
    return f"inventory-{digest.hexdigest()[:16]}"


def _normalized_name(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _json_list(value: Iterable[object]) -> str:
    return json.dumps(list(value), separators=(",", ":"))


def _dev_env() -> dict[str, str]:
    households = json.dumps(
        [
            {
                "household_id": REVIEWER_HOUSEHOLD_ID,
                "household_name": REVIEWER_HOUSEHOLD_NAME,
                "role": "owner",
            },
            {
                "household_id": SECONDARY_HOUSEHOLD_ID,
                "household_name": SECONDARY_HOUSEHOLD_NAME,
                "role": "owner",
            },
        ],
        separators=(",", ":"),
    )
    return {
        "MEAL_PLANNER_DEV_USER_ID": REVIEWER_USER_ID,
        "MEAL_PLANNER_DEV_USER_EMAIL": REVIEWER_USER_EMAIL,
        "MEAL_PLANNER_DEV_USER_NAME": REVIEWER_USER_NAME,
        "MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_ID": REVIEWER_HOUSEHOLD_ID,
        "MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_NAME": REVIEWER_HOUSEHOLD_NAME,
        "MEAL_PLANNER_DEV_ACTIVE_HOUSEHOLD_ROLE": "owner",
        "MEAL_PLANNER_DEV_HOUSEHOLDS": households,
    }

