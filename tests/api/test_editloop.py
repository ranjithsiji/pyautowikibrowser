"""The edit loop (AWB MainForm's load/check/process/save) against a fake Arabic Wikipedia."""

from typing import Any

from pyawb.api.models import WatchOptions
from pyawb.core import process
from pyawb.editloop import EditLoop, LoopOptions
from pyawb.rules.skip import create_comparer

from .fakes import userinfo
from .test_session import SAVE_OK, approved_session


def open_response(
    title: str,
    text: str | None,
    *,
    protection: str = "",
    redirect_from: str = "",
) -> dict[str, Any]:
    page: dict[str, Any] = {"ns": 0, "title": title, "contentmodel": "wikitext"}
    if text is None:
        page["missing"] = True
    else:
        page |= {
            "pageid": 9,
            "lastrevid": 50,
            "revisions": [
                {
                    "revid": 50,
                    "timestamp": "2026-10-01T09:00:00Z",
                    "slots": {"main": {"contentmodel": "wikitext", "content": text}},
                }
            ],
        }
    if protection:
        page["protection"] = [{"type": "edit", "level": protection, "expiry": "infinity"}]
    query: dict[str, Any] = {"pages": [page], "tokens": {"csrftoken": "abc+\\"}}
    if redirect_from:
        query["redirects"] = [{"from": redirect_from, "to": title}]
    return {"curtimestamp": "2026-10-13T10:00:00Z", "query": query}


def loop_with(title: str, response: dict[str, Any]) -> tuple[EditLoop, Any]:
    session, t = approved_session()
    t.responses[("titles", title)] = response
    return EditLoop(session), t


def opts(**process_options: Any) -> LoopOptions:
    return LoopOptions(process=process.ProcessOptions(user_name="Alice", **process_options))


def test_protected_page_is_skipped() -> None:
    result = EditLoop(approved_session()[0]).load("مرحبا بالعالم", opts())
    assert result.skip_reason == "Page is protected"


def test_load_process_and_save() -> None:
    loop, t = loop_with("قط", open_response("قط", "حيوان [[أليف|أليف]] صغير."))
    result = loop.load("قط", opts(general_fixes=True))
    assert not result.skipped, result.skip_reason
    assert result.text == "حيوان [[أليف]] صغير."
    assert not result.renamed

    t.responses[("action", "edit")] = SAVE_OK
    info = loop.save(result, result.text, "تنظيف", minor=True, watch=WatchOptions.WATCH)
    assert info.success
    edit = t.last("edit")
    assert edit["text"] == "حيوان [[أليف]] صغير."
    assert edit["summary"] == "تنظيف" + loop.session.site.summary_tag
    assert edit["baserevid"] == "50" and edit["minor"] == "1" and edit["watchlist"] == "watch"


def test_unchanged_page_is_skipped() -> None:
    loop, _ = loop_with("قط", open_response("قط", "نص"))
    assert loop.load("قط", opts()).skip_reason == "No change"
    loop, _ = loop_with("قط", open_response("قط", "نص"))
    options = opts()
    options.process.skip_no_changes = False
    result = loop.load("قط", options)
    assert not result.skipped and result.summary == ""


def test_missing_and_existing_pages() -> None:
    loop, _ = loop_with("كلب", open_response("كلب", None))
    assert loop.load("كلب", opts()).skip_reason == "Non-existent page"
    loop, _ = loop_with("قط", open_response("قط", "نص"))
    options = opts()
    options.skip_existent = True
    assert loop.load("قط", options).skip_reason == "Existing page"


def test_followed_redirect_renames_the_list_entry() -> None:
    loop, t = loop_with("قط", open_response("قط", "نص &amp;", redirect_from="هر"))
    t.responses[("titles", "هر")] = t.responses.pop(("titles", "قط"))
    result = loop.load("هر", opts())
    assert result.renamed and result.page is not None and result.page.title == "قط"
    assert t.last("query")["redirects"] == "1"


def test_skip_if_redirect_does_not_follow() -> None:
    loop, t = loop_with("هر", open_response("هر", "#تحويل [[قط]]"))
    options = opts()
    options.skip_if_redirect = True
    assert loop.load("هر", options).skip_reason == "Page is a redirect"
    assert "redirects" not in t.last("query")


def test_nobots_and_contains_checks() -> None:
    loop, _ = loop_with("قط", open_response("قط", "{{nobots}} نص &amp;"))
    assert loop.load("قط", opts()).skip_reason == "Restricted by {{bots}}/{{nobots}}"

    check = process.ContainsCheck("بذرة", create_comparer("بذرة", False, False, False, False))
    loop, _ = loop_with("قط", open_response("قط", "نص {{بذرة}} &amp;"))
    assert loop.load("قط", opts(skip_if_contains=check)).skip_reason == "Page contains: بذرة"


def test_new_messages_stop_the_loop() -> None:
    loop, t = loop_with("قط", open_response("قط", "نص"))
    info = userinfo("Alice")
    info["query"]["userinfo"]["messages"] = True
    t.responses[("meta", "userinfo")] = info
    loop.session.refresh_user()
    result = loop.load("قط", opts())
    assert result.new_messages and not result.skipped


def test_invalid_title() -> None:
    assert EditLoop(approved_session()[0]).load("قط[1]", opts()).skip_reason == "Invalid page title"
