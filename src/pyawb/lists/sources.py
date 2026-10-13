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
"""The list maker's sources (AWB's cmboSourceSelect): which providers exist, what input each
takes, and building one for the connected wiki."""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pyawb.api.sparql import Sparql
from pyawb.api.transport import Transport
from pyawb.api.web import PywikibotWebFetcher, WebFetcher
from pyawb.lists import providers as P
from pyawb.lists.pagegenerators import PagegeneratorsListProvider
from pyawb.lists.wikidataquery import WikidataQueryListProvider

if TYPE_CHECKING:
    from pyawb.api.session import WikiSession
    from pyawb.settings.appconfig import AppConfig


class Input(enum.Enum):
    NONE = "none"
    LINE = "line"  # one line; several values separated by "|"
    TEXT = "text"  # several lines (manual list, SPARQL)
    FILE = "file"


@dataclass(frozen=True)
class Source:
    provider: type[P.ListProvider]
    input: Input

    @property
    def name(self) -> str:
        return self.provider.display_text

    @property
    def label(self) -> str:
        return self.provider.user_input_text

    @property
    def needs_wiki(self) -> bool:
        return not issubclass(
            self.provider,
            (
                P.ManualListProvider,
                P.TextFileListProvider,
                P.HTMLPageScraperListProvider,
                P.AdvancedRegexHtmlScraper,
            ),
        ) or issubclass(self.provider, P.CheckWikiWithNumberListProvider)

    @property
    def option(self) -> P.NumberOption | None:
        return self.provider.option

    @property
    def is_web(self) -> bool:
        return self.provider in P.WEB_PROVIDERS

    @property
    def takes_namespace(self) -> bool:
        """A namespace can be chosen (not for the "all NS" variants, nor where the source
        fixes it: all categories, all files)."""
        cls = self.provider
        if cls in _FIXED_NAMESPACE or str(getattr(cls, "search_prefix", "")).startswith("all:"):
            return False
        if not cls.namespaces_enabled or not dataclasses.is_dataclass(cls):
            return False
        ns = next((f for f in dataclasses.fields(cls) if f.name == "namespace"), None)
        return ns is not None and ns.default is not None


_FIXED_NAMESPACE: frozenset[type[P.ListProvider]] = frozenset(
    {P.AllCategoriesSpecialPageProvider, P.AllFilesSpecialPageProvider}
)


def _source(provider: type[P.ListProvider]) -> Source:
    if provider is P.ManualListProvider or provider is WikidataQueryListProvider:
        kind = Input.TEXT
    elif issubclass(provider, P.TextFileListProvider):
        kind = Input.FILE
    elif not provider.user_input_text:
        kind = Input.NONE
    else:
        kind = Input.LINE
    return Source(provider, kind)


SOURCES: Sequence[Source] = tuple(
    _source(p)
    for p in (
        P.ManualListProvider,
        *P.API_PROVIDERS,
        *P.WEB_PROVIDERS,
        WikidataQueryListProvider,
        PagegeneratorsListProvider,
        P.TextFileListProvider,
        P.TextFileListProviderWindows1252,
    )
)


ADD_FROM_SELECTED: Sequence[Source] = tuple(
    s for s in SOURCES if s.provider in P.API_PROVIDERS and s.input is Input.LINE
)
"""Sources for the list's "Add selected to list from ▸" menu: those that take page names (AWB
offers every provider with an input box except the web ones)."""


def source(name: str) -> Source:
    for s in SOURCES:
        if s.name == name:
            return s
    raise KeyError(name)


@dataclass(frozen=True)
class WikiContext:
    """What providers need from the connected wiki."""

    transport: Transport
    wikidata: Transport | None = None
    sparql: Sparql | None = None
    site_id: str = ""  # siteinfo wikiid, e.g. "mlwiki"
    article_url: str = ""  # with $1
    pywikibot_site: Any = None
    web: WebFetcher | None = None


class SourceUnavailable(ValueError):
    """The source needs something the connection does not have (log in first, ...)."""


def build(
    src: Source,
    wiki: WikiContext | None,
    namespace: int | None = None,
    option: int | None = None,
    settings: Mapping[str, object] | None = None,
) -> P.ListProvider:
    """A provider for src on the connected wiki. namespace: for sources that take one; option:
    the source's NumberOption value (clamped to its range); settings: other provider fields
    (the advanced HTML scraper's pattern and options)."""
    provider = _build(src, wiki, namespace)
    if src.option is not None:
        value = src.option.default if option is None else option
        value = max(src.option.minimum, min(src.option.maximum, value))
        setattr(provider, src.option.field, value)
    for name, value in (settings or {}).items():
        if not hasattr(provider, name):
            raise AttributeError(f"{type(provider).__name__} has no setting {name!r}")
        setattr(provider, name, value)
    return provider


def _build(src: Source, wiki: WikiContext | None, namespace: int | None) -> P.ListProvider:
    cls = src.provider
    if src.is_web:
        web = (wiki.web if wiki else None) or PywikibotWebFetcher()
        if cls is P.CheckWikiWithNumberListProvider:
            if wiki is None:
                raise SourceUnavailable("connect to a wiki first")
            return P.CheckWikiWithNumberListProvider(web, site_id=wiki.site_id)
        return cls(web)  # pyright: ignore[reportCallIssue]
    if cls is P.ManualListProvider:
        return P.ManualListProvider()
    if issubclass(cls, P.TextFileListProvider):
        return cls()
    if wiki is None:
        raise SourceUnavailable("connect to a wiki first")
    if cls is WikidataQueryListProvider:
        if wiki.sparql is None or wiki.wikidata is None or not wiki.site_id:
            raise SourceUnavailable("Wikidata is not available for this wiki")
        return WikidataQueryListProvider(wiki.sparql, wiki.wikidata, wiki.site_id, wiki.article_url)
    if cls is PagegeneratorsListProvider:
        if wiki.pywikibot_site is None:
            raise SourceUnavailable("pywikibot is not available for this connection")
        return PagegeneratorsListProvider(wiki.pywikibot_site)
    assert issubclass(cls, P.ApiListProvider)
    provider = cls(wiki.transport)  # pyright: ignore[reportCallIssue]
    if src.takes_namespace and namespace is not None:
        provider.namespace = namespace  # type: ignore[attr-defined]
    return provider


def criteria(src: Source, text: str) -> list[str]:
    """The user's input as the provider's criteria (AWB splits the box on "|")."""
    if src.input is Input.TEXT or src.input is Input.FILE:
        return [text] if text.strip() else []
    if src.input is Input.NONE:
        return []
    return [c for c in text.split("|") if c.strip()]


def wiki_context(config: AppConfig, session: WikiSession) -> WikiContext:
    """What the list maker needs from a connected wiki (Wikidata and SPARQL for the Wikidata
    query source). Blocking (it may open a Wikidata connection): run it off the UI thread."""
    from pyawb.api import connect
    from pyawb.api.sparql import PywikibotSparql

    general: Mapping[str, Any] = (
        session.siteinfo.query.get("general", {}) if session.siteinfo else {}
    )
    try:
        wikidata: Transport | None = connect.wikidata_transport(config)
    except Exception:  # Wikidata unreachable: everything else still works
        wikidata = None
    return WikiContext(
        transport=session.transport,
        wikidata=wikidata,
        sparql=PywikibotSparql(),
        site_id=str(general.get("wikiid", "")),
        article_url=session.siteinfo.article_url if session.siteinfo else "",
        pywikibot_site=getattr(session.transport, "site", None),
    )
