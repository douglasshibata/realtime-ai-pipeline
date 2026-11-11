import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import redis.asyncio as aioredis

from app.config import settings
from app.worker import process_text_task, publish_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Real-Time AI Intelligence & Ingestion Pipeline API with non-blocking SSE streaming.",
    version="1.0.0"
)

# CORS Middleware enabling cross-origin requests from frontend UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    text: str = Field(..., description="Raw text payload (review, log, or news item) to be analyzed.")
    source: Optional[str] = Field("general", description="Data source identifier (e.g., 'customer_feedback', 'security_logs').")

class IngestResponse(BaseModel):
    task_id: str
    status: str
    message: str

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": settings.PROJECT_NAME}

@app.post("/api/ingest", response_model=IngestResponse, status_code=202)
async def ingest_text(payload: IngestRequest):
    """
    Data Ingestion Endpoint:
    Accepts raw unstructured text, generates a task_id, enqueues the Celery worker task,
    broadcasts initial 'queued' status, and returns task_id immediately.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text payload cannot be empty.")

    task_id = str(uuid.uuid4())
    logger.info(f"Ingesting text payload. Assigned task_id: {task_id}")

    # Dispatch Celery background worker task asynchronously
    process_text_task.delay(task_id, payload.text, payload.source)

    # Broadcast initial queued event over Redis Pub/Sub
    publish_event(task_id, "queued", payload={"source": payload.source})

    return IngestResponse(
        task_id=task_id,
        status="queued",
        message="Task queued for asynchronous AI processing and search indexing."
    )

@app.get("/api/stream/{task_id}")
async def stream_task_events(task_id: str, request: Request):
    """
    Real-Time Subscription Endpoint (Server-Sent Events - SSE):
    ----------------------------------------------------------
    This endpoint maintains an open HTTP connection with the client ('text/event-stream').
    It uses Python's `asyncio` and `redis.asyncio` to subscribe to the Redis Pub/Sub channel
    `task_channel:{task_id}` without blocking Uvicorn's main event loop thread.

    Why SSE avoids server thread blocking:
    1. Async Event Loop: `async for message in pubsub.listen()` yields control back to the event loop
       whenever no message is pending, allowing FastAPI to handle hundreds of concurrent SSE clients.
    2. Zero Polling: The server pushes updates directly when published by Celery workers.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        channel_name = f"task_channel:{task_id}"

        try:
            await pubsub.subscribe(channel_name)
            logger.info(f"Client connected to SSE stream for channel: {channel_name}")

            # Send initial connection handshake event
            init_event = {
                "task_id": task_id,
                "status": "connected",
                "message": f"Subscribed to real-time events for task {task_id}"
            }
            yield f"data: {json.dumps(init_event)}\n\n"

            # Non-blocking async loop waiting for Redis Pub/Sub messages
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE stream: {task_id}")
                    break

                try:
                    # Non-blocking get with timeout to allow disconnect checking & heartbeat
                    message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0)
                    if message and message["type"] == "message":
                        data_str = message["data"]
                        yield f"data: {data_str}\n\n"

                        # Parse payload to check if terminal state reached
                        try:
                            parsed = json.loads(data_str)
                            if parsed.get("status") in ["completed", "failed"]:
                                logger.info(f"Terminal status '{parsed.get('status')}' received for task {task_id}. Closing SSE stream.")
                                break
                        except Exception:
                            pass
                    else:
                        # Yield SSE ping heartbeat every cycle if idle to keep connection active
                        yield ": ping\n\n"

                except asyncio.TimeoutError:
                    # Send periodic ping to prevent proxies/browsers from timing out connection
                    yield ": ping\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {task_id}")
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()
            await redis_client.aclose()
            logger.info(f"Cleaned up Redis Pub/Sub resources for task {task_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Prevents Nginx/proxies from buffering SSE
        }
    )
