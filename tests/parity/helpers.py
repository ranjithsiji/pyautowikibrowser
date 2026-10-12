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
