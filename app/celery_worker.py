import os
from celery import Celery
from .rag_engine import retrieve_and_generate

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery("rag_worker", broker=redis_url, backend=redis_url)

@celery.task
def generate_quiz_task(job_id, book_id, unit, topic):
    # We accept job_id as arg but we might not use it if we rely on celery task id.
    # But let's log it.
    print(f"Processing user-job-id: {job_id}")
    return retrieve_and_generate(book_id, unit, topic)
