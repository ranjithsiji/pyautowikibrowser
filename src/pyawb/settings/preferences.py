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
"""The user's preferences (the [preferences] and [fonts.<script>] tables of config.toml), and
which script a wiki's language is written in, so that fonts can be chosen per script.

Fonts matter: a font without the script's glyphs, or with poor shaping for it, makes Malayalam,
Arabic or Devanagari text unreadable in the editor and the diff. The choice is kept per script
(not per wiki): every Malayalam wiki uses the Malayalam fonts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

THEMES = ("system", "light", "dark")
ON_LOAD = ("diff", "preview", "edit")  # AWB's "On load": show changes / preview / edit box

# script -> languages (MediaWiki codes); anything else is Latin. Names are Qt's
# QFontDatabase.WritingSystem names where Qt has one.
_SCRIPT_LANGUAGES: Mapping[str, tuple[str, ...]] = {
    "Arabic": ("ar", "arz", "ary", "aeb", "fa", "ur", "ps", "sd", "ckb", "azb", "mzn", "glk", "ks",
               "ug", "pnb", "lrc", "bqi", "skr", "bcc", "khw", "ku-arab", "ha-arab"),
    "Hebrew": ("he", "yi", "lad-hebr"),
    "Thaana": ("dv",),
    "Syriac": ("arc", "syc"),
    "Devanagari": ("hi", "mr", "ne", "sa", "mai", "bh", "bho", "new", "awa", "dty", "anp",
                   "gom-deva", "mag", "hne", "kok", "sat-deva"),
    "Bengali": ("bn", "as", "bpy", "mni-beng", "rkt"),
    "Gurmukhi": ("pa", "pa-guru"),
    "Gujarati": ("gu",),
    "Oriya": ("or",),
    "Tamil": ("ta",),
    "Telugu": ("te",),
    "Kannada": ("kn", "tcy"),
    "Malayalam": ("ml",),
    "Sinhala": ("si",),
    "Thai": ("th",),
    "Lao": ("lo",),
    "Tibetan": ("bo", "dz"),
    "Myanmar": ("my", "shn", "mnw", "blk"),
    "Georgian": ("ka", "xmf"),
    "Khmer": ("km",),
    "Armenian": ("hy", "hyw"),
    "Greek": ("el", "pnt", "grc"),
    "Ethiopic": ("am", "ti"),
    "Cyrillic": ("ru", "uk", "be", "be-tarask", "bg", "sr", "mk", "kk", "ky", "tg", "tt", "ba",
                 "cv", "ce", "sah", "os", "mn", "ab", "av", "kbd", "krc", "lbe", "lez", "mhr",
                 "mrj", "myv", "koi", "kv", "udm", "xal", "tyv", "bxr", "rue", "inh", "ady", "mdf",
                 "alt", "cu", "sr-ec", "tt-cyrl", "kk-cyrl"),
    "SimplifiedChinese": ("zh", "zh-hans", "zh-cn", "wuu", "gan", "gan-hans"),
    "TraditionalChinese": ("zh-hant", "zh-tw", "zh-hk", "yue", "zh-yue", "lzh", "zh-classical",
                           "gan-hant"),
    "Japanese": ("ja",),
    "Korean": ("ko", "ko-kp"),
    "Vietnamese": ("vi",),
    "Nko": ("nqo",),
    "Ol Chiki": ("sat",),
}  # fmt: skip
_LANGUAGE_SCRIPT = {lang: script for script, langs in _SCRIPT_LANGUAGES.items() for lang in langs}

SAMPLES: Mapping[str, str] = {
    "Latin": "Wikipedia, the free encyclopedia — Ąą Ğğ İı Øø Şş ẞß",
    "Arabic": "ويكيبيديا، الموسوعة الحرة — پ چ ژ گ ی",
    "Hebrew": "ויקיפדיה, האנציקלופדיה החופשית",
    "Thaana": "ވިކިޕީޑިއާ",
    "Syriac": "ܘܝܩܝܦܕܝܐ",
    "Devanagari": "विकिपीडिया, एक मुक्त ज्ञानकोश — क्षत्रिय श्री",
    "Bengali": "উইকিপিডিয়া, মুক্ত বিশ্বকোষ",
    "Gurmukhi": "ਵਿਕੀਪੀਡੀਆ, ਇੱਕ ਆਜ਼ਾਦ ਗਿਆਨਕੋਸ਼",
    "Gujarati": "વિકિપીડિયા, મુક્ત જ્ઞાનકોશ",
    "Oriya": "ଉଇକିପିଡ଼ିଆ, ଏକ ମୁକ୍ତ ଜ୍ଞାନକୋଷ",
    "Tamil": "விக்கிப்பீடியா, கட்டற்ற கலைக்களஞ்சியம்",
    "Telugu": "వికీపీడియా, స్వేచ్ఛా విజ్ఞాన సర్వస్వం",
    "Kannada": "ವಿಕಿಪೀಡಿಯ, ಮುಕ್ತ ವಿಶ್ವಕೋಶ",
    "Malayalam": "വിക്കിപീഡിയ, സ്വതന്ത്ര വിജ്ഞാനകോശം — ൻ ൽ ർ ൾ ൺ",
    "Sinhala": "විකිපීඩියා, නිදහස් විශ්වකෝෂය",
    "Thai": "วิกิพีเดีย สารานุกรมเสรี",
    "Lao": "ວິກິພີເດຍ",
    "Tibetan": "ཝེ་ཁེ་རིག་མཛོད།",
    "Myanmar": "ဝီကီပီးဒီးယား",
    "Georgian": "ვიკიპედია, თავისუფალი ენციკლოპედია",
    "Khmer": "វិគីភីឌា",
    "Armenian": "Վիքիպեդիա, ազատ հանրագիտարան",
    "Greek": "Βικιπαίδεια, η ελεύθερη εγκυκλοπαίδεια",
    "Ethiopic": "ውክፔዲያ",
    "Cyrillic": "Википедия — свободная энциклопедия",
    "SimplifiedChinese": "维基百科，自由的百科全书 𠀋",
    "TraditionalChinese": "維基百科，自由的百科全書",
    "Japanese": "ウィキペディア、フリー百科事典 ー",
    "Korean": "위키백과, 우리 모두의 백과사전",
    "Vietnamese": "Wikipedia tiếng Việt, bách khoa toàn thư mở",
    "Nko": "ߥߞߌߔߌߘߌߦߊ",
    "Ol Chiki": "ᱣᱤᱠᱤᱯᱤᱰᱤᱭᱟ",
}

_RTL_LANGUAGES = frozenset(
    _SCRIPT_LANGUAGES["Arabic"] + _SCRIPT_LANGUAGES["Hebrew"] + _SCRIPT_LANGUAGES["Thaana"]
    + _SCRIPT_LANGUAGES["Syriac"] + _SCRIPT_LANGUAGES["Nko"]
)  # fmt: skip


def script_for_language(lang: str) -> str:
    """The script a MediaWiki language code is written in ("Malayalam", "Arabic"…; "Latin" for the
    rest). A code with a script suffix ("sr-el", "kk-latn") falls back to its base language."""
    lang = lang.lower()
    if lang in _LANGUAGE_SCRIPT:
        return _LANGUAGE_SCRIPT[lang]
    if lang.endswith(("-latn", "-el", "-latin")):
        return "Latin"
    base = lang.split("-", 1)[0]
    return _LANGUAGE_SCRIPT.get(base, "Latin")


def is_rtl_language(lang: str) -> bool:
    """Whether a language is written right to left (the window is then mirrored): Meta-Wiki's
    languageinfo, else the scripts above."""
    from pyawb.settings import languages

    known = languages.load().languages.get(lang)
    if known is not None:
        return known.rtl
    lang = lang.lower()
    return lang in _RTL_LANGUAGES or lang.split("-", 1)[0] in _RTL_LANGUAGES


@dataclass(frozen=True)
class FontChoice:
    """The fonts for one script; "" / 0 means the system's default."""

    editor: str = ""
    editor_size: int = 0
    interface: str = ""
    diff: str = ""


PASTE_MORE_SLOTS = 10


# Options ▸ Preferences ▸ Alerts (AWB Preferences.cs ids): which alerts the Start tab shows;
# none chosen shows them all, as in AWB
ALERTS: tuple[tuple[int, str], ...] = (
    (1, "Ambiguous citation dates"),
    (2, "Contains 'sic' tag"),
    (3, "DAB page with <ref>s"),
    (4, "Dead links"),
    (5, "Duplicate parameters in WPBannerShell"),
    (6, "Has <ref> after </references>"),
    (7, "Has 'No/More footnotes' template yet many references"),
    (8, "Headers with wikilinks"),
    (9, "Invalid citation parameters"),
    (10, "Links with double pipes"),
    (11, "Links with no target"),
    (12, "Long article with stub tag"),
    (13, "Multiple DEFAULTSORT"),
    (14, "No category (may be one in a template)"),
    (15, "See also section out of place"),
    (16, "Starts with heading"),
    (17, "Unbalanced brackets"),
    (18, "Unclosed tags"),
    (19, "Unformatted references"),
    (20, "Unknown parameters in multiple issues"),
    (21, "Unknown parameters in WikiProject banner shell"),
    (22, "Editor's signature or link to user space"),
)

# AWB's LoadDefaultEditSummaries: English Wikipedia's wording, offered on English-language wikis
DEFAULT_SUMMARIES: tuple[str, ...] = (
    "clean up",
    "re-categorisation per [[WP:CFD|CFD]]",
    "clean up and re-categorisation per [[WP:CFD|CFD]]",
    "removing category per [[WP:CFD|CFD]]",
    "[[Wikipedia:Template substitution|subst:'ing]]",
    "[[Wikipedia:WikiProject Stub sorting|stub sorting]]",
    "[[WP:AWB/T|Typo fixing]]",
    "bad link repair",
    "Fixing [[Wikipedia:Disambiguation pages with links|links to disambiguation pages]]",
    "Unicodifying",
)

AUTOSAVE_SECONDS = (5, 3600)  # the edit box auto-save period's range


def default_autosave_file() -> Path:
    """AWB's "Edit Box.txt", in PyAWB's data directory."""
    from pyawb import paths

    return paths.data_dir() / "Edit Box.txt"


@dataclass(frozen=True)
class Preferences:
    theme: str = "system"  # system / light / dark
    language: str = ""  # the interface language ("" = the system's)
    on_load: str = "diff"  # what to show when a page is loaded: diff, preview or the edit box
    diff_in_bot_mode: bool = False  # bot mode (Bots ▸ Auto save) shows the diff as well
    warn_on_exit: bool = True
    word_wrap: bool = True
    # the edit box's Paste more ▸ texts (Ctrl+1 … Ctrl+0); AWB kept them in the settings file
    paste_more: tuple[str, ...] = ("",) * PASTE_MORE_SLOTS
    # AWB Preferences: General
    minimize_to_tray: bool = False
    low_priority: bool = False  # process pages in low-priority threads
    # Site. AWB's "Suppress 'using AWB'" is left out: AWB enables it only on non-Wikimedia
    # wikis, where no tag is added anyway; on Wikimedia wikis only bots may drop the tag.
    clear_list_on_wiki_change: bool = False
    # Editing and saving
    autosave_edit_box: bool = False
    autosave_seconds: int = 30
    autosave_file: str = ""  # "" = "Edit Box.txt" in PyAWB's data directory
    show_timer: bool = False  # seconds since the last save, in the status bar
    tag_page_actions: bool = False  # add the tool's summary tag to move/delete/protect reasons
    flash: bool = False  # when a page is ready to save and the window is in the background
    beep: bool = False
    # Alerts: ids from ALERTS to show ((): all)
    alerts: tuple[int, ...] = ()
    # Options ▸ Default edit summaries; custom_summaries False: AWB's list on English wikis
    summaries: tuple[str, ...] = ()
    custom_summaries: bool = False
    fonts: Mapping[str, FontChoice] = field(default_factory=dict[str, FontChoice])

    def autosave_path(self) -> Path:
        return Path(self.autosave_file) if self.autosave_file else default_autosave_file()

    def summaries_for(self, lang: str) -> tuple[str, ...]:
        """The Default summary list for a wiki in language lang."""
        if self.custom_summaries:
            return self.summaries
        return DEFAULT_SUMMARIES if lang == "en" or lang.startswith("en-") else ()

    def font_for(self, script: str) -> FontChoice:
        return self.fonts.get(script, FontChoice())

    def with_font(self, script: str, choice: FontChoice) -> Preferences:
        from dataclasses import replace

        fonts = dict(self.fonts)
        if choice == FontChoice():
            fonts.pop(script, None)
        else:
            fonts[script] = choice
        return replace(self, fonts=fonts)


# Noto's family names where they are not "Noto Sans <script>"
_NOTO_NAMES: Mapping[str, tuple[str, ...]] = {
    # installed names first; the last is the family on Google Fonts
    "SimplifiedChinese": ("Noto Sans CJK SC", "Noto Sans SC"),
    "TraditionalChinese": ("Noto Sans CJK TC", "Noto Sans TC"),
    "Japanese": ("Noto Sans CJK JP", "Noto Sans JP"),
    "Korean": ("Noto Sans CJK KR", "Noto Sans KR"),
    "Arabic": ("Noto Naskh Arabic", "Noto Sans Arabic"),
    "Hebrew": ("Noto Sans Hebrew", "Noto Serif Hebrew"),
    "Ol Chiki": ("Noto Sans Ol Chiki",),
    "Nko": ("Noto Sans NKo",),
}


def suggest_font(script: str, families: Sequence[str]) -> str:
    """A font to start with for the script, from the installed families that have it: its Noto
    font if installed, else a family named after the script, else the first. "" for Latin (the
    system's font has it) and when nothing is installed."""
    if script == "Latin" or not families:
        return ""
    installed = {f.casefold(): f for f in families}
    for name in (*_NOTO_NAMES.get(script, ()), f"Noto Sans {script}", f"Noto Serif {script}"):
        if name.casefold() in installed:
            return installed[name.casefold()]
    word = script.casefold()
    named = [f for f in families if word in f.casefold() and "mono" not in f.casefold()]
    return named[0] if named else families[0]


# Debian/Ubuntu packages with fonts for scripts often missing from a default install
_DEBIAN_PACKAGES: Mapping[str, str] = {
    "Malayalam": "fonts-smc-manjari fonts-noto-core",
    "Tamil": "fonts-noto-core fonts-taml",
    "Devanagari": "fonts-noto-core fonts-deva",
    "Bengali": "fonts-noto-core fonts-beng",
    "SimplifiedChinese": "fonts-noto-cjk",
    "TraditionalChinese": "fonts-noto-cjk",
    "Japanese": "fonts-noto-cjk",
    "Korean": "fonts-noto-cjk",
}


@dataclass(frozen=True)
class FontHelp:
    """How to get a font for a script: the Noto family to look for and where to download it."""

    family: str
    download_url: str
    linux: str
    windows: str
    macos: str


def font_install_help(script: str) -> FontHelp:
    """Install advice for a script's font (Google's Noto family covers every script)."""
    family = (_NOTO_NAMES.get(script) or (f"Noto Sans {script}",))[-1]
    url = "https://fonts.google.com/noto/specimen/" + family.replace(" ", "+")
    package = _DEBIAN_PACKAGES.get(script, "fonts-noto-core fonts-noto-extra")
    return FontHelp(
        family=family,
        download_url=url,
        linux=f"sudo apt install {package}   (Fedora: sudo dnf install google-noto-sans-fonts)",
        windows="Settings → Time & language → Language & region → add the language, or "
        "Settings → Personalization → Fonts → install the downloaded font",
        macos="Font Book → File → Add Fonts… with the downloaded font",
    )
