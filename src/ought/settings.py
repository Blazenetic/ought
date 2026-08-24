"""Hierarchical, context-aware application settings.

``Settings`` combines ordinary mappings into a read-only hierarchical view.  It
supports mapping access for predictability and attribute access for convenience:

>>> settings = Settings({"timeout": 30, "db": {"host": "localhost"}})
>>> settings["timeout"]
30
>>> settings.db.host
'localhost'
>>> with settings.override(timeout=5):
...     settings.timeout
5
>>> settings.timeout
30

Source precedence is explicit: defaults, then TOML files in order, then the
environment, then runtime overrides.  Later mappings are merged recursively and
later non-mapping values replace earlier values.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Self, TypeVar, overload

_T = TypeVar("_T")
_Path = tuple[str, ...]
_Tree = dict[str, object]
_PathLike = str | os.PathLike[str]


class SettingsError(Exception):
    """Base class for settings-specific errors."""


class SettingsSourceError(SettingsError):
    """Raised when a settings source cannot be read or interpreted."""


class MissingSettingError(KeyError, SettingsError):
    """Raised when a required setting is absent."""


class InvalidSettingError(TypeError, SettingsError):
    """Raised when a setting has an invalid type or shape."""


@dataclass(frozen=True, slots=True, repr=False)
class Secret(Generic[_T]):
    """Wrap a sensitive value so routine display does not disclose it.

    Accessing the value requires an explicit call to :meth:`reveal`.

    >>> token = Secret("development-token")
    >>> token
    Secret(<redacted>)
    >>> str(token)
    '**********'
    >>> token.reveal()
    'development-token'
    """

    _value: _T = field(repr=False)

    def reveal(self) -> _T:
        """Return the wrapped value."""
        return self._value

    def __repr__(self) -> str:
        return "Secret(<redacted>)"

    def __str__(self) -> str:
        return "**********"


@dataclass(slots=True)
class _SettingsState:
    base: _Tree
    active: ContextVar[_Tree | None]
    sensitive_paths: tuple[_Path, ...]

    def current(self) -> _Tree:
        active = self.active.get()
        return self.base if active is None else active


class Settings(Mapping[str, object]):
    """A read-only, hierarchical view over application settings.

    Args:
        values: Initial settings. Nested mappings become nested ``Settings``
            views. Built-in mutable containers are frozen on ingestion: lists
            become tuples, sets become frozensets, and bytearrays become bytes.
        sensitive: Dotted paths whose resolved values should be wrapped in
            :class:`Secret`. Missing paths are allowed so optional secrets can
            be supplied by a later context override.

    Keys that collide with method names, or that are not valid Python
    identifiers, remain available through mapping access.
    """

    __slots__ = ("_path", "_state")

    def __init__(
        self,
        values: Mapping[str, object] | None = None,
        *,
        sensitive: Iterable[str] = (),
    ) -> None:
        sensitive_paths = tuple(_parse_path(path) for path in sensitive)
        initial_values = {} if values is None else values
        base = _freeze_mapping(initial_values, source="settings")
        _apply_sensitive(base, sensitive_paths)
        self._state = _SettingsState(
            base=base,
            active=ContextVar(f"ought.settings.{id(self):x}", default=None),
            sensitive_paths=sensitive_paths,
        )
        self._path: _Path = ()

    @classmethod
    def from_sources(
        cls,
        *,
        defaults: Mapping[str, object] | None = None,
        files: Iterable[_PathLike] | _PathLike = (),
        env_prefix: str | None = None,
        env: Mapping[str, str] | None = None,
        overrides: Mapping[str, object] | None = None,
        sensitive: Iterable[str] = (),
    ) -> Self:
        """Build settings from explicitly ordered sources.

        Precedence, from lowest to highest, is ``defaults``; each TOML file in
        the supplied order; environment variables; and ``overrides``.

        Environment names after ``env_prefix`` are lower-cased and split on a
        double underscore.  For example, ``MYAPP_DB__PORT=5432`` becomes
        ``{"db": {"port": 5432}}``. Values use TOML scalar syntax when valid
        and otherwise remain strings.

        Args:
            defaults: Lowest-precedence settings.
            files: One TOML path or an iterable of paths. A missing or malformed
                file is an error rather than being silently skipped.
            env_prefix: Prefix selecting environment variables. ``None``
                disables the environment source; an empty prefix is rejected.
            env: Environment mapping to read. Defaults to :data:`os.environ`.
                Supplying a mapping is useful for deterministic tests.
            overrides: Highest-precedence runtime values.
            sensitive: Dotted paths to wrap in :class:`Secret` after merging.

        Raises:
            SettingsSourceError: If a source is malformed or cannot be read.
            InvalidSettingError: If a sensitive path points to a section.
        """
        merged: _Tree = {}

        if defaults is not None:
            merged = _merge(
                merged,
                _freeze_mapping(defaults, source="defaults"),
            )

        for file_path in _normalise_files(files):
            document = _load_toml(file_path)
            merged = _merge(merged, document)

        if env_prefix is not None:
            environment = os.environ if env is None else env
            env_values = _load_environment(environment, env_prefix)
            merged = _merge(merged, env_values)

        if overrides is not None:
            merged = _merge(
                merged,
                _freeze_mapping(overrides, source="runtime overrides"),
            )

        return cls(merged, sensitive=sensitive)

    def __getitem__(self, key: str) -> object:
        if not isinstance(key, str):
            raise TypeError("setting keys must be strings")
        full_path = (*self._path, key)
        try:
            value = _lookup(self._state.current(), full_path)
        except KeyError:
            raise KeyError(_format_path(full_path)) from None
        return self._wrap(value, full_path)

    def __iter__(self) -> Iterator[str]:
        return iter(self._mapping())

    def __len__(self) -> int:
        return len(self._mapping())

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            path = _format_path((*self._path, name))
            raise AttributeError(f"no setting named {path!r}") from None

    def __repr__(self) -> str:
        return f"Settings({self.as_dict()!r})"

    @overload
    def require(self, path: str) -> object: ...

    @overload
    def require(self, path: str, expected_type: type[_T]) -> _T: ...

    def require(
        self,
        path: str,
        expected_type: type[object] | None = None,
    ) -> object:
        """Return a required dotted path, optionally checking its type.

        ``require`` is the intentionally small validation seam. It gives
        applications clear failures without turning Settings into a schema
        framework.

        >>> settings = Settings({"server": {"port": 8080}})
        >>> settings.require("server.port", int)
        8080
        >>> settings.require("server.port", str)
        Traceback (most recent call last):
        ...
        ought.settings.InvalidSettingError: setting 'server.port' expected str, got int
        """
        relative_path = _parse_path(path)
        full_path = (*self._path, *relative_path)
        try:
            value = _lookup(self._state.current(), full_path)
        except KeyError:
            formatted = _format_path(full_path)
            raise MissingSettingError(
                f"required setting {formatted!r} is missing"
            ) from None

        wrapped = self._wrap(value, full_path)
        if expected_type is not None and not isinstance(wrapped, expected_type):
            formatted = _format_path(full_path)
            raise InvalidSettingError(
                f"setting {formatted!r} expected {expected_type.__name__}, "
                f"got {type(wrapped).__name__}"
            )
        return wrapped

    def as_dict(self, *, reveal_secrets: bool = False) -> dict[str, object]:
        """Return a detached dictionary of the current view.

        Secrets remain wrapped by default. ``reveal_secrets=True`` is an
        explicit escape hatch intended for passing configuration to code that
        needs the raw values.
        """
        exported = _export(self._mapping(), reveal_secrets=reveal_secrets)
        if not isinstance(exported, dict):
            raise AssertionError("a settings view must export as a dictionary")
        return exported

    @contextmanager
    def override(
        self,
        values: Mapping[str, object] | None = None,
        /,
        **changes: object,
    ) -> Iterator[Self]:
        """Temporarily overlay values in the current execution context.

        Overrides nest cleanly, restore even when the block raises, and are
        inherited by asyncio tasks created inside the block. Keyword arguments
        take precedence over duplicate keys in ``values``.

        The mapping is relative to the current view, so
        ``settings.db.override(host="test")`` updates ``db.host``.
        """
        initial_values = {} if values is None else values
        layer = _freeze_mapping(initial_values, source="context override")
        if changes:
            layer = _merge(
                layer,
                _freeze_mapping(changes, source="context override keywords"),
            )

        nested_layer = _nest(self._path, layer)
        merged = _merge(self._state.current(), nested_layer)
        _apply_sensitive(merged, self._state.sensitive_paths)
        token = self._state.active.set(merged)
        try:
            yield self
        finally:
            self._state.active.reset(token)

    @classmethod
    def _view(cls, state: _SettingsState, path: _Path) -> Self:
        view = cls.__new__(cls)
        view._state = state
        view._path = path
        return view

    def _mapping(self) -> _Tree:
        value = _lookup(self._state.current(), self._path)
        if not isinstance(value, dict):
            path = _format_path(self._path)
            raise InvalidSettingError(f"setting {path!r} is not a section")
        return value

    def _wrap(self, value: object, path: _Path) -> object:
        if isinstance(value, dict):
            return type(self)._view(self._state, path)
        return value


def _normalise_files(files: Iterable[_PathLike] | _PathLike) -> tuple[Path, ...]:
    if isinstance(files, (str, os.PathLike)):
        return (Path(files),)
    try:
        return tuple(Path(path) for path in files)
    except TypeError as error:
        raise TypeError("files must be a path or an iterable of paths") from error


def _load_toml(path: Path) -> _Tree:
    try:
        with path.open("rb") as file:
            document = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SettingsSourceError(
            f"could not load TOML settings from {str(path)!r}: {error}"
        ) from error
    return _freeze_mapping(document, source=f"TOML file {str(path)!r}")


def _load_environment(environment: Mapping[str, str], prefix: str) -> _Tree:
    if not prefix:
        raise ValueError("env_prefix must not be empty")

    result: _Tree = {}
    names = sorted(name for name in environment if name.startswith(prefix))
    for name in names:
        raw_value = environment[name]
        if not isinstance(raw_value, str):
            raise SettingsSourceError(
                f"environment value for {name!r} must be a string"
            )

        suffix = name.removeprefix(prefix)
        parts = tuple(part.lower() for part in suffix.split("__"))
        if not suffix or any(not part for part in parts):
            raise SettingsSourceError(
                f"environment variable {name!r} does not form a valid setting path"
            )
        _insert_environment_value(
            result, parts, _parse_environment_value(raw_value), name
        )
    return _freeze_mapping(result, source=f"environment prefix {prefix!r}")


def _insert_environment_value(
    target: _Tree,
    path: _Path,
    value: object,
    variable_name: str,
) -> None:
    current = target
    for part in path[:-1]:
        existing = current.get(part)
        if existing is None:
            child: _Tree = {}
            current[part] = child
            current = child
        elif isinstance(existing, dict):
            current = existing
        else:
            raise SettingsSourceError(
                f"environment variable {variable_name!r} conflicts at "
                f"{_format_path(path)!r}"
            )

    leaf = path[-1]
    if leaf in current:
        raise SettingsSourceError(
            f"environment variable {variable_name!r} duplicates setting "
            f"{_format_path(path)!r}"
        )
    current[leaf] = value


def _parse_environment_value(raw_value: str) -> object:
    try:
        document = tomllib.loads(f"value = {raw_value}\n")
    except tomllib.TOMLDecodeError:
        return raw_value
    if set(document) != {"value"}:
        return raw_value
    return document["value"]


def _freeze_mapping(values: Mapping[str, object], *, source: str) -> _Tree:
    frozen = _freeze(values, path=(), source=source)
    if not isinstance(frozen, dict):
        raise SettingsSourceError(f"{source} must be a mapping")
    return frozen


def _freeze(value: object, *, path: _Path, source: str) -> object:
    if isinstance(value, Secret):
        revealed = _freeze(value.reveal(), path=path, source=source)
        if isinstance(revealed, dict):
            raise InvalidSettingError(
                f"sensitive setting {_format_path(path)!r} cannot be a section"
            )
        return Secret(revealed)

    if isinstance(value, Mapping):
        result: _Tree = {}
        for key, item in value.items():
            if not isinstance(key, str):
                location = _format_path(path) if path else "<root>"
                raise SettingsSourceError(
                    f"{source} contains non-string key {key!r} under {location!r}"
                )
            result[key] = _freeze(item, path=(*path, key), source=source)
        return result

    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, path=path, source=source) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item, path=path, source=source) for item in value)
    if isinstance(value, bytearray):
        return bytes(value)
    return value


def _merge(
    base: Mapping[str, object],
    overlay: Mapping[str, object],
    *,
    path: _Path = (),
) -> _Tree:
    merged = dict(base)
    for key, overlay_value in overlay.items():
        if key not in merged:
            merged[key] = overlay_value
            continue

        base_value = merged[key]
        if isinstance(base_value, dict) and isinstance(overlay_value, dict):
            merged[key] = _merge(base_value, overlay_value, path=(*path, key))
        elif isinstance(base_value, Secret) and not isinstance(overlay_value, Secret):
            if isinstance(overlay_value, dict):
                raise InvalidSettingError(
                    f"sensitive setting {_format_path((*path, key))!r} "
                    "cannot become a section"
                )
            merged[key] = Secret(overlay_value)
        else:
            merged[key] = overlay_value
    return merged


def _apply_sensitive(tree: _Tree, paths: Iterable[_Path]) -> None:
    for path in paths:
        current = tree
        missing = False
        for index, part in enumerate(path):
            if part not in current:
                missing = True
                break
            value = current[part]
            if index == len(path) - 1:
                if isinstance(value, dict):
                    raise InvalidSettingError(
                        f"sensitive setting {_format_path(path)!r} cannot be a section"
                    )
                if not isinstance(value, Secret):
                    current[part] = Secret(value)
            elif isinstance(value, dict):
                current = value
            else:
                raise InvalidSettingError(
                    f"sensitive path {_format_path(path)!r} crosses non-section "
                    f"setting {_format_path(path[: index + 1])!r}"
                )
        if missing:
            continue


def _lookup(tree: _Tree, path: _Path) -> object:
    current: object = tree
    for index, part in enumerate(path):
        if not isinstance(current, dict):
            traversed = _format_path(path[:index])
            requested = _format_path(path)
            raise InvalidSettingError(
                f"setting {traversed!r} is not a section while resolving {requested!r}"
            )
        if part not in current:
            raise KeyError(part)
        current = current[part]
    return current


def _parse_path(path: str) -> _Path:
    if not isinstance(path, str):
        raise TypeError("setting path must be a string")
    parts = tuple(path.split("."))
    if not path or any(not part for part in parts):
        raise ValueError(f"invalid setting path {path!r}")
    return parts


def _format_path(path: _Path) -> str:
    return ".".join(path)


def _nest(path: _Path, values: _Tree) -> _Tree:
    nested = values
    for part in reversed(path):
        nested = {part: nested}
    return nested


def _export(value: object, *, reveal_secrets: bool) -> object:
    if isinstance(value, Secret):
        if not reveal_secrets:
            return value
        return _export(value.reveal(), reveal_secrets=True)
    if isinstance(value, dict):
        return {
            key: _export(item, reveal_secrets=reveal_secrets)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_export(item, reveal_secrets=reveal_secrets) for item in value)
    if isinstance(value, frozenset):
        return frozenset(_export(item, reveal_secrets=reveal_secrets) for item in value)
    return value


__all__ = [
    "InvalidSettingError",
    "MissingSettingError",
    "Secret",
    "Settings",
    "SettingsError",
    "SettingsSourceError",
]
