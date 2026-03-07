from app.main import load_worker_settings


def test_worker_has_default_queue_name() -> None:
    assert load_worker_settings()["queue_name"] == "meal-planner-default"
