"""Shared helpers for ported AWB tests."""

from awb_l.core import wikiregexes as W
from awb_l.core.site import SiteConfig, set_current_site

EN = SiteConfig.english()


def set_lang(lang_code: str) -> W.SiteRegexes:
    """Variables.SetProjectLangCode + WikiRegexes.MakeLangSpecificRegexes (undone after the test
    by the autouse fixture in conftest.py)."""
    from awb_l.core.site import current_site

    site = current_site().with_lang_code(lang_code)
    set_current_site(site)
    return W.for_site(site)


def set_site(**changes: object) -> W.SiteRegexes:
    """Assigning to a Variables property in AWB tests: change the current site's settings."""
    from dataclasses import replace

    from awb_l.core.site import current_site

    site = replace(current_site(), **changes)  # pyright: ignore[reportArgumentType]
    set_current_site(site)
    return W.for_site(site)


def cs_len(x: object) -> int:
    """C# .Length: string length, or a match's length."""
    if isinstance(x, str):
        return len(x)
    return x.length  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]


def utc_month_year() -> str:
    """System.DateTime.UtcNow.ToString("MMMM yyyy", BritishEnglish), e.g. "October 2026"."""
    import datetime

    from awb_l.core.site import EN_MONTH_NAMES

    now = datetime.datetime.now(datetime.UTC)
    return f"{EN_MONTH_NAMES[now.month - 1]} {now.year}"


def set_project(lang_code: str, project: str) -> W.SiteRegexes:
    """Variables.SetProject / SetProjectSimple: switch wiki. English Wikipedia gets AWB's full
    English configuration; other wikis keep the current namespaces (AWB would load them)."""
    from dataclasses import replace

    from awb_l.core.site import current_site

    if (lang_code, project) == ("en", "wikipedia"):
        site = SiteConfig.english()
    else:
        site = replace(current_site().with_lang_code(lang_code), project=project)
    set_current_site(site)
    return W.for_site(site)
