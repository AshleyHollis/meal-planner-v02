from __future__ import annotations

import sys
from pathlib import Path

WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from worker_runtime import GenerationWorker, build_session_factory, load_worker_settings


def main() -> None:
    settings = load_worker_settings()
    if settings.database_url:
        session_factory = build_session_factory(settings.database_url)
        processed = GenerationWorker(session_factory=session_factory).process_available_requests()
        print(
            f"Meal Planner worker processed {processed} queued request(s) from '{settings.queue_name}'."
        )
        return
    print(f"Meal Planner worker scaffold ready for queue '{settings.queue_name}'.")


if __name__ == "__main__":
    main()
