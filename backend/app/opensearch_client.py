import logging
from typing import Dict, Any
from opensearchpy import OpenSearch
from app.config import settings

logger = logging.getLogger(__name__)

def get_opensearch_client() -> OpenSearch:
    """
    Initialize OpenSearch client with configuration settings.
    """
    auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD)
    client = OpenSearch(
        hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
        http_auth=auth,
        use_ssl=settings.OPENSEARCH_USE_SSL,
        verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )
    return client

def ensure_index_exists(client: OpenSearch, index_name: str = settings.OPENSEARCH_INDEX) -> None:
    """
    Create OpenSearch index with mapping if it doesn't already exist.
    """
    try:
        if not client.indices.exists(index=index_name):
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "task_id": {"type": "keyword"},
                        "original_text": {"type": "text"},
                        "source": {"type": "keyword"},
                        "sentiment": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "entities": {"type": "keyword"},
                        "summary": {"type": "text"},
                        "timestamp": {"type": "date"}
                    }
                }
            }
            client.indices.create(index=index_name, body=mapping)
            logger.info(f"OpenSearch index '{index_name}' created successfully.")
        else:
            logger.info(f"OpenSearch index '{index_name}' already exists.")
    except Exception as e:
        logger.warning(f"Unable to ensure OpenSearch index '{index_name}': {e}")

def index_insight_document(doc: Dict[str, Any], index_name: str = settings.OPENSEARCH_INDEX) -> Dict[str, Any]:
    """
    Index structured document into OpenSearch.
    """
    client = get_opensearch_client()
    ensure_index_exists(client, index_name)
    try:
        response = client.index(
            index=index_name,
            body=doc,
            id=doc.get("task_id"),
            refresh=True
        )
        logger.info(f"Indexed document {doc.get('task_id')} into OpenSearch index '{index_name}'.")
        return response
    except Exception as e:
        logger.error(f"Failed to index document in OpenSearch: {e}")
        return {"result": "error", "error": str(e)}
