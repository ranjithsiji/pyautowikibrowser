"""WikiSession against a fake transport: configuration loading, the CheckPage gate, open/save."""

import json
from typing import Any

import pytest

from pyawb.api import checkpage, siteinfo
from pyawb.api.errors import (
    ApiException,
    CaptchaException,
    EditConflictException,
    LoggedOffException,
    MaxlagException,
)
from pyawb.api.models import PageTitleStatus, WatchOptions
from pyawb.api.session import LoginException, NotApprovedException, WikiSession, md5

from .fakes import AR_MONTHS, AR_SITEINFO, FakeTransport, allmessages, userinfo

OPEN_RESPONSE: dict[str, Any] = {
    "curtimestamp": "2026-10-13T10:00:00Z",
    "query": {
        "normalized": [{"fromencoded": False, "from": "مرحبا_بالعالم", "to": "مرحبا بالعالم"}],
        "pages": [
            {
                "pageid": 7,
                "ns": 0,
                "title": "مرحبا بالعالم",
                "contentmodel": "wikitext",
                "lastrevid": 1234,
                "protection": [{"type": "edit", "level": "autoconfirmed", "expiry": "infinity"}],
                "displaytitle": "مرحبا بالعالم",
                "revisions": [
                    {
                        "revid": 1234,
                        "timestamp": "2026-10-01T09:00:00Z",
                        "slots": {"main": {"contentmodel": "wikitext", "content": "سطر\nسطر ثان"}},
                    }
                ],
            }
        ],
        "tokens": {"csrftoken": "abc+\\", "watchtoken": "w+\\", "rollbacktoken": "r+\\"},
    },
}

SAVE_OK = {
    "edit": {
        "result": "Success",
        "pageid": 7,
        "title": "مرحبا بالعالم",
        "contentmodel": "wikitext",
        "oldrevid": 1234,
        "newrevid": 1240,
        "newtimestamp": "2026-10-13T10:01:00Z",
    }
}


def make_session(
    user: str = "Alice", checkpage_json: str | None = None
) -> tuple[WikiSession, FakeTransport]:
    t = FakeTransport()
    t.responses[("meta", "siteinfo")] = AR_SITEINFO
    t.responses[("meta", "allmessages")] = allmessages(list(siteinfo.MONTH_MESSAGES), AR_MONTHS)
    t.responses[("list", "tags")] = {"query": {"tags": []}}
    t.responses[("action", "sitematrix")] = {"sitematrix": {"count": 0}}
    t.responses[("meta", "userinfo")] = userinfo(user)
    t.responses[("titles", "مرحبا بالعالم")] = OPEN_RESPONSE
    t.pages[checkpage.VERSION_PAGE_TITLE] = json.dumps({"badnames": [], "globalusers": []})
    t.pages[checkpage.CONFIG_TITLE] = json.dumps(
        {
            "allusersenabled": False,
            "allusersenabledusermode": False,
            "underscoretitles": ["C_Sharp"],
        }
    )
    t.pages[checkpage.CHECKPAGE_TITLE] = checkpage_json or json.dumps(
        {"enabledusers": ["Alice"], "enabledbots": []}
    )
    t.pages["Project:AutoWikiBrowser/Dated templates"] = (
        "* {{tl|citation needed}}\n* {{tl|Dead link}}"
    )
    t.pages["Project:AutoWikiBrowser/Template redirects"] = "{{tl|Cn}} → {{tl|Citation needed}}"
    session = WikiSession(t, siteinfo.base_site_config("ar", "wikipedia"))
    return session, t


def approved_session() -> tuple[WikiSession, FakeTransport]:
    session, t = make_session()
    session.load_site()
    session.refresh_user()
    assert session.check_status().can_edit
    return session, t


def test_load_site() -> None:
    session, _ = make_session()
    cfg = session.load_site()
    assert cfg.rtl and cfg.namespaces[14] == "تصنيف:"
    assert cfg.dated_templates == ("Citation needed", "Dead link")
    assert "Cn" in cfg.template_redirects_text
    assert session.siteinfo is not None and not session.tag_edits


def test_check_status_applies_underscored_titles() -> None:
    session, _ = approved_session()
    assert session.site.underscored_titles == {"C_Sharp"}
    assert session.can_save


def test_open_page() -> None:
    session, _ = approved_session()
    page = session.open("مرحبا بالعالم")
    assert page.text == "سطر\r\nسطر ثان"
    assert page.revision_id == 1234
    assert page.timestamp == "2026-10-01T09:00:00Z"
    assert page.token_timestamp == "2026-10-13T10:00:00Z"
    assert page.edit_protection == "autoconfirmed"
    assert page.original_title == "مرحبا_بالعالم"
    assert page.title_changed_status == PageTitleStatus.NORMALISED
    assert session.user.can_edit_page(page) is False  # not autoconfirmed in this fake


def test_save_sends_conflict_detection_and_md5() -> None:
    session, t = approved_session()
    session.open("مرحبا بالعالم")
    t.responses[("action", "edit")] = SAVE_OK
    info = session.save("سطر\r\nجديد", "تعديل", minor=True, watch=WatchOptions.WATCH)
    assert info.success and info.new_revision_id == 1240
    params, post, token = t.requests[-1]
    assert post and token == "csrf"
    assert params["text"] == "سطر\nجديد"
    assert params["md5"] == md5("سطر\nجديد")
    assert params["baserevid"] == "1234"
    assert params["basetimestamp"] == "2026-10-01T09:00:00Z"
    assert params["starttimestamp"] == "2026-10-13T10:00:00Z"
    assert params["nocreate"] == "1"
    assert params["assert"] == "user"
    assert params["minor"] == "1" and params["watchlist"] == "watch"
    assert "bot" not in params  # not a bot
    assert "tags" not in params
    assert session.page is None  # must be opened again before the next save


def test_save_refused_without_checkpage_approval() -> None:
    session, t = make_session(checkpage_json=json.dumps({"enabledusers": ["Someone else"]}))
    session.load_site()
    session.refresh_user()
    with pytest.raises(NotApprovedException):  # gate not run yet
        session.save("x", "y")
    assert not session.check_status().can_edit
    session.open("مرحبا بالعالم")
    with pytest.raises(NotApprovedException, match="not registered"):
        session.save("x", "y")
    assert not any(p.get("action") == "edit" for p, _, _ in t.requests)


def test_save_refuses_leftover_placeholders() -> None:
    session, t = approved_session()
    session.open("مرحبا بالعالم")
    with pytest.raises(ApiException, match="placeholders"):
        session.save("text ⌊⌊⌊⌊0⌋⌋⌋⌋ more", "summary")
    assert not any(p.get("action") == "edit" for p, _, _ in t.requests)


def test_save_needs_opened_page() -> None:
    session, _ = approved_session()
    with pytest.raises(ApiException, match="not opened"):
        session.save("x", "y")


def test_save_errors() -> None:
    session, t = approved_session()
    session.open("مرحبا بالعالم")
    t.responses[("action", "edit")] = {"error": {"code": "editconflict", "info": "Edit conflict."}}
    with pytest.raises(EditConflictException):
        session.save("x", "y")
    t.responses[("action", "edit")] = {
        "error": {"code": "maxlag", "info": "Waiting for 10.64.0.1: 7 seconds lagged.", "lag": 7}
    }
    with pytest.raises(MaxlagException) as e:
        session.save("x", "y")
    assert e.value.maxlag == 7
    t.responses[("action", "edit")] = {
        "error": {"code": "assertuserfailed", "info": "Not logged in."}
    }
    with pytest.raises(LoggedOffException):
        session.save("x", "y")
    t.responses[("action", "edit")] = {
        "edit": {"result": "Failure", "captcha": {"type": "image", "id": "1"}}
    }
    with pytest.raises(CaptchaException):
        session.save("x", "y")


def test_bot_flag_and_tags() -> None:
    session, t = make_session(
        user="AliceBot",
        checkpage_json=json.dumps({"enabledusers": [], "enabledbots": ["AliceBot"]}),
    )
    t.responses[("meta", "userinfo")] = userinfo("AliceBot", groups=("bot",))
    t.responses[("list", "tags")] = {"query": {"tags": [{"name": "AWB", "active": True}]}}
    session.load_site()
    session.refresh_user()
    assert session.check_status().is_bot
    assert session.site.summary_tag == ""
    session.open("مرحبا بالعالم")
    t.responses[("action", "edit")] = SAVE_OK
    session.save("x", "y", bot=True)
    params = t.last("edit")
    assert params["bot"] == "1" and params["tags"] == "AWB"


def test_new_page_is_create_only() -> None:
    session, t = approved_session()
    t.responses[("titles", "صفحة جديدة")] = {
        "curtimestamp": "2026-10-13T10:00:00Z",
        "query": {
            "pages": [{"ns": 0, "title": "صفحة جديدة", "missing": True}],
            "tokens": {"csrftoken": "abc+\\"},
        },
    }
    page = session.open("صفحة جديدة")
    assert not page.exists
    with pytest.raises(ValueError):
        session.save("", "y")
    t.responses[("action", "edit")] = SAVE_OK
    session.save("نص", "y")
    params = t.last("edit")
    assert params["createonly"] == "1" and "baserevid" not in params


def test_open_redirects() -> None:
    session, t = approved_session()
    t.responses[("titles", "Loop")] = {
        "query": {
            "redirects": [{"from": "Loop", "to": "Loop 2"}, {"from": "Loop 2", "to": "Loop"}],
            "pages": [],
        }
    }
    page = session.open("Loop", resolve_redirects=True)
    assert page.title_changed_status == PageTitleStatus.REDIRECT_LOOP
    assert t.requests[-1][0]["redirects"] == "1"


def test_preview_compare_expand() -> None:
    session, t = approved_session()
    t.responses[("action", "parse")] = {
        "parse": {"title": "T", "text": "<p>نص</p>", "parsewarnings": ["Duplicate argument"]}
    }
    html = session.preview("T", "نص\r\n")
    assert html.startswith('<div class="previewnote"') and html.endswith("<p>نص</p>")
    assert t.last("parse")["text"] == "نص\n"
    t.responses[("action", "compare")] = {"compare": {"body": "<tr><td>diff</td></tr>"}}
    assert session.compare("T", "x") == "<tr><td>diff</td></tr>"
    t.responses[("action", "expandtemplates")] = {"expandtemplates": {"wikitext": "expanded"}}
    assert session.expand_templates("{{x}}", "T") == "expanded"


class LoginTransport(FakeTransport):
    def __init__(self) -> None:
        super().__init__()
        self.logged_in_as: str | None = None

    def login(self, username: str, password: str) -> None:
        if password != "secret":
            raise LoginException("wrong password")
        self.logged_in_as = username

    def logout(self) -> None:
        self.logged_in_as = None


def test_login_runs_checkpage() -> None:
    session, base = make_session()
    t = LoginTransport()
    t.responses, t.pages = base.responses, base.pages
    session.transport = session.global_transport = t
    with pytest.raises(LoginException):
        session.login("Alice@PyAWB", "wrong")
    user = session.login("Alice@PyAWB", "secret")
    assert user.name == "Alice" and t.logged_in_as == "Alice@PyAWB"
    assert session.can_save
    session.logout()
    assert not session.can_save and not session.user.is_logged_in
