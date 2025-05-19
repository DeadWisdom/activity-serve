from activity_store import ActivityStore
from activity_bus import ActivityBus
from app.core.settings import Settings


class ActivityComponents:
    """Global container for ActivityStore and ActivityBus components."""
    store: ActivityStore | None = None
    bus: ActivityBus | None = None


activity_components = ActivityComponents()


def init_activity_components(settings: Settings) -> None:
    """Initialize ActivityStore and ActivityBus based on configuration."""
    # Initialize activity store based on backend setting
    if settings.activity_store_backend == "elasticsearch" and settings.elasticsearch_url:
        from activity_store.backends.elasticsearch import ElasticsearchBackend
        backend = ElasticsearchBackend(settings.elasticsearch_url)
    else:
        from activity_store.backends.memory import MemoryBackend
        backend = MemoryBackend()
    
    # Initialize activity store cache based on cache setting
    if settings.activity_store_cache == "redis" and settings.redis_url:
        from activity_store.cache.redis import RedisCache
        cache = RedisCache(settings.redis_url)
    else:
        from activity_store.cache.memory import MemoryCache
        cache = MemoryCache()
    
    # Create the activity store with configured backend and cache
    activity_components.store = ActivityStore(backend=backend, cache=cache)
    
    # Create the activity bus using the activity store
    activity_components.bus = ActivityBus(store=activity_components.store)


def get_activity_store() -> ActivityStore:
    """Get the configured ActivityStore instance."""
    if activity_components.store is None:
        raise RuntimeError("ActivityStore not initialized.")
    return activity_components.store


def get_activity_bus() -> ActivityBus:
    """Get the configured ActivityBus instance."""
    if activity_components.bus is None:
        raise RuntimeError("ActivityBus not initialized.")
    return activity_components.bus