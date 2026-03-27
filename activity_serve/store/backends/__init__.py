"""Backend implementations for the activity store."""

from activity_serve.store.backends.memory import InMemoryStorageBackend, InMemoryCacheBackend

__all__ = ["InMemoryStorageBackend", "InMemoryCacheBackend"]


def __getattr__(name):
    if name == "ElasticsearchBackend":
        from activity_serve.store.backends.elasticsearch import ElasticsearchBackend
        return ElasticsearchBackend
    if name == "RedisCacheBackend":
        from activity_serve.store.backends.redis import RedisCacheBackend
        return RedisCacheBackend
    if name == "FirestoreBackend":
        from activity_serve.store.backends.firestore import FirestoreBackend
        return FirestoreBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
