"""config.toml: profiles, defaults, round trip, and no passwords."""

from pathlib import Path

import pytest

from awb_x import paths
from awb_x.settings import appconfig as C

EXAMPLE = """
user_agent_contact = "https://ml.wikipedia.org/wiki/User:Example"
default_profile = "മലയാളം"

[[profiles]]
name = "English"
username = "Example@AWB-X"

[[profiles]]
name = "മലയാളം"
lang = "ml"
username = "Example@AWB-X"
remember_password = true
notes = "typo \\"fixing\\"\\nsecond line"
future_option = 1
"""


def test_parse_example() -> None:
    cfg = C.parse(EXAMPLE)
    assert cfg.user_agent_contact == "https://ml.wikipedia.org/wiki/User:Example"
    ml = cfg.profile()
    assert ml is not None and ml.name == "മലയാളം"
    assert ml.lang == "ml" and ml.project == "wikipedia" and ml.remember_password
    assert ml.wiki_url == "https://ml.wikipedia.org/w/"
    assert ml.user_name == "Example"
    assert ml.notes == 'typo "fixing"\nsecond line'
    assert cfg.profile("English") == C.Profile("English", username="Example@AWB-X")
    assert cfg.profile("Missing") is None


def test_defaults_without_file(tmp_path: Path) -> None:
    cfg = C.load(tmp_path / "none.toml")
    assert cfg == C.AppConfig()
    assert cfg.user_agent_contact == C.DEFAULT_USER_AGENT_CONTACT
    assert cfg.profile() is None


def test_round_trip(tmp_path: Path) -> None:
    cfg = C.parse(EXAMPLE)
    path = C.save(cfg, tmp_path / "sub" / "config.toml")
    assert C.load(path) == cfg
    lines = path.read_text(encoding="utf-8").splitlines()
    assert not any(line.startswith("password") for line in lines)
    if paths.os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600


def test_custom_wiki_profile() -> None:
    p = C.Profile("Example wiki", project="custom", custom_url="https://wiki.example.org/w/")
    assert p.wiki_url == "https://wiki.example.org/w/"


def test_with_and_without_profile() -> None:
    cfg = C.AppConfig().with_profile(C.Profile("A"), make_default=True).with_profile(C.Profile("B"))
    assert C.profile_names(cfg) == ["A", "B"] and cfg.default_profile == "A"
    cfg = cfg.with_profile(C.Profile("A", lang="hi"))
    assert cfg.profile("A") == C.Profile("A", lang="hi")
    cfg = cfg.without_profile("A")
    assert C.profile_names(cfg) == ["B"] and cfg.default_profile == ""
    assert cfg.profile() == C.Profile("B")  # first profile when there is no default


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[[profiles]]\nname = 'A'\npassword = 'x'", "keychain"),
        ("[[profiles]]\nlang = 'en'", "needs a name"),
        ("[[profiles]]\nname = 'A'\n[[profiles]]\nname = 'A'", "unique"),
        ("[[profiles]]\nname = 'A'\nremember_password = 'yes'", "bool"),
        ("profiles = 3", "array of tables"),
        ("not toml =", "line 1"),
    ],
)
def test_errors(text: str, message: str) -> None:
    with pytest.raises(C.ConfigError, match=message):
        C.parse(text)


def test_config_path_honours_awb_x_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWB_X_HOME", str(tmp_path))
    assert C.config_path() == tmp_path / "config.toml"
    assert paths.data_dir() == tmp_path
