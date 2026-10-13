"""The CheckPage gate (Session.UpdateWikiStatus), offline."""

import json
from typing import Any

from awb_l.api.checkpage import (
    CheckPage,
    StatusResult,
    VersionPage,
    WikiConfigPage,
    WikiStatus,
    evaluate_status,
    parse_messages,
    usernames_equal,
)
from awb_l.api.models import UserInfo

VERSION = json.dumps(
    {
        "enabledversions": [
            {"version": "6.5.0.1", "dev": False},
            {"version": "6.6.0.0", "dev": True},
            {"version": "6.7.0.0", "dev": False},
        ],
        "updaterversion": "1.3.0.0",
        "badnames": ["^Vandal", "spambot$"],
        "globalusers": ["Global helper"],
        "messages": [
            {"version": "*", "text": " Hello everyone "},
            {"version": ["6.5.0.1", "0.1.0"], "text": "Old version note"},
            {"version": "*", "text": "Switched off", "enabled": False},
        ],
    }
)

CONFIG_RESTRICTED = json.dumps(
    {
        "typolink": "Project:AutoWikiBrowser/Typos",
        "allusersenabled": False,
        "allusersenabledusermode": False,
        "messages": [{"version": "*", "text": "Local note"}],
        "underscoretitles": [" C_Sharp ", ""],
        "nogenfixes": ["Foo", "Foo", "Bar"],
        "noregextypofix": ["Baz"],
    }
)

CHECKPAGE = json.dumps({"enabledusers": ["alice", "Ünal"], "enabledbots": ["AliceBot"]})

ALICE = UserInfo(name="Alice", id=10)


def status(
    user: UserInfo, config: str = CONFIG_RESTRICTED, check: str = CHECKPAGE, **kw: Any
) -> StatusResult:
    return evaluate_status(user, VERSION, config, check, app_version="0.1.0", **kw)


def test_usernames_compare_first_letter_case_insensitively() -> None:
    assert usernames_equal("alice", "Alice")
    assert usernames_equal("ünal", "Ünal")
    assert not usernames_equal("alice", "ALICE")


def test_listed_user_is_registered() -> None:
    r = status(ALICE, require_enabled_version=False)
    assert r.status == WikiStatus.REGISTERED and r.can_edit
    assert not r.is_bot
    assert r.messages == ("Hello everyone", "Old version note", "Local note")
    assert r.config.typo_link == "Project:AutoWikiBrowser/Typos"
    assert r.config.underscore_titles == ("C_Sharp",)
    assert r.config.no_genfixes == ("Foo", "Bar")
    assert status(UserInfo(name="ünal", id=3), require_enabled_version=False).can_edit


def test_bot_listed_in_enabledbots() -> None:
    r = status(UserInfo(name="aliceBot", id=11), require_enabled_version=False)
    assert r.status == WikiStatus.REGISTERED
    assert r.is_bot


def test_unlisted_user_is_not_registered() -> None:
    r = status(UserInfo(name="Bob", id=12), require_enabled_version=False)
    assert r.status == WikiStatus.NOT_REGISTERED and not r.can_edit


def test_sysops_and_global_users() -> None:
    sysop = UserInfo(name="Bob", id=12, groups=frozenset({"sysop"}))
    assert status(sysop, require_enabled_version=False).can_edit
    assert not status(sysop, require_enabled_version=False, project="wikia").can_edit
    helper = UserInfo(name="Global helper", id=13)
    assert status(helper, require_enabled_version=False).can_edit
    assert not status(helper, require_enabled_version=False, project="custom").can_edit


def test_not_logged_in() -> None:
    assert status(UserInfo(), require_enabled_version=False).status == WikiStatus.NOT_LOGGED_IN


def test_bad_names_refused() -> None:
    r = status(UserInfo(name="vandalism fan", id=14), require_enabled_version=False)
    assert r.status == WikiStatus.NOT_REGISTERED
    r = status(UserInfo(name="Alice the SpamBot", id=15), require_enabled_version=False)
    assert r.status == WikiStatus.NOT_REGISTERED


def test_no_checkpage_or_all_users_enabled() -> None:
    bob = UserInfo(name="Bob", id=12)
    r = status(bob, check="", require_enabled_version=False)
    assert r.can_edit and r.is_bot  # AWB enables bot mode too
    all_enabled = json.dumps({"allusersenabled": True, "allusersenabledusermode": False})
    assert status(bob, config=all_enabled, require_enabled_version=False).can_edit
    user_mode = json.dumps({"allusersenabled": False, "allusersenabledusermode": True})
    r = status(bob, config=user_mode, require_enabled_version=False)
    assert r.can_edit and not r.is_bot


def test_missing_config_page_uses_default() -> None:
    config = WikiConfigPage.parse("")
    assert config.is_default and config.all_users_enabled
    assert status(UserInfo(name="Bob", id=12), config="", require_enabled_version=False).can_edit


def test_version_check() -> None:
    r = evaluate_status(ALICE, VERSION, CONFIG_RESTRICTED, CHECKPAGE, app_version="6.4.0.0")
    assert r.status == WikiStatus.OLD_VERSION
    r = evaluate_status(ALICE, VERSION, CONFIG_RESTRICTED, CHECKPAGE, app_version="6.5.0.1")
    assert r.can_edit
    # disabled versions are refused before the login check, as in AWB
    r = evaluate_status(UserInfo(), VERSION, CONFIG_RESTRICTED, CHECKPAGE, app_version="1.0")
    assert r.status == WikiStatus.OLD_VERSION


def test_malformed_pages_give_error() -> None:
    r = evaluate_status(
        ALICE, "{not json", "", "", app_version="0.1.0", require_enabled_version=False
    )
    assert r.status == WikiStatus.ERROR
    r = status(ALICE, config="[1, 2]", require_enabled_version=False)
    assert r.status == WikiStatus.ERROR
    r = status(ALICE, check="nonsense", require_enabled_version=False)
    assert r.status == WikiStatus.ERROR


def test_version_page() -> None:
    page = VersionPage.parse(VERSION)
    assert page.is_enabled("6.5.0.1")
    assert page.newer_versions("6.5.0.1") == ["6.7.0.0"]  # dev versions are not offered
    assert page.updater_version == "1.3.0.0"


def test_messages() -> None:
    msgs = parse_messages(
        [
            {"version": "*", "text": "a"},
            {"version": ["1.0", "2.0"], "text": "b"},
            {"version": "*"},
            "junk",
        ]
    )
    assert [m.text for m in msgs] == ["a", "b"]
    assert msgs[1].applies_to("2.0") and not msgs[1].applies_to("3.0")


def test_checkpage_parse() -> None:
    page = CheckPage.parse(CHECKPAGE)
    assert page.enabled_users == ("alice", "Ünal")
    assert page.enabled_bots == ("AliceBot",)
