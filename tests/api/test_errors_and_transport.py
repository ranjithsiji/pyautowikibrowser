"""Error mapping (ApiEdit.CheckForErrors), request parameters and pywikibot set-up."""

import os
from pathlib import Path

import pytest

from pyawb.api import errors as E
from pyawb.api.transport import USER_AGENT_FORMAT, normalise_params


@pytest.mark.parametrize(
    ("code", "info", "extra", "cls"),
    [
        ("maxlag", "Waiting for db1: 12.5 seconds lagged", {}, E.MaxlagException),
        ("wrnotloggedin", "", {}, E.LoggedOffException),
        ("assertuserfailed", "", {}, E.LoggedOffException),
        ("spamblacklist", "", {"spamblacklist": "example.com"}, E.SpamlistException),
        ("fileexists-sharedrepo-perm", "", {}, E.SharedRepoException),
        ("hookaborted", "", {}, E.MediaWikiSaysNoException),
        ("abusefilter-disallowed", "", {}, E.MediaWikiSaysNoException),
        (
            "readonly",
            "The wiki is read-only",
            {"readonlyreason": "maintenance"},
            E.MediaWikiReadOnlyException,
        ),
        ("editconflict", "", {}, E.EditConflictException),
        ("readapidenied", "", {}, E.ReadApiDeniedException),
        ("uploaddisabled", "", {}, E.FeatureDisabledException),
        ("tpt-target-page", "", {}, E.TranslationPageEditException),
        ("badtoken", "", {}, E.ApiErrorException),
    ],
)
def test_api_error_mapping(code: str, info: str, extra: dict[str, str], cls: type) -> None:
    e = E.api_error(code, info, extra)
    assert isinstance(e, cls)
    assert isinstance(e, E.ApiErrorException)
    assert e.code == code


def test_maxlag_from_info_and_readonly_reason() -> None:
    e = E.api_error("maxlag", "Waiting for db1: 12.5 seconds lagged")
    assert isinstance(e, E.MaxlagException) and e.maxlag == 12.5
    ro = E.api_error("readonly", "Read-only", {"readonlyreason": "maintenance"})
    assert "Reason: maintenance" in ro.info


def test_check_errors() -> None:
    with pytest.raises(E.ApiBlankException):
        E.check_errors({})
    with pytest.raises(E.SpamlistException) as e:
        E.check_errors({"error": {"code": "spamblacklist", "info": "x", "spamblacklist": "a.com"}})
    assert e.value.extra == {"spamblacklist": "a.com"}
    assert E.check_errors({"query": {}}) == {"query": {}}


def test_normalise_params() -> None:
    p = normalise_params(
        {"action": "query", "redirects": True, "curtimestamp": None, "minor": False, "limit": 10}
    )
    assert p == {
        "format": "json",
        "formatversion": "2",
        "action": "query",
        "redirects": "1",
        "curtimestamp": "1",
        "limit": "10",
    }


def test_user_agent_is_descriptive() -> None:
    assert USER_AGENT_FORMAT.startswith("PyAutoWikiBrowser/")
    assert "{script_comments}" in USER_AGENT_FORMAT


def test_load_pywikibot_without_user_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pyawb.api.transport as transport

    monkeypatch.setattr(transport, "_pywikibot", None)
    monkeypatch.setenv("PYWIKIBOT_DIR", "")
    pwb = transport.load_pywikibot(tmp_path / "pwb")
    from pywikibot import config

    assert pwb is not None
    assert os.environ["PYWIKIBOT_NO_USER_CONFIG"] == "2"
    assert config.user_agent_format == USER_AGENT_FORMAT
    assert config.write_maxlag == 5
    assert config.base_dir == str(tmp_path / "pwb")  # not the working directory
    assert transport.load_pywikibot() is pwb  # loaded once
