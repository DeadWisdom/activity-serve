# Activity Bus: Spec vs Implementation Analysis

## Spec Summary

The SPEC.md describes a Python library called "Activity Bus" for processing Activity Streams 2.0 activities via a rule-based engine. It defines:

- An `ActivityBus` class with `submit()`, `process()`, and `process_next()` methods
- A submit workflow that validates, generates IDs, stores, and enqueues activities
- A process workflow that matches behaviors via JSON-LD frame matching and executes them
- A `@when` decorator for registering behaviors with pattern matching
- Error handling that converts failed activities to Tombstones with error results
- Integration with a separate `ActivityStore` library for persistence
- An error hierarchy rooted at `ActivityBusError`

---

## Implemented

### ActivityBus class with correct API shape
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 25-46
- The class has `queue` (asyncio.Queue), `store` (ActivityStore), and `namespace` (str) attributes, matching the spec's API section.
- Constructor accepts optional `store` and `namespace` parameters.

### submit() - Validation of required fields
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 65-69
- Validates presence of `actor` and `type` fields, raising `InvalidActivityError` on missing fields. This matches the spec: "Must contain at minimum: actor, type".

### submit() - Timestamp setting
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 76-77
- Sets `published` timestamp if not present, using `datetime.datetime.now(datetime.timezone.utc).isoformat()`. Matches spec: "On submission, published timestamp is set."

### submit() - Store and enqueue
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 83-87
- Stores activity via `self.store.store(activity)` and enqueues via `self.queue.put_nowait(activity)`. Matches spec steps 4 and 5.

### submit() - Result field initialization
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 79-81
- Initializes `result` as an empty list if not present. Consistent with the spec's "Result Field" section.

### process_next() - Dequeue and process
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 91-113
- Dequeues from `self.queue` and calls `self.process()`. Returns `None` if queue is empty. Matches spec step 1.

### process() - Behavior matching via frame()
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 133-139
- Fetches all behaviors via `get_all_behaviors()` and matches using `frame(activity, behavior_data["when"], require_match=True)`. Matches spec steps 2-3.

### process() - Execute matching behaviors
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 140-154
- Calls the behavior function and handles returned lists of new activities by submitting them with `context` set to the parent activity ID. Matches spec steps 4-5.

### process() - Error handling with Tombstone conversion
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 156-199
- On exception: appends an Error object to `activity["result"]`, converts to Tombstone via `store.convert_to_tombstone()`, stores the Tombstone. Matches spec step 6 in structure.

### @when decorator
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/behaviors.py`, lines 13-47
- Registers behavior functions with pattern matching. Auto-generates IDs from `module.function` or accepts custom `id` keyword. Matches the spec's Behaviors section.

### Behavior ID format
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/behaviors.py`, lines 32-36
- Generates IDs as `/sys/behaviors/{module}.{function}`, matching the spec example `/sys/behaviors/notes.create_note`.

### Error hierarchy
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/errors.py`, lines 6-33
- Implements `ActivityBusError` (base), `InvalidActivityError`, `ActivityIdError`, `BehaviorExecutionError`, `BehaviorRegistrationError`. Matches spec's Error Handling section.

### Standard note behaviors
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/standard/notes.py`
- Implements `create_note`, `update_note`, `delete_note`, and `create_reply` behaviors. These are implementation details beyond the spec but demonstrate the system working.

### ActivityStore integration
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 11-15, 42, 84, 170, 194, 197
- Defaults to `ActivityStore()` if none provided. Uses `store.store()`, `store.convert_to_tombstone()`. Matches the spec's "Activity Store Integration" section.

---

## Partially Implemented

### Error result preservation during Tombstone conversion
- **Spec:** "Append an ephemeral Error object to activity['result']" then "Convert activity to Tombstone"
- **Implementation:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 174-199
- The code appends the error to `activity["result"]` (line 191), but then calls `store.convert_to_tombstone(activity)` (line 194) which returns a new Tombstone dict. The Tombstone does not carry the `result` field. The error data is appended to the original `activity` dict but is not persisted -- only the Tombstone is stored (line 197). The spec implies the error should be accessible after processing, but it is effectively lost.

### Error object format
- **Spec:** `{"type": "Error", "content": "<stacktrace>", "context": activity["id"]}`
- **Implementation:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 158-163
- The implementation adds an extra field `error_type` not in the spec. Minor deviation but the core fields match.

---

## Not Implemented

### ID generation when missing
- **Spec (line 21-22):** "If id is not present, it is generated: /users/<user-id>/outbox/<nanoid>"
- **Implementation:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, line 72-73
- Instead of generating an ID, the code raises `InvalidActivityError("Activity must have an 'id'")`. The `nanoid` package is listed as a dependency in `pyproject.toml` (line 9) but is never imported or used anywhere. `uuid` is imported on line 8 of `bus.py` but also never used. The PLAN.md marks this as complete (line 38: "ID check/generation using nanoid"), but it is not implemented.
- **Impact:** The test `test_submit_valid_activity` (test_bus.py:74-97) submits an activity without an `id` and expects one to be generated. This test fails.

### ID scope validation
- **Spec (line 23):** "Must be scoped under actor's URI; otherwise, rejected"
- **Implementation:** No scope validation exists anywhere in `bus.py`. The `ActivityIdError` exception class is defined in `errors.py` (line 18) but is never raised in any source file.
- **Impact:** The test `test_submit_invalid_id_scope` (test_bus.py:167-187) expects an `ActivityIdError` with message "not properly scoped under actor". This test fails.

### _extract_user_id helper method
- **Spec (line 22):** ID generation pattern `/users/<user-id>/outbox/<nanoid>` implies extracting a user ID from the actor field.
- **Implementation:** Three tests in `test_bus.py` (lines 282-313) call `bus._extract_user_id(...)`, but this method does not exist on `ActivityBus`. All three tests fail with `AttributeError`.

### Behaviors stored in ActivityStore at /sys/behaviors
- **Spec (lines 67-76):** Behaviors should be stored as Activity Streams objects in `/sys/behaviors` via ActivityStore, and `process()` should "Fetch all behaviors from /sys/behaviors".
- **Implementation:** Behaviors are only stored in a global in-memory `BehaviorRegistry` singleton (`registry.py`, line 52). The `process()` method reads from this registry via `get_all_behaviors()` (`bus.py`, line 134), never from ActivityStore. PLAN.md marks this as complete (line 48), but it is not implemented.

### Async behavior support
- **Spec (Design Goals):** "Clean, async-first interface" and "Support for asynchronous and dynamic rule processing"
- **Implementation:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, line 143
- Behavior functions are called synchronously: `result = function(activity)`. If a behavior is an async function, the coroutine object would be returned instead of being awaited. There is no `await` or `asyncio.iscoroutine()` check.

### Delivery as pluggable behavior
- **Spec (lines 122-123):** "No built-in delivery logic. Defined as a pluggable Behavior (e.g., deliver_to_targets(activity))"
- **Implementation:** No delivery behavior exists. This is stated as "no built-in" which is technically correct, but there is also no example or documentation showing how one would implement it.

---

## Deviations

### ID handling: rejection instead of generation
- **Spec:** Generate ID if missing using nanoid pattern
- **Implementation:** Raises `InvalidActivityError` if ID is missing
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, line 72-73
- This is the most significant deviation. The spec describes a permissive submit that auto-assigns IDs; the implementation requires them upfront.

### Behavior matching source
- **Spec:** "Fetch all behaviors from /sys/behaviors" (implying from ActivityStore)
- **Implementation:** Fetches from in-memory registry via `get_all_behaviors()`
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, line 134
- The spec envisions behaviors as stored Activity Streams objects; the implementation treats them as Python-only runtime registrations.

### Error handling stops further behavior execution
- **Spec (line 48):** "Execute builtin for each matching behavior" (implies all matching behaviors run)
- **Implementation:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 156-167
- When a behavior raises an exception, the inner `except` block raises `BehaviorExecutionError`, which is caught by the outer `except` on line 174. This immediately converts to a Tombstone and no further behaviors execute. The spec implies all behaviors should be attempted.

### Tombstone does not include error result
- **Spec (line 50):** Append error to `activity["result"]`, then convert to Tombstone
- **Implementation:** Error is appended to the original `activity["result"]` dict, but `convert_to_tombstone()` returns a new dict without `result`. Only the Tombstone (without errors) is stored.
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 191-197

### Error object has extra field
- **Spec:** `{"type": "Error", "content": "<stacktrace>", "context": activity["id"]}`
- **Implementation:** Adds `"error_type": type(e).__name__` as an additional field
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, lines 158-163

---

## Implementation Beyond Spec

### Standard note behaviors module
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/standard/notes.py`
- The spec mentions behaviors only abstractly. The implementation includes concrete behaviors for `create_note`, `update_note`, `delete_note`, and `create_reply` with validation logic, logging, and notification generation.

### BehaviorRegistrationError
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/errors.py`, line 30
- Defined but never raised anywhere. Not mentioned in the spec's error list.

### Dual behavior matching on replies
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/standard/notes.py`, lines 11 and 95
- A reply Note matches both `create_note` (pattern: `{"type": "Create", "object": {"type": "Note"}}`) and `create_reply` (pattern adds `"inReplyTo": {"@exists": True}`). Both behaviors execute when a reply is submitted. There is no priority or exclusion mechanism, and this overlap is not documented.

### Notification activity generation
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/standard/notes.py`, lines 130-138
- `create_reply` returns a Notification activity. This activity lacks an `id` field, which would fail submission since the implementation requires IDs (deviation from spec notwithstanding).

### namespace attribute
- **File:** `/Users/deadwisdom/Projects/activity-bus/activity_bus/bus.py`, line 45
- The `namespace` attribute is stored but never used anywhere in the codebase. It appears in the spec API section but the spec does not describe what it is for.

### Unused dependencies
- **File:** `/Users/deadwisdom/Projects/activity-bus/pyproject.toml`
- `pyyaml` (line 8): declared but never imported anywhere in the source
- `nanoid` (line 9): declared but never imported (should be used for ID generation)
- `asyncio` (line 11 via `uv`): `uv` is a build tool listed as a runtime dependency
- `uuid` imported in `bus.py` line 8 but never used

### Dev dependencies as runtime dependencies
- **File:** `/Users/deadwisdom/Projects/activity-bus/pyproject.toml`, lines 11-14
- `uv`, `pytest`, `pytest-asyncio`, and `ruff` are listed under `dependencies` rather than dev/optional dependencies. Anyone installing this library as a dependency would also install the test runner and linter.

### PLAN.md claims vs reality
- **File:** `/Users/deadwisdom/Projects/activity-bus/PLAN.md`
- Several items are marked complete that are not actually implemented:
  - Line 38: "ID check/generation using nanoid" -- not implemented
  - Line 39: "Scope validation" -- not implemented
  - Line 48: "Store each behavior in /sys/behaviors" -- not implemented
  - Line 76: "ID generation" tests -- tests exist but fail
  - Line 80: "Integration tests for end-to-end submit() + process_next()" -- all tests use mocks, no integration tests exist

---

## Test Status Summary

Of the 30 tests in the test suite, 5 are expected to fail based on code analysis:

| Test | File | Reason |
|------|------|--------|
| `test_submit_valid_activity` | test_bus.py:74 | Submits without `id`, expects auto-generation; implementation raises error |
| `test_submit_invalid_id_scope` | test_bus.py:167 | Expects `ActivityIdError`; scope validation not implemented |
| `test_extract_user_id_string` | test_bus.py:283 | Calls `bus._extract_user_id()`; method does not exist |
| `test_extract_user_id_object` | test_bus.py:293 | Same as above |
| `test_extract_user_id_invalid` | test_bus.py:303 | Same as above |
