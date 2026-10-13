"""Wikidata items: parsing wbgetentities, batching, and the interwiki check in core."""

from typing import Any

from pyawb.api.wikidata import fetch_items_by_id, fetch_items_for_titles, parse_entities
from pyawb.core.site import SiteConfig
from pyawb.core.wikidata import (
    JULIAN,
    InterwikiCheck,
    WikidataItem,
    WikidataTime,
    check_interwikis,
    dbname,
    remove_interwikis_on_wikidata,
)

from .fakes import FakeTransport


def statement(
    prop: str, value: Any, rank: str = "normal", snaktype: str = "value"
) -> dict[str, Any]:
    snak: dict[str, Any] = {"snaktype": snaktype, "property": prop}
    if snaktype == "value":
        snak["datavalue"] = {"value": value}
    return {"mainsnak": snak, "type": "statement", "rank": rank}


def time_value(
    time: str, precision: int = 11, calendar: str = "http://www.wikidata.org/entity/Q1985727"
) -> dict[str, Any]:
    return {"time": time, "precision": precision, "calendarmodel": calendar, "timezone": 0}


ENTITY: dict[str, Any] = {
    "type": "item",
    "id": "Q42",
    "labels": {"en": {"language": "en", "value": "Douglas Adams"}},
    "descriptions": {"ml": {"language": "ml", "value": "ഇംഗ്ലീഷ് എഴുത്തുകാരൻ"}},
    "sitelinks": {
        "enwiki": {"site": "enwiki", "title": "Douglas Adams"},
        "dewiki": {"site": "dewiki", "title": "Douglas Adams"},
        "zh_yuewiki": {"site": "zh_yuewiki", "title": "道格拉斯·亞當斯"},
        "be_x_oldwiki": {"site": "be_x_oldwiki", "title": "Дуглас Адамс"},
    },
    "claims": {
        "P31": [statement("P31", {"entity-type": "item", "id": "Q5"})],
        "P569": [
            statement("P569", time_value("+1952-03-11T00:00:00Z")),
            statement("P569", time_value("+1950-00-00T00:00:00Z", 9), rank="deprecated"),
        ],
        "P570": [statement("P570", time_value("+2001-05-11T00:00:00Z"))],
        "P625": [statement("P625", {"latitude": 51.5, "longitude": -0.12, "precision": 0.01})],
        "P214": [statement("P214", "113230702"), statement("P214", "99", snaktype="novalue")],
        "P244": [statement("P244", "n80076765", rank="preferred"), statement("P244", "old")],
    },
}


def test_parse_entity() -> None:
    items = parse_entities(
        {"entities": {"Q42": ENTITY, "Q999999999": {"id": "Q999999999", "missing": ""}}}
    )
    assert list(items) == ["Q42"]
    item = items["Q42"]
    assert item.is_human
    assert item.birth_dates == (WikidataTime(1952, 3, 11, 11),)  # deprecated value ignored
    assert item.birth_year() == 1952 and item.death_year() == 2001
    assert item.is_living is False
    assert item.coordinates[0].latitude == 51.5
    assert item.authority_control == {"P214": ("113230702",), "P244": ("n80076765",)}
    assert item.descriptions["ml"] == "ഇംഗ്ലീഷ് എഴുത്തുകാരൻ"
    assert item.sitelinks["dewiki"] == "Douglas Adams"


def test_wikidata_time() -> None:
    assert WikidataTime.parse("+1952-03-11T00:00:00Z") == WikidataTime(1952, 3, 11)
    assert WikidataTime.parse("+1952-03-00T00:00:00Z", 10) == WikidataTime(1952, 3, 0, 10)
    assert WikidataTime.parse("-0044-03-15T00:00:00Z", 11, JULIAN).year == -44
    assert WikidataTime.parse("-0044-03-15T00:00:00Z", 11, JULIAN).is_julian


def test_ambiguous_birth_year() -> None:
    item = WikidataItem("Q1", birth_dates=(WikidataTime(1900), WikidataTime(1901)))
    assert item.birth_year() is None
    assert item.is_living is None  # not known to be human


def test_fetch_batches_of_fifty() -> None:
    t = FakeTransport(lambda p: {"entities": {}})
    fetch_items_by_id(t, [f"Q{i}" for i in range(120)] + ["Q1"], languages=["ml", "en", "ml"])
    assert [len(p["ids"].split("|")) for p, _, _ in t.requests] == [50, 50, 20]
    assert t.requests[0][0]["languages"] == "ml|en"


def test_fetch_for_titles_keys_by_requested_title() -> None:
    t = FakeTransport(
        lambda p: {
            "entities": {"Q42": ENTITY, "-1": {"site": "enwiki", "title": "Nope", "missing": ""}}
        }
    )
    items = fetch_items_for_titles(t, "enwiki", ["Douglas_Adams", "Nope"])
    assert list(items) == ["Douglas_Adams"]
    assert t.requests[0][0]["sites"] == "enwiki"


def test_dbname() -> None:
    assert dbname("de") == "dewiki"
    assert dbname("zh-yue") == "zh_yuewiki"
    assert dbname("be-tarask") == "be_x_oldwiki"
    assert dbname("fr", "wiktionary") == "frwiktionary"


ITEM = parse_entities({"entities": {"Q42": ENTITY}})["Q42"]
SITE = SiteConfig(interwiki_languages=frozenset({"de", "zh-yue", "be-tarask", "fr", "en"}))

TEXT = (
    "'''Douglas Adams''' was a writer.\r\n"
    "{{Infobox|link=[[de:Douglas Adams]]}}\r\n"
    "<!-- [[fr:Douglas Adams]] -->\r\n"
    "\r\n"
    "[[Category:Writers]]\r\n"
    "\r\n"
    "[[de:Douglas_Adams]]\r\n"
    "[[zh-yue:道格拉斯·亞當斯]]\r\n"
    "[[be-tarask:Інша назва]]\r\n"
    "[[fr:Douglas Adams]]\r\n"
)


def test_check_interwikis() -> None:
    check = check_interwikis(TEXT, ITEM, SITE)
    assert check == InterwikiCheck(
        redundant=("[[de:Douglas_Adams]]", "[[zh-yue:道格拉斯·亞當斯]]"),
        conflicts=(("[[be-tarask:Інша назва]]", "Інша назва", "Дуглас Адамс"),),
        not_on_wikidata=("[[fr:Douglas Adams]]",),
    )


def test_remove_interwikis_on_wikidata() -> None:
    text, check = remove_interwikis_on_wikidata(TEXT, ITEM, SITE)
    assert len(check.redundant) == 2
    assert text == (
        "'''Douglas Adams''' was a writer.\r\n"
        "{{Infobox|link=[[de:Douglas Adams]]}}\r\n"
        "<!-- [[fr:Douglas Adams]] -->\r\n"
        "\r\n"
        "[[Category:Writers]]\r\n"
        "\r\n"
        "[[be-tarask:Інша назва]]\r\n"
        "[[fr:Douglas Adams]]\r\n"
    )
    unchanged, check = remove_interwikis_on_wikidata("No links.", ITEM, SITE)
    assert unchanged == "No links." and check == InterwikiCheck()


def test_wiktionary_titles_are_case_sensitive() -> None:
    item = WikidataItem("Q1", sitelinks={"dewiktionary": "Haus"})
    site = SiteConfig(project="wiktionary", interwiki_languages=frozenset({"de"}))
    assert check_interwikis("[[de:haus]]", item, site).conflicts
    wiki = WikidataItem("Q1", sitelinks={"dewiki": "Haus"})
    assert check_interwikis(
        "[[de:haus]]", wiki, SiteConfig(interwiki_languages=frozenset({"de"}))
    ).redundant
