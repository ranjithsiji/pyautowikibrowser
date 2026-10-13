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
"""Fetch Wikidata items for pages (batched wbgetentities) and parse them into
core.wikidata.WikidataItem. Not in AWB."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any

from awb_x.api.errors import check_errors
from awb_x.api.transport import Transport
from awb_x.core.wikidata import (
    AUTHORITY_CONTROL,
    GREGORIAN,
    Coordinates,
    WikidataItem,
    WikidataTime,
)

BATCH_SIZE = 50
"""wbgetentities accepts at most 50 ids or titles per request."""

PROPS = "sitelinks|labels|descriptions|claims"


def _batches[T](items: Sequence[T], size: int = BATCH_SIZE) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _best_statements(claims: Mapping[str, Any], prop: str) -> list[Mapping[str, Any]]:
    """Preferred statements if any, else normal ones; deprecated are never used."""
    statements: Sequence[Mapping[str, Any]] = claims.get(prop, ())
    preferred = [s for s in statements if s.get("rank") == "preferred"]
    return preferred or [s for s in statements if s.get("rank", "normal") == "normal"]


def _values(claims: Mapping[str, Any], prop: str) -> list[Any]:
    out: list[Any] = []
    for s in _best_statements(claims, prop):
        snak: Mapping[str, Any] = s.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        out.append(snak.get("datavalue", {}).get("value"))
    return out


def _times(claims: Mapping[str, Any], prop: str) -> tuple[WikidataTime, ...]:
    out: list[WikidataTime] = []
    for v in _values(claims, prop):
        if isinstance(v, Mapping) and "time" in v:
            tv: Mapping[str, Any] = v  # pyright: ignore[reportUnknownVariableType]
            out.append(
                WikidataTime.parse(
                    str(tv["time"]),
                    int(tv.get("precision", 11)),
                    str(tv.get("calendarmodel", GREGORIAN)),
                )
            )
    return tuple(out)


def _coordinates(claims: Mapping[str, Any]) -> tuple[Coordinates, ...]:
    out: list[Coordinates] = []
    for v in _values(claims, "P625"):
        if isinstance(v, Mapping) and "latitude" in v:
            cv: Mapping[str, Any] = v  # pyright: ignore[reportUnknownVariableType]
            precision = cv.get("precision")
            out.append(
                Coordinates(
                    float(cv["latitude"]),
                    float(cv["longitude"]),
                    None if precision is None else float(precision),
                    str(cv.get("globe", Coordinates(0, 0).globe)),
                )
            )
    return tuple(out)


def _entity_ids(claims: Mapping[str, Any], prop: str) -> tuple[str, ...]:
    return tuple(
        str(v["id"]) for v in _values(claims, prop) if isinstance(v, Mapping) and "id" in v
    )


def parse_entity(entity: Mapping[str, Any]) -> WikidataItem | None:
    """One entity from wbgetentities; None for a missing one."""
    if "missing" in entity or "id" not in entity:
        return None
    claims: Mapping[str, Any] = entity.get("claims", {})
    sitelinks: Mapping[str, Mapping[str, Any]] = entity.get("sitelinks", {})
    labels: Mapping[str, Mapping[str, Any]] = entity.get("labels", {})
    descriptions: Mapping[str, Mapping[str, Any]] = entity.get("descriptions", {})
    authority: dict[str, tuple[str, ...]] = {}
    for prop in AUTHORITY_CONTROL:
        ids = tuple(str(v) for v in _values(claims, prop) if isinstance(v, str))
        if ids:
            authority[prop] = ids
    return WikidataItem(
        id=str(entity["id"]),
        sitelinks={site: str(s.get("title", "")) for site, s in sitelinks.items()},
        labels={lang: str(v.get("value", "")) for lang, v in labels.items()},
        descriptions={lang: str(v.get("value", "")) for lang, v in descriptions.items()},
        instance_of=_entity_ids(claims, "P31"),
        birth_dates=_times(claims, "P569"),
        death_dates=_times(claims, "P570"),
        coordinates=_coordinates(claims),
        authority_control=authority,
    )


def parse_entities(result: Mapping[str, Any]) -> dict[str, WikidataItem]:
    """wbgetentities response -> {item id: item}, missing entities left out."""
    check_errors(result)
    out: dict[str, WikidataItem] = {}
    entities: Mapping[str, Mapping[str, Any]] = result.get("entities", {})
    for entity in entities.values():
        item = parse_entity(entity)
        if item is not None:
            out[item.id] = item
    return out


def _languages(languages: Iterable[str]) -> str:
    return "|".join(dict.fromkeys(languages))


def fetch_items_by_id(
    transport: Transport, ids: Sequence[str], languages: Iterable[str] = ("en",)
) -> dict[str, WikidataItem]:
    """Items by id ("Q42"), 50 per request. transport is Wikidata's API."""
    out: dict[str, WikidataItem] = {}
    langs = _languages(languages)
    for batch in _batches(list(dict.fromkeys(ids))):
        result = transport.request(
            {"action": "wbgetentities", "ids": "|".join(batch), "props": PROPS, "languages": langs}
        )
        out.update(parse_entities(result))
    return out


def fetch_items_for_titles(
    transport: Transport,
    site_id: str,
    titles: Sequence[str],
    languages: Iterable[str] = ("en",),
) -> dict[str, WikidataItem]:
    """Items for pages of one wiki (site_id e.g. "enwiki"), keyed by page title as the wiki
    was asked for; pages without an item are left out. Titles are matched through the item's
    sitelink, with underscores read as spaces."""
    out: dict[str, WikidataItem] = {}
    langs = _languages(languages)
    for batch in _batches(list(dict.fromkeys(titles))):
        result = transport.request(
            {
                "action": "wbgetentities",
                "sites": site_id,
                "titles": "|".join(batch),
                "props": PROPS,
                "languages": langs,
            }
        )
        wanted = {t.replace("_", " "): t for t in batch}
        for item in parse_entities(result).values():
            linked = item.sitelinks.get(site_id)
            if linked is not None and linked in wanted:
                out[wanted[linked]] = item
    return out
