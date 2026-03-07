import os


def load_worker_settings() -> dict[str, str]:
    queue_name = os.getenv("MEAL_PLANNER_QUEUE_NAME", "meal-planner-default")
    return {"queue_name": queue_name}


def main() -> None:
    settings = load_worker_settings()
    print(f"Meal Planner worker scaffold ready for queue '{settings['queue_name']}'.")


if __name__ == "__main__":
    main()
