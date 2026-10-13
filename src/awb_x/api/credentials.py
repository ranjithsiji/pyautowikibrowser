# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""Bot passwords in the operating system's keychain (keyring), never in settings files."""

from __future__ import annotations

import contextlib
from typing import Protocol

SERVICE = "awb-x"


class KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


def _key(wiki_url: str, username: str) -> str:
    return f"{username}@{wiki_url.rstrip('/')}"


def _backend(backend: KeyringBackend | None) -> KeyringBackend:
    if backend is not None:
        return backend
    import keyring

    return keyring  # type: ignore[return-value]


def save_password(
    wiki_url: str, username: str, password: str, backend: KeyringBackend | None = None
) -> None:
    """Remember the (bot) password for username ("Name@BotName") on a wiki."""
    _backend(backend).set_password(SERVICE, _key(wiki_url, username), password)


def load_password(
    wiki_url: str, username: str, backend: KeyringBackend | None = None
) -> str | None:
    return _backend(backend).get_password(SERVICE, _key(wiki_url, username))


def forget_password(wiki_url: str, username: str, backend: KeyringBackend | None = None) -> None:
    import keyring.errors

    with contextlib.suppress(keyring.errors.PasswordDeleteError):
        _backend(backend).delete_password(SERVICE, _key(wiki_url, username))
