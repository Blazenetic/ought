from __future__ import annotations

import asyncio
import contextvars
from pathlib import Path

import pytest

from ought import (
    InvalidSettingError,
    MissingSettingError,
    Secret,
    Settings,
    SettingsError,
    SettingsSourceError,
)


def test_sources_merge_recursively_in_documented_precedence(tmp_path: Path) -> None:
    first = tmp_path / "base.toml"
    first.write_text(
        """
title = "from-first-file"
[db]
host = "database.internal"
port = 5432
""".strip(),
        encoding="utf-8",
    )
    second = tmp_path / "local.toml"
    second.write_text(
        """
[db]
port = 5433
pool_size = 10
""".strip(),
        encoding="utf-8",
    )

    settings = Settings.from_sources(
        defaults={
            "title": "default",
            "debug": False,
            "db": {"host": "localhost", "port": 5000},
        },
        files=[first, second],
        env_prefix="MYAPP_",
        env={
            "IGNORED_DEBUG": "true",
            "MYAPP_DEBUG": "true",
            "MYAPP_DB__POOL_SIZE": "20",
        },
        overrides={"db": {"port": 6432}},
    )

    assert settings.as_dict() == {
        "title": "from-first-file",
        "debug": True,
        "db": {
            "host": "database.internal",
            "port": 6432,
            "pool_size": 20,
        },
    }


def test_single_file_path_is_accepted(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text("answer = 42\n", encoding="utf-8")

    settings = Settings.from_sources(files=config)

    assert settings.answer == 42


def test_environment_values_use_toml_values_with_string_fallback() -> None:
    settings = Settings.from_sources(
        env_prefix="APP_",
        env={
            "APP_BOOL": "false",
            "APP_COUNT": "12",
            "APP_DB__HOST": "localhost",
            "APP_DB__PORT": "5432",
            "APP_LABEL": "plain text",
            "APP_NAMES": '["Ada", "Grace"]',
            "APP_OPTIONS": "{retries = 3, enabled = true}",
            "APP_QUOTED": '"explicit string"',
            "APP_RATIO": "1.25",
            "APP_UNTRUSTED": "1\nother = 2",
        },
    )

    assert settings.as_dict() == {
        "bool": False,
        "count": 12,
        "db": {"host": "localhost", "port": 5432},
        "label": "plain text",
        "names": ("Ada", "Grace"),
        "options": {"retries": 3, "enabled": True},
        "quoted": "explicit string",
        "ratio": 1.25,
        "untrusted": "1\nother = 2",
    }


@pytest.mark.parametrize("prefix", ["", None])
def test_environment_prefix_controls_loading(prefix: str | None) -> None:
    if prefix is None:
        settings = Settings.from_sources(env_prefix=None, env={"VALUE": "1"})
        assert settings.as_dict() == {}
    else:
        with pytest.raises(ValueError, match="must not be empty"):
            Settings.from_sources(env_prefix=prefix, env={"VALUE": "1"})


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({"APP_": "1"}, "valid setting path"),
        ({"APP_DB____HOST": "localhost"}, "valid setting path"),
        ({"APP_DB": "url", "APP_DB__HOST": "localhost"}, "conflicts"),
        ({"APP_NAME": "first", "APP_name": "second"}, "duplicates"),
    ],
)
def test_malformed_environment_layout_has_actionable_errors(
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(SettingsSourceError, match=message):
        Settings.from_sources(env_prefix="APP_", env=environment)


def test_file_errors_retain_path_and_cause(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with pytest.raises(SettingsSourceError, match=r"missing\.toml") as missing_error:
        Settings.from_sources(files=missing)
    assert isinstance(missing_error.value.__cause__, OSError)

    malformed = tmp_path / "malformed.toml"
    malformed.write_text("not valid = [", encoding="utf-8")
    with pytest.raises(SettingsSourceError, match=r"malformed\.toml") as parse_error:
        Settings.from_sources(files=malformed)
    assert parse_error.value.__cause__ is not None


def test_mapping_and_attribute_access_return_live_nested_views() -> None:
    settings = Settings({"db": {"host": "localhost"}, "items": "collision"})
    db = settings.db

    assert isinstance(db, Settings)
    assert db.host == "localhost"
    assert settings["db"]["host"] == "localhost"  # type: ignore[index]
    assert settings["items"] == "collision"
    assert list(settings) == ["db", "items"]
    assert len(settings) == 2
    assert repr(db) == "Settings({'host': 'localhost'})"

    with settings.override(db={"host": "temporary"}):
        assert db.host == "temporary"


def test_missing_access_uses_standard_protocol_errors_with_full_paths() -> None:
    settings = Settings({"db": {}})

    with pytest.raises(KeyError) as key_error:
        settings.db["host"]
    assert key_error.value.args == ("db.host",)

    with pytest.raises(AttributeError, match=r"db\.host"):
        _ = settings.db.host

    with pytest.raises(MissingSettingError, match=r"db\.host"):
        settings.require("db.host")


def test_require_is_a_small_typed_validation_seam() -> None:
    settings = Settings({"port": 8080, "server": {"host": "localhost"}})

    assert settings.require("port", int) == 8080
    server = settings.require("server", Settings)
    assert server.host == "localhost"

    with pytest.raises(InvalidSettingError, match="expected str, got int"):
        settings.require("port", str)

    with pytest.raises(InvalidSettingError, match="not a section"):
        settings.require("port.value")


def test_secret_values_remain_redacted_across_sources_and_exports() -> None:
    settings = Settings.from_sources(
        defaults={"db": {"password": Secret("development")}},
        env_prefix="APP_",
        env={"APP_DB__PASSWORD": "production"},
    )

    password = settings.db.password
    assert isinstance(password, Secret)
    assert password.reveal() == "production"
    assert str(password) == "**********"
    assert repr(password) == "Secret(<redacted>)"
    assert "production" not in repr(settings)
    assert settings.as_dict() == {"db": {"password": Secret("production")}}
    assert settings.as_dict(reveal_secrets=True) == {"db": {"password": "production"}}


def test_sensitive_paths_cover_optional_and_overridden_values() -> None:
    settings = Settings(
        {"db": {"password": "nested"}, "token": "initial"},
        sensitive=["db.password", "token", "optional"],
    )

    assert settings.db.password.reveal() == "nested"
    assert settings.token.reveal() == "initial"
    with settings.override(token="temporary", optional="present"):
        assert settings.token.reveal() == "temporary"
        assert settings.optional.reveal() == "present"
    assert settings.token.reveal() == "initial"
    assert "optional" not in settings


def test_sensitive_path_requires_its_parent_to_remain_a_section() -> None:
    settings = Settings(
        {"db": {"password": "development"}},
        sensitive=["db.password"],
    )

    with (
        pytest.raises(InvalidSettingError, match="crosses non-section"),
        settings.override(db="database-url"),
    ):
        pytest.fail("the invalid override must fail before entering")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Settings({"section": Secret({"value": 1})}),
        lambda: Settings({"section": {"value": 1}}, sensitive=["section"]),
        lambda: Settings({"section": "scalar"}, sensitive=["section.value"]),
    ],
)
def test_sections_cannot_be_marked_as_leaf_secrets(factory: object) -> None:
    with pytest.raises(InvalidSettingError):
        factory()  # type: ignore[operator]


def test_context_overrides_nest_and_restore_after_exceptions() -> None:
    settings = Settings({"timeout": 30, "db": {"host": "localhost", "port": 5432}})

    with (
        pytest.raises(RuntimeError, match="stop"),
        settings.override({"timeout": 10}, timeout=5),
    ):
        assert settings.timeout == 5
        with settings.db.override(host="test"):
            assert settings.db.host == "test"
            assert settings.db.port == 5432
        assert settings.db.host == "localhost"
        raise RuntimeError("stop")

    assert settings.timeout == 30
    assert settings.db.host == "localhost"

    with settings.override():
        assert settings.timeout == 30


def test_a_nested_view_reports_if_an_override_changes_its_shape() -> None:
    settings = Settings({"section": {"value": 1}})
    section = settings.section

    with (
        settings.override(section="now a scalar"),
        pytest.raises(InvalidSettingError, match="not a section"),
    ):
        len(section)


def test_a_secret_leaf_cannot_be_overridden_with_a_section() -> None:
    settings = Settings({"token": Secret("initial")})

    with (
        pytest.raises(InvalidSettingError, match="cannot become a section"),
        settings.override(token={"nested": "value"}),
    ):
        pytest.fail("the invalid override must fail before entering")


def test_context_override_is_task_local_and_inherited_by_child_tasks() -> None:
    settings = Settings({"mode": "base"})

    async def scenario() -> tuple[str, str, str]:
        started = asyncio.Event()
        release = asyncio.Event()

        async def outside_task() -> str:
            started.set()
            await release.wait()
            return settings.mode

        outside = asyncio.create_task(outside_task())
        await started.wait()
        with settings.override(mode="temporary"):
            inside = asyncio.create_task(asyncio.sleep(0, result=settings.mode))
            release.set()
            return settings.mode, await inside, await outside

    assert asyncio.run(scenario()) == ("temporary", "temporary", "base")


def test_child_task_retains_inherited_override_after_parent_scope_exits() -> None:
    settings = Settings({"mode": "base"})

    async def scenario() -> tuple[str, str]:
        release = asyncio.Event()

        async def read_later() -> str:
            await release.wait()
            return settings.mode

        with settings.override(mode="inherited"):
            child = asyncio.create_task(read_later())

        release.set()
        return await child, settings.mode

    assert asyncio.run(scenario()) == ("inherited", "base")


def test_nested_child_override_is_isolated_from_sibling_and_parent() -> None:
    settings = Settings({"mode": "base"})

    async def scenario() -> tuple[str, str, str]:
        child_entered = asyncio.Event()
        sibling_read = asyncio.Event()

        async def changed_child() -> str:
            with settings.override(mode="child"):
                child_entered.set()
                await sibling_read.wait()
                return settings.mode

        async def sibling() -> str:
            await child_entered.wait()
            value = settings.mode
            sibling_read.set()
            return value

        with settings.override(mode="parent"):
            changed, unchanged = await asyncio.gather(
                asyncio.create_task(changed_child()),
                asyncio.create_task(sibling()),
            )
            parent = settings.mode
        return changed, unchanged, parent

    assert asyncio.run(scenario()) == ("child", "parent", "parent")


def test_override_can_be_applied_in_an_explicit_copied_context() -> None:
    settings = Settings({"value": "base"})
    context = contextvars.copy_context()

    def read_with_override() -> str:
        with settings.override(value="copied"):
            return settings.value

    assert context.run(read_with_override) == "copied"
    assert settings.value == "base"


def test_builtin_mutable_values_are_frozen_without_mutating_inputs() -> None:
    source = {"names": ["Ada"], "flags": {"safe"}, "buffer": bytearray(b"ok")}
    settings = Settings(source)

    source["names"].append("Grace")  # type: ignore[union-attr]
    assert settings.names == ("Ada",)
    assert settings.flags == frozenset({"safe"})
    assert settings.buffer == b"ok"
    assert settings.as_dict() == {
        "names": ("Ada",),
        "flags": frozenset({"safe"}),
        "buffer": b"ok",
    }


def test_reference_cycles_are_rejected_but_shared_containers_are_allowed() -> None:
    shared = ["value"]
    settings = Settings({"first": shared, "second": shared})
    assert settings.first == settings.second == ("value",)

    cycle: list[object] = []
    cycle.append(cycle)
    with pytest.raises(SettingsSourceError, match=r"reference cycle at 'cycle'"):
        Settings({"cycle": cycle})


def test_invalid_mapping_keys_and_paths_fail_early() -> None:
    with pytest.raises(SettingsSourceError, match="non-string key"):
        Settings({1: "value"})  # type: ignore[dict-item]

    settings = Settings({})
    with pytest.raises(TypeError, match="keys must be strings"):
        settings[1]  # type: ignore[index]
    with pytest.raises(ValueError, match="invalid setting path"):
        settings.require("db..host")
    with pytest.raises(TypeError, match="path must be a string"):
        settings.require(1)  # type: ignore[call-overload]


def test_invalid_source_container_types_fail_clearly() -> None:
    with pytest.raises(TypeError, match="path or an iterable"):
        Settings.from_sources(files=42)  # type: ignore[arg-type]

    with pytest.raises(SettingsSourceError, match="must be a string"):
        Settings.from_sources(
            env_prefix="APP_",
            env={"APP_VALUE": 1},  # type: ignore[dict-item]
        )

    with pytest.raises(TypeError, match="env_prefix must be a string or None"):
        Settings.from_sources(env_prefix=1, env={})  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="env must be a mapping"):
        Settings.from_sources(env_prefix="APP_", env=[])  # type: ignore[arg-type]

    with pytest.raises(SettingsSourceError, match="non-string variable name"):
        Settings.from_sources(
            env_prefix="APP_",
            env={1: "value"},  # type: ignore[dict-item]
        )


def test_exception_hierarchy_supports_specific_and_general_catches() -> None:
    assert issubclass(MissingSettingError, (KeyError, SettingsError))
    assert issubclass(InvalidSettingError, (TypeError, SettingsError))
    assert issubclass(SettingsSourceError, SettingsError)
