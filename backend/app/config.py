import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Real-Time AI Intelligence & Ingestion Pipeline"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    OPENSEARCH_HOST: str = os.getenv("OPENSEARCH_HOST", "localhost")
    OPENSEARCH_PORT: int = int(os.getenv("OPENSEARCH_PORT", "9200"))
    OPENSEARCH_USER: str = os.getenv("OPENSEARCH_USER", "admin")
    OPENSEARCH_PASSWORD: str = os.getenv("OPENSEARCH_PASSWORD", "admin")
    OPENSEARCH_USE_SSL: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"
    OPENSEARCH_VERIFY_CERTS: bool = os.getenv("OPENSEARCH_VERIFY_CERTS", "false").lower() == "true"
    OPENSEARCH_INDEX: str = os.getenv("OPENSEARCH_INDEX", "insights_index")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEEPINFRA_API_KEY: str = os.getenv("DEEPINFRA_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

settings = Settings()
