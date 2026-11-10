from redis import Redis
from rq import Queue

from app.config import REDIS_URL


def get_queue() -> Queue:
    return Queue("reviews", connection=Redis.from_url(REDIS_URL))


def enqueue_event(event_id: int) -> None:
    # The job is referenced by its import path, so the API never imports worker code.
    get_queue().enqueue("app.worker.process_event", event_id)
