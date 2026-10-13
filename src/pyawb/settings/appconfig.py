# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Profiles follow AutoWikiBrowser WikiFunctions/Profiles (AWBProfile).
"""The user's PyAutoWikiBrowser configuration: config.toml in paths.config_dir().

Profiles say which wiki to work on and which account to use, as AWB's login profiles did.
Passwords are never written to this file: with remember_password the (bot) password is kept in
the operating system's keychain (api.credentials), keyed by wiki and login name.

    user_agent_contact = "https://en.wikipedia.org/wiki/Wikipedia:PyAutoWikiBrowser"
    default_profile = "Malayalam"

    [[profiles]]
    name = "Malayalam"
    lang = "ml"
    project = "wikipedia"
    custom_url = ""                # a non-Wikimedia wiki's script path instead of lang/project
    username = "Example@PyAWB"     # bot password login name (Special:BotPasswords)
    remember_password = true
    notes = ""
"""

from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

from pyawb.paths import config_dir
from pyawb.settings.preferences import (
    ON_LOAD,
    PASTE_MORE_SLOTS,
    THEMES,
    FontChoice,
    Preferences,
)

CONFIG_FILE = "config.toml"

DEFAULT_USER_AGENT_CONTACT = "https://en.wikipedia.org/wiki/Wikipedia:PyAutoWikiBrowser"
"""The tool's documentation page, sent in the User-Agent so wiki operators can reach us
(Wikimedia User-Agent policy). docs/wiki/PyAutoWikiBrowser.wikitext is the text for that page."""


class ConfigError(ValueError):
    """config.toml could not be read."""


@dataclass(frozen=True)
class Profile:
    """A wiki and an account (AWB's AWBProfile, without the stored password)."""

    name: str
    lang: str = "en"
    project: str = "wikipedia"
    custom_url: str = ""
    username: str = ""
    remember_password: bool = False
    notes: str = ""

    @property
    def wiki_url(self) -> str:
        """The script path, e.g. "https://ml.wikipedia.org/w/" (the keychain key)."""
        from pyawb.api.siteinfo import wiki_url

        url, url_end, _ = wiki_url(self.lang, self.project, self.custom_url)
        return url + url_end

    @property
    def user_name(self) -> str:
        """The account name without a bot password suffix ("Example" for "Example@PyAWB")."""
        return self.username.split("@", 1)[0]


@dataclass(frozen=True)
class AppConfig:
    profiles: tuple[Profile, ...] = ()
    default_profile: str = ""
    user_agent_contact: str = DEFAULT_USER_AGENT_CONTACT
    preferences: Preferences = field(default_factory=Preferences)

    def profile(self, name: str | None = None) -> Profile | None:
        """The named profile, or the default one, or the first."""
        wanted = name if name is not None else self.default_profile
        for p in self.profiles:
            if p.name == wanted:
                return p
        return self.profiles[0] if self.profiles and name is None else None

    def with_profile(self, profile: Profile, make_default: bool = False) -> AppConfig:
        """Add or replace (by name) a profile."""
        profiles = [p for p in self.profiles if p.name != profile.name]
        profiles.append(profile)
        return replace(
            self,
            profiles=tuple(profiles),
            default_profile=profile.name if make_default else self.default_profile,
        )

    def without_profile(self, name: str) -> AppConfig:
        return replace(
            self,
            profiles=tuple(p for p in self.profiles if p.name != name),
            default_profile="" if self.default_profile == name else self.default_profile,
        )


_PROFILE_FIELDS = {f.name: f for f in fields(Profile)}


def _profile(data: Mapping[str, Any]) -> Profile:
    if not isinstance(data.get("name"), str) or not data["name"]:
        raise ConfigError("every profile needs a name")
    if "password" in data:
        raise ConfigError(
            f"profile {data['name']!r}: passwords are not read from config.toml; "
            "use remember_password to keep it in the system keychain"
        )
    values: dict[str, Any] = {}
    for key, value in data.items():
        f = _PROFILE_FIELDS.get(key)
        if f is None:
            continue  # unknown keys from newer versions are ignored
        expected = bool if f.type == "bool" else str
        if not isinstance(value, expected):
            raise ConfigError(f"profile {data['name']!r}: {key} must be a {expected.__name__}")
        values[key] = value
    return Profile(**values)


def parse(text: str) -> AppConfig:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(str(e)) from e
    raw_profiles = data.get("profiles", [])
    if not isinstance(raw_profiles, list):
        raise ConfigError("profiles must be an array of tables ([[profiles]])")
    profiles = tuple(_profile(p) for p in raw_profiles)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    names = [p.name for p in profiles]
    if len(names) != len(set(names)):
        raise ConfigError("profile names must be unique")
    return AppConfig(
        profiles=profiles,
        default_profile=str(data.get("default_profile", "")),
        user_agent_contact=str(data.get("user_agent_contact", DEFAULT_USER_AGENT_CONTACT)),
        preferences=_preferences(data.get("preferences", {}), data.get("fonts", {})),
    )


def _preferences(raw: Any, raw_fonts: Any) -> Preferences:
    """[preferences] and [fonts.<script>]; unknown keys and bad values fall back to defaults (a
    preference is never a reason to refuse the whole file)."""
    p: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}  # pyright: ignore[reportUnknownVariableType]
    d = Preferences()

    def choice(key: str, allowed: tuple[str, ...], default: str) -> str:
        value = p.get(key, default)
        return value if value in allowed else default

    def flag(key: str, default: bool) -> bool:
        value = p.get(key, default)
        return value if isinstance(value, bool) else default

    fonts: dict[str, FontChoice] = {}
    if isinstance(raw_fonts, Mapping):
        for script, f in raw_fonts.items():  # pyright: ignore[reportUnknownVariableType]
            if isinstance(f, Mapping):
                fm: Mapping[str, Any] = f  # pyright: ignore[reportUnknownVariableType]
                size = fm.get("editor_size", 0)
                fonts[str(script)] = FontChoice(
                    editor=str(fm.get("editor", "")),
                    editor_size=size if isinstance(size, int) and 0 <= size <= 72 else 0,
                    interface=str(fm.get("interface", "")),
                    diff=str(fm.get("diff", "")),
                )
    language = p.get("language", "")
    raw_paste = p.get("paste_more", [])
    paste: list[str] = (
        [str(x) for x in raw_paste][:PASTE_MORE_SLOTS]  # pyright: ignore[reportUnknownVariableType]
        if isinstance(raw_paste, list)
        else []
    )
    paste += [""] * (PASTE_MORE_SLOTS - len(paste))
    return Preferences(
        theme=choice("theme", THEMES, d.theme),
        language=language if isinstance(language, str) else "",
        on_load=choice("on_load", ON_LOAD, d.on_load),
        warn_on_exit=flag("warn_on_exit", d.warn_on_exit),
        word_wrap=flag("word_wrap", d.word_wrap),
        paste_more=tuple(paste),
        fonts=fonts,
    )


def _toml_value(value: str | bool | int | tuple[str, ...]) -> str:
    if isinstance(value, tuple):
        # a JSON array of strings is a valid TOML inline array
        return json.dumps(list(value), ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    # JSON string escapes are valid TOML basic-string escapes
    return json.dumps(value, ensure_ascii=False)


def dumps(config: AppConfig) -> str:
    lines = [
        "# PyAutoWikiBrowser settings. Passwords are kept in the system keychain, never here.",
        f"user_agent_contact = {_toml_value(config.user_agent_contact)}",
        f"default_profile = {_toml_value(config.default_profile)}",
    ]
    prefs = config.preferences
    lines += ["", "[preferences]"]
    for key in ("theme", "language", "on_load", "warn_on_exit", "word_wrap", "paste_more"):
        lines.append(f"{key} = {_toml_value(getattr(prefs, key))}")
    for script, f in sorted(prefs.fonts.items()):
        lines += ["", f"[fonts.{json.dumps(script, ensure_ascii=False)}]"]
        lines += [
            f"editor = {_toml_value(f.editor)}",
            f"editor_size = {_toml_value(f.editor_size)}",
            f"interface = {_toml_value(f.interface)}",
            f"diff = {_toml_value(f.diff)}",
        ]
    for p in config.profiles:
        lines += ["", "[[profiles]]"]
        lines += [f"{f} = {_toml_value(getattr(p, f))}" for f in _PROFILE_FIELDS]
    return "\n".join(lines) + "\n"


def config_path() -> Path:
    return config_dir() / CONFIG_FILE


def load(path: Path | None = None) -> AppConfig:
    """The configuration, or the defaults when there is no file yet."""
    path = path or config_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return AppConfig()
    return parse(text)


def save(config: AppConfig, path: Path | None = None) -> Path:
    """Write atomically (a crash never leaves a half-written file); readable by the user only."""
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(dumps(config), encoding="utf-8")
    if os.name != "nt":
        tmp.chmod(0o600)
    tmp.replace(path)
    return path


def profile_names(config: AppConfig) -> Sequence[str]:
    return [p.name for p in config.profiles]
