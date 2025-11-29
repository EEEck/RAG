import os
import sys
from celery import Celery
from .rag_engine import retrieve_and_generate

# Ensure we can import from ingest if running from app directory or root
# If running as 'python -m app.celery_worker', root is in sys.path
try:
    from ingest.vision_enricher import VisionEnricher
except ImportError:
    # If running from app/ dir directly (unlikely for celery but possible for testing)
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from ingest.vision_enricher import VisionEnricher

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery("rag_worker", broker=redis_url, backend=redis_url)

@celery.task
def generate_quiz_task(job_id, book_id, unit, topic):
    # We accept job_id as arg but we might not use it if we rely on celery task id.
    # But let's log it.
    print(f"Processing user-job-id: {job_id}")
    return retrieve_and_generate(book_id, unit, topic)

@celery.task
def enrich_images_task(batch_size=10):
    """
    Celery task to run the vision enrichment process.
    Scans for pending images and generates descriptions.
    """
    print(f"Starting image enrichment task (batch_size={batch_size})...")
    enricher = VisionEnricher()
    enricher.process_batch(batch_size=batch_size)
    print("Image enrichment task complete.")
