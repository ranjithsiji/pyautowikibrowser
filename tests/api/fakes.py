"""A fake Transport: answers requests from a handler and records them."""

from collections.abc import Callable, Mapping
from typing import Any

from pyawb.api.errors import check_errors
from pyawb.api.transport import Param, normalise_params

type Handler = Callable[[dict[str, str]], Mapping[str, Any]]


class FakeTransport:
    def __init__(self, handler: Handler | None = None) -> None:
        self.handler = handler
        self.pages: dict[str, str] = {}  # raw page texts served to prop=revisions queries
        self.requests: list[tuple[dict[str, str], bool, str | None]] = []
        self.responses: dict[tuple[str, str], Mapping[str, Any]] = {}  # (key, value) -> response

    def request(
        self, params: Mapping[str, Param], *, post: bool = False, token: str | None = None
    ) -> Mapping[str, Any]:
        p = normalise_params(params)
        self.requests.append((p, post, token))
        if token is not None:
            p["token"] = "TOKEN+\\"
        for (k, v), response in self.responses.items():
            if p.get(k) == v:
                return check_errors(response)
        if p.get("prop") == "revisions" and p.get("rvprop") == "content" and "titles" in p:
            return page_response(p["titles"], self.pages.get(p["titles"]))
        if self.handler is None:
            raise AssertionError(f"unexpected request {p}")
        return check_errors(self.handler(p))

    def last(self, action: str) -> dict[str, str]:
        for p, _, _ in reversed(self.requests):
            if p.get("action") == action:
                return p
        raise AssertionError(f"no {action} request")


def page_response(title: str, text: str | None) -> Mapping[str, Any]:
    if text is None:
        return {"query": {"pages": [{"ns": 0, "title": title, "missing": True}]}}
    return {
        "query": {
            "pages": [
                {
                    "pageid": 1,
                    "ns": 0,
                    "title": title,
                    "revisions": [
                        {"slots": {"main": {"contentmodel": "wikitext", "content": text}}}
                    ],
                }
            ]
        }
    }


def namespaces(names: Mapping[int, tuple[str, str]]) -> dict[str, Any]:
    """formatversion=2 namespaces: id -> (local name, canonical name)."""
    out: dict[str, Any] = {"0": {"id": 0, "case": "first-letter", "name": "", "content": True}}
    for ns, (name, canonical) in names.items():
        out[str(ns)] = {"id": ns, "case": "first-letter", "name": name, "canonical": canonical}
    return out


AR_NAMESPACES: dict[int, tuple[str, str]] = {
    -2: ("ميديا", "Media"),
    -1: ("خاص", "Special"),
    1: ("نقاش", "Talk"),
    2: ("مستخدم", "User"),
    3: ("نقاش المستخدم", "User talk"),
    4: ("ويكيبيديا", "Project"),
    5: ("نقاش ويكيبيديا", "Project talk"),
    6: ("ملف", "File"),
    7: ("نقاش الملف", "File talk"),
    8: ("ميدياويكي", "MediaWiki"),
    9: ("نقاش ميدياويكي", "MediaWiki talk"),
    10: ("قالب", "Template"),
    11: ("نقاش القالب", "Template talk"),
    12: ("مساعدة", "Help"),
    13: ("نقاش المساعدة", "Help talk"),
    14: ("تصنيف", "Category"),
    15: ("نقاش التصنيف", "Category talk"),
    100: ("بوابة", "Portal"),
    101: ("نقاش البوابة", "Portal talk"),
    828: ("وحدة", "Module"),
    829: ("نقاش الوحدة", "Module talk"),
}

AR_SITEINFO: dict[str, Any] = {
    "batchcomplete": True,
    "query": {
        "general": {
            "mainpage": "الصفحة الرئيسية",
            "base": "https://ar.wikipedia.org/wiki/",
            "sitename": "ويكيبيديا",
            "generator": "MediaWiki 1.45.0-wmf.20",
            "case": "first-letter",
            "lang": "ar",
            "rtl": True,
            "server": "//ar.wikipedia.org",
            "scriptpath": "/w",
            "articlepath": "/wiki/$1",
            "categorycollation": "uca-ar",
        },
        "namespaces": namespaces(AR_NAMESPACES),
        "namespacealiases": [
            {"id": 4, "alias": "WP"},
            {"id": 6, "alias": "صورة"},
            {"id": 6, "alias": "Image"},
            {"id": 2, "alias": "مستخدمة"},
        ],
        "magicwords": [
            {"name": "redirect", "aliases": ["#تحويل", "#REDIRECT"], "case-sensitive": False},
            {"name": "defaultsort", "aliases": ["ترتيب:", "DEFAULTSORT:"], "case-sensitive": True},
        ],
    },
}

AR_MONTHS = [
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
]


def allmessages(names: list[str], values: list[str]) -> dict[str, Any]:
    return {
        "query": {
            "allmessages": [
                {"name": n, "normalizedname": n, "content": v}
                for n, v in zip(names, values, strict=True)
            ]
        }
    }


def userinfo(name: str, uid: int = 1, groups: tuple[str, ...] = ("user",)) -> dict[str, Any]:
    return {
        "query": {
            "userinfo": {
                "id": uid,
                "name": name,
                "groups": ["*", *groups],
                "rights": ["read", "edit", *(["bot"] if "bot" in groups else [])],
            }
        }
    }
