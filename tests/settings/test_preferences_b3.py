"""AWB's remaining preferences, alerts and default summaries in config.toml."""

from dataclasses import replace

from pyawb.settings import appconfig
from pyawb.settings.preferences import DEFAULT_SUMMARIES, Preferences


def roundtrip(p: Preferences) -> Preferences:
    return appconfig.parse(
        appconfig.dumps(replace(appconfig.AppConfig(), preferences=p))
    ).preferences


def test_new_preferences_roundtrip() -> None:
    p = replace(
        Preferences(),
        on_load="preview",
        minimize_to_tray=True,
        low_priority=True,
        clear_list_on_wiki_change=True,
        autosave_edit_box=True,
        autosave_seconds=90,
        autosave_file="/tmp/x.txt",
        show_timer=True,
        flash=True,
        beep=True,
        alerts=(4, 17),
        summaries=("ശുചീകരണം", "تنظيف"),
        custom_summaries=True,
    )
    assert roundtrip(p) == p


def test_bad_values_fall_back() -> None:
    text = (
        "[preferences]\n"
        'on_load = "sideways"\nautosave_seconds = 1\nflash = "yes"\nalerts = [4, 99, "x"]\n'
        'paste_more = ["a"]\n'
    )
    p = appconfig.parse(text).preferences
    assert p.on_load == "diff" and p.autosave_seconds == 30 and not p.flash
    assert p.alerts == (4,)
    assert p.paste_more[0] == "a" and len(p.paste_more) == 10


def test_default_summaries_only_for_english() -> None:
    p = Preferences()
    assert p.summaries_for("en") == DEFAULT_SUMMARIES
    assert p.summaries_for("ml") == ()
    p = replace(p, summaries=(), custom_summaries=True)
    assert p.summaries_for("en") == ()  # cleared on purpose stays cleared
