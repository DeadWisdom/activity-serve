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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
