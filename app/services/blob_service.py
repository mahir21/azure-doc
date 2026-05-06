from azure.storage.blob import BlobServiceClient
from app.core.config import BLOB_CONNECTION_STRING, BLOB_CONTAINER

blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
container = blob_service.get_container_client(BLOB_CONTAINER)

try:
    container.create_container()
except Exception:
    pass


def upload_file(filename: str, content: bytes) -> str:
    blob = container.get_blob_client(filename)
    blob.upload_blob(content, overwrite=True)
    return blob.url