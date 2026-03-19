# activity-bus

Rule-based processing engine for Activity Streams 2.0 activities. Validates, enqueues, and executes declarative behaviors matched by pattern.

**Location:** `../activity-bus`
**Version:** 0.1.0
**Python:** >=3.10 (targets 3.13)

## Directory Structure

```
activity_bus/
├── __init__.py          # Exports: ActivityBus, when, error classes
├── bus.py               # Core ActivityBus class (submit, process, process_next)
├── behaviors.py         # @when decorator and get_all_behaviors()
├── registry.py          # BehaviorRegistry class (global singleton)
├── errors.py            # Exception hierarchy
└── standard/
    ├── __init__.py
    └── notes.py         # Standard behaviors: Create/Update/Delete Note, Reply

tests/
├── __init__.py
├── test_bus.py          # ActivityBus submit/process tests (11 tests)
├── test_behaviors.py    # @when decorator tests (4 tests)
├── test_registry.py     # Registry tests (3 tests)
└── test_notes.py        # Standard note behavior tests (11 tests)

conftest.py              # Pytest fixtures (clear_registry, mock_store, bus)
pytest.ini               # Pytest config (strict asyncio mode)
```

## Module Dependencies

```
__init__.py
├── bus.py
│   ├── activity_store (external: ActivityStore, ld.frame)
│   ├── behaviors.py (get_all_behaviors)
│   └── errors.py
├── behaviors.py
│   └── registry.py (global registry instance)
└── errors.py (no deps)

standard/notes.py
├── behaviors.py (@when decorator)
└── errors.py (InvalidActivityError)
```

## External Dependencies

| Package | Purpose |
|---------|---------|
| `activity-store` | Object storage + JSON-LD `frame()` for pattern matching |
| `pyyaml` | YAML parsing |
| `nanoid` | Short unique ID generation |

## Key APIs

### ActivityBus

```python
bus = ActivityBus(store=activity_store_instance)

await bus.submit(activity)       # Validate → store → enqueue
await bus.process_next()         # Dequeue and process one activity
await bus.process(activity)      # Process a specific activity directly
```

### Behavior Registration

```python
from activity_bus import when

@when({"type": "Create", "object": {"type": "Note"}})
def handle_create_note(activity):
    # Process activity
    activity["result"].append({"log": "Note created"})
    return [new_activity]  # Optional: return new activities to submit
```

Patterns support `@exists` operator for presence checks:
```python
@when({"type": "Create", "object": {"type": "Note", "inReplyTo": {"@exists": True}}})
def handle_reply(activity):
    ...
```

### Error Hierarchy

```
ActivityBusError
├── InvalidActivityError
│   └── ActivityIdError
├── BehaviorExecutionError
└── BehaviorRegistrationError
```

## Processing Pipeline

1. **Submit**: Validate activity (requires `actor`, `type`), set `published`, init `result` list, store in activity-store, enqueue
2. **Process**: Match all registered behaviors against activity using `frame()`, execute matches, collect returned activities
3. **Error handling**: Exceptions during behavior execution → error logged in `result`, activity converted to Tombstone

## Design Notes

- Behavior ID format: `/sys/behaviors/{module}.{function}` or custom via `id` param
- New activities returned by behaviors get `context` set to parent activity ID
- Registry is a global singleton, cleared between tests for isolation
- Pattern matching delegates to `activity_store.ld.frame()`
