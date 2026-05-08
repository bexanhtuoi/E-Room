"""Background task definitions for Celery workers.

Each task module registers one or more ``@celery_app.task`` decorated
functions.  The Celery beat schedule in ``infrastructure/celery_app.py``
references them by fully-qualified name (``app.tasks.<module>.<function>``).

Organisation
------------
* **matching.py** — room matchmaking tick
* **moderation.py** — active-room content scan
* **ai.py** — AI agent / STT pipelines
* **rag.py** — document ingestion & vector index
* **tts.py** — text-to-speech synthesis
"""

from app.tasks.ai import run_ai_pipeline
from app.tasks.matching import run_matchmaking_tick
from app.tasks.moderation import scan_active_rooms
from app.tasks.rag import ingest_document
from app.tasks.tts import synthesize_speech

__all__ = [
    "ingest_document",
    "run_ai_pipeline",
    "run_matchmaking_tick",
    "scan_active_rooms",
    "synthesize_speech",
]