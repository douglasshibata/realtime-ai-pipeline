import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.llm_extractor import extractor
from app.worker import process_text_task

client = TestClient(app)

def test_health_check():
    """Verify health check endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch("app.main.process_text_task.delay")
@patch("app.main.publish_event")
def test_ingest_endpoint_success(mock_publish, mock_celery_delay):
    """Verify ingestion endpoint enqueues background task and returns task_id."""
    payload = {
        "text": "Payment failed during checkout with card error 4002.",
        "source": "customer_feedback"
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"
    mock_celery_delay.assert_called_once()
    mock_publish.assert_called_once()

def test_ingest_endpoint_empty_text():
    """Verify empty text submission is rejected with 400 Bad Request."""
    payload = {"text": "   ", "source": "logs"}
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 400

def test_llm_extractor_heuristics():
    """Verify heuristic LLM extractor correctly identifies sentiment and categories."""
    # Test Negative Billing
    res_neg = extractor.extract_insights("Billing error: double charge on invoice #9042!")
    assert res_neg["sentiment"] == "Negative"
    assert "Billing" in res_neg["category"]

    # Test Positive Feedback
    res_pos = extractor.extract_insights("Awesome service, fast performance and love the smooth interface!")
    assert res_pos["sentiment"] == "Positive"

    # Test Neutral
    res_neu = extractor.extract_insights("System updated at 10:00 AM UTC.")
    assert res_neu["sentiment"] == "Neutral"

@patch("app.worker.index_insight_document")
@patch("app.worker.publish_event")
def test_worker_process_text_task(mock_publish, mock_index_doc):
    """Verify Celery task pipeline executes extraction, indexing, and Pub/Sub broadcasting."""
    mock_index_doc.return_value = {"result": "created"}

    task_id = "test-task-12345"
    text = "Critical error in database connection pool!"
    source = "security_logs"

    result = process_text_task(task_id, text, source)

    assert result["insights"]["sentiment"] == "Negative"
    assert result["indexed"] is True
    assert result["document"]["task_id"] == task_id
    assert result["document"]["source"] == source

    # Verify publish_event was called for processing, indexing, and completed states
    published_statuses = [call[0][1] for call in mock_publish.call_args_list]
    assert "processing" in published_statuses
    assert "indexing" in published_statuses
    assert "completed" in published_statuses

@patch("redis.asyncio.from_url")
def test_sse_stream_endpoint_headers(mock_redis_from_url):
    """Verify SSE streaming endpoint returns proper event-stream content headers."""
    mock_redis = AsyncMock()
    mock_pubsub = AsyncMock()

    # pubsub() is a synchronous method on aioredis.Redis returning pubsub instance
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis_from_url.return_value = mock_redis

    # Return completion message on get_message
    mock_pubsub.get_message.return_value = {
        "type": "message",
        "data": json.dumps({"task_id": "test-task-999", "status": "completed", "payload": {}})
    }

    with client.stream("GET", "/api/stream/test-task-999") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "no-cache" in response.headers["cache-control"]
