"""Preferences in config.toml, scripts of wiki languages, and Meta-Wiki's language data."""

from pathlib import Path

import pytest

from pyawb.api.languages import fetch_language_data
from pyawb.settings import appconfig, languages
from pyawb.settings.preferences import (
    FontChoice,
    Preferences,
    is_rtl_language,
    script_for_language,
)
from tests.api.fakes import FakeTransport


@pytest.mark.parametrize(
    ("lang", "script"),
    [
        ("ml", "Malayalam"),
        ("ar", "Arabic"),
        ("fa", "Arabic"),
        ("hi", "Devanagari"),
        ("zh-hant", "TraditionalChinese"),
        ("sr", "Cyrillic"),
        ("sr-el", "Latin"),
        ("en", "Latin"),
        ("de", "Latin"),
        ("ja", "Japanese"),
    ],
)
def test_script_for_language(lang: str, script: str) -> None:
    assert script_for_language(lang) == script


def test_rtl_languages_from_meta() -> None:
    assert is_rtl_language("ar") and is_rtl_language("he") and is_rtl_language("ckb")
    assert not is_rtl_language("ml") and not is_rtl_language("en")


def test_bundled_snapshot() -> None:
    data = languages.load()
    ml = data.language("ml")
    assert ml.autonym == "മലയാളം" and ml.name == "Malayalam" and not ml.rtl
    assert ml.label == "മലയാളം — Malayalam (ml)"
    codes = [lang.code for lang in data.wiki_languages("wikipedia")]
    assert {"en", "ml", "ar", "ta"} <= set(codes) and len(codes) > 300


def test_parse_meta_responses() -> None:
    info = {
        "query": {
            "languageinfo": {
                "ml": {"code": "ml", "autonym": "മലയാളം", "name": "Malayalam", "dir": "ltr"},
                "ar": {"code": "ar", "autonym": "العربية", "name": "Arabic", "dir": "rtl"},
                "x-alias": {"code": "x-alias", "autonym": "", "name": "", "dir": "ltr"},
            }
        }
    }
    matrix = {
        "sitematrix": {
            "count": 3,
            "0": {"code": "ml", "site": [{"code": "wiki"}, {"code": "wiktionary"}]},
            "1": {"code": "ar", "site": [{"code": "wiki"}, {"code": "wikinews", "closed": True}]},
            "specials": [],
        }
    }
    t = FakeTransport(lambda p: info if p.get("meta") == "languageinfo" else matrix)
    data = fetch_language_data(t)
    assert set(data.languages) == {"ml", "ar"} and data.languages["ar"].rtl
    assert data.wikis["wikipedia"] == ("ar", "ml")
    assert data.wikis["wiktionary"] == ("ml",) and data.wikis["wikinews"] == ()
    assert languages.from_json(languages.to_json(data)) == data


def test_newer_fetched_copy_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYAWB_HOME", str(tmp_path))
    languages.load.cache_clear()
    bundled = languages.load()
    newer = languages.LanguageData("9999-01-01", {}, {"wikipedia": ("ml",)})
    languages.save_cache(newer)
    assert languages.load().fetched == "9999-01-01"
    older = languages.LanguageData("2000-01-01", {}, {})
    languages.save_cache(older)
    assert languages.load().fetched == bundled.fetched
    languages.load.cache_clear()


def test_preferences_round_trip() -> None:
    prefs = Preferences(theme="dark", language="ml", on_load="edit", warn_on_exit=False)
    prefs = prefs.with_font("Malayalam", FontChoice("Noto Sans Malayalam", 14, "Manjari", ""))
    prefs = prefs.with_font("Arabic", FontChoice(editor="Noto Naskh Arabic"))
    config = appconfig.AppConfig(preferences=prefs)
    again = appconfig.parse(appconfig.dumps(config))
    assert again.preferences == prefs
    assert prefs.with_font("Arabic", FontChoice()).fonts.keys() == {"Malayalam"}


def test_bad_preferences_fall_back() -> None:
    text = '[preferences]\ntheme = "purple"\nword_wrap = "yes"\n[fonts.Latin]\neditor_size = 900\n'
    prefs = appconfig.parse(text).preferences
    assert prefs.theme == "system" and prefs.word_wrap is True
    assert prefs.font_for("Latin").editor_size == 0
