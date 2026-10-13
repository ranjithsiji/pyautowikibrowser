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

THEMES = ("system", "light", "dark")
ON_LOAD = ("diff", "edit")

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


@dataclass(frozen=True)
class Preferences:
    theme: str = "system"  # system / light / dark
    language: str = ""  # the interface language ("" = the system's)
    on_load: str = "diff"  # what to show when a page is loaded: the diff, or the edit box
    warn_on_exit: bool = True
    word_wrap: bool = True
    fonts: Mapping[str, FontChoice] = field(default_factory=dict[str, FontChoice])

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
