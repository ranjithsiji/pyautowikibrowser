"""The Start tab's Watch, Move, Protect and Delete (AWB Main.cs, ArticleActionDialog)."""

from dataclasses import replace
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from pyawb.api.pageactions import PageAction
from pyawb.lists.listmaker import ArticleList
from pyawb.ui.page_action_dialog import PageActionDialog
from tests.api.fakes import userinfo
from tests.api.test_editloop import open_response
from tests.ui.test_main_loop import window

TEXT = "حيوان [[أليف|أليف]] صغير."


def admin_window(qtbot: QtBot) -> tuple[Any, Any]:
    w, t = window(qtbot, {"قط": TEXT, "كلب": TEXT})
    info = userinfo("Alice", groups=("user", "sysop"))
    info["query"]["userinfo"]["rights"] += ["move", "delete", "protect"]
    t.responses[("meta", "userinfo")] = info
    assert w.session is not None
    w.session.refresh_user()
    t.responses[("meta", "allmessages")] = {"query": {"allmessages": [{"missing": True}]}}
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    return w, t


def test_buttons_follow_the_rights(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": TEXT})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    st = w.start_tab
    assert st.watch_button.isEnabled()
    assert not st.move_button.isEnabled() and not st.delete_button.isEnabled()
    assert not st.protect_button.isEnabled()


def test_dialog_validation(qtbot: QtBot) -> None:
    d = PageActionDialog(PageAction.PROTECT, "قط", ["تخريب"], levels=["", "autoconfirmed", "sysop"])
    qtbot.addWidget(d)
    d.reason.setEditText("")
    assert d.problems()
    d.reason.setEditText("تخريب")
    d.edit_level.setCurrentIndex(2)
    d.expiry.setText("")
    assert any("expiry" in p for p in d.problems())
    d.expiry.setText("1 week")
    assert d.problems() == [] and d.cascade.isEnabled()
    d.edit_level.setCurrentIndex(1)
    assert not d.cascade.isEnabled()  # cascading needs the top level
    assert d.protect_request().edit == "autoconfirmed"


def test_move_replaces_and_reloads(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, t = admin_window(qtbot)
    assert w.start_tab.move_button.isEnabled()

    def fill(d: PageActionDialog) -> int:
        d.new_title.setText("قطة")
        d.reason.setEditText("عنوان أدق")
        return PageActionDialog.DialogCode.Accepted

    monkeypatch.setattr(PageActionDialog, "exec", fill)
    t.responses[("action", "move")] = {"move": {"from": "قط", "to": "قطة"}}
    t.responses[("titles", "قطة")] = open_response("قطة", TEXT)
    w.page_action(PageAction.MOVE)
    qtbot.waitUntil(lambda: w.page_logs.successful.rowCount() == 1 and not w.busy, timeout=5000)
    assert t.last("move")["to"] == "قطة" and t.last("move")["reason"] == "عنوان أدق"
    assert w.list_maker.articles.items[0].name == "قطة"


def test_delete_marks_the_page(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, t = admin_window(qtbot)

    def fill(d: PageActionDialog) -> int:
        d.reason.setEditText("تخريب")
        return PageActionDialog.DialogCode.Accepted

    monkeypatch.setattr(PageActionDialog, "exec", fill)
    t.responses[("action", "delete")] = {"delete": {"title": "قط"}}
    w._save_preferences(  # pyright: ignore[reportPrivateUsage]
        replace(w.config.preferences, tag_page_actions=True)
    )
    w.page_action(PageAction.DELETE)
    qtbot.waitUntil(lambda: w.list_maker.articles.items[0].list_status != "", timeout=5000)
    assert w.list_maker.articles.items[0].list_status == ArticleList.DELETED
    assert t.last("delete")["reason"].startswith("تخريب (")  # with the tool tag


def test_failed_action_is_logged(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, message_boxes: list[tuple[str, str]]
) -> None:
    w, t = admin_window(qtbot)
    monkeypatch.setattr(
        PageActionDialog,
        "exec",
        lambda d: (d.reason.setEditText("x"), PageActionDialog.DialogCode.Accepted)[1],
    )
    t.responses[("action", "protect")] = {"error": {"code": "permissiondenied", "info": "No"}}
    w.page_action(PageAction.PROTECT)
    qtbot.waitUntil(lambda: w.page_logs.failed.rowCount() == 1, timeout=5000)
    assert message_boxes


def test_watch_toggle(qtbot: QtBot) -> None:
    w, t = admin_window(qtbot)
    t.responses[("action", "watch")] = {"watch": [{"title": "قط", "watched": True}]}
    assert w.start_tab.watch_button.text() == "Watch"
    w.toggle_watch()
    qtbot.waitUntil(lambda: w.start_tab.watch_button.text() == "Unwatch", timeout=5000)
    assert "unwatch" not in t.last("watch")
