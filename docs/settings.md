# Settings

`ought.settings` turns a small number of ordinary sources into one hierarchical,
read-only view. It deliberately stops short of schemas, dependency injection,
and application lifecycle management.

## Quick start

```python
from ought import Secret, Settings

settings = Settings.from_sources(
    defaults={
        "debug": False,
        "server": {"host": "127.0.0.1", "port": 8000},
        "database": {"password": Secret("development")},
    },
    files=["base.toml", "local.toml"],
    env_prefix="SERVICE_",
    overrides={"server": {"port": 9000}},
)

settings.server.host
settings["server"]["port"]
settings.require("server.port", int)
```

## Source precedence

Sources are merged from lowest to highest precedence:

| Order | Source | Notes |
| --- | --- | --- |
| 1 | `defaults` | An optional nested mapping |
| 2 | `files` | TOML files, with each later file overriding earlier files |
| 3 | environment | Enabled only when `env_prefix` is supplied |
| 4 | `overrides` | An optional highest-precedence mapping at construction time |

Mappings merge recursively. A later scalar or sequence replaces the earlier
value. A later mapping replaces an earlier scalar and vice versa. Key order is
the natural insertion order of the merged dictionaries: overriding a key does
not move it, while a new key is appended.

Missing or malformed files raise `SettingsSourceError`. They are never silently
ignored; applications that want an optional file should decide whether it
exists before including it.

TOML is the only file format in the foundation. JSON or YAML should be added
only after a concrete need establishes semantics worth supporting.

## Environment mapping

`env_prefix="SERVICE_"` selects only names beginning with that exact prefix.
The remainder is lower-cased, and a double underscore creates a nested section:

| Environment variable | Setting path | Value |
| --- | --- | --- |
| `SERVICE_DEBUG=true` | `debug` | `True` |
| `SERVICE_SERVER__PORT=8080` | `server.port` | `8080` |
| `SERVICE_ALLOWED='["a", "b"]'` | `allowed` | `("a", "b")` |
| `SERVICE_OPTIONS='{retries=3}'` | `options.retries` | `3` |
| `SERVICE_LABEL=plain-text` | `label` | `"plain-text"` |

Values are parsed when the complete string is one valid TOML value. Bare text
that is not valid in a TOML assignment remains a string. This gives booleans,
numbers, explicitly quoted strings, arrays, inline tables, dates, and times
predictable types without a custom coercion language. Lists and inline tables
then follow the same freezing and section rules as other sources.

Conflicting paths such as `SERVICE_DB=value` and `SERVICE_DB__HOST=localhost`
raise `SettingsSourceError`. Case variants that collapse to the same lower-case
path also raise rather than depending on environment iteration order.

The prefix, environment names, and selected values must be strings, and `env=`
must be a mapping. Invalid source shapes fail before a partial result can be
observed.

The optional `env=` mapping exists for deterministic tests. Production code
normally reads `os.environ` by omitting it.

## Access and required values

Both access styles are available:

```python
settings.server.host
settings["server"]["host"]
```

Mapping access remains the escape hatch for keys that collide with methods such
as `items`, contain punctuation, or are not Python identifiers.

Dotted paths used by `require()` and `sensitive=` deliberately have no escaping
grammar: each dot is a section separator. Use mapping access for a literal key
containing a dot, and wrap such a value with `Secret` directly when needed.

Missing mapping keys raise `KeyError` with the complete dotted path. Missing
attributes raise `AttributeError`, preserving normal Python protocol behaviour.
Use `require()` at application boundaries for a settings-specific error and an
optional type check:

```python
port = settings.require("server.port", int)
```

- a missing path raises `MissingSettingError`, which is also a `KeyError`;
- a wrong type or invalid nested shape raises `InvalidSettingError`, which is
  also a `TypeError`.

This is the validation seam. Ought does not infer schemas or coerce values to
annotations. Applications needing a larger schema system can pass
`settings.as_dict(reveal_secrets=True)` into their chosen validator.

## Read-only snapshots

The settings structure is read-only. On ingestion, common container types are
frozen recursively:

- mappings become internal settings sections;
- lists and tuples become tuples;
- sets become frozensets; and
- bytearrays become bytes.

Reference cycles among these supported containers raise `SettingsSourceError`
with the affected setting path. Reusing the same acyclic container at several
paths is valid and freezes each occurrence independently.

This prevents mutations to an input list from changing resolved settings later.
Arbitrary user-defined leaf objects are retained by reference, however, and
callers remain responsible for their mutability. The contract is therefore
structural immutability, not a claim that every possible leaf object is deeply
immutable.

`as_dict()` returns a structurally detached dictionary. Frozen sequence and set
values stay tuples and frozensets so exporting does not quietly change their
meaning; arbitrary leaf identities remain shared.

## Sensitive values

Wrap a default or override with `Secret`, or declare a dotted path with the
`sensitive=` argument:

```python
settings = Settings.from_sources(
    defaults={"database": {"password": "development"}},
    env_prefix="SERVICE_",
    sensitive=["database.password"],
)

password = settings.database.password
repr(password)  # 'Secret(<redacted>)'
str(password)  # '**********'
password.reveal()  # explicit raw access
```

`Secret` marks a resolved leaf value. A later value at that same merge location
inherits the marker while its surrounding sections remain mergeable.
`sensitive=` is the stronger path policy: it is reapplied after every merge,
follows context overrides, and may name an optional path that is initially
absent. Because that policy describes a section path, replacing an intermediate
section with a scalar is an `InvalidSettingError`.

`Secret` prevents routine `repr()` and `str()` disclosure. It is not encryption,
a secret manager, access control, or protection against deliberate inspection.
Avoid calling `as_dict(reveal_secrets=True)` in logging code.

## Context-local overrides

`override()` creates a merged snapshot in a `ContextVar` and restores the prior
snapshot even when the block raises:

```python
with settings.override(timeout=5):
    ...

with settings.server.override(host="test.internal"):
    ...
```

The mapping passed to an override is relative to the current view. Nested
overrides compose, and keyword arguments take precedence over duplicate keys in
the positional mapping.

Python copies the active context into an asyncio task when that task is created.
Therefore tasks created inside an override inherit it, while already-running
tasks keep the context in which they were created. An inherited override remains
visible to the child even if it finishes after the parent's `with` block, and a
nested override in one child does not affect its siblings. Threads need the
normal `contextvars.copy_context()` hand-off if context should cross the
boundary.

## Public API

| Name | Purpose |
| --- | --- |
| `Settings` | Read-only hierarchical mapping and source loader |
| `Settings.from_sources()` | Merge defaults, TOML, environment, and overrides |
| `Settings.require()` | Resolve a dotted path and optionally check its type |
| `Settings.override()` | Apply a context-local temporary mapping |
| `Settings.as_dict()` | Export the current view, redacted by default |
| `Secret` | Explicit redacting value wrapper |
| `SettingsError` | Base for settings-specific errors |
| `SettingsSourceError` | Source read or interpretation failure |
| `MissingSettingError` | Required value is absent |
| `InvalidSettingError` | Wrong type or invalid nested shape |
