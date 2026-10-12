"""Port of the ArticleTests fixture in AWB UnitTests/MiscellaneousTests.cs: the Article class (awb_l.core.article).

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from awb_l.core import genfixes, namespace, rx, tools
from awb_l.core import wikiregexes as W
from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.parsers.parsers import DateLocale
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import (
    EN,
    cs_len,
    set_lang,
    set_project,
    set_site,
    unit_test,
    utc_month_year,
)
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser
from awb_l.core.article import Article, CategorisationOptions  # noqa: E402

LongText = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse dictum ultrices augue. Fusce sem diam, vestibulum sit amet, vehicula id, congue a, nisl. Phasellus pulvinar posuere purus. Donec elementum justo mattis nulla. Sed a purus dictum lacus pharetra adipiscing. Nam non dui non ante viverra iaculis. Fusce euismod lacus id nulla vulputate gravida. Suspendisse lectus pede, tempus sed, tristique id, pharetra eget, urna. Integer mattis libero vel quam accumsan suscipit. Vivamus molestie dapibus est. Quisque quis metus eget nisl accumsan aliquet. Donec tempus pellentesque tellus. Aliquam lacinia gravida justo. Aliquam erat volutpat. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Mauris ultricies suscipit urna. Ut mollis tempor leo. Pellentesque fringilla mattis enim. Proin sapien enim, congue non, aliquet et, sollicitudin nec, mauris. Sed porta.\r\n\r\nCurabitur luctus mollis massa. Nullam consectetur mollis lacus. Suspendisse turpis. Fusce velit. Morbi egestas dui. Donec commodo ornare lorem. Vestibulum sodales. Curabitur egestas libero ut metus. Sed eget orci a ligula consectetur vestibulum. Cras sapien.\r\n\r\nSed libero. Ut volutpat massa. Donec nulla pede, porttitor eu, sodales et, consectetur nec, quam. Pellentesque vestibulum hendrerit est. Nulla facilisi. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Duis et nibh eu lacus iaculis pretium. Fusce sed turpis. In cursus. Etiam interdum augue. Morbi commodo auctor ligula. In imperdiet, neque nec hendrerit consequat, lacus purus tristique turpis, eu hendrerit ipsum ligula at libero. Duis varius nunc vel tortor. Praesent tempor. Nunc non pede at velit congue feugiat. Curabitur gravida, nisl quis mattis porttitor, purus nulla viverra dui, non suscipit augue nunc ac libero. Donec lacinia est non augue.\r\n\r\nNulla quam dui, tristique id, condimentum sed, sodales in, ante. Vestibulum vitae diam. Integer placerat ante non orci. Nulla gravida. Integer magna enim, iaculis ut, ornare dignissim, ultrices a, urna. Donec urna. Fusce fringilla, pede vitae pulvinar ullamcorper, est nisi eleifend ipsum, ac adipiscing odio massa vehicula neque. Sed blandit est. Morbi faucibus, nisl vel commodo vulputate, mi ipsum tincidunt sem, id ornare orci orci et velit. Morbi commodo sollicitudin ligula. Pellentesque vitae urna. Duis massa arcu, accumsan id, euismod eu, tincidunt et, odio. Phasellus purus leo, rhoncus sed, condimentum nec, vestibulum vel, lacus. In egestas, lectus vitae lacinia tristique, elit magna consequat risus, id sodales metus nulla ac pede. Suspendisse potenti.\r\n\r\nFusce massa. Nullam lacinia purus nec ipsum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Suspendisse potenti. Proin augue. Donec mi magna, interdum a, elementum quis, bibendum sit amet, felis. Donec vel libero eget magna hendrerit ultrices. Suspendisse potenti. Sed scelerisque lacinia nisi. Quisque elementum, nunc nec luctus iaculis, ante quam aliquet orci, et ullamcorper dui ipsum at mi. Vestibulum a dolor id tortor posuere elementum. Sed mauris nisl, ultrices a, malesuada non, convallis ac, velit. Sed aliquam elit id metus. Donec malesuada, lorem ut pharetra auctor, mi risus viverra enim, vitae pulvinar urna metus at lorem. Vivamus id lorem. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Nulla facilisi. Ut vel odio. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Pellentesque lobortis sem.\r\n\r\nProin in odio. Pellentesque [[habitant]] [[morbi]] [[tristique]] senectus et netus et malesuada fames ac turpis egestas. Vivamus bibendum arcu nec risus. Nulla iaculis ligula in purus. Etiam vulputate nibh sit amet lectus. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Suspendisse potenti. Suspendisse eleifend. Donec blandit nibh hendrerit turpis. Integer accumsan posuere odio. Ut commodo augue malesuada risus. Curabitur augue. Praesent volutpat nunc a diam. Nulla lobortis interdum dolor. Nunc imperdiet, ipsum ac tempor iaculis, nunc.\r\n"


def test_general() -> None:
    S = W.for_site(EN)
    a = Article(r"A")
    b = Article(r"A")
    b = None
    assert not (a == None)
    b = Article(r"A")
    assert str(a) == r"A"
    assert a.name == r"A"
    assert not (a != b)
    assert a.url_encoded_name == r"A"
    assert a.display_title == None


def test_auto_tag() -> None:
    S = W.for_site(EN)
    LongText = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse dictum ultrices augue. Fusce sem diam, vestibulum sit amet, vehicula id, congue a, nisl. Phasellus pulvinar posuere purus. Donec elementum justo mattis nulla. Sed a purus dictum lacus pharetra adipiscing. Nam non dui non ante viverra iaculis. Fusce euismod lacus id nulla vulputate gravida. Suspendisse lectus pede, tempus sed, tristique id, pharetra eget, urna. Integer mattis libero vel quam accumsan suscipit. Vivamus molestie dapibus est. Quisque quis metus eget nisl accumsan aliquet. Donec tempus pellentesque tellus. Aliquam lacinia gravida justo. Aliquam erat volutpat. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Mauris ultricies suscipit urna. Ut mollis tempor leo. Pellentesque fringilla mattis enim. Proin sapien enim, congue non, aliquet et, sollicitudin nec, mauris. Sed porta.\r\n\r\nCurabitur luctus mollis massa. Nullam consectetur mollis lacus. Suspendisse turpis. Fusce velit. Morbi egestas dui. Donec commodo ornare lorem. Vestibulum sodales. Curabitur egestas libero ut metus. Sed eget orci a ligula consectetur vestibulum. Cras sapien.\r\n\r\nSed libero. Ut volutpat massa. Donec nulla pede, porttitor eu, sodales et, consectetur nec, quam. Pellentesque vestibulum hendrerit est. Nulla facilisi. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Duis et nibh eu lacus iaculis pretium. Fusce sed turpis. In cursus. Etiam interdum augue. Morbi commodo auctor ligula. In imperdiet, neque nec hendrerit consequat, lacus purus tristique turpis, eu hendrerit ipsum ligula at libero. Duis varius nunc vel tortor. Praesent tempor. Nunc non pede at velit congue feugiat. Curabitur gravida, nisl quis mattis porttitor, purus nulla viverra dui, non suscipit augue nunc ac libero. Donec lacinia est non augue.\r\n\r\nNulla quam dui, tristique id, condimentum sed, sodales in, ante. Vestibulum vitae diam. Integer placerat ante non orci. Nulla gravida. Integer magna enim, iaculis ut, ornare dignissim, ultrices a, urna. Donec urna. Fusce fringilla, pede vitae pulvinar ullamcorper, est nisi eleifend ipsum, ac adipiscing odio massa vehicula neque. Sed blandit est. Morbi faucibus, nisl vel commodo vulputate, mi ipsum tincidunt sem, id ornare orci orci et velit. Morbi commodo sollicitudin ligula. Pellentesque vitae urna. Duis massa arcu, accumsan id, euismod eu, tincidunt et, odio. Phasellus purus leo, rhoncus sed, condimentum nec, vestibulum vel, lacus. In egestas, lectus vitae lacinia tristique, elit magna consequat risus, id sodales metus nulla ac pede. Suspendisse potenti.\r\n\r\nFusce massa. Nullam lacinia purus nec ipsum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Suspendisse potenti. Proin augue. Donec mi magna, interdum a, elementum quis, bibendum sit amet, felis. Donec vel libero eget magna hendrerit ultrices. Suspendisse potenti. Sed scelerisque lacinia nisi. Quisque elementum, nunc nec luctus iaculis, ante quam aliquet orci, et ullamcorper dui ipsum at mi. Vestibulum a dolor id tortor posuere elementum. Sed mauris nisl, ultrices a, malesuada non, convallis ac, velit. Sed aliquam elit id metus. Donec malesuada, lorem ut pharetra auctor, mi risus viverra enim, vitae pulvinar urna metus at lorem. Vivamus id lorem. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Nulla facilisi. Ut vel odio. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Pellentesque lobortis sem.\r\n\r\nProin in odio. Pellentesque [[habitant]] [[morbi]] [[tristique]] senectus et netus et malesuada fames ac turpis egestas. Vivamus bibendum arcu nec risus. Nulla iaculis ligula in purus. Etiam vulputate nibh sit amet lectus. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Suspendisse potenti. Suspendisse eleifend. Donec blandit nibh hendrerit turpis. Integer accumsan posuere odio. Ut commodo augue malesuada risus. Curabitur augue. Praesent volutpat nunc a diam. Nulla lobortis interdum dolor. Nunc imperdiet, ipsum ac tempor iaculis, nunc.\r\n"
    a = Article(r"A", r"ABC")
    p = genfixes.Parsers(500, True)
    a.auto_tag(p, True, True)
    assert not (a.no_article_text_changed)
    a = Article(r"A", LongText)
    unit_test.int_value = 1
    unit_test.bool_value = False
    a.auto_tag(p, True, True)
    assert a.no_article_text_changed


def test_alert_properties() -> None:
    S = W.for_site(EN)
    a = Article(r"A", r"{{dead link}}")
    assert len(a.dead_links()) == 1
    assert a.has_dead_links
    a = Article(r"A", r"<small>")
    assert len(a.unclosed_tags()) == 1
    a = Article(r"A", r"==[[A]]==")
    assert len(a.wiki_linked_headers()) == 1
    a = Article(r"A", r"{{multiple issues|foo=bar}}")
    assert len(a.unknown_multiple_issues_parameters()) == 1
    a = Article(r"Talk:A", r"{{WikiProject banner shell|foo=bar}}")
    assert len(a.unknown_wiki_project_banner_shell_parameters()) == 1
    a = Article(
        r"Talk:A",
        r"{{WikiProject banner shell|collapsed=true|living=a|class=a|listas=a|demo_page=a|vital=a}}",
    )
    assert len(a.unknown_wiki_project_banner_shell_parameters()) == 0
    a = Article(r"Talk:A", r"{{WikiProject banner shell|foo=bar|foo=bar}}")
    assert len(a.duplicate_wiki_project_banner_shell_parameters()) == 1
    a = Article(r"A", r"{{multiple issues|section=bar|collapsed=yes}}")
    assert len(a.unknown_multiple_issues_parameters()) == 0
    a = Article(r"A", r"[[A|B|C]]")
    assert len(a.doublepipe_links()) == 1
    a = Article(r"A", r"[[A||BC]]")
    assert len(a.doublepipe_links()) == 1
    a = Article(r"A", r"[[|A]]")
    assert len(a.targetless_links()) == 1
    a = Article(r"A", r"{{cite web|sajksdfa=a}}")
    assert len(a.bad_cite_parameters()) == 1
    a = Article(r"A", r"{{cite web|date=5-4-10}}")
    assert len(a.ambiguous_cite_template_dates()) == 1
    a = Article(r"A", r"[[User talk:Noobie]]")
    assert len(a.user_signature()) == 1
    a.reset_edit_summary()
    assert len(a.edit_summary) == 0


def test_properties() -> None:
    S = W.for_site(EN)
    a = Article(r"A", r"ABC")
    assert not (a.article_is_about_a_person)
    a = Article(r"A")
    assert not (a.has_diacritics_in_title)
    a = Article(r"Aé")
    assert a.has_diacritics_in_title
    assert a.is_stub
    a = Article(r"A", r"ABC")
    assert not (a.has_stub_template)
    assert not (a.has_info_box)
    assert not (a.has_sic_tag)
    assert not (a.is_in_use)
    assert not (a.has_target_less_links)
    assert not (a.has_double_pipe_links)
    assert not (a.has_morefootnotes_and_many_references)
    assert not (a.is_disambiguation_page)
    assert not (a.is_disambiguation_page_with_refs)
    assert not (a.is_sia_page)
    assert not (a.has_ref_after_reflist)
    assert not (a.has_named_references)
    assert not (a.has_bare_references)
    assert not (a.has_ambiguous_cite_template_dates)
    assert not (a.has_see_also_after_notes_references_or_external_links)
    assert not (a.is_missing_references_display)
    assert not (a.is_redirect)


def test_can_do_general_fixes() -> None:
    S = W.for_site(EN)
    a = Article(r"A", r"ABC")
    assert a.can_do_general_fixes
    assert not (a.can_do_talk_general_fixes)
    a = Article(r"Talk:A", r"ABC")
    assert a.can_do_talk_general_fixes


def test_fix_people_categories() -> None:
    S = W.for_site(EN)
    p = genfixes.Parsers()
    a = Article(r"A", r"ABC")
    a.fix_people_categories(p, True)
    assert a.article_text == r"ABC"


def test_set_default_sort() -> None:
    S = W.for_site(EN)
    a = Article(r"A", r"ABC")
    a.set_default_sort(r"en", True)
    assert a.article_text == r"ABC"


def test_changes() -> None:
    S = W.for_site(EN)
    a = Article(r"A", r"ABC")
    a.awb_change_article_text(r"test", r"ABC D", False)
    assert not (a.only_white_space_changed)
    assert not (a.only_casing_changed)
    a = Article(r"A", r"ABC")
    a.awb_change_article_text(r"test", r"AB C", False)
    assert a.only_white_space_changed
    assert a.only_white_space_and_casing_changed
    assert not (a.only_casing_changed)
    assert not (a.no_article_text_changed)
    a = Article(r"A", r"ABC")
    a.awb_change_article_text(r"test", r"ABc", False)
    assert a.only_casing_changed
    a = Article(r"A", r"ABC")
    a.awb_change_article_text(r"test", r"ABC", False)
    assert a.no_article_text_changed
    assert not (a.only_minor_general_fixes_changed)


def test_categorisation() -> None:
    S = W.for_site(EN)
    theArticle = Article(r"Category:Hello", r"Text [[Category:Foo]]")
    p = genfixes.Parsers(500, True)
    theArticle.categorisation(CategorisationOptions(1), p, False, r"Foo", r"Foo2", False)
    assert theArticle.article_text == r"Text [[Category:Foo2]]", r"Category rename operation"


def test_namespaceless_name() -> None:
    S = W.for_site(EN)
    assert Article(r"Foo").namespaceless_name == r"Foo"
    assert Article(r"Category:Foo").namespaceless_name == r"Foo"
    assert Article(r"Category:Category:Foo").namespaceless_name == r"Category:Foo"


def test_unbalanced_brackets() -> None:
    S = W.for_site(EN)
    UnB = {}
    a = Article(r"TestArticle", r"This is the text (here.")
    UnB = a.unbalanced_brackets()
    assert len(UnB) == 1, r"One unbalanced bracket in mainspace article"
    a = Article(r"TestArticle", "This is the text here.\r\n== Section ==\r\nThere [was.")
    UnB = a.unbalanced_brackets()
    assert len(UnB) == 1, r"Unbalanced bracket in mainspace article later sections found"
    a = Article(r"Talk:TestArticle", "This is the text (here.\r\n== Section ==\r\nThere [was.")
    UnB = a.unbalanced_brackets()
    assert len(UnB) == 1, r"One unbalanced bracket in zeroth section of talk article"
    a = Article(r"Talk:TestArticle", "This is the text here.\r\n== Section ==\r\nThere [was.")
    UnB = a.unbalanced_brackets()
    assert len(UnB) == 0, r"No unbalanced bracket in zeroth section of talk article"


@pytest.mark.skip(reason="article comparers (Article/Comparers) are ported with skip conditions")
def test_contains_comparers() -> None:
    S = W.for_site(EN)
    containsComparer = ArticleComparerFactory.create(  # noqa: F821  # pyright: ignore[reportUndefinedVariable]
        "foo\nbar", False, False, False, False
    )
    notContainsComparer = ArticleComparerFactory.create(  # noqa: F821  # pyright: ignore[reportUndefinedVariable]
        "foo\nbar", False, False, False, False
    )
    a = Article(r"A", "Now foo\nbar")
    assert notContainsComparer.matches(a), r"does not contain comparer"
    assert containsComparer.matches(a), r"it contains comparer"
    a = Article(r"A", r"Now foo-bar")
    assert not (notContainsComparer.matches(a)), r"not contains is false"
    assert not (containsComparer.matches(a)), r"contains is false"


def test_comparers() -> None:
    S = W.for_site(EN)
    a = Article(r"A")
    b = Article(r"B")
    z = Article(r"Z")
    one = Article(r"1")
    diacritic = Article(r"Ș")
    dollar = Article(r"$")
    assert a.compare_to(b) == -1, r"A just before B"
    assert a.compare_to(a) == 0, r"equal"
    assert b.compare_to(a) == 1, r"B just after A"
    assert one.compare_to(a) == -16, r"1 before A"
    assert z.compare_to(diacritic) == -446, r"Diacritics later than Latin"
    assert one.compare_to(diacritic) == -487, r"Diacritics later than numbers"
    assert a.compare_to(dollar) == 29, r"Keyboard characters before Latin"


def test_unicodify() -> None:
    S = W.for_site(EN)
    Parser = genfixes.Parsers()
    RemoveText = HideText(False, True, False)
    a = Article(
        r"a",
        "'''test'''. z &amp; a&Dagger; &dagger;.\r\n\r\n{{DEFAULTSORT:Hello test}}\r\n[[Category:Test pages]]\r\n",
    )
    a.unicodify(True, Parser, RemoveText)
    assert (
        a.article_text
        == "'''test'''. z & a‡ †.\r\n\r\n{{DEFAULTSORT:Hello test}}\r\n[[Category:Test pages]]\r\n"
    ), r"Text unicodified"
    a = Article(
        r"a",
        "'''test'''. z &amp; {{t|a&Dagger; &dagger;}}.\r\n\r\n{{DEFAULTSORT:Hello test}}\r\n[[Category:Test pages]]\r\n",
    )
    a.unicodify(True, Parser, RemoveText)
    assert (
        a.article_text
        == "'''test'''. z & {{t|a&Dagger; &dagger;}}.\r\n\r\n{{DEFAULTSORT:Hello test}}\r\n[[Category:Test pages]]\r\n"
    ), r"Text unicodified, hidemore used"
    a = Article(r"a", r"ABC")
    a.unicodify(True, Parser, RemoveText)
    assert a.article_text == r"ABC", r"No change"


def test_bullet_external_links() -> None:
    S = W.for_site(EN)
    a = Article(r"a", "A\r\n==External links==\r\nhttp://www.site.com\r\n\r\n[[Category:A]]")
    a.bullet_external_links(False)
    assert r"* http://www.site.com" in a.article_text
    a = Article(r"a", "A\r\n==External links==\r\nhttp://www.site.com\r\n\r\n[[Category:A]]")
    a.bullet_external_links(True)
    assert r"* http://www.site.com" in a.article_text
    a = Article(r"a", "A\r\n==External links==\r\n* http://www.site.com\r\n\r\n[[Category:A]]")
    a.bullet_external_links(True)
    assert r"* http://www.site.com" in a.article_text


def test_fix_links() -> None:
    S = W.for_site(EN)
    a = Article(r"a", r"A [[_B ]]")
    a.fix_links(False)
    assert r"[[B]]" in a.article_text
    a = Article(r"a", r"A [[ B_]]")
    a.fix_links(True)
    assert r"[[B]]" in a.article_text
    a = Article(r"a", r"A [[B]]")
    a.fix_links(True)
    assert r"[[B]]" in a.article_text
    a = Article(r"a", r"A [[B]]")
    a.fix_links(False)
    assert r"[[B]]" in a.article_text


def test_cite_template_dates() -> None:
    S = W.for_site(EN)
    Parser = genfixes.Parsers()
    a = Article(r"a", r"A [[B]]")
    a.cite_template_dates(Parser, True)
    assert r"[[B]]" in a.article_text


def test_embolden_titles() -> None:
    S = W.for_site(EN)
    Parser = genfixes.Parsers()
    a = Article(r"a", r"A [[B]]")
    a.embolden_titles(Parser, True)
    assert r"[[B]]" in a.article_text
