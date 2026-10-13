# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/Lists/Providers/ApiListProviderBase.cs,
# CategoryProviderBase.cs, ListProviders.cs and NonMWListProviders.cs (text files).
# Copyright (C) 2007 Martin Richards, (C) 2008 Stephen Kennedy, Sam Reed and the AutoWikiBrowser
# contributors (GPL-2.0-or-later).
"""List providers: make a page list from a category, links, search, a user's contributions, a
text file, ...

Each AWB provider is one API query with AWB's parameters, limits and filters, run through an
awb_l.api Transport with MediaWiki's "continue" continuation (AWB used rawcontinue). Providers
that need user input AWB asked for with a dialog (depth, number of edits, protection level) take
it as a parameter. pywikibot's own page generators are available through
lists.pagegenerators.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from awb_l.api.transport import Param, Transport
from awb_l.core import tools
from awb_l.core.article import Article
from awb_l.core.rx import DotNetOptions, DotNetRegex
from awb_l.core.site import Namespace, current_site
from awb_l.core.textutil import remove_hash_from_page_title, turn_first_to_upper, wiki_decode

DEFAULT_LIMIT = 25000

type Item = Mapping[str, Any]
type Extract = Callable[[Mapping[str, Any]], Iterable[Item]]


def first_to_upper_and_remove_hash(titles: Iterable[str]) -> list[str]:
    """Tools.FirstToUpperAndRemoveHashOnArray: trim [[ ]], drop #section, first letter upper."""
    return [turn_first_to_upper(remove_hash_from_page_title(t.strip("[] \t"))) for t in titles]


def _list_items(name: str) -> Extract:
    """Items of a list module: query[name][]."""

    def extract(result: Mapping[str, Any]) -> Iterable[Item]:
        return result.get("query", {}).get(name, ())

    return extract


def _prop_items(name: str) -> Extract:
    """Items of a prop module, over all pages: query.pages[][name][]."""

    def extract(result: Mapping[str, Any]) -> Iterator[Item]:
        for page in result.get("query", {}).get("pages", ()):
            yield from page.get(name, ())

    return extract


def _backlink_items(result: Mapping[str, Any]) -> Iterator[Item]:
    """Backlinks; with blredirect, the pages linking through each redirect follow it (AWB read
    the nested <bl> elements the same way)."""
    for bl in result.get("query", {}).get("backlinks", ()):
        yield bl
        yield from bl.get("redirlinks", ())


def _generator_pages(result: Mapping[str, Any]) -> Iterable[Item]:
    return result.get("query", {}).get("pages", ())


def api_make_list(
    transport: Transport,
    params: Mapping[str, Param],
    extract: Extract,
    limit: int,
    have_so_far: int = 0,
    evaluate: Callable[[Item], bool] | None = None,
    wanted: str = "title",
) -> list[Article]:
    """ApiListProviderBase.ApiMakeList: run a query, following continuation while the list has
    fewer than limit pages (counting have_so_far). evaluate filters items."""
    out: list[Article] = []
    request: dict[str, Param] = {**params, "continue": ""}
    while len(out) + have_so_far < limit:
        result = transport.request(request)
        for item in extract(result):
            if evaluate is not None and not evaluate(item):
                continue
            name = item.get(wanted)
            if not name:
                continue
            ns = item.get("ns")
            out.append(
                Article(str(name), namespace_key=ns if isinstance(ns, int) and ns >= 0 else None)
            )
        cont: Mapping[str, Any] | None = result.get("continue")
        if not cont:
            break
        request.update({k: str(v) for k, v in cont.items()})
    return out


class ListProvider:
    """IListProvider: make a list of pages from search criteria."""

    display_text: ClassVar[str] = ""
    user_input_text: ClassVar[str] = ""  # label for the criteria box
    user_input_enabled: ClassVar[bool] = True
    strip_url: ClassVar[bool] = False  # criteria may be pasted page URLs
    namespaces_enabled: ClassVar[bool] = False  # takes a namespace (special page providers)

    def make_list(self, *criteria: str) -> list[Article]:
        raise NotImplementedError


@dataclass
class ApiListProvider(ListProvider):
    """A provider backed by the wiki's API."""

    transport: Transport
    limit: int = DEFAULT_LIMIT

    def _run(
        self,
        params: Mapping[str, Param],
        extract: Extract,
        have_so_far: int,
        evaluate: Callable[[Item], bool] | None = None,
        wanted: str = "title",
    ) -> list[Article]:
        return api_make_list(
            self.transport, params, extract, self.limit, have_so_far, evaluate, wanted
        )


# categories -----------------------------------------------------------------------------------


def prepare_categories(source: Iterable[str]) -> list[str]:
    """CategoryProviderBase.PrepareCategories: category names without namespace or #section."""
    ns = current_site().namespaces_case_insensitive.get(Namespace.CATEGORY, "Category:")
    strip = DotNetRegex("^" + ns)
    return [
        strip.replace(remove_hash_from_page_title(wiki_decode(c)).strip(), "").strip()
        for c in source
    ]


@dataclass
class CategoryListProvider(ApiListProvider):
    display_text: ClassVar[str] = "Category"
    user_input_text: ClassVar[str] = "Category:"
    strip_url: ClassVar[bool] = True

    def get_listing(self, category: str, have_so_far: int = 0) -> list[Article]:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:" + category,
            "cmlimit": "max",
        }
        return self._run(params, _list_items("categorymembers"), 0)

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for cat in prepare_categories(criteria):
            out.extend(self.get_listing(cat, len(out)))
        return out


@dataclass
class CategoryRecursiveListProvider(CategoryListProvider):
    """Category members and the members of its subcategories, depth levels down (at most 30)."""

    MAX_DEPTH: ClassVar[int] = 30
    display_text: ClassVar[str] = "Category (recursive)"

    limit: int = 200000
    depth: int = MAX_DEPTH
    _visited: list[str] = field(default_factory=list[str], init=False, repr=False)

    def __post_init__(self) -> None:
        self.depth = min(self.depth, self.MAX_DEPTH)

    def recurse_category(self, category: str, have_so_far: int, depth: int) -> list[Article]:
        if have_so_far > self.limit or depth < 0:
            return []
        category = turn_first_to_upper(wiki_decode(category))
        if category in self._visited:
            return []
        self._visited.append(category)

        out = self.get_listing(category, have_so_far)
        from_subcats: list[Article] = []
        if depth > 0 and have_so_far + len(out) < self.limit:
            for pg in out:
                if have_so_far + len(out) > self.limit:
                    break
                if pg.namespace_key == Namespace.CATEGORY and pg.name not in self._visited:
                    from_subcats.extend(
                        self.recurse_category(
                            pg.namespaceless_name, have_so_far + len(out), depth - 1
                        )
                    )
        out.extend(from_subcats)
        return out

    def make_list(self, *criteria: str) -> list[Article]:
        self._visited.clear()
        out: list[Article] = []
        for cat in prepare_categories(criteria):
            out.extend(self.recurse_category(cat, len(out), self.depth))
        self._visited.clear()
        return out


@dataclass
class CategoryRecursiveOneLevelListProvider(CategoryRecursiveListProvider):
    display_text: ClassVar[str] = "Category (recurse 1 level)"
    depth: int = 1


@dataclass
class CategoriesOnPageListProvider(ApiListProvider):
    display_text: ClassVar[str] = "Categories on page"
    user_input_text: ClassVar[str] = "Pages:"
    clshow: ClassVar[str] = ""

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in first_to_upper_and_remove_hash(criteria):
            params: dict[str, Param] = {
                "action": "query",
                "prop": "categories",
                "cllimit": "max",
                "titles": page,
            }
            if self.clshow:
                params["clshow"] = self.clshow
            out.extend(self._run(params, _prop_items("categories"), len(out)))
        return out


@dataclass
class CategoriesOnPageNoHiddenListProvider(CategoriesOnPageListProvider):
    display_text: ClassVar[str] = "Categories on page (no hidden cats)"
    clshow: ClassVar[str] = "!hidden"


@dataclass
class CategoriesOnPageOnlyHiddenListProvider(CategoriesOnPageListProvider):
    display_text: ClassVar[str] = "Categories on page (only hidden cats)"
    clshow: ClassVar[str] = "hidden"


# links ----------------------------------------------------------------------------------------


@dataclass
class WhatLinksHereListProvider(ApiListProvider):
    """Pages linking to the given pages, in namespace (None: all namespaces)."""

    display_text: ClassVar[str] = "What links here"
    user_input_text: ClassVar[str] = "What links to:"
    namespaces_enabled: ClassVar[bool] = True
    include_what_links_to_redirects: ClassVar[bool] = False
    blfilterredir: ClassVar[str] = ""

    namespace: int | None = Namespace.ARTICLE
    force_query_limit: str = ""

    def _evaluate(self, item: Item) -> bool:
        return True

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in first_to_upper_and_remove_hash(criteria):
            params: dict[str, Param] = {
                "action": "query",
                "list": "backlinks",
                "bltitle": page,
                "bllimit": self.force_query_limit or "max",
            }
            if self.namespace is not None:
                params["blnamespace"] = self.namespace
            if self.include_what_links_to_redirects:
                params["blredirect"] = True
            if self.blfilterredir:
                params["blfilterredir"] = self.blfilterredir
            out.extend(self._run(params, _backlink_items, len(out), self._evaluate))
        return out


@dataclass
class WhatLinksHereAllNSListProvider(WhatLinksHereListProvider):
    display_text: ClassVar[str] = "What links here (all NS)"
    namespace: int | None = None


@dataclass
class WhatLinksHereAndToRedirectsListProvider(WhatLinksHereListProvider):
    display_text: ClassVar[str] = "What links here (and to redirects)"
    include_what_links_to_redirects: ClassVar[bool] = True


@dataclass
class WhatLinksHereAndToRedirectsAllNSListProvider(WhatLinksHereAllNSListProvider):
    display_text: ClassVar[str] = "What links here (all NS) (and to redirects)"
    include_what_links_to_redirects: ClassVar[bool] = True


@dataclass
class WhatLinksHereAndPageRedirectsExcludingTheRedirectsListProvider(WhatLinksHereListProvider):
    display_text: ClassVar[str] = "What links here directly"
    include_what_links_to_redirects: ClassVar[bool] = True
    blfilterredir: ClassVar[str] = "nonredirects"

    def _evaluate(self, item: Item) -> bool:
        return not item.get("redirect")


@dataclass
class WhatLinksHereExcludingPageRedirectsListProvider(WhatLinksHereListProvider):
    display_text: ClassVar[str] = "What links here (no redirects)"
    blfilterredir: ClassVar[str] = "nonredirects"


@dataclass
class RedirectsListProvider(WhatLinksHereListProvider):
    display_text: ClassVar[str] = "What redirects here"
    user_input_text: ClassVar[str] = "Redirects to:"
    blfilterredir: ClassVar[str] = "redirects"


@dataclass
class RedirectsAllNSListProvider(WhatLinksHereAllNSListProvider):
    display_text: ClassVar[str] = "What redirects here (all NS)"
    user_input_text: ClassVar[str] = "Redirects to:"
    blfilterredir: ClassVar[str] = "redirects"


@dataclass
class WhatTranscludesPageListProvider(ApiListProvider):
    display_text: ClassVar[str] = "What transcludes page"
    user_input_text: ClassVar[str] = "What embeds:"
    namespaces_enabled: ClassVar[bool] = True

    namespace: int | None = Namespace.ARTICLE

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in criteria:
            params: dict[str, Param] = {
                "action": "query",
                "list": "embeddedin",
                "eititle": page,
                "eilimit": "max",
            }
            if self.namespace is not None:
                params["einamespace"] = self.namespace
            out.extend(self._run(params, _list_items("embeddedin"), len(out)))
        return out


@dataclass
class WhatTranscludesPageAllNSListProvider(WhatTranscludesPageListProvider):
    display_text: ClassVar[str] = "What transcludes page (all NS)"
    namespace: int | None = None


@dataclass
class DisambiguationPagesSpecialPageProvider(WhatTranscludesPageListProvider):
    display_text: ClassVar[str] = "Disambiguation pages"
    user_input_enabled: ClassVar[bool] = False

    def make_list(self, *criteria: str) -> list[Article]:
        return super().make_list("Template:Disambiguation")


@dataclass
class _PagePropProvider(ApiListProvider):
    """prop=<prop> on each page (links, images, templates)."""

    prop: ClassVar[str] = ""
    prefix: ClassVar[str] = ""
    user_input_text: ClassVar[str] = "Pages:"

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in first_to_upper_and_remove_hash(criteria):
            params = {
                "action": "query",
                "prop": self.prop,
                "titles": page,
                self.prefix + "limit": "max",
            }
            out.extend(self._run(params, _prop_items(self.prop), len(out)))
        return out


@dataclass
class LinksOnPageListProvider(_PagePropProvider):
    display_text: ClassVar[str] = "Links on page"
    prop: ClassVar[str] = "links"
    prefix: ClassVar[str] = "pl"


@dataclass
class FilesOnPageListProvider(_PagePropProvider):
    display_text: ClassVar[str] = "Files on page"
    prop: ClassVar[str] = "images"
    prefix: ClassVar[str] = "im"


@dataclass
class TransclusionsOnPageListProvider(_PagePropProvider):
    display_text: ClassVar[str] = "Transclusions on page"
    prop: ClassVar[str] = "templates"
    prefix: ClassVar[str] = "tl"


@dataclass
class LinksOnPageOnlyRedListProvider(ApiListProvider):
    display_text: ClassVar[str] = "Links on page (only redlinks)"
    user_input_text: ClassVar[str] = "Pages:"
    want_missing: ClassVar[bool] = True

    limit: int = 5000

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in first_to_upper_and_remove_hash(criteria):
            params = {"action": "query", "generator": "links", "titles": page, "gpllimit": "max"}
            out.extend(
                self._run(
                    params,
                    _generator_pages,
                    len(out),
                    lambda item: bool(item.get("missing")) == self.want_missing,
                )
            )
        return out


@dataclass
class LinksOnPageOnlyBlueListProvider(LinksOnPageOnlyRedListProvider):
    display_text: ClassVar[str] = "Links on page (only bluelinks)"
    want_missing: ClassVar[bool] = False


@dataclass
class ImageFileLinksListProvider(ApiListProvider):
    display_text: ClassVar[str] = "Image file links"
    user_input_text: ClassVar[str] = "File:"

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        file_ns = DotNetRegex(
            "^(?:" + current_site().generate_namespace_regex(Namespace.FILE) + "):",
            DotNetOptions.IGNORE_CASE,
        )
        for page in first_to_upper_and_remove_hash(criteria):
            image = file_ns.replace(page, "")
            params = {
                "action": "query",
                "list": "imageusage",
                "iutitle": "File:" + image,
                "iulimit": "max",
            }
            out.extend(self._run(params, _list_items("imageusage"), len(out)))
        return out


# users ----------------------------------------------------------------------------------------


@dataclass
class UserContribsListProvider(ApiListProvider):
    """Pages a user edited. number_of_edits: AWB's "user defined number" variant (at most
    25000)."""

    display_text: ClassVar[str] = "User contribs"
    user_input_text: ClassVar[str] = "User:"
    namespaces_enabled: ClassVar[bool] = True

    namespace: int | None = None
    number_of_edits: int | None = None

    def make_list(self, *criteria: str) -> list[Article]:
        if self.number_of_edits is not None:
            self.limit = min(self.number_of_edits, 25000)
        # AWB stripped the Category namespace here (a slip); the User namespace is meant
        user_ns = DotNetRegex(current_site().namespaces_case_insensitive[Namespace.USER])
        out: list[Article] = []
        for page in first_to_upper_and_remove_hash(criteria):
            params: dict[str, Param] = {
                "action": "query",
                "list": "usercontribs",
                "ucuser": user_ns.replace(page, ""),
                "uclimit": "max" if self.number_of_edits is None else str(self.limit),
            }
            if self.namespace is not None:
                params["ucnamespace"] = self.namespace
            out.extend(self._run(params, _list_items("usercontribs"), len(out)))
        return out


@dataclass
class MyWatchlistListProvider(ApiListProvider):
    display_text: ClassVar[str] = "My watchlist"
    user_input_enabled: ClassVar[bool] = False

    def make_list(self, *criteria: str) -> list[Article]:
        params = {"action": "query", "list": "watchlistraw", "wrlimit": "max"}
        return self._run(params, _list_items("watchlistraw"), 0)


@dataclass
class AllUsersSpecialPageProvider(ApiListProvider):
    display_text: ClassVar[str] = "All users"
    user_input_enabled: ClassVar[bool] = False

    def make_list(self, *criteria: str) -> list[Article]:
        params = {"action": "query", "list": "allusers", "aulimit": "max"}
        users = self._run(params, _list_items("allusers"), 0, wanted="name")
        prefix = current_site().namespaces[Namespace.USER]
        return [Article(prefix + u.name, namespace_key=Namespace.USER) for u in users]


# search ---------------------------------------------------------------------------------------


@dataclass
class WikiSearchListProvider(ApiListProvider):
    display_text: ClassVar[str] = "Wiki search (text)"
    user_input_text: ClassVar[str] = "Wiki search:"
    namespaces_enabled: ClassVar[bool] = True
    search_prefix: ClassVar[str] = ""

    limit: int = 1000  # slow query
    namespace: int = Namespace.ARTICLE

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in criteria:
            all_ns = self.search_prefix.startswith("all:")
            params: dict[str, Param] = {
                "action": "query",
                "list": "search",
                "srwhat": "text",
                "srnamespace": "*" if all_ns else self.namespace,
                "srsearch": (self.search_prefix if not all_ns else self.search_prefix[4:]) + page,
                "srlimit": "max",
                "srprop": "",
            }
            out.extend(self._run(params, _list_items("search"), len(out)))
        return out


@dataclass
class WikiSearchAllNSListProvider(WikiSearchListProvider):
    display_text: ClassVar[str] = "Wiki search (text) (all NS)"
    search_prefix: ClassVar[str] = "all:"


@dataclass
class WikiTitleSearchListProvider(WikiSearchListProvider):
    display_text: ClassVar[str] = "Wiki search (title)"
    search_prefix: ClassVar[str] = "intitle:"


@dataclass
class WikiTitleSearchAllNSListProvider(WikiSearchListProvider):
    display_text: ClassVar[str] = "Wiki search (title) (all NS)"
    search_prefix: ClassVar[str] = "all:intitle:"


@dataclass
class LinkSearchSpecialPageProvider(ApiListProvider):
    display_text: ClassVar[str] = "Link search"
    user_input_text: ClassVar[str] = "URL:"
    namespaces_enabled: ClassVar[bool] = True

    namespace: int = Namespace.ARTICLE

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for search_url in criteria:
            protocol, sep, url_end = search_url.partition("://")
            if not sep:
                protocol, url_end = "", search_url
            params: dict[str, Param] = {
                "action": "query",
                "list": "exturlusage",
                "euquery": url_end,
                "eunamespace": self.namespace,
                "euprotocol": protocol,
                "eulimit": "max",
            }
            out.extend(self._run(params, _list_items("exturlusage"), len(out)))
        return out


# special pages --------------------------------------------------------------------------------


@dataclass
class RandomPagesSpecialPageProvider(ApiListProvider):
    display_text: ClassVar[str] = "Random pages"
    user_input_enabled: ClassVar[bool] = False
    namespaces_enabled: ClassVar[bool] = True
    redirects: ClassVar[bool] = False

    limit: int = 100
    namespace: int = Namespace.ARTICLE

    def make_list(self, *criteria: str) -> list[Article]:
        params: dict[str, Param] = {
            "action": "query",
            "list": "random",
            "rnnamespace": self.namespace,
            "rnlimit": "max",
        }
        if self.redirects:
            params["rnfilterredir"] = "redirects"
        return self._run(params, _list_items("random"), 0)


@dataclass
class RandomRedirectsSpecialPageProvider(RandomPagesSpecialPageProvider):
    display_text: ClassVar[str] = "Random redirects"
    redirects: ClassVar[bool] = True


@dataclass
class AllPagesSpecialPageProvider(ApiListProvider):
    """Special:AllPages from each criterion (apfrom), or Special:PrefixIndex (apprefix)."""

    display_text: ClassVar[str] = "All pages"
    user_input_text: ClassVar[str] = "Start from:"
    namespaces_enabled: ClassVar[bool] = True
    from_param: ClassVar[str] = "apfrom"
    extra: ClassVar[Mapping[str, str]] = {}

    namespace: int = Namespace.ARTICLE
    protection_type: str = ""  # with ProtectedPagesSpecialPageProvider
    protection_level: str = ""

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in criteria or ("",):
            params: dict[str, Param] = {
                "action": "query",
                "list": "allpages",
                self.from_param: page,
                "apnamespace": self.namespace,
                "aplimit": "max",
                **self.extra,
            }
            if self.protection_type:
                params["apprtype"] = self.protection_type
                params["apprlevel"] = self.protection_level
            out.extend(self._run(params, _list_items("allpages"), len(out)))
        return out


@dataclass
class AllCategoriesSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "All categories"
    namespace: int = Namespace.CATEGORY


@dataclass
class AllFilesSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "All files"
    namespace: int = Namespace.FILE


@dataclass
class AllRedirectsSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "All redirects"
    extra: ClassVar[Mapping[str, str]] = {"apfilterredir": "redirects"}


@dataclass
class AllPagesNoRedirectsSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "All pages (no redirects)"
    extra: ClassVar[Mapping[str, str]] = {"apfilterredir": "nonredirects"}


@dataclass
class ProtectedPagesSpecialPageProvider(AllPagesSpecialPageProvider):
    """Protected pages: protection_type ("edit", "move", "upload") and protection_level
    ("autoconfirmed", "sysop", ...), which AWB asked for in a dialog."""

    display_text: ClassVar[str] = "Protected pages"
    protection_type: str = "edit"
    protection_level: str = "sysop"


@dataclass
class PagesWithoutLanguageLinksSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "Pages without language links"
    extra: ClassVar[Mapping[str, str]] = {"apfilterlanglinks": "withoutlanglinks"}


@dataclass
class PagesWithoutLanguageLinksNoRedirectsSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "Pages without language links (no redirects)"
    extra: ClassVar[Mapping[str, str]] = {
        "apfilterlanglinks": "withoutlanglinks",
        "apfilterredir": "nonredirects",
    }


@dataclass
class PrefixIndexSpecialPageProvider(AllPagesSpecialPageProvider):
    display_text: ClassVar[str] = "All pages with prefix (Prefixindex)"
    user_input_text: ClassVar[str] = "Prefix:"
    from_param: ClassVar[str] = "apprefix"


@dataclass
class RecentChangesSpecialPageProvider(ApiListProvider):
    display_text: ClassVar[str] = "Recent changes"
    namespaces_enabled: ClassVar[bool] = True

    namespace: int = Namespace.ARTICLE

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for page in criteria:
            params: dict[str, Param] = {
                "action": "query",
                "list": "recentchanges",
                "rctitle": page,
                "rcnamespace": self.namespace,
                "rclimit": "max",
            }
            out.extend(self._run(params, _list_items("recentchanges"), len(out)))
        return out


@dataclass
class NewPagesListProvider(ApiListProvider):
    display_text: ClassVar[str] = "New pages"
    user_input_enabled: ClassVar[bool] = False
    namespaces_enabled: ClassVar[bool] = True

    limit: int = 500
    namespace: int = Namespace.ARTICLE

    def make_list(self, *criteria: str) -> list[Article]:
        params: dict[str, Param] = {
            "action": "query",
            "list": "recentchanges",
            "rclimit": "max",
            "rctype": "new",
            "rcshow": "!redirect",
            "rcnamespace": self.namespace,
        }
        return self._run(params, _list_items("recentchanges"), 0)


@dataclass
class GalleryNewFilesSpecialPageProvider(ApiListProvider):
    display_text: ClassVar[str] = "New files"
    user_input_enabled: ClassVar[bool] = False

    limit: int = 1000  # slow query

    def make_list(self, *criteria: str) -> list[Article]:
        params = {"action": "query", "list": "logevents", "letype": "upload", "lelimit": "max"}
        return self._run(params, _list_items("logevents"), 0)


@dataclass
class PagesWithPropListProvider(ApiListProvider):
    display_text: ClassVar[str] = "Pages with a page property"
    user_input_text: ClassVar[str] = "Property name:"

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for prop in criteria:
            params = {
                "action": "query",
                "list": "pageswithprop",
                "pwppropname": prop,
                "pwplimit": "max",
            }
            out.extend(self._run(params, _list_items("pageswithprop"), len(out)))
        return out


# files ----------------------------------------------------------------------------------------

_RegexFromFile = DotNetRegex("(^[a-z]{2,3}:)|(simple:)")
_LoadWikiLink = DotNetRegex(r"\[\[:?([^\|[\]]+)(?:\]\]|\|)")


def titles_from_text(page_text: str, validate: bool = True) -> list[Article]:
    """TextFileListProviderUFT8: the [[wikilinks]] in a text (not interwikis or #sections), or
    else one title per line. validate=False is AWB's "no validation" filter: every line."""
    lines = [s for s in page_text.replace("\r\n", "\n").split("\n") if s]
    if not validate:
        return [Article(tools.remove_syntax(turn_first_to_upper(s.strip()))) for s in lines]
    if _LoadWikiLink.is_match(page_text):
        titles = (m.group(1) for m in _LoadWikiLink.matches(page_text))
        return [
            Article(tools.remove_syntax(turn_first_to_upper(t)))
            for t in titles
            if not _RegexFromFile.is_match(t) and not t.startswith("#")
        ]
    return [
        Article(tools.remove_syntax(turn_first_to_upper(s.strip())))
        for s in lines
        if s.strip() and tools.is_valid_title(s)
    ]


@dataclass
class TextFileListProvider(ListProvider):
    """Pages listed in text files (UTF-8; AWB also offered Windows-1252)."""

    display_text: ClassVar[str] = "Text file (UTF-8)"
    user_input_enabled: ClassVar[bool] = False

    encoding: str = "utf-8"
    validate: bool = True

    def make_list(self, *criteria: str) -> list[Article]:
        out: list[Article] = []
        for file_name in criteria:
            out.extend(titles_from_text(Path(file_name).read_text(self.encoding), self.validate))
        return out


@dataclass
class TextFileListProviderWindows1252(TextFileListProvider):
    display_text: ClassVar[str] = "Text file (Windows 1252 / ANSI)"
    encoding: str = "cp1252"


API_PROVIDERS: Sequence[type[ApiListProvider]] = (
    CategoryListProvider,
    CategoryRecursiveListProvider,
    CategoryRecursiveOneLevelListProvider,
    CategoriesOnPageListProvider,
    CategoriesOnPageNoHiddenListProvider,
    CategoriesOnPageOnlyHiddenListProvider,
    WhatLinksHereListProvider,
    WhatLinksHereAllNSListProvider,
    WhatLinksHereAndToRedirectsListProvider,
    WhatLinksHereAndToRedirectsAllNSListProvider,
    WhatLinksHereExcludingPageRedirectsListProvider,
    WhatLinksHereAndPageRedirectsExcludingTheRedirectsListProvider,
    RedirectsListProvider,
    RedirectsAllNSListProvider,
    WhatTranscludesPageListProvider,
    WhatTranscludesPageAllNSListProvider,
    LinksOnPageListProvider,
    LinksOnPageOnlyRedListProvider,
    LinksOnPageOnlyBlueListProvider,
    FilesOnPageListProvider,
    TransclusionsOnPageListProvider,
    ImageFileLinksListProvider,
    UserContribsListProvider,
    MyWatchlistListProvider,
    WikiSearchListProvider,
    WikiSearchAllNSListProvider,
    WikiTitleSearchListProvider,
    WikiTitleSearchAllNSListProvider,
    LinkSearchSpecialPageProvider,
    RandomPagesSpecialPageProvider,
    RandomRedirectsSpecialPageProvider,
    AllPagesSpecialPageProvider,
    AllCategoriesSpecialPageProvider,
    AllFilesSpecialPageProvider,
    AllRedirectsSpecialPageProvider,
    AllPagesNoRedirectsSpecialPageProvider,
    ProtectedPagesSpecialPageProvider,
    PagesWithoutLanguageLinksSpecialPageProvider,
    PagesWithoutLanguageLinksNoRedirectsSpecialPageProvider,
    PrefixIndexSpecialPageProvider,
    RecentChangesSpecialPageProvider,
    NewPagesListProvider,
    AllUsersSpecialPageProvider,
    DisambiguationPagesSpecialPageProvider,
    GalleryNewFilesSpecialPageProvider,
    PagesWithPropListProvider,
)
"""The wiki-backed providers, in the order the list maker offers them."""
