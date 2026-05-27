from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
from app.config import settings
from app.utils.logger import logger


# ─── Field definitions ─────────────────────────────────────────────────────

def _laws_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="clause", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="visa_type", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="doc_version", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(
            name="embedding",
            dtype=DataType.FLOAT_VECTOR,
            dim=settings.EMBEDDING_DIMENSION,
        ),
    ]
    return CollectionSchema(
        fields=fields,
        description="USCIS laws and policy documents"
    )


def _cases_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="case_number", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="visa_type", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="year", dtype=DataType.INT64),
        FieldSchema(name="outcome", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="jurisdiction", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(
            name="embedding",
            dtype=DataType.FLOAT_VECTOR,
            dim=settings.EMBEDDING_DIMENSION,
        ),
    ]
    return CollectionSchema(
        fields=fields,
        description="Immigration legal case files"
    )


# ─── Index config ──────────────────────────────────────────────────────────

INDEX_PARAMS = {
    "metric_type": "COSINE",        # cosine similarity for legal text
    "index_type": "HNSW",           # fast approximate nearest neighbor
    "params": {"M": 16, "efConstruction": 256},
}


# ─── Connection & setup ────────────────────────────────────────────────────

def connect_milvus():
    """Connect to Milvus server."""
    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
    )
    logger.info(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")


def _create_collection_if_not_exists(name: str, schema: CollectionSchema) -> Collection:
    """Create collection and index if it doesn't already exist."""
    if utility.has_collection(name):
        logger.info(f"Milvus collection '{name}' already exists")
        return Collection(name)

    collection = Collection(name=name, schema=schema)
    collection.create_index(field_name="embedding", index_params=INDEX_PARAMS)
    logger.info(f"Created Milvus collection '{name}' with HNSW index")
    return collection


def setup_collections():
    """
    Called on app startup.
    Creates laws and cases collections if they don't exist.
    """
    connect_milvus()
    _create_collection_if_not_exists(
        settings.MILVUS_LAWS_COLLECTION,
        _laws_schema()
    )
    _create_collection_if_not_exists(
        settings.MILVUS_CASES_COLLECTION,
        _cases_schema()
    )
    logger.info("Milvus collections ready")


def get_laws_collection() -> Collection:
    try:
        connections.has_connection("default")
    except Exception:
        pass
    if not connections.has_connection("default") or not connections.get_connection_addr("default"):
        connect_milvus()
    col = Collection(settings.MILVUS_LAWS_COLLECTION)
    col.load()
    return col


def get_cases_collection() -> Collection:
    try:
        connections.has_connection("default")
    except Exception:
        pass
    if not connections.has_connection("default") or not connections.get_connection_addr("default"):
        connect_milvus()
    col = Collection(settings.MILVUS_CASES_COLLECTION)
    col.load()
    return col