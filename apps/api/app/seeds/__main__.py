from __future__ import annotations

import argparse
import os

from app.seeds import SUPPORTED_SCENARIOS, format_seed_summary, seed_reviewer_data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Meal Planner reviewer seed data tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reviewer_reset = subparsers.add_parser(
        "reviewer-reset",
        help="Reset the local API database and seed the deterministic reviewer dataset.",
    )
    reviewer_reset.add_argument(
        "--database-url",
        dest="database_url",
        help="Optional SQLAlchemy database URL. Defaults to the API build SQLite database.",
    )
    reviewer_reset.add_argument(
        "--scenario",
        action="append",
        default=[],
        choices=SUPPORTED_SCENARIOS,
        help="Optional named reviewer scenario overlay. May be provided more than once.",
    )
    reviewer_reset.add_argument(
        "--environment",
        default=os.getenv("MEAL_PLANNER_BOOTSTRAP_ENV", os.getenv("ASPIRE_ENV", "local")),
        help="Seed safety environment. Only local, preview, and test are allowed; production is blocked.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command != "reviewer-reset":
        raise ValueError(f"Unsupported command: {args.command}")

    summary = seed_reviewer_data(
        database_url=args.database_url,
        scenario_names=args.scenario,
        reset=True,
        environment=args.environment,
    )
    print(format_seed_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

