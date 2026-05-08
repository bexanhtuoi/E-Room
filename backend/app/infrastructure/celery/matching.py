from __future__ import annotations

from app.infrastructure.celery import celery_app


@celery_app.task(name="app.tasks.matching.run_matchmaking_tick")
def run_matchmaking_tick() -> dict[str, str]:
    return {"status": "ok", "task": "matchmaking_tick"}
