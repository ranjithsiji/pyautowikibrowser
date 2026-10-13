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
#
# Ported from AutoWikiBrowser WikiFunctions/ObjectCache.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""A disk cache for things loaded from the network (siteinfo, the site matrix, config pages),
with an expiry per entry. Entries are kept per type: "foo" as a str and "foo" as an int are
different entries. Stored as JSON (AWB used XML); a file from another version is ignored."""

from __future__ import annotations

import contextlib
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import IO, Any, ClassVar

from awb_x import __version__

DEFAULT_LIFESPAN = timedelta(days=5)

_TYPE_NAMES: dict[type, str] = {str: "str", list: "list", bool: "bool", int: "int", float: "float"}


class ObjectCache:
    """ObjectCache.cs. Supported types: str, list (of str), bool, plus any added with add_type
    (only JSON-serialisable types)."""

    _global: ClassVar[ObjectCache | None] = None

    def __init__(self, file_name: Path | str | None = None) -> None:
        self._lock = threading.Lock()
        self._supported: dict[type, timedelta] = {
            str: DEFAULT_LIFESPAN,
            list: DEFAULT_LIFESPAN,
            bool: DEFAULT_LIFESPAN,
        }
        self._storage: dict[type, dict[str, tuple[Any, datetime]]] = {}
        self.file_name: Path | None = None
        if file_name is not None:
            self.load(file_name)

    @classmethod
    def global_cache(cls) -> ObjectCache:
        """ObjectCache.Global, in AWB-X's data directory."""
        if cls._global is None:
            from awb_x.paths import data_dir

            cls._global = ObjectCache(data_dir() / "ObjectCache.json")
        return cls._global

    def add_type(self, what: type, life_span: timedelta) -> None:
        self._supported[what] = life_span

    def get[T](self, what: type[T], key: str) -> T | None:
        """The value stored for key as type what, or None if absent or expired."""
        with self._lock:
            found = self._storage.get(what, {}).get(key)
            if found is None:
                return None
            value, expires = found
            if expires < datetime.now():
                del self._storage[what][key]
                return None
            return value  # type: ignore[no-any-return]

    def set(self, key: str, value: Any, expiry: datetime | timedelta | None = None) -> None:
        """Store value for key; it expires at expiry (a time, or a time from now), or after its
        type's lifespan.

        AWB's ArgumentNullException (empty key, None value) is ValueError; its
        ArgumentException for an unsupported type is TypeError.
        """
        if not key:
            raise ValueError("key")
        if value is None:
            raise ValueError("value")
        what = type(value)
        if what not in self._supported:
            raise TypeError(f"Caching of type {what.__name__} is not supported")
        if expiry is None:
            expiry = datetime.now() + self._supported[what]
        elif isinstance(expiry, timedelta):
            expiry = datetime.now() + expiry
        with self._lock:
            self._storage.setdefault(what, {})[key] = (value, expiry)

    def __getitem__(self, key: str) -> Any:
        for what in self._supported:
            value = self.get(what, key)
            if value is not None:
                return value
        return None

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    # persistence ------------------------------------------------------------------------------

    def save(self, target: Path | str | IO[str] | None = None) -> None:
        """Save unexpired entries to a stream, a file, or the cache's own file."""
        if target is None:
            target = self.file_name
            if target is None:
                return
        if isinstance(target, str | Path):
            self.file_name = Path(target)
            self.file_name.parent.mkdir(parents=True, exist_ok=True)
            with self.file_name.open("w", encoding="utf-8") as f:
                self.save(f)
            return
        now = datetime.now()
        types: dict[str, list[dict[str, Any]]] = {}
        with self._lock:
            for what, entries in self._storage.items():
                name = _TYPE_NAMES.get(what, what.__qualname__)
                items = [
                    {"key": k, "expires": exp.isoformat(), "value": v}
                    for k, (v, exp) in entries.items()
                    if exp >= now
                ]
                if items:
                    types[name] = items
        json.dump({"version": __version__, "types": types}, target, ensure_ascii=False)

    def load(self, source: Path | str | IO[str]) -> bool:
        """Replace the entries with those from a stream or file. A missing, corrupt or
        other-version file is ignored (a corrupt or old file is deleted), as in AWB."""
        if isinstance(source, str | Path):
            self.file_name = Path(source)
            try:
                with self.file_name.open(encoding="utf-8") as f:
                    loaded = self.load(f)
            except OSError:
                return False
            if not loaded:
                self.file_name.unlink(missing_ok=True)
            return loaded
        try:
            data = json.load(source)
            if data.get("version") != __version__:
                return False
            by_name = {_TYPE_NAMES.get(t, t.__qualname__): t for t in self._supported}
            storage: dict[type, dict[str, tuple[Any, datetime]]] = {}
            for name, items in data.get("types", {}).items():
                what = by_name.get(name)
                if what is None:
                    continue
                storage[what] = {
                    i["key"]: (_restore(what, i["value"]), datetime.fromisoformat(i["expires"]))
                    for i in items
                }
        except (ValueError, KeyError, TypeError, AttributeError):
            return False
        with self._lock:
            self._storage = storage
        return True

    def invalidate(self) -> None:
        """Clear everything and delete the file."""
        with self._lock:
            self._storage.clear()
        if self.file_name is not None:
            self.file_name.unlink(missing_ok=True)

    def close(self) -> None:
        """Save to the cache's file (AWB's Dispose)."""
        with contextlib.suppress(OSError):
            self.save()


def _restore(what: type, value: Any) -> Any:
    return what(value) if what in (int, float, str, bool) else value
