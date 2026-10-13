"""Building SiteConfig from siteinfo (offline, recorded-style responses)."""

import copy

import pytest

from awb_x.api import siteinfo as si
from awb_x.api.errors import BrokenResponseException, ReadApiDeniedException
from awb_x.core import namespace, wikiregexes
from awb_x.core.site import Namespace, use_site

from .fakes import AR_MONTHS, AR_SITEINFO, FakeTransport, allmessages


def test_parse_siteinfo_arabic() -> None:
    info = si.parse_siteinfo(AR_SITEINFO)
    assert info.language == "ar"
    assert info.is_right_to_left
    assert info.capitalize_first_letter
    assert info.mediawiki_version == "1.45.0-wmf.20"
    assert info.unicode_category_collation
    assert info.article_url == "https://ar.wikipedia.org/wiki/$1"
    assert info.namespaces[Namespace.CATEGORY] == "تصنيف:"
    assert 0 not in info.namespaces
    assert info.namespace_aliases[Namespace.FILE] == ("صورة:", "Image:")
    assert info.magic_words["redirect"] == ("#تحويل", "#REDIRECT")


def test_parse_siteinfo_errors() -> None:
    with pytest.raises(ReadApiDeniedException):
        si.parse_siteinfo({"error": {"code": "readapidenied", "info": "You need read permission"}})
    broken = copy.deepcopy(AR_SITEINFO)
    del broken["query"]["namespaces"]["14"]
    with pytest.raises(BrokenResponseException):
        si.parse_siteinfo(broken)


def test_rtl_formatversion_1() -> None:
    ltr = copy.deepcopy(AR_SITEINFO)
    del ltr["query"]["general"]["rtl"]
    assert not si.parse_siteinfo(ltr).is_right_to_left
    fv1 = copy.deepcopy(AR_SITEINFO)
    fv1["query"]["general"]["rtl"] = ""
    assert si.parse_siteinfo(fv1).is_right_to_left


def test_wiki_url() -> None:
    assert si.wiki_url("ml", "wikipedia") == ("https://ml.wikipedia.org", "/w/", "ml")
    assert si.wiki_url("de", "commons") == ("https://commons.wikimedia.org", "/w/", "en")
    assert si.wiki_url("", "custom", "wiki.example.org:8080/mw") == (
        "https://wiki.example.org:8080",
        "/mw/",
        "en",
    )
    assert si.wiki_url("", "custom", "http://localhost/w/") == ("http://localhost", "/w/", "en")


def test_summary_tag() -> None:
    assert si.summary_tag("en", "wikipedia") == " using [[WP:AWB|AWB]]"
    assert si.summary_tag("en", "wiktionary") == " using [[Project:AWB|AWB]]"
    assert si.summary_tag("de", "wikipedia") == " mit [[Project:AWB|AWB]]"
    # empty "using" part: no double space (AWB leaves one)
    assert si.summary_tag("ar", "wikipedia") == " باستخدام [[Project:أوب|أوب]]"
    assert si.summary_tag("zh", "wikipedia") == " 由 [[维基百科:自动维基浏览器|自动维基浏览器]]协助"
    # language wording is for the per-language projects only
    assert si.summary_tag("de", "commons") == " using [[Project:AWB|AWB]]"


def test_base_site_config() -> None:
    cfg = si.base_site_config("ar", "wikipedia")
    assert cfg.url_long == "https://ar.wikipedia.org/w/"
    assert cfg.lang_code == "ar"
    assert cfg.typo_summary_tag == "الأخطاء المصححة: "
    assert cfg.summary_tag == " باستخدام [[Project:أوب|أوب]]"
    commons = si.base_site_config("fr", "commons")
    assert commons.url == "https://commons.wikimedia.org"
    assert commons.lang_code == "en"


def test_site_config_from_siteinfo() -> None:
    base = si.base_site_config("ar", "wikipedia")
    cfg = si.site_config(base, si.parse_siteinfo(AR_SITEINFO), AR_MONTHS)
    assert cfg.rtl
    assert cfg.unicode_category_collation
    assert cfg.namespaces[Namespace.TEMPLATE] == "قالب:"
    assert cfg.canonical_namespaces[Namespace.TEMPLATE] == "Template:"
    assert cfg.canonical_namespaces[Namespace.PORTAL] == "Portal:"  # from the wiki
    assert cfg.month_names[0] == "يناير"
    assert cfg.summary_tag == base.summary_tag

    with use_site(cfg):
        assert namespace.determine("قالب:مرحبا") == Namespace.TEMPLATE
        assert namespace.determine("Template:مرحبا") == Namespace.TEMPLATE
        assert namespace.determine("صورة:Foo.jpg") == Namespace.FILE
        assert namespace.determine("Image:Foo.jpg") == Namespace.FILE
        s = wikiregexes.for_site(cfg)
        assert s.Category.is_match("[[تصنيف:علوم]]")
        assert s.Redirect.is_match("#تحويل [[مرحبا]]")


def test_site_config_tagged_edits_and_wiktionary() -> None:
    info = si.parse_siteinfo(AR_SITEINFO)
    assert (
        si.site_config(si.base_site_config("ar", "wikipedia"), info, tag_edits=True).summary_tag
        == ""
    )
    wikt = si.site_config(si.base_site_config("ar", "wiktionary"), info)
    assert not wikt.capitalize_first_letter
    # English Wikipedia keeps English month names whatever the messages say
    en = si.site_config(si.base_site_config("en", "wikipedia"), info, AR_MONTHS)
    assert en.month_names[0] == "January"


def test_custom_wiki_takes_language_from_siteinfo() -> None:
    cfg = si.site_config(
        si.base_site_config("", "custom", "https://wiki.example.org/w/"),
        si.parse_siteinfo(AR_SITEINFO),
    )
    assert cfg.lang_code == "ar"
    assert not cfg.unicode_category_collation  # never on custom wikis, as in AWB


def test_month_names_need_all_twelve() -> None:
    messages = dict(zip(si.MONTH_MESSAGES, AR_MONTHS, strict=True))
    assert si.month_names(messages) == tuple(AR_MONTHS)
    del messages["may-gen"]
    assert si.month_names(messages) is None


def test_parse_awb_tag_defined() -> None:
    assert si.parse_awb_tag_defined({"query": {"tags": [{"name": "AWB", "active": True}]}})
    assert not si.parse_awb_tag_defined({"query": {"tags": [{"name": "AWB"}]}})
    assert not si.parse_awb_tag_defined({"error": {"code": "readapidenied"}})


def test_load_site_config() -> None:
    t = FakeTransport()
    t.responses[("meta", "siteinfo")] = AR_SITEINFO
    t.responses[("meta", "allmessages")] = allmessages(list(si.MONTH_MESSAGES), AR_MONTHS)
    t.responses[("list", "tags")] = {"query": {"tags": [{"name": "AWB", "active": True}]}}
    cfg, info, tagged = si.load_site_config(t, si.base_site_config("ar", "wikipedia"))
    assert tagged and cfg.summary_tag == ""
    assert info.language == "ar"
    assert cfg.month_names[11] == "ديسمبر"
    assert t.last("query")["formatversion"] == "2"


IW_PAGE = """<!--InterwikiLocalAlphaBegins-->
ru, sq, en
<!--InterwikiLocalAlphaEnds-->
<!--InterwikiLocalFirstBegins-->
en, sq, ru, be-tarask, be
<!--InterwikiLocalFirstEnds-->"""


def test_parse_interwiki_order() -> None:
    order = si.parse_interwiki_order(IW_PAGE)
    assert order["interwiki_local_alpha"] == ("ru", "sq", "en")
    assert order["interwiki_local_first"] == ("en", "sq", "ru", "be-tarask", "be")
    assert order["interwiki_alpha"] == ("be", "be-tarask", "en", "ru", "sq")
    assert order["interwiki_alpha_en_first"] == ("en", "be", "be-tarask", "ru", "sq")


def test_parse_sitematrix() -> None:
    result = {
        "sitematrix": {
            "count": 3,
            "0": {
                "code": "ml",
                "name": "മലയാളം",
                "site": [
                    {"url": "https://ml.wikipedia.org", "dbname": "mlwiki", "code": "wiki"},
                    {
                        "url": "https://ml.wiktionary.org",
                        "dbname": "mlwiktionary",
                        "code": "wiktionary",
                    },
                ],
            },
            "1": {
                "code": "be-x-old",
                "name": "беларуская (тарашкевіца)",
                "site": [{"url": "https://be-tarask.wikipedia.org", "code": "wiki"}],
            },
            "specials": [{"url": "https://commons.wikimedia.org", "code": "commons"}],
        }
    }
    matrix = si.parse_sitematrix(result)
    assert matrix.languages == {"ml", "be-tarask"}
    assert matrix.language_names["ml"] == "മലയാളം"
    assert matrix.project_languages["wiktionary"] == {"ml"}
    assert matrix.project_languages["wikipedia"] == {"ml", "be-tarask"}
