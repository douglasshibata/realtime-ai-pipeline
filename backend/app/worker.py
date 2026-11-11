import json
import logging
from datetime import datetime, timezone
import redis
from app.celery_app import celery_app
from app.config import settings
from app.llm_extractor import extractor
from app.opensearch_client import index_insight_document

logger = logging.getLogger(__name__)

# Synchronous Redis client for Celery worker
redis_sync_client = redis.Redis.from_url(settings.REDIS_URL)

def publish_event(task_id: str, status: str, payload: dict = None):
    """
    Publish state update to Redis Pub/Sub channel.
    FastAPI SSE listener will receive this message and stream it to the client.
    """
    channel = f"task_channel:{task_id}"
    event_data = {
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {}
    }
    message = json.dumps(event_data)
    redis_sync_client.publish(channel, message)
    logger.info(f"Published status '{status}' for task {task_id} to Redis channel {channel}")

@celery_app.task(name="app.worker.process_text_task")
def process_text_task(task_id: str, text: str, source: str = "general"):
    """
    Celery task orchestrating LLM processing, OpenSearch indexing, and Redis Pub/Sub broadcasting.
    """
    logger.info(f"Starting execution for task {task_id}")

    # Step 1: Broadcast 'processing' status
    publish_event(task_id, "processing")

    # Step 2: Extract insights via LLM
    try:
        insights = extractor.extract_insights(text)
    except Exception as e:
        logger.error(f"Error during LLM extraction for task {task_id}: {e}")
        insights = {
            "sentiment": "Unknown",
            "entities": [],
            "category": "Error",
            "summary": f"Extraction failed: {str(e)}"
        }

    # Step 3: Broadcast 'indexing' status
    publish_event(task_id, "indexing")

    # Step 4: Prepare document for OpenSearch
    doc = {
        "task_id": task_id,
        "original_text": text,
        "source": source,
        "sentiment": insights.get("sentiment", "Neutral"),
        "category": insights.get("category", "General"),
        "entities": insights.get("entities", []),
        "summary": insights.get("summary", ""),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Step 5: Index in OpenSearch
    index_res = index_insight_document(doc)

    # Step 6: Broadcast 'completed' status with full result payload
    final_payload = {
        "insights": insights,
        "indexed": index_res.get("result") in ["created", "updated", "indexed"],
        "opensearch_index": settings.OPENSEARCH_INDEX,
        "document": doc
    }
    publish_event(task_id, "completed", payload=final_payload)

    return final_payload
