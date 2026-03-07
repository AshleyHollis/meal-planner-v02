from fastapi import FastAPI

from app.routers import grocery, inventory, planner, session


def health_check() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="Meal Planner API")

app.include_router(session.router)
app.include_router(inventory.router)
app.include_router(planner.router)
app.include_router(grocery.router)


@app.get("/health")
def read_health() -> dict[str, str]:
    return health_check()


@app.get("/api/v1/health")
def read_v1_health() -> dict[str, str]:
    return health_check()
