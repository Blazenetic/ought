"""Focused practical batteries for modern Python."""

from .multimap import MultiMap
from .nursery import Nursery, nursery
from .settings import (
    InvalidSettingError,
    MissingSettingError,
    Secret,
    Settings,
    SettingsError,
    SettingsSourceError,
)

__version__ = "0.1.0a1"

__all__ = [
    "InvalidSettingError",
    "MissingSettingError",
    "MultiMap",
    "Nursery",
    "Secret",
    "Settings",
    "SettingsError",
    "SettingsSourceError",
    "__version__",
    "nursery",
]
