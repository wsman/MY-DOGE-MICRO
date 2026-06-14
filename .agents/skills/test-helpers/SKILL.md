---
name: test-helpers
description: "Generate test helper libraries for the project's test suite. Game: engine-specific helpers (Godot, Unity, Unreal). Product: language-appropriate helpers (pytest fixtures, vitest factories, etc.). Reads existing test patterns and produces tests/helpers/ with assertion utilities, factory functions, and mock objects tailored to the project's systems."
argument-hint: "[system-name | all | scaffold]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write
---

## User Guide

- When to use: Generate test helper libraries for the project's test suite. Game: engine-specific helpers (Godot, Unity, Unreal). Product: language-appropriate helpers (pytest fixtures, vitest factories, etc.). Reads existing test patterns and produces tests/helpers/ with assertion utilities, factory functions, and mock objects tailored to the project's systems.
- Inputs: Command arguments: `/test-helpers [system-name | all | scaffold]`; project artifacts referenced below; user decisions and approvals before writes.
- Outputs: Primary artifacts, reports, or conversation guidance described below; write files only after user approval.
- Memory-bank writes: None.
- Next steps: Follow the workflow hand-off or next-step guidance below; recommendations do not auto-run and require explicit user command/approval.

# Test Helpers

Writing test cases is faster and more consistent when common setup, teardown,
and assertion patterns are abstracted into helpers. This skill generates a
`tests/helpers/` library tailored to the project's actual engine/stack, language,
and systems — so every developer writes less boilerplate and more assertions.

**Output:** `tests/helpers/` directory with domain-specific helper files

**When to run:**
- After `/test-setup` scaffolds the framework (first time)
- When multiple test files repeat the same setup boilerplate
- When starting to write tests for a new system

---

## Phase 0: Domain Detection

Check for concept documents in `design/cdd/`:
- `design/cdd/game-concept.md` → `[Game]` paths below
- `design/cdd/product-concept.md` → `[Product]` paths below
- Neither → default to game paths (backward compatible)

---

## 1. Parse Arguments

**Modes:**
- `/test-helpers [system-name]` — generate helpers for a specific system
  (e.g., `/test-helpers combat`)
- `/test-helpers all` — generate helpers for all systems with test files
- `/test-helpers scaffold` — generate only the base helper library (no
  system-specific helpers); use this on first run
- No argument — run `scaffold` if no helpers exist, else `all`

---

## 2. Detect Engine/Language/Stack

Read `standards/technical-preferences.md` and extract:
- `Engine:` value (if game)
- `Language:` value
- `Framework:` from the Testing section

**[Game]** If engine is not configured: "Engine not configured. Run `/setup-engine` first."
**[Product]** If language is not configured: "Language/stack not configured. Run `/setup-engine` first."

---

## 3. Load Existing Test Patterns

Scan the test directory for patterns already in use:

```
Glob pattern="tests/**/*_test.*" (all test files)
```

For a representative sample (up to 5 files), read the test files and extract:
- Setup patterns (how `before_each` / `setUp` / fixtures are written)
- Common assertion patterns (what is being asserted most often)
- Object creation patterns (how game objects or scenes are instantiated in tests)
- Mock/stub patterns (how dependencies are replaced)

This ensures generated helpers match the project's existing style, not a
generic template.

Also read:
- `design/cdd/module-index.md` — to know which systems exist
- In-scope GDD(s) — to understand what data types and values need testing
- `docs/architecture/tr-registry.yaml` — to map requirements to tested systems

---

## 4. Generate Engine-Specific Helpers

### Godot 4 (GDUnit4 / GDScript)

**Base helper** (`tests/helpers/game_assertions.gd`):

```gdscript
## Game-specific assertion utilities for [Project Name] tests.
## Extends GdUnitAssertions with domain-specific helpers.
##
## Usage:
##   var assert = GameAssertions.new()
##   assert.health_in_range(entity, 0, entity.max_health)

class_name GameAssertions
extends RefCounted

## Assert a value is within the inclusive range [min_val, max_val].
## Use for any formula output that has defined bounds in a CDD.
static func assert_in_range(
    value: float,
    min_val: float,
    max_val: float,
    label: String = "value"
) -> void:
    assert(
        value >= min_val and value <= max_val,
        "%s %.2f is outside expected range [%.2f, %.2f]" % [label, value, min_val, max_val]
    )

## Assert a signal was emitted during a callable block.
## Usage: assert_signal_emitted(entity, "health_changed", func(): entity.take_damage(10))
static func assert_signal_emitted(
    obj: Object,
    signal_name: String,
    action: Callable
) -> void:
    var emitted := false
    obj.connect(signal_name, func(_args): emitted = true)
    action.call()
    assert(emitted, "Expected signal '%s' to be emitted, but it was not." % signal_name)

## Assert that a callable does NOT emit a signal.
static func assert_signal_not_emitted(
    obj: Object,
    signal_name: String,
    action: Callable
) -> void:
    var emitted := false
    obj.connect(signal_name, func(_args): emitted = true)
    action.call()
    assert(not emitted, "Expected signal '%s' NOT to be emitted, but it was." % signal_name)

## Assert a node exists at path within a parent.
static func assert_node_exists(parent: Node, path: NodePath) -> void:
    assert(
        parent.has_node(path),
        "Expected node at path '%s' to exist." % str(path)
    )
```

**Factory helper** (`tests/helpers/game_factory.gd`):

```gdscript
## Factory functions for creating test game objects.
## Returns minimal objects configured for unit testing (no scene tree required).
##
## Usage: var player = GameFactory.make_player(health: 100)

class_name GameFactory
extends RefCounted

## Create a minimal player-like object for testing.
## Override fields as needed.
static func make_player(health: int = 100) -> Node:
    var player = Node.new()
    player.set_meta("health", health)
    player.set_meta("max_health", health)
    return player
```

**Scene helper** (`tests/helpers/scene_runner_helper.gd`):

```gdscript
## Utilities for scene-based integration tests.
## Wraps GdUnitSceneRunner for common patterns.

class_name SceneRunnerHelper
extends GdUnitTestSuite

## Load a scene and wait one frame for _ready() to complete.
func load_scene_and_wait(scene_path: String) -> Node:
    var scene = load(scene_path).instantiate()
    add_child(scene)
    await get_tree().process_frame
    return scene
```

---

### Unity (NUnit / C#)

**Base helper** (`tests/helpers/GameAssertions.cs`):

```csharp
using NUnit.Framework;
using UnityEngine;

/// <summary>
/// Game-specific assertion utilities for [Project Name] tests.
/// Extends NUnit's Assert with domain-specific helpers.
/// </summary>
public static class GameAssertions
{
    /// <summary>
    /// Assert a value is within an inclusive range [min, max].
    /// Use for any formula output defined in CDD Formulas sections.
    /// </summary>
    public static void AssertInRange(float value, float min, float max, string label = "value")
    {
        Assert.That(value, Is.InRange(min, max),
            $"{label} ({value:F2}) is outside expected range [{min:F2}, {max:F2}]");
    }

    /// <summary>Assert a UnityEvent or C# event was raised during an action.</summary>
    public static void AssertEventRaised(ref bool wasCalled, System.Action action, string eventName)
    {
        wasCalled = false;
        action();
        Assert.IsTrue(wasCalled, $"Expected event '{eventName}' to be raised, but it was not.");
    }

    /// <summary>Assert a component exists on a GameObject.</summary>
    public static void AssertHasComponent<T>(GameObject obj) where T : Component
    {
        var component = obj.GetComponent<T>();
        Assert.IsNotNull(component,
            $"Expected GameObject '{obj.name}' to have component {typeof(T).Name}.");
    }
}
```

**Factory helper** (`tests/helpers/GameFactory.cs`):

```csharp
using UnityEngine;

/// <summary>
/// Factory methods for creating minimal test objects without loading scenes.
/// </summary>
public static class GameFactory
{
    /// <summary>Create a minimal GameObject with a named component for testing.</summary>
    public static GameObject MakeGameObject(string name = "TestObject")
    {
        var go = new GameObject(name);
        return go;
    }

    /// <summary>
    /// Create a ScriptableObject of type T for data-driven tests.
    /// Dispose with Object.DestroyImmediate after test.
    /// </summary>
    public static T MakeScriptableObject<T>() where T : ScriptableObject
    {
        return ScriptableObject.CreateInstance<T>();
    }
}
```

---

### Unreal Engine (C++)

**Base helper** (`tests/helpers/GameTestHelpers.h`):

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

/**
 * Game-specific assertion macros and helpers for [Project Name] automation tests.
 * Include in any test file that needs domain-specific assertions.
 *
 * Usage:
 *   GAME_TEST_ASSERT_IN_RANGE(TestName, DamageValue, 10.0f, 50.0f, TEXT("Damage"));
 */

// Assert a float value is within inclusive range [Min, Max]
#define GAME_TEST_ASSERT_IN_RANGE(TestName, Value, Min, Max, Label) \
    TestTrue( \
        FString::Printf(TEXT("%s (%.2f) in range [%.2f, %.2f]"), Label, Value, Min, Max), \
        (Value) >= (Min) && (Value) <= (Max) \
    )

// Assert a UObject pointer is valid (not null, not garbage collected)
#define GAME_TEST_ASSERT_VALID(TestName, Ptr, Label) \
    TestTrue( \
        FString::Printf(TEXT("%s is valid"), Label), \
        IsValid(Ptr) \
    )

// Assert an Actor is in the world (spawned successfully)
#define GAME_TEST_ASSERT_SPAWNED(TestName, ActorPtr, ClassName) \
    TestNotNull( \
        FString::Printf(TEXT("Spawned actor of class %s"), TEXT(#ClassName)), \
        ActorPtr \
    )

/**
 * Helper to create a minimal test world.
 * Remember to call World->DestroyWorld(false) in teardown.
 */
namespace GameTestHelpers
{
    inline UWorld* CreateTestWorld(const FString& WorldName = TEXT("TestWorld"))
    {
        UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
        FWorldContext& WorldContext = GEngine->CreateNewWorldContext(EWorldType::Game);
        WorldContext.SetCurrentWorld(World);
        return World;
    }
}
```

---

### [Product] Language-Specific Helpers

#### Python (pytest)

**Base helper** (`tests/helpers/conftest.py` — auto-loaded by pytest):

```python
"""Shared fixtures and assertion helpers for [Project Name] tests.

Usage: fixtures in this file are auto-discovered by pytest.
No explicit import needed — just use fixture names as test arguments.
"""
import pytest
from typing import Any, Callable


@pytest.fixture
def app_client():
    """Create a test client for the application.
    Override in your own conftest.py for app-specific setup.
    """
    # Import your app factory here
    # from myapp import create_app
    # app = create_app(testing=True)
    # return app.test_client()
    raise NotImplementedError("Implement app_client for your application")


@pytest.fixture
def db_session():
    """Create a clean database session for a test, rolled back after.
    Use for any test that reads/writes to the database.
    """
    # Import your DB session here
    raise NotImplementedError("Implement db_session for your database")


def assert_response_ok(response, status_code: int = 200):
    """Assert response has expected status code and valid JSON body."""
    assert response.status_code == status_code, \
        f"Expected {status_code}, got {response.status_code}: {response.data[:200]}"


def assert_validation_error(response, field: str):
    """Assert response is a 422 with validation error for the given field."""
    assert response.status_code == 422
    data = response.get_json()
    assert "errors" in data or "detail" in data
    error_str = str(data)
    assert field in error_str, f"Expected error about '{field}', got: {error_str[:200]}"


def assert_paginated(response, expected_total: int = None):
    """Assert response contains pagination metadata."""
    data = response.get_json()
    assert "items" in data or "data" in data, "Response missing paginated items"
    if expected_total is not None:
        meta = data.get("meta", data)
        assert meta.get("total") == expected_total or len(data.get("items", data.get("data", []))) <= expected_total
```

**Factory helper** (`tests/helpers/factories.py`):

```python
"""Minimal factory functions for creating test objects.

Use these instead of constructing objects manually in every test.
"""
from datetime import datetime, timezone


def make_user(**overrides) -> dict:
    """Create a minimal user dict for API tests."""
    return {
        "id": overrides.get("id", 1),
        "email": overrides.get("email", "test@example.com"),
        "name": overrides.get("name", "Test User"),
        **overrides
    }


def make_timestamp() -> str:
    """Return a consistent ISO timestamp for test data."""
    return datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
```

#### TypeScript / Node (Vitest / Jest)

**Base helper** (`tests/helpers/test-utils.ts`):

```typescript
/**
 * Shared test utilities for [Project Name].
 *
 * Usage: import { createTestApp, assertOk } from '../helpers/test-utils';
 */
import { expect } from 'vitest'; // or '@jest/globals'

/** Minimal type for a HTTP response in tests. */
interface TestResponse {
  status: number;
  body: unknown;
  headers?: Record<string, string>;
}

/** Assert response has expected status code. */
export function assertOk(res: TestResponse, expectedStatus = 200): void {
  if (res.status !== expectedStatus) {
    const bodyStr = JSON.stringify(res.body).slice(0, 200);
    throw new Error(`Expected ${expectedStatus}, got ${res.status}: ${bodyStr}`);
  }
}

/** Assert response is a validation error (422). */
export function assertValidationError(res: TestResponse, field: string): void {
  expect(res.status).toBe(422);
  const body = JSON.stringify(res.body);
  expect(body).toContain(field);
}

/** Assert response is paginated with items array. */
export function assertPaginated(res: TestResponse, maxItems?: number): void {
  const body = res.body as Record<string, unknown>;
  const items = body.items ?? body.data;
  expect(Array.isArray(items)).toBe(true);
  if (maxItems !== undefined) {
    expect((items as unknown[]).length).toBeLessThanOrEqual(maxItems);
  }
}
```

**Factory helper** (`tests/helpers/factories.ts`):

```typescript
/** Minimal factory functions for creating test objects. */

export interface TestUser {
  id: number;
  email: string;
  name: string;
}

export function makeUser(overrides: Partial<TestUser> = {}): TestUser {
  return {
    id: 1,
    email: 'test@example.com',
    name: 'Test User',
    ...overrides,
  };
}
```

#### Rust (cargo test)

**Base helper** (`tests/helpers/mod.rs`):

```rust
/// Shared test utilities for [Project Name].
/// Include with: `mod helpers;` in tests or `#[path = "helpers/mod.rs"] mod helpers;`

use std::fmt::Debug;

/// Assert that a Result is Ok and return the inner value.
/// Use in tests where you need the value immediately on success.
pub fn assert_ok<T, E: Debug>(result: Result<T, E>) -> T {
    match result {
        Ok(val) => val,
        Err(e) => panic!("Expected Ok, got Err({:?})", e),
    }
}

/// Assert that two values are within epsilon of each other.
/// Useful for floating-point comparisons in formula tests.
pub fn assert_near(a: f64, b: f64, epsilon: f64) {
    assert!(
        (a - b).abs() < epsilon,
        "assertion failed: `(left ≈ right)`\n  left: `{}`,\n right: `{}`,\n epsilon: `{}`",
        a, b, epsilon
    );
}

/// Assert a string contains a substring, with a helpful panic message.
pub fn assert_contains(haystack: &str, needle: &str) {
    assert!(
        haystack.contains(needle),
        "assertion failed: string does not contain expected substring\n  string: `{}`\n  expected substring: `{}`",
        haystack, needle
    );
}
```

**Factory helper** (`tests/helpers/factories.rs`):

```rust
/// Minimal factory functions for creating test structs.
/// Add per-system factory modules as the project grows.

// Example structure — replace with your actual types:
// pub fn make_user(id: u64, email: &str) -> User { ... }
```

#### Go (go test)

**Base helper** (`tests/helpers/helpers.go`):

```go
// Package helpers provides shared test utilities for [Project Name].
// Import with: import "myproject/tests/helpers"
package helpers

import (
	"fmt"
	"testing"
)

// AssertEqual fails the test if expected != actual, with a formatted message.
func AssertEqual[T comparable](t *testing.T, expected, actual T, msg ...string) {
	t.Helper()
	if expected != actual {
		label := ""
		if len(msg) > 0 {
			label = msg[0] + ": "
		}
		t.Errorf("%sexpected %v, got %v", label, expected, actual)
	}
}

// AssertContains fails the test if the string does not contain the substring.
func AssertContains(t *testing.T, haystack, needle string) {
	t.Helper()
	// Avoid false positive on empty needle
	if len(needle) > 0 && len(haystack) == 0 {
		t.Errorf("expected string to contain %q, but it was empty", needle)
		return
	}
	// Use a simple contains check that works for any substring
	found := false
	for i := 0; i <= len(haystack)-len(needle); i++ {
		if haystack[i:i+len(needle)] == needle {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("string does not contain %q:\n  %s", needle, haystack)
	}
}

// AssertNoError fails the test if err is not nil.
func AssertNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

// AssertStatusOK fails the test if the HTTP status code is not 2xx.
func AssertStatusOK(t *testing.T, statusCode int) {
	t.Helper()
	if statusCode < 200 || statusCode >= 300 {
		t.Errorf("expected 2xx status, got %d", statusCode)
	}
}
```

**Factory helper** (`tests/helpers/factories.go`):

```go
package helpers

// MakeTestUser returns a minimal user struct for testing.
// Override fields as needed.
type TestUser struct {
	ID    int
	Email string
	Name  string
}

func MakeTestUser(overrides ...func(*TestUser)) TestUser {
	u := TestUser{
		ID:    1,
		Email: "test@example.com",
		Name:  "Test User",
	}
	for _, fn := range overrides {
		fn(&u)
	}
	return u
}
```

---

## 5. Generate System-Specific Helpers

For `[system-name]` or `all` modes, generate a helper per system:

Read the system's CDD to extract:
- Data types (entity types, component names)
- Formula variables and their bounds
- Common test scenarios mentioned in Edge Cases

Generate `tests/helpers/[system]_factory.[ext]` with factory functions
specific to that system's objects.

Example pattern for a `combat` system (Godot/GDScript):

```gdscript
## Factory and assertion helpers for Combat system tests.
## Generated by /test-helpers combat on [date].
## Based on: design/cdd/combat.md

class_name CombatTestFactory
extends RefCounted

const DAMAGE_MIN := 0
const DAMAGE_MAX := 999  # From CDD: damage formula upper bound

## Create a minimal attacker object for damage formula tests.
static func make_attacker(attack: float = 10.0, crit_chance: float = 0.0) -> Node:
    var attacker = Node.new()
    attacker.set_meta("attack", attack)
    attacker.set_meta("crit_chance", crit_chance)
    return attacker

## Create a minimal target object for damage receive tests.
static func make_target(defense: float = 0.0, health: float = 100.0) -> Node:
    var target = Node.new()
    target.set_meta("defense", defense)
    target.set_meta("health", health)
    target.set_meta("max_health", health)
    return target

## Assert damage output is within GDD-specified bounds.
static func assert_damage_in_bounds(damage: float) -> void:
    GameAssertions.assert_in_range(damage, DAMAGE_MIN, DAMAGE_MAX, "damage")
```

---

## 6. Write Output

Present a summary of what will be created:

```
## Test Helpers to Create

**[Game]**
Base helpers (engine: [engine]):
- tests/helpers/game_assertions.[ext]
- tests/helpers/game_factory.[ext]
[engine-specific extras]

**[Product]**
Base helpers (language: [language]):
- tests/helpers/conftest.py / test-utils.ts / helpers.go / mod.rs
- tests/helpers/factories.[ext]

System helpers ([mode]):
- tests/helpers/[system]_factory.[ext]  ← from [system] CDD
```

Ask: "May I write these helper files to `tests/helpers/`?"

**Never overwrite existing files.** If a file already exists, report:
"Skipping `[path]` — already exists. Remove the file manually if you want it
regenerated."

After writing: Verdict: **COMPLETE** — helper files created.

**[Game]** "Helper files created. To use them in a test:
- Godot: `class_name` is auto-imported — no explicit import needed
- Unity: Add `using` directive or reference the test assembly
- Unreal: `#include \"tests/helpers/GameTestHelpers.h\"`"

**[Product]** "Helper files created. To use them in a test:
- Python: imports are path-based — add `tests/` to `PYTHONPATH` or use relative imports
- TypeScript: use `import { assertOk } from '../helpers/test-utils'`
- Rust: add `mod helpers;` to test module or use `#[path = \"helpers/mod.rs\"]`
- Go: import `\"module/tests/helpers\"` in test files"

---

## Collaborative Protocol

- **Never overwrite existing helpers** — they may contain hand-written
  customisations. Only generate new files that don't exist yet
- **Generated code is a starting point** — the generated factory functions use
  metadata patterns for simplicity; adapt to the actual class structure once
  the code exists
- **Helpers should reflect the CDD** — **[Game]** bounds and constants in helpers should
  trace to CDD Formulas sections. **[Product]** test data and assertions should trace to CDD Data Model and acceptance criteria. Not invented values.
- **Ask before writing** — always confirm before creating files in `tests/`

## Next Steps

- Run `/test-setup` if the test framework has not been scaffolded yet.
- Use `/dev-story` to implement stories — helpers reduce boilerplate in new test files.
- Run `/skill-test` to validate other skills that may need helper coverage.
