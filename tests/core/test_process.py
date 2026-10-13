"""ProcessPage, the skip checks and the edit summary (AWB MainForm), without the UI."""

from pyawb.core import process
from pyawb.core.article import Article
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.parsers import Parsers
from pyawb.core.site import current_site, replace, use_site
from pyawb.rules.skip import create_comparer


def run(text: str, title: str = "Foo", **options: object) -> Article:
    a = Article(title, text)
    opts = process.ProcessOptions(user_name="Alice", **options)  # type: ignore[arg-type]
    process.process_page(a, opts, Parsers(), HideText(False, True, True))
    return a


def test_general_fixes_change_the_page() -> None:
    a = run("A [[Bar|Bar]] thing.", general_fixes=True)
    assert a.article_text == "A [[Bar]] thing."
    assert not a.skip_article


def test_unicodify_whole_page() -> None:
    assert run("Foo &amp; &eacute;").article_text == "Foo & é"
    assert run("Foo &eacute;", unicodify_whole=False).article_text == "Foo &eacute;"


def test_nobots_skips_unless_ignored() -> None:
    a = run("{{nobots}} x")
    assert a.skip_article and a.log.skip_reason == "Restricted by {{bots}}/{{nobots}}"
    assert not run("{{bots|allow=Alice}} x").skip_article
    assert not run("{{nobots}} x", ignore_no_bots=True).skip_article


def test_no_parse_titles_get_no_general_fixes() -> None:
    a = run("A [[Bar|Bar]] thing.", general_fixes=True, no_parse={"Foo"})
    assert a.article_text == "A [[Bar|Bar]] thing."


def test_append_and_prepend_with_keywords() -> None:
    a = run("Text", append_text="{{tag|%%title%%}}", append_newlines=1)
    assert a.article_text == "Text\n{{tag|Foo}}"
    a = run("Text", append_text="{{tag}}", prepend=True)
    assert a.article_text == "{{tag}}\n\nText"


def test_no_change_skip_reasons() -> None:
    opts = process.ProcessOptions()
    assert process.no_change_skip_reason(Article("Foo", "x"), opts) == "No change"
    assert (
        process.no_change_skip_reason(
            Article("Foo", "x"), process.ProcessOptions(skip_no_changes=False)
        )
        is None
    )

    a = Article("Foo", "a  b")
    a.awb_change_article_text("test", "a b", False)
    assert process.no_change_skip_reason(a, opts) is None
    ws = process.ProcessOptions(skip_whitespace_only=True)
    assert process.no_change_skip_reason(a, ws) == "Only whitespace changed"

    no_links = process.ProcessOptions(skip_no_page_links=True)
    assert process.no_change_skip_reason(a, no_links) == "Page contains no links"


def test_contains_checks_before_and_after() -> None:
    contains = process.ContainsCheck("stub", create_comparer("stub", False, False, False, False))
    not_contains = process.ContainsCheck(
        "{{x}}", create_comparer("{{x}}", True, False, False, False), negate=True, after=True
    )
    opts = process.ProcessOptions(skip_if_contains=contains, skip_if_not_contains=not_contains)
    a = Article("Foo", "A {{Stub}}")
    assert process.contains_skip_reason(a, opts, after=False) == "Page contains: stub"
    assert process.contains_skip_reason(a, opts, after=True) == "Page doesn't contain: {{x}}"
    b = Article("Foo", "{{x}}")
    assert process.contains_skip_reason(b, opts, after=False) is None
    assert process.contains_skip_reason(b, opts, after=True) is None


def test_private_use_characters() -> None:
    assert process.has_private_use_characters("ab")
    assert not process.has_private_use_characters("മലയാളം 𠀋")


def test_default_edit_summary() -> None:
    a = Article("Foo", "x")
    a.awb_change_article_text("t", "y", False)
    a._append_to_summary("typos fixed: a → b")  # pyright: ignore[reportPrivateUsage]
    summary = process.make_default_edit_summary(a, " cleanup ", "y", section_summary=False)
    assert summary == "cleanup, typos fixed: a → b"
    assert process.make_default_edit_summary(a, "", "y", False) == "typos fixed: a → b"
    # a page without headings is one section, "top"
    assert process.make_default_edit_summary(a, "", "y") == "/* top */ typos fixed: a → b"


def test_default_edit_summary_arabic_comma() -> None:
    with use_site(current_site().with_lang_code("ar")):
        a = Article("Foo", "x")
        a._append_to_summary("تصحيح")  # pyright: ignore[reportPrivateUsage]
        summary = process.make_default_edit_summary(a, "تنظيف", "x", section_summary=False)
        assert summary == "تنظيف، تصحيح"


def test_section_edit_summary() -> None:
    original = "Intro\r\n\r\n==History==\r\nOld\r\n\r\n==Later==\r\nText"
    edited = original.replace("Old", "New")
    a = Article("Foo", original)
    assert process.make_default_edit_summary(a, "fix", edited) == "/* History */ fix"
    assert process.make_default_edit_summary(a, "fix", edited, section_summary=False) == "fix"

    assert (
        process.check_section_summary("/* History */ fix", original, edited) == "/* History */ fix"
    )
    both = edited.replace("Text", "Other")
    assert process.check_section_summary("/* History */ fix", original, both) == " fix"


def test_summary_tag() -> None:
    site = current_site()
    assert process.append_summary_tag("fix", site) == "fix" + site.summary_tag
    assert process.append_summary_tag("fix", site, is_bot=True, suppress=True) == "fix"
    assert process.append_summary_tag("fix", site, suppress=True) == "fix" + site.summary_tag
    custom = replace(site, project="custom")
    assert process.append_summary_tag("fix", custom) == "fix"


def test_clean_category_input() -> None:
    assert process.clean_category_input("[[Category:foo bar]]") == "Foo bar"
    assert process.clean_category_input("category: x") == "X"
    assert process.clean_category_input("Foo") == "Foo"


def test_clean_file_input() -> None:
    assert process.clean_file_input("File:A.jpg") == "A.jpg"
    assert process.clean_file_input("file:B.png") == "B.png"
    assert process.clean_file_input("Image:C.png") == "Image:C.png"  # as AWB: the wiki's name only


def test_page_info_statistics_and_alerts() -> None:
    text = (
        "'''Foo''' is a [[bar]] and [[bar]] with [[baz|qux]] [[File:x.jpg|thumb]] on 2020-01-05 "
        "and 5 May 2020.\n[[Category:X]]\n== [[Link]] =="
    )
    info = process.page_info(text, Article("Foo"))
    s = info.statistics
    assert (s.links, s.images, s.categories) == (4, 1, 1)
    assert s.dates == "1/1/0"
    assert info.alerts == ("Header(s) with wikilinks (1)",)
    assert info.multiple_wikilinks == ("Bar (2)",)


def test_page_info_alerts_for_a_bare_page() -> None:
    info = process.page_info("==H==\nx [[a]] [[b|", Article("Foo"))
    assert info.alerts == (
        "No category (may be one in a template)",
        "Starts with heading",
        "Unbalanced brackets (1)",
    )
    talk = process.page_info("x", Article("Talk:Foo"))
    assert "No category (may be one in a template)" not in talk.alerts
