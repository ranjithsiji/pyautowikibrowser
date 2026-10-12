"""Port of AWB UnitTests/RegexTests.cs: the parity suite for awb_l.core.wikiregexes.

Converted mechanically from the C# (CRLF line endings in multi-line strings preserved).
Expectations that differ from AWB on purpose are marked with a comment explaining why.
"""

# ruff: noqa: E501, F841
# pyright: reportUnusedVariable=false

from awb_l.core import tools
from awb_l.core import wikiregexes as W
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig
from tests.parity import regex_assert
from tests.parity.regex_assert import check_match, check_matches

EN = SiteConfig.english()


def test_generate_namespace_regex() -> None:
    S = W.for_site(EN)
    assert len(S.site.generate_namespace_regex(0)) == 0
    assert S.site.generate_namespace_regex(Namespace.USER) == r"User"
    assert S.site.generate_namespace_regex(Namespace.USER_TALK) == r"User[ _]talk"
    assert S.site.generate_namespace_regex(Namespace.FILE) == r"File|Image"
    assert S.site.generate_namespace_regex(Namespace.PROJECT) == r"Wikipedia|Project"
    assert S.site.generate_namespace_regex(Namespace.MEDIA, Namespace.FILE) == r"Media|File|Image"


def test_simple_wiki_link() -> None:
    S = W.for_site(EN)
    check_match(W.SimpleWikiLink, r"[[foo]]", r"[[foo]]", r"foo")
    check_matches(W.SimpleWikiLink, r"[[foo[]]", 0)
    check_match(W.SimpleWikiLink, r"[[foo bar]]", r"[[foo bar]]", r"foo bar")
    check_matches(W.SimpleWikiLink, "[[foo\r\nbar]]", 0)
    check_matches(W.SimpleWikiLink, r"[foo]]", 0)
    check_match(W.SimpleWikiLink, r"[[foo|bar]]", r"[[foo|bar]]", r"foo|bar")
    check_match(W.SimpleWikiLink, r"[[foo]] [[bar]]", r"[[foo]]", r"foo")
    check_matches(W.SimpleWikiLink, r"[[foo]] [[bar]]", 2)
    check_match(W.SimpleWikiLink, r"[[foo]]]", r"[[foo]]", r"foo")
    check_match(
        W.SimpleWikiLink, r"[[foo [[bar]] here]]", r"[[foo [[bar]] here]]", r"foo [[bar]] here"
    )
    check_match(W.SimpleWikiLink, r"[[[foo]]", r"[[foo]]", r"foo")
    check_match(W.SimpleWikiLink, r"[[foo|bar]]")
    check_match(W.SimpleWikiLink, r"[[Image:Foo.jpg]]")
    check_match(W.SimpleWikiLink, r"[[Image:Bar.jpg|Bar]]")
    check_match(W.SimpleWikiLink, r"[[Image:Bar.jpg|Bar|20px]]")
    check_match(W.SimpleWikiLink, r"[[Category:Foo]]")
    check_match(W.SimpleWikiLink, r"[[Category:Foo|Bar]]")


def test_redirect_test() -> None:
    S = W.for_site(EN)
    check_match(S.Redirect, r"#redirect [[Foo]]", r"#redirect [[Foo]]", r"Foo")
    check_match(S.Redirect, r"#redirect [[Foo|bar]]", r"#redirect [[Foo|bar]]", r"Foo")
    check_match(S.Redirect, r"#Redirect : [[Foo#bar]]", r"#Redirect : [[Foo#bar]]", r"Foo#bar")
    check_match(S.Redirect, r"#REDIRECT[[Foo]]", r"#REDIRECT[[Foo]]", r"Foo")
    check_match(S.Redirect, "#REDIRECT\r\n[[Foo]]", "#REDIRECT\r\n[[Foo]]", r"Foo")
    check_match(S.Redirect, r"#redirect[[:Foo bar ]]", r"#redirect[[:Foo bar ]]", r"Foo bar")
    check_matches(S.Redirect, r"[foo]]", 0)


def test_talkpage_header() -> None:
    S = W.for_site(EN)
    check_matches(W.TalkHeaderTemplate, r"{{talk header|foo}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{ talk header}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{Talk header|foo}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{Talkheader|foo}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{Talkpageheader|foo}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{talkheader|foo}}", 1)
    check_matches(W.TalkHeaderTemplate, "{{talkheader\r\n|foo|bar\r\n|here}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{Talkheader}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{talk header|search=yes}}", 1)
    check_matches(W.TalkHeaderTemplate, r"{{talk header|noarchive=yes}}", 1)
    assert W.TalkHeaderTemplate.match(r"{{ Talkpageheader  |foo}}").group(1) == r"Talkpageheader"
    check_matches(W.TalkHeaderTemplate, r"{{talkarchivenav|noredlinks=yes}}", 0)
    check_matches(W.TalkHeaderTemplate, r"{{talkheadernav}}", 0)


def test_skip_toctemplate_regex() -> None:
    S = W.for_site(EN)
    check_matches(W.SkipTOCTemplateRegex, r"{{Skip to talk}}", 1)
    check_matches(W.SkipTOCTemplateRegex, r"{{ skiptotoctalk}}", 1)
    check_matches(W.SkipTOCTemplateRegex, r"{{skiptotoc}}", 1)


def test_wiki_project_banner_shell_template() -> None:
    S = W.for_site(EN)
    check_matches(W.WikiProjectBannerShellTemplate, r"{{WPBS|1=foo}}", 1)
    check_matches(W.WikiProjectBannerShellTemplate, r"{{WikiProjectBannerShell}}", 1)
    check_matches(W.WikiProjectBannerShellTemplate, r"{{WikiProject banner shell}}", 1)
    check_matches(W.WikiProjectBannerShellTemplate, r"{{WikiProject Banner Shell}}", 1)
    check_matches(W.WikiProjectBannerShellTemplate, r"{{WikiProjectBanners|foo}}", 1)
    check_matches(W.WikiProjectBannerShellTemplate, r"{{WikiProjectBanners|1=foo|bar}}", 1)
    check_matches(
        W.WikiProjectBannerShellTemplate, r"{{WikiProjectBanners|blp=yes|activepol=yes|1=foo}}", 1
    )
    check_matches(
        W.WikiProjectBannerShellTemplate,
        "{{WikiProjectBanners|blp=yes|1=\r\n            {{WPBiography|living=yes|class=}}\r\n            }}",
        1,
    )
    check_matches(
        W.WikiProjectBannerShellTemplate,
        "{{WikiProjectBanners|blp=yes|1=\r\n            {{WPBiography|living=yes|class=}}\r\n            {{WikiProject Greece}}\r\n            |activepol=yes\r\n            }}",
        1,
    )


def test_blpunsourced() -> None:
    S = W.for_site(EN)
    check_matches(W.BLPSources, r"{{BLP unsourced|foo}}", 1)
    check_matches(W.BLPSources, r"{{UnsourcedBLP|foo}}", 1)
    check_matches(W.BLPSources, r"{{BLPunreferenced|foo}}", 1)
    check_matches(W.BLPSources, r"{{Unreferencedblp|foo}}", 1)
    check_matches(W.BLPSources, r"{{Blpunsourced|foo}}", 1)
    check_matches(W.BLPSources, r"{{BLPunsourced|foo}}", 1)
    check_matches(W.BLPSources, r"{{Unsourcedblp|foo}}", 1)
    check_matches(W.BLPSources, r"{{BLPUnreferenced|foo}}", 1)
    check_matches(W.BLPSources, r"{{Unsourced BLP|foo}}", 1)
    check_matches(W.BLPSources, r"{{BLP unreferenced|foo}}", 1)
    check_matches(W.BLPSources, r"{{Blpunref|foo}}", 1)
    check_matches(W.BLPSources, r"{{Unreferenced BLP|foo}}", 1)
    check_matches(W.BLPSources, r"{{Blpunreferenced|foo}}", 1)
    check_matches(W.BLPSources, r"{{UnreferencedBLP|foo}}", 1)
    check_matches(W.BLPSources, r"{{BLPUnsourced|foo}}", 1)
    check_matches(W.BLPSources, r"{{Unreferenced blp|foo}}", 1)
    check_matches(W.BLPSources, r"{{ BLP Unreferenced | foo}}", 1)
    check_matches(W.BLPSources, r"{{ BLP unsourced section| foo}}", 1)
    check_matches(W.BLPSources, r"{{bLP Unreferenced}}", 1)
    check_matches(W.BLPSources, r"{{BLP unreferenced section| foo}}", 1)


def test_named_references() -> None:
    S = W.for_site(EN)
    assert W.NamedReferences.is_match(r'<ref name = "foo">text</ref>')
    assert W.NamedReferences.is_match(r'<ref name = "foo"></ref>')
    assert W.NamedReferences.is_match(r"<ref name =foo>text</ref>")
    assert W.NamedReferences.is_match(r"<ref name=foo>text< / ref >")
    assert W.NamedReferences.is_match(r"<ref name=foo>te<taga</tag>xt</ref>"), r"nested tag support"
    assert W.NamedReferences.is_match(r"<ref name = 'foo'>text</ref>")
    assert W.NamedReferences.is_match(r'< REF NAME = "foo">text</ref>')
    assert W.NamedReferences.is_match(
        '< REF NAME = "foo">\r\n{{ cite web|\r\ntitle = text |\r\nwork = text\r\n}}</ref>'
    ), r"matches multiple line ref"
    assert W.NamedReferences.is_match(r'< REF NAME = "foo">text <br>more</ref>'), (
        r"case insensitive matching"
    )
    assert (
        W.NamedReferences.match(
            r'<ref name="vietnam.ttu.edu"/><ref name="Shul726">Shul, p. 726</ref>'
        ).value
        == r'<ref name="Shul726">Shul, p. 726</ref>'
    ), r"match is not across consecutive references – first condensed"
    assert (
        W.NamedReferences.match(
            r'<ref name="Shul726">Shul, p. 726</ref><ref name="Foo">foo text</ref>'
        ).value
        == r'<ref name="Shul726">Shul, p. 726</ref>'
    ), r"match is not across consecutive references – first full"
    assert (
        W.NamedReferences.match(
            r'<ref name="vietnam.ttu.edu"/><ref name="Shul726">Shul, p. 726</ref>'
        ).group(2)
        == r"Shul726"
    ), r"ref name is group 2"
    assert (
        W.NamedReferences.match(
            r'<ref name="vietnam.ttu.edu"/><ref name="Shul726">Shul, p. 726</ref>'
        ).group(3)
        == r"Shul, p. 726"
    ), r"ref value is group 3"
    assert (
        W.NamedReferences.match(
            '<ref name="vietnam.ttu.edu"/><ref name="Shul726">\r\nShul, p. 726    </ref>'
        ).group(2)
        == r"Shul726"
    ), r"ref value doesn't include leading/trailing whitespace"
    assert W.NamedReferencesIncludingCondensed.is_match(r'<ref name = "foo">text</ref>')
    assert W.NamedReferencesIncludingCondensed.is_match(r'<ref name = "fo/o">text</ref>')
    assert W.NamedReferencesIncludingCondensed.is_match(
        r'<ref name = "foo">text<tag>a</tag></ref>'
    ), r"matches with nested tags"
    assert W.NamedReferencesIncludingCondensed.is_match(r'<ref name = "foo"></ref>')
    assert W.NamedReferencesIncludingCondensed.is_match(r"<ref Name =foo>text</ref>")
    assert W.NamedReferencesIncludingCondensed.is_match(r"<ref name=foo>text< / ref >")
    assert W.NamedReferencesIncludingCondensed.is_match(r"<ref name=foo>te<taga</tag>xt</ref>"), (
        r"nested tag support"
    )
    assert W.NamedReferencesIncludingCondensed.is_match(r"<ref name = 'foo'>text</ref>")
    assert W.NamedReferencesIncludingCondensed.is_match(r'< ref NAME = "foo">text</ref>')
    assert W.NamedReferencesIncludingCondensed.is_match(r'< ref NAME = "foo" />'), (
        r"matches condensed named ref"
    )
    assert W.NamedReferencesIncludingCondensed.is_match(
        '< ref NAME = "foo">\r\n{{ cite web|\r\ntitle = text |\r\nwork = text\r\n}}</ref>'
    ), r"matches multiple line ref"
    assert W.NamedReferencesIncludingCondensed.is_match(
        r'< ref NAME = "foo">text <br>more</ref>'
    ), r"case insensitive matching"
    assert (
        W.NamedReferencesIncludingCondensed.match(
            r'<ref name="vietnam.ttu.edu"/><ref name="Shul726">Shul, p. 726</ref>'
        ).value
        == r'<ref name="vietnam.ttu.edu"/>'
    ), r"match is not across consecutive references – first condensed"
    assert (
        W.NamedReferencesIncludingCondensed.match(r'<ref name="Shul726">Shul, p. 726</ref>').group(
            2
        )
        == r"Shul726"
    ), r"ref name is group 2"
    assert (
        W.NamedReferencesIncludingCondensed.match(r'<ref name="Shul726">Shul, p. 726</ref>').group(
            3
        )
        == r"Shul, p. 726"
    ), r"ref value is group 3"
    assert (
        W.NamedReferencesIncludingCondensed.match(
            '<ref name="Shul726">\r\nShul, p. 726    </ref>'
        ).group(2)
        == r"Shul726"
    ), r"ref value doesn't include leading/trailing whitespace"


def test_unformatted_text_tests() -> None:
    S = W.for_site(EN)
    assert W.UnformattedText.is_match(r"<pre>{{abc}}</pre>")
    assert W.UnformattedText.is_match(r"<math>{{abc}}</math>")
    assert W.UnformattedText.is_match(r"<math chem>{{abc}}</math>")
    assert W.UnformattedText.is_match(r"<chem>{{abc}}</chem>")
    assert W.UnformattedText.is_match(r"<nowiki>{{abc}}</nowiki>")
    assert W.UnformattedText.is_match(r"now hello {{bye}} <pre>{now}}</pre>")
    assert W.UnformattedText.is_match(r"<!--{{abc}}-->")
    assert not (W.UnformattedText.is_match(r"<pre>{{abc}}</nowiki>")), (
        r"Does not match unbalanced tags"
    )


def test_all_tags() -> None:
    S = W.for_site(EN)
    assert W.AllTags.is_match(r"<pre>{{abc}}</pre>")
    assert W.AllTags.is_match(r"<math>{{abc}}</math>")
    assert W.AllTags.is_match(r"<nowiki>{{abc}}</nowiki>")
    assert W.AllTags.is_match(r"<timeline>{{abc}}</timeline>")
    assert W.AllTags.is_match(r"<cite>{{abc}}</cite>")
    assert W.AllTags.is_match(r"<blockquote>{{abc}}</blockquote>")
    assert W.AllTags.is_match(r"<BLOCKQUOTE>{{abc}}</BLOCKQUOTE>")
    assert W.AllTags.is_match(r"<poem>{{abc}}</poem>")
    assert W.AllTags.is_match(r"<imagemap>{{abc}}</imagemap>")
    assert W.AllTags.is_match(r"<noinclude>{{abc}}</noinclude>")
    assert W.AllTags.is_match(r"<includeonly>{{abc}}</includeonly>")
    assert W.AllTags.is_match(r"<onlyinclude>{{abc}}</onlyinclude>")
    assert W.AllTags.is_match(r"<hiero>abc</hiero>")
    assert W.AllTags.is_match(
        r"<score>{a,, c, e, a, c e a c' e' a' c'' e'' a'' c''' e''' g''' \bar</score>"
    )
    assert W.AllTags.is_match(r"now hello {{bye}} <pre>{now}}</pre>")
    assert not (W.AllTags.is_match(r"<!--{{abc}}-->"))
    assert not (W.AllTags.is_match(r"<pre>{{abc}}</nowiki>")), r"Does not match unbalanced tags"
    assert W.AllTags.is_match(r"<pre>{{abc}}</pre>")
    assert W.AllTags.is_match(r"<code>{{abc}}</code>")
    assert W.AllTags.is_match(r"<source lang=xml>{{abc}}</source>")
    assert W.AllTags.is_match(r"<syntaxhighlight lang=xml>{{abc}}</syntaxhighlight>")
    assert W.AllTags.is_match(r"<source>{{abc}}</source>")
    assert W.AllTags.is_match(r"<syntaxhighlight>{{abc}}</syntaxhighlight>")
    assert W.AllTags.is_match(r"now hello {{bye}} <pre>{now}}</pre>")
    assert W.AllTags.is_match(r"<math>{{abc}}</math>")
    assert W.AllTags.is_match(r"<chem>{{abc}}</chem>")
    assert W.AllTags.is_match(r"<math chem>{{abc}}</math>")
    assert W.AllTags.is_match(r"<pre>now <br> now </pre>")
    assert W.AllTags.is_match(r"< pre >{{abc}}< / pre >")
    assert W.AllTags.is_match(r"< pre > {{abc}} < / pre >")
    assert W.AllTags.is_match("< pre >\r\n{{abc}}\r\n< / pre >")
    assert W.AllTags.is_match("<\r\n pre > {{abc}} < / pre\r\n >")
    assert (
        W.AllTags.match(r"<nowiki>now <math>{{abc}}</math> now </nowiki>").value
        == r"<nowiki>now <math>{{abc}}</math> now </nowiki>"
    )


def test_source_code_tests() -> None:
    S = W.for_site(EN)
    assert W.SourceCode.is_match(r"<code>{{abc}}</code>")
    assert W.SourceCode.is_match(r"<source lang=xml>{{abc}}</source>")
    assert W.SourceCode.is_match(r"<syntaxhighlight lang=xml>{{abc}}</syntaxhighlight>")
    assert W.SourceCode.is_match(r'<syntaxhighlight lang="xml">{{abc}}</syntaxhighlight>')
    assert W.SourceCode.is_match(
        r'<syntaxhighlight lang="javascript">\r\n var x; //defines the variable x</syntaxhighlight>'
    )
    assert W.SourceCode.is_match(r"<source>{{abc}}</source>")
    assert W.SourceCode.is_match(r"<syntaxhighlight>{{abc}}</syntaxhighlight>")
    assert W.SourceCode.is_match(r"<tt>{{abc}}</tt>")
    assert not (W.SourceCode.is_match(r"<math>{{abc}}</math>"))
    assert not (W.SourceCode.is_match(r"<pre>{{abc}}</pre>"))


def test_math_pre_source_code_tests() -> None:
    S = W.for_site(EN)
    assert W.MathPreSourceCodeComments.is_match(r"<pre>{{abc}}</pre>")
    assert W.MathPreSourceCodeComments.is_match(r"<!--{{abc}}-->")
    assert W.MathPreSourceCodeComments.is_match(r"<code>{{abc}}</code>")
    assert W.MathPreSourceCodeComments.is_match(r"<source lang=xml>{{abc}}</source>")
    assert W.MathPreSourceCodeComments.is_match(
        r"<syntaxhighlight lang=xml>{{abc}}</syntaxhighlight>"
    )
    assert W.MathPreSourceCodeComments.is_match(
        r'<syntaxhighlight lang="xml">{{abc}}</syntaxhighlight>'
    )
    assert W.SourceCode.is_match(
        r'<syntaxhighlight lang="javascript">\r\n var x; //defines the variable x</syntaxhighlight>'
    )
    assert W.MathPreSourceCodeComments.is_match(r"<source>{{abc}}</source>")
    assert W.MathPreSourceCodeComments.is_match(r"<syntaxhighlight>{{abc}}</syntaxhighlight>")
    assert W.MathPreSourceCodeComments.is_match(r"now hello {{bye}} <pre>{now}}</pre>")
    assert W.MathPreSourceCodeComments.is_match(r"<math>{{abc}}</math>")
    assert W.MathPreSourceCodeComments.is_match(r'<math display="block">{{abc}}</math>')
    assert W.MathPreSourceCodeComments.is_match(r'<math display = "inline" >{{abc}}</math>')
    assert W.MathPreSourceCodeComments.is_match(r"<chem>{{abc}}</chem>")
    assert W.MathPreSourceCodeComments.is_match(r"<math chem>{{abc}}</math>")
    assert W.SourceCode.is_match(r"<tt>{{abc}}</tt>")
    assert not (W.MathPreSourceCodeComments.is_match(r"<nowiki>{{abc}}</nowiki>"))


def test_wiki_links_only() -> None:
    S = W.for_site(EN)
    check_match(W.WikiLinksOnly, r"[[foo]]", r"[[foo]]")
    check_match(W.WikiLinksOnly, r"[[foo#bar]]", r"[[foo#bar]]")
    check_match(W.WikiLinksOnly, r"[[:foo]]", r"[[:foo]]")
    check_match(W.WikiLinksOnly, r"[[a:foo]]", r"[[a:foo]]")
    check_match(W.WikiLinksOnly, r"[[FOO:BAR]]", r"[[FOO:BAR]]")
    check_match(W.WikiLinksOnly, r"[[foo bar:world series]]", r"[[foo bar:world series]]")
    check_match(W.WikiLinksOnly, r"[[foo bar]]", r"[[foo bar]]")
    check_matches(W.WikiLinksOnly, "[[foo\r\nbar]]", 0)
    check_matches(W.WikiLinksOnly, r"[foo]]", 0)
    check_match(W.WikiLinksOnly, r"[[foo|bar]]", r"[[foo|bar]]")
    check_match(W.WikiLinksOnly, r"[[foo]] [[bar]]", r"[[foo]]")
    check_matches(W.WikiLinksOnly, r"[[foo]] [[bar]]", 2)
    check_match(W.WikiLinksOnly, r"[[foo]]]", r"[[foo]]")
    check_match(W.WikiLinksOnly, r"[[[foo]]", r"[[foo]]")
    check_matches(W.WikiLinksOnly, r"[[foo[]]", 0)
    check_match(W.WikiLinksOnly, r"[[foo [[bar]] here]", r"[[bar]]")
    check_matches(W.WikiLinksOnly, r"[[Category:Test]]", 0)
    check_matches(W.WikiLinksOnly, r"[[de:Test]]", 0)
    check_matches(W.WikiLinksOnly, r"[[Image:Test,]]", 0)


def test_wiki_links_only_possible_pipe() -> None:
    S = W.for_site(EN)
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo]]", r"[[foo]]")
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[:foo]]", r"[[:foo]]")
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo#bar]]", r"[[foo#bar]]")
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[a:foo]]", r"[[a:foo]]")
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[FOO:BAR]]", r"[[FOO:BAR]]")
    check_match(
        W.WikiLinksOnlyPossiblePipe, r"[[foo bar:world series]]", r"[[foo bar:world series]]"
    )
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo bar]]", r"[[foo bar]]")
    check_matches(W.WikiLinksOnlyPossiblePipe, "[[foo\r\nbar]]", 0)
    check_matches(W.WikiLinksOnlyPossiblePipe, r"[foo]]", 0)
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo|bar]]", r"[[foo|bar]]")
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo]] [[bar]]", r"[[foo]]")
    check_matches(W.WikiLinksOnlyPossiblePipe, r"[[foo]] [[bar]]", 2)
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo]]]", r"[[foo]]")
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[[foo]]", r"[[foo]]")
    check_matches(W.WikiLinksOnlyPossiblePipe, r"[[foo[]]", 0)
    check_match(W.WikiLinksOnlyPossiblePipe, r"[[foo [[bar]] here]", r"[[bar]]")
    check_matches(W.WikiLinksOnlyPossiblePipe, r"[[Category:Test]]", 0)
    check_matches(W.WikiLinksOnlyPossiblePipe, r"[[de:Test]]", 0)
    check_matches(W.WikiLinksOnlyPossiblePipe, r"[[Image:Test,]]", 0)
    assert W.WikiLinksOnlyPossiblePipe.match(r"[[foo|bar]]").group(1) == r"foo"
    assert W.WikiLinksOnlyPossiblePipe.match(r"[[foo]]").group(1) == r"foo"
    assert (
        W.WikiLinksOnlyPossiblePipe.match(r"[[foo smith:the great|bar]]").group(1)
        == r"foo smith:the great"
    )
    assert W.WikiLinksOnlyPossiblePipe.match(r"[[foo|bar here]]").group(2) == r"bar here"


def test_dead_link_tests() -> None:
    S = W.for_site(EN)
    check_match(W.DeadLink, r"{{dead link}}", r"{{dead link}}")
    check_match(W.DeadLink, r"{{Dead link}}", r"{{Dead link}}")
    check_match(W.DeadLink, r"{{Deadlink}}", r"{{Deadlink}}")
    check_match(W.DeadLink, r"{{brokenlink}}", r"{{brokenlink}}")
    check_match(W.DeadLink, r"{{Dl}}", r"{{Dl}}")
    check_match(W.DeadLink, r"{{Dead link}}", r"{{Dead link}}")
    check_match(W.DeadLink, r"{{dead link|date=May 2009}}", r"{{dead link|date=May 2009}}")


def test_target_less_link_tests() -> None:
    S = W.for_site(EN)
    check_match(W.TargetLessLink, r"[[|foo]]", r"[[|foo]]")
    check_match(W.TargetLessLink, r"[[|Foo]]", r"[[|Foo]]")
    check_match(W.TargetLessLink, r"[[|Foo ]]", r"[[|Foo ]]")
    check_match(W.TargetLessLink, r"[[|foo bar]]", r"[[|foo bar]]")
    check_match(W.TargetLessLink, r"[[|linktext]]", r"[[|linktext]]")
    check_match(W.TargetLessLink, r"[[|linktext (foo)]]", r"[[|linktext (foo)]]")
    check_match(W.TargetLessLink, r"[[|link.text (foo)]]", r"[[|link.text (foo)]]")
    check_match(W.TargetLessLink, r"[[|link!?]]", r"[[|link!?]]")
    check_match(W.TargetLessLink, r"[[|Foo (1971–1985)]]", r"[[|Foo (1971–1985)]]")
    check_match(W.TargetLessLink, r"[[|Victor + Victoria]]", r"[[|Victor + Victoria]]")
    check_match(W.TargetLessLink, r"[[foo|bar]]", False)


def test_double_pipe_link_tests() -> None:
    S = W.for_site(EN)
    check_match(W.DoublePipeLink, r"[[text|text2|text3]]", r"[[text|text2|text3]]")
    check_match(W.DoublePipeLink, r"[[Text|Text2|Text3]]", r"[[Text|Text2|Text3]]")
    check_match(W.DoublePipeLink, r"[[text||text3]]", r"[[text||text3]]")
    check_match(W.DoublePipeLink, r"[[text|(text2)|text3]]", r"[[text|(text2)|text3]]")
    check_match(W.DoublePipeLink, r"[[text (1)|text2|text3]]", r"[[text (1)|text2|text3]]")
    check_match(
        W.DoublePipeLink,
        r"[[Saint-Georges-du-Bois|Saint-Georges-du-Bois|Saint-Georges-du-Bois]]",
        r"[[Saint-Georges-du-Bois|Saint-Georges-du-Bois|Saint-Georges-du-Bois]]",
    )
    check_match(
        W.DoublePipeLink,
        r"[[text, bar|text2, bar2|text3, bar3]]",
        r"[[text, bar|text2, bar2|text3, bar3]]",
    )
    check_match(
        W.DoublePipeLink,
        r"[[First Australian Imperial Force|Australian Imperial Force|A.I.F.]]",
        r"[[First Australian Imperial Force|Australian Imperial Force|A.I.F.]]",
    )
    check_match(W.DoublePipeLink, r"[[Ric (f)|Ric (f)|o.g.]]", r"[[Ric (f)|Ric (f)|o.g.]]")
    check_match(W.DoublePipeLink, r"[[text|text2|text3 & text4]]", r"[[text|text2|text3 & text4]]")
    check_match(
        W.DoublePipeLink,
        r"[[Bairnsdale|, Victoria|Bairnsdale]]",
        r"[[Bairnsdale|, Victoria|Bairnsdale]]",
    )
    check_match(
        W.DoublePipeLink,
        r"[[Bairnsdale!|Victoria|Bairnsdale]]",
        r"[[Bairnsdale!|Victoria|Bairnsdale]]",
    )
    check_match(
        W.DoublePipeLink,
        r"[[Bairnsdale!|Victoria?|Bairns, dale]]",
        r"[[Bairnsdale!|Victoria?|Bairns, dale]]",
    )
    check_match(
        W.DoublePipeLink,
        r"[[Foo (1971–1985)|Victoria?|Bairns, dale]]",
        r"[[Foo (1971–1985)|Victoria?|Bairns, dale]]",
    )
    check_match(
        W.DoublePipeLink,
        r"[[Foo (1971–1985)|Victor + Victoria|Bairns, dale]]",
        r"[[Foo (1971–1985)|Victor + Victoria|Bairns, dale]]",
    )
    check_match(W.DoublePipeLink, r"[[test's test|test1|test2]]", r"[[test's test|test1|test2]]")
    check_match(
        W.DoublePipeLink, r'[[Vlach "Roman Legion"|The Roman Legion|The so called "Roman Legion"]]'
    )
    check_match(W.DoublePipeLink, r"[[text|foo bar]]", False)
    check_match(W.DoublePipeLink, r"[[|linktext]]", False)
    check_match(W.DoublePipeLink, r"[[foo|bar]]", False)
    check_match(W.DoublePipeLink, r"[[text!@?()&123456789|foo bar]]", False)
    check_match(W.DoublePipeLink, r'[["text"|foo bar]]', False)


def test_wiki_link_tests() -> None:
    S = W.for_site(EN)
    assert W.WikiLink.match(r"[[foo]]").group(1) == r"foo"
    assert W.WikiLink.match(r"[[foo|bar]]").group(1) == r"foo"
    assert W.WikiLink.match(r"[[foo bar]]").group(1) == r"foo bar"
    assert W.WikiLink.match(r"[[Foo]]").group(1) == r"Foo"
    assert W.WikiLink.match(r"[[foo bar|word here]]").group(1) == r"foo bar"
    check_match(W.WikiLink, r"[[foo|'''bar''']]")
    check_match(W.WikiLink, r"[[foo|''bar'']]")


def test_piped_wiki_link() -> None:
    S = W.for_site(EN)
    check_match(W.PipedWikiLink, r"[[foo|bar]]")
    check_match(W.PipedWikiLink, r"a [[foo boo | bar bar ]] !one", r"[[foo boo | bar bar ]]")
    check_match(W.PipedWikiLink, r"[[foo]]", False)
    check_match(W.PipedWikiLink, r"[[foo|bar|]]")
    check_match(W.PipedWikiLink, r"[[foo]] [[foo|bar]]", r"[[foo|bar]]")
    check_match(W.PipedWikiLink, r"[[foo|bar]] [[foo]]", r"[[foo|bar]]")
    check_match(W.PipedWikiLink, "[[foo|\r\nbar]]", False)
    check_match(W.PipedWikiLink, "[[foo\r\n|bar]]", False)
    check_match(W.PipedWikiLink, r"[[foo]] | bar]]", False)
    check_match(W.PipedWikiLink, r"[[foo | [[bar]]", False)
    assert W.PipedWikiLink.match(r"[[foo|bar]]").group(1) == r"foo"
    assert W.PipedWikiLink.match(r"[[foo|bar]]").group(2) == r"bar"


def test_un_piped_wiki_link() -> None:
    S = W.for_site(EN)
    check_match(W.UnPipedWikiLink, r"[[foo]]")
    check_match(W.UnPipedWikiLink, r"a [[foo boo ]] !one", r"[[foo boo ]]")
    check_match(W.UnPipedWikiLink, r"[[foo|bar]]", False)
    assert W.UnPipedWikiLink.match(r"[[foo]]").group(1) == r"foo"
    assert W.UnPipedWikiLink.match(r"[[foo bar]]").group(1) == r"foo bar"


def test_blockquote() -> None:
    S = W.for_site(EN)
    check_match(
        W.Blockquote, r"<blockquote>foo bar< /blockquote>", r"<blockquote>foo bar< /blockquote>"
    )
    check_match(
        W.Blockquote,
        r"<blockquote style=x>foo bar< /blockquote>",
        r"<blockquote style=x>foo bar< /blockquote>",
    )
    check_match(
        W.Blockquote,
        "< Blockquote >foo\r\nbar</ BLOCKQUOTE>",
        "< Blockquote >foo\r\nbar</ BLOCKQUOTE>",
    )


def test_persondata() -> None:
    S = W.for_site(EN)
    assert S.Persondata.is_match(r"{{Persondata}}")
    S = W.for_site(EN.with_lang_code(r"de"))
    assert S.Persondata.is_match(r"{{personendaten}}")


def test_use_dates_template_tests() -> None:
    S = W.for_site(EN)
    check_match(W.UseDatesTemplate, r"{{use mdy dates}}", True)
    check_match(W.UseDatesTemplate, r"{{mdy}}", True)
    check_match(W.UseDatesTemplate, r"{{Mdy}}", True)
    check_match(W.UseDatesTemplate, r"{{ Use dmy dates}}", True)
    check_match(W.UseDatesTemplate, r"{{dmy}}", True)
    check_match(W.UseDatesTemplate, r"{{DMY}}", True)
    check_match(W.UseDatesTemplate, r"{{use ymd dates}}", True)
    check_match(W.UseDatesTemplate, r"{{ISO}}", True)
    assert W.UseDatesTemplate.match(r"{{use mdy dates}}").group(2) == r"use mdy dates"


def test_isodates() -> None:
    S = W.for_site(EN)
    check_match(W.ISODates, r"on 2009-12-11 a", True)
    check_match(W.ISODates, r"on 2009-12-01 a", True)
    check_match(W.ISODates, r"on 2009-12-21 a", True)
    check_match(W.ISODates, r"on 2009-08-31 a", True)
    check_match(W.ISODates, r"BC]] |date=2003-10-19 }}", True)
    check_match(W.ISODates, r"on 1009-12-11 a", False)
    check_match(W.ISODates, r"on 2209-12-11 a", False)
    check_match(W.ISODates, r"on 2009-14-11 a", False)
    check_match(W.ISODates, r"on 2009-2-11 a", False)
    check_match(W.ISODates, r"on 2009-08-33 a", False)
    check_match(W.ISODates, r"on 2009/08/31 a", False)
    check_match(W.ISODatesQuick, r"on 2009-12-11 a", True)
    check_match(W.ISODatesQuick, r"on 2009-12-01 a", True)
    check_match(W.ISODatesQuick, r"on 2009-12-21 a", True)
    check_match(W.ISODatesQuick, r"on 2009-08-31 a", True)
    check_match(W.ISODatesQuick, r"BC]] |date=2003-10-19 }}", True)
    check_match(W.ISODatesQuick, r"on 1009-12-11 a", False)
    check_match(W.ISODatesQuick, r"on 2209-12-11 a", False)
    check_match(W.ISODatesQuick, r"on 2009-14-11 a", False)
    check_match(W.ISODatesQuick, r"on 2009-2-11 a", False)
    check_match(W.ISODatesQuick, r"on 2009-08-33 a", False)
    check_match(W.ISODatesQuick, r"on 2009/08/31 a", False)


def test_image_map_tests() -> None:
    S = W.for_site(EN)
    check_match(W.ImageMap, r"<imagemap>foo bar< /imagemap>", r"<imagemap>foo bar< /imagemap>")
    check_match(W.ImageMap, r"<Imagemap>foo bar< /Imagemap>", r"<Imagemap>foo bar< /Imagemap>")
    check_match(
        W.ImageMap,
        r"<imagemap id=hello>foo bar< /imagemap>",
        r"<imagemap id=hello>foo bar< /imagemap>",
    )
    check_match(
        W.ImageMap, "< imagemap >foo\r\nbar</ IMAGEMAP>", "< imagemap >foo\r\nbar</ IMAGEMAP>"
    )


def test_gallery_tag_tests() -> None:
    S = W.for_site(EN)
    g1 = "< gallery >\r\nFile:foo.JPG\r\nImage:Bar.png|description\r\n</ gallery>"
    g2 = "<GALLERY>\r\nFile:foo.JPG\r\nImage:Bar.png|description\r\n</ gallery>"
    g3 = '<gallery param="value">\r\nFile:foo.JPG\r\nImage:Bar.png|description\r\n</ gallery>'
    check_match(W.GalleryTag, g1, g1)
    check_match(W.GalleryTag, g2, g2)
    check_match(W.GalleryTag, g3, g3)


def test_noinclude_tests() -> None:
    S = W.for_site(EN)
    check_match(W.Noinclude, r"<noinclude>foo bar< /noinclude>", r"<noinclude>foo bar< /noinclude>")
    check_match(W.Noinclude, r"<Noinclude>foo bar< /Noinclude>", r"<Noinclude>foo bar< /Noinclude>")
    check_match(
        W.Noinclude, "< noinclude >foo\r\nbar</ NOINCLUDE>", "< noinclude >foo\r\nbar</ NOINCLUDE>"
    )


def test_includeonly_tests() -> None:
    S = W.for_site(EN)
    check_match(
        W.Includeonly,
        r"<includeonly>foo bar< /includeonly>",
        r"<includeonly>foo bar< /includeonly>",
    )
    check_match(
        W.Includeonly,
        r"<Includeonly>foo bar< /Includeonly>",
        r"<Includeonly>foo bar< /Includeonly>",
    )
    check_match(
        W.Includeonly,
        r"<onlyInclude>foo bar< /onlyInclude>",
        r"<onlyInclude>foo bar< /onlyInclude>",
    )
    check_match(
        W.Includeonly,
        "< includeonly >foo\r\nbar</ INCLUDEONLY>",
        "< includeonly >foo\r\nbar</ INCLUDEONLY>",
    )


def test_template() -> None:
    S = W.for_site(EN)
    regex_assert.matches(r"{{foo}}", W.TemplateMultiline, r"{{foo}}")
    regex_assert.matches(r"{{foo}}", W.TemplateMultiline, r"123{{foo}}test")
    regex_assert.matches(r"{{foo|bar}}", W.TemplateMultiline, r"{{foo|bar}}")
    regex_assert.matches("{{foo\r\n|bar=test}}", W.TemplateMultiline, "{{foo\r\n|bar=test}}")
    regex_assert.matches(
        r"Should match distinct templates",
        W.TemplateMultiline,
        r"{{foo}}{{bar}}",
        r"{{foo}}",
        r"{{bar}}",
    )
    regex_assert.no_match(W.TemplateMultiline, r"{{foo| {bar} }}")


def test_nested_templates() -> None:
    S = W.for_site(EN)
    regex_assert.matches(r"{{foo}}", W.NestedTemplates, r"{{foo}}")
    regex_assert.matches(r"{{foo}}", W.NestedTemplates, r"123{{foo}}test")
    regex_assert.matches(r"{{foo|bar}}", W.NestedTemplates, r"{{foo|bar}}")
    regex_assert.matches("{{foo\r\n|bar=test}}", W.NestedTemplates, "{{foo\r\n|bar=test}}")
    regex_assert.matches(
        r"Should match distinct templates",
        W.NestedTemplates,
        r"{{foo}}{{bar}}",
        r"{{foo}}",
        r"{{bar}}",
    )
    regex_assert.matches(r"{{foo| {bar} }}", W.NestedTemplates, r"{{foo| {bar} }}")
    regex_assert.matches(r"{{foo {{bar}} end}}", W.NestedTemplates, r"{{foo {{bar}} end}}")
    regex_assert.matches(
        r"{{foo {{bar}} {{bar2}} end}}", W.NestedTemplates, r"{{foo {{bar}} {{bar2}} end}}"
    )
    regex_assert.matches(r"{{foo {bar} end}}", W.NestedTemplates, r"{{foo {bar} end}}")
    regex_assert.matches(r"{{ foo |bar}}", W.NestedTemplates, r"{{ foo |bar}}")
    regex_assert.matches(r"{{foo<!--comm-->|bar}}", W.NestedTemplates, r"{{foo<!--comm-->|bar}}")
    regex_assert.matches(r"", W.NestedTemplates, r"{{foo")
    regex_assert.matches(r"{{{foo}}}", W.NestedTemplates, r"{{{foo}}}")


def test_template_name() -> None:
    S = W.for_site(EN)
    assert (
        W.TemplateName.match(r"{{Start date and age|1833|7|11}}").group(1) == r"Start date and age"
    )
    assert (
        W.TemplateName.match(r"{{ Start date and age |1833|7|11}}").group(1)
        == r"Start date and age"
    )
    assert (
        W.TemplateName.match("{{\r\nStart date and age\r\n|1833|7|11}}").group(1)
        == r"Start date and age"
    )
    assert (
        W.TemplateName.match(r"{{start date and age <!--comm--> |1833|7|11}}").group(1)
        == r"start date and age"
    )
    assert (
        W.TemplateName.match(r"{{start date and age <!--comm-->}}").group(1)
        == r"start date and age"
    )
    assert W.TemplateName.match(r"{{Start date and age|1833|7|").group(1) == r"Start date and age"


def test_bulleted_text() -> None:
    S = W.for_site(EN)
    regex_assert.no_match(W.BulletedText, r"")
    regex_assert.matches(W.BulletedText, r":foo", r":foo")
    regex_assert.matches(W.BulletedText, ":foo\r\n", ":foo\r")
    regex_assert.matches(W.BulletedText, "#foo\r\n*:bar", "#foo\r", r"*:bar")
    regex_assert.matches(W.BulletedText, "#foo\r\ntest\r\n*:bar", "#foo\r", r"*:bar")
    regex_assert.matches(W.BulletedText, " foo\r\nfoo bar", " foo\r")


def test_headings() -> None:
    S = W.for_site(EN)
    regex_assert.no_match(W.Headings, r"")
    regex_assert.is_match(W.Headings, r"=Foo=")
    regex_assert.is_match(W.Headings, r"=Foo=<!--comm-->")
    regex_assert.is_match(W.Headings, r"==Foo==")
    regex_assert.is_match(W.Headings, r"======Foo======")
    assert W.Headings.match(r"======Foo======").group(1) == r"Foo"
    assert W.Headings.match(r"== Foo == ").group(1) == r"Foo"
    regex_assert.is_match(W.Headings, r"==Foo=", r"matches unbalanced headings")
    regex_assert.is_match(W.Headings, "=='''Header with bold'''==<br/>\r\n")


def test_specific_level2_headings() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(W.ReferencesHeader, r"==References==")
    regex_assert.is_match(W.ReferencesHeader, r"== References ==")
    regex_assert.is_match(W.ReferencesHeader, r"==references==")
    regex_assert.is_match(W.NotesHeader, r"==Notes==")
    regex_assert.is_match(W.NotesHeader, r"== Notes ==")
    regex_assert.is_match(W.NotesHeader, r"==notes==")
    regex_assert.is_match(W.NotesHeader, r"== notes ==")
    regex_assert.is_match(S.ExternalLinksHeader, r"==External links==")
    regex_assert.is_match(S.ExternalLinksHeader, r"== External links ==")
    regex_assert.is_match(S.ExternalLinksHeader, r"==External link==")
    regex_assert.is_match(S.ExternalLinksHeader, r"== External link ==")
    regex_assert.is_match(S.SeeAlso, r"==See also==")
    regex_assert.is_match(S.SeeAlso, r"== See also ==")


def test_refs() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.Refs, r"<ref>foo</ref>", r"<ref>foo</ref>")
    regex_assert.matches(W.Refs, r"<ref>foo<br></ref>", r"<ref>foo<br></ref>")
    regex_assert.matches(W.Refs, r"<ref>foo<br>bar</ref>", r"<ref>foo<br>bar</ref>")
    regex_assert.is_match(
        W.Refs,
        "<ref>{{cite web\r\n|url=http://www.h.com/.php?tmi=5177|title=Season-by-season record |accessdate = 2008-12-01}}</ref>",
    )
    regex_assert.matches(W.Refs, r'<REF NAME="foo" >bar</ref >', r'<REF NAME="foo" >bar</ref >')
    regex_assert.matches(W.Refs, r"<REF  NAME=foo>bar< /ref>", r"<REF  NAME=foo>bar< /ref>")
    regex_assert.matches(W.Refs, r"<ReF Name=foo/>", r"<ReF Name=foo/>")
    regex_assert.matches(W.Refs, r"<ReF Name = 'foo'/>", r"<ReF Name = 'foo'/>")
    regex_assert.matches(W.Refs, r'<ReF Name = "foo"/>', r'<ReF Name = "foo"/>')
    regex_assert.matches(W.Refs, r"< ref>foo</ ref>", r"< ref>foo</ ref>")
    regex_assert.matches(W.Refs, r'<ref name= "foo/bar"/>', r'<ref name= "foo/bar"/>')
    regex_assert.matches(W.Refs, r'<ref name= "foo/bar">a</ref>', r'<ref name= "foo/bar">a</ref>')
    regex_assert.no_match(W.Refs, r"<refname=foo>bar</ref>")
    regex_assert.no_match(W.Refs, r"<refname=foo/>")
    regex_assert.matches(W.Refs, r"<ref group=a name=foo/>", r"<ref group=a name=foo/>")
    regex_assert.matches(W.Refs, r"<ref name=foo group=a />", r"<ref name=foo group=a />")
    regex_assert.matches(W.Refs, r"<ref>foo<!-- bar --></ref>", r"<ref>foo<!-- bar --></ref>")
    regex_assert.matches(
        W.Refs,
        r"<ref>foo<!-- bar --></ref> <ref>foo</ref>",
        r"<ref>foo<!-- bar --></ref>",
        r"<ref>foo</ref>",
    )
    check_matches(
        W.Refs, r"Article<ref>A</ref> <ref>B</ref> <ref>C</ref> <ref>B</ref> <ref>E</ref>", 5
    )
    regex_assert.matches(
        DotNetRegex(W.Refs + r"\."),
        r"Foo.<ref>bar</ref>. The next Foo.<ref>bar <br> other</ref> The next Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The nextFoo<ref>bar2</ref>. The next",
        r"<ref>bar</ref>.",
        r"<ref>bar2</ref>.",
    )


def test_unnamed_references() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(W.UnnamedReferences, r"<ref>Foo</ref>")
    regex_assert.is_match(W.UnnamedReferences, r"< ref >Foo< / ref >")
    regex_assert.is_match(W.UnnamedReferences, r"<ref> Foo </ref>")
    regex_assert.is_match(W.UnnamedReferences, "<ref>\r\nFoo\r\n</ref>")
    regex_assert.is_match(W.UnnamedReferences, r"<ref>Foo<small>bar</small>Here</ref>")
    assert W.UnnamedReferences.match(r"<ref>Foo</ref>").group(1) == r"Foo"


def test_refs_grouped() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.RefsGrouped, r"<ref group=X>foo</ref>", r"<ref group=X>foo</ref>")
    regex_assert.matches(
        W.RefsGrouped, r"<ref group=X>foo<br></ref>", r"<ref group=X>foo<br></ref>"
    )
    regex_assert.matches(
        W.RefsGrouped, r"<ref group=X>foo<br>bar</ref>", r"<ref group=X>foo<br>bar</ref>"
    )
    M1 = "<ref group=X>{{cite web\r\n|url=http://www.h.com/.php?tmi=5177|title=Season-by-season record |accessdate = 2008-12-01}}</ref>"
    regex_assert.matches(W.RefsGrouped, M1, M1)
    regex_assert.matches(
        W.RefsGrouped, r'<REF group="foo" >bar</ref >', r'<REF group="foo" >bar</ref >'
    )
    regex_assert.matches(
        W.RefsGrouped, r"<REF  group=foo>bar< /ref>", r"<REF  group=foo>bar< /ref>"
    )
    regex_assert.matches(W.RefsGrouped, r"<ReF Group=foo/>", r"<ReF Group=foo/>")
    regex_assert.matches(W.RefsGrouped, r"<ReF Group = 'foo'/>", r"<ReF Group = 'foo'/>")
    regex_assert.matches(W.RefsGrouped, r'<ReF Group = "foo"/>', r'<ReF Group = "foo"/>')
    regex_assert.matches(W.RefsGrouped, r"< ref group=X>foo</ ref>", r"< ref group=X>foo</ ref>")
    regex_assert.matches(W.RefsGrouped, r'<ref group= "foo/bar"/>', r'<ref group= "foo/bar"/>')
    regex_assert.matches(
        W.RefsGrouped, r'<ref group= "foo/bar">a</ref>', r'<ref group= "foo/bar">a</ref>'
    )
    regex_assert.matches(W.RefsGrouped, r"<ref name=A group=foo/>", r"<ref name=A group=foo/>")
    regex_assert.matches(
        W.RefsGrouped, r'<ref group="ref" name="Cannon"/>', r'<ref group="ref" name="Cannon"/>'
    )
    regex_assert.matches(
        W.RefsGrouped, r"<ref group=X name=Y>foo</ref>", r"<ref group=X name=Y>foo</ref>"
    )
    regex_assert.matches(
        W.RefsGrouped, r"<ref name=Y group=X>foo</ref>", r"<ref name=Y group=X>foo</ref>"
    )
    regex_assert.matches(
        W.RefsGrouped, r"<ref group=X>foo<!-- bar --></ref>", r"<ref group=X>foo<!-- bar --></ref>"
    )
    regex_assert.matches(
        W.RefsGrouped,
        r"<ref group=X>foo<!-- bar --></ref> <ref group=Y>foo</ref>",
        r"<ref group=X>foo<!-- bar --></ref>",
        r"<ref group=Y>foo</ref>",
    )
    regex_assert.matches(
        DotNetRegex(W.Refs + r"\."),
        r"Foo.<ref group=X>bar</ref>. The next Foo.<ref>bar <br> other</ref> The next Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The nextFoo<ref group=Y>bar2</ref>. The next",
        r"<ref group=X>bar</ref>.",
        r"<ref group=Y>bar2</ref>.",
    )
    regex_assert.no_match(W.RefsGrouped, r"<ref>foo</ref>", r"<ref>foo</ref>")
    regex_assert.no_match(W.RefsGrouped, r"<ref>foo<br></ref>", r"<ref>foo<br></ref>")
    regex_assert.no_match(W.RefsGrouped, r"<ref>foo<br>bar</ref>", r"<ref>foo<br>bar</ref>")
    regex_assert.no_match(
        W.RefsGrouped,
        "<ref>{{cite web\r\n|url=http://www.h.com/.php?tmi=5177|title=Season-by-season record |accessdate = 2008-12-01}}</ref>",
    )
    regex_assert.no_match(
        W.RefsGrouped, r'<REF NAME="foo" >bar</ref >', r'<REF NAME="foo" >bar</ref >'
    )
    regex_assert.no_match(W.RefsGrouped, r"<REF  NAME=foo>bar< /ref>", r"<REF  NAME=foo>bar< /ref>")
    regex_assert.no_match(W.RefsGrouped, r"<ReF Name=foo/>", r"<ReF Name=foo/>")
    regex_assert.no_match(W.RefsGrouped, r"<ReF Name = 'foo'/>", r"<ReF Name = 'foo'/>")
    regex_assert.no_match(W.RefsGrouped, r'<ReF Name = "foo"/>', r'<ReF Name = "foo"/>')
    regex_assert.no_match(W.RefsGrouped, r"< ref>foo</ ref>", r"< ref>foo</ ref>")
    regex_assert.no_match(W.RefsGrouped, r'<ref name= "foo/bar"/>', r'<ref name= "foo/bar"/>')
    regex_assert.no_match(
        W.RefsGrouped, r'<ref name= "foo/bar">a</ref>', r'<ref name= "foo/bar">a</ref>'
    )
    regex_assert.no_match(W.RefsGrouped, r"<refname=foo>bar</ref>")
    regex_assert.no_match(W.RefsGrouped, r"<refname=foo/>")
    regex_assert.matches(W.RefsGrouped, r"<ref group=a name=foo/>", r"<ref group=a name=foo/>")
    regex_assert.matches(W.RefsGrouped, r"<ref name=foo group=a />", r"<ref name=foo group=a />")
    regex_assert.no_match(
        W.RefsGrouped, r"<ref>foo<!-- bar --></ref>", r"<ref>foo<!-- bar --></ref>"
    )
    regex_assert.no_match(W.RefsGrouped, r"<ref>foo<!-- bar --></ref> <ref>foo</ref>")
    regex_assert.matches(
        DotNetRegex(W.RefsGrouped + r"\."),
        r"Foo.<ref group=X>bar</ref>. The next Foo.<ref group=X>bar <br> other</ref> The next Foo.<ref group=X>bar</ref> The next Foo.<ref group=X>bar</ref> The nextFoo<ref group=X>bar2</ref>. The next",
        r"<ref group=X>bar</ref>.",
        r"<ref group=X>bar2</ref>.",
    )


def test_small() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.Small, r"<small>foo</small>", r"<small>foo</small>")
    assert W.Small.match(r"<small>foo</small>").group(1) == r"foo"
    regex_assert.matches(W.Small, r"<small  >foo</small >", r"<small  >foo</small >")
    regex_assert.matches(W.Small, "<small>\r\nfoo\r\n</small>", "<small>\r\nfoo\r\n</small>")
    regex_assert.matches(W.Small, r"<SMALL>foo</SMALL>", r"<SMALL>foo</SMALL>")
    regex_assert.matches(
        W.Small, r"<small>a<small>foo</small>b</small>", r"<small>a<small>foo</small>b</small>"
    )
    regex_assert.matches(W.Small, r"<small>..<small>...</small>", r"<small>...</small>")
    regex_assert.matches(W.Small, r"<small>foo<br>bar</small>", r"<small>foo<br>bar</small>")


def test_big() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.Big, r"<big>foo</big>", r"<big>foo</big>")
    regex_assert.matches(W.Big, r"<big  >foo</big >", r"<big  >foo</big >")
    regex_assert.matches(W.Big, "<big>\r\nfoo\r\n</big>", "<big>\r\nfoo\r\n</big>")
    regex_assert.matches(W.Big, r"<big>foo</big>", r"<big>foo</big>")
    regex_assert.matches(W.Big, r"<big>a<big>foo</big>b</big>", r"<big>a<big>foo</big>b</big>")
    regex_assert.matches(W.Big, r"<big>..<big>...</big>", r"<big>...</big>")


def test_nowiki() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.Nowiki, r"<nowiki>foo</nowiki>", r"<nowiki>foo</nowiki>")
    regex_assert.matches(W.Nowiki, r"<nowiki >foo</nowiki >", r"<nowiki >foo</nowiki >")


def test_external_link() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.ExternalLinks, r"http://google.co.uk", r"http://google.co.uk")
    regex_assert.matches(W.ExternalLinks, r"http://google-here.co.uk", r"http://google-here.co.uk")
    regex_assert.matches(W.ExternalLinks, r"https://google.co.uk", r"https://google.co.uk")
    regex_assert.matches(
        W.ExternalLinks, r"http://foo.com/asdfasdf/asdf.htm", r"http://foo.com/asdfasdf/asdf.htm"
    )
    regex_assert.matches(W.ExternalLinks, r"http://www.google.co.uk", r"http://www.google.co.uk")
    regex_assert.matches(W.ExternalLinks, r"//google.co.uk", r"//google.co.uk")
    regex_assert.matches(
        W.ExternalLinks, r"http://foo.com/asdfasdf/asdf.htm", r"http://foo.com/asdfasdf/asdf.htm"
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"https://www.foo.com/asdfasdf/asdf.htm",
        r"https://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"ftp://www.foo.com/asdfasdf/asdf.htm",
        r"ftp://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"mailto://www.foo.com/asdfasdf/asdf.htm",
        r"mailto://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"irc://www.foo.com/asdfasdf/asdf.htm",
        r"irc://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"gopher://www.foo.com/asdfasdf/asdf.htm",
        r"gopher://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"telnet://www.foo.com/asdfasdf/asdf.htm",
        r"telnet://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"nntp://www.foo.com/asdfasdf/asdf.htm",
        r"nntp://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"worldwind://www.foo.com/asdfasdf/asdf.htm",
        r"worldwind://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"news://www.foo.com/asdfasdf/asdf.htm",
        r"news://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"svn://www.foo.com/asdfasdf/asdf.htm",
        r"svn://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinks, r"lol http://www.google.co.uk lol", r"http://www.google.co.uk"
    )
    regex_assert.matches(
        W.ExternalLinks, r"[http://www.google.co.uk]", r"[http://www.google.co.uk]"
    )
    regex_assert.matches(
        W.ExternalLinks, r"[http://www.google.co.uk google]", r"[http://www.google.co.uk google]"
    )
    regex_assert.matches(
        W.ExternalLinks, r"lol [http://www.google.co.uk] lol", r"[http://www.google.co.uk]"
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"lol [http://www.google.co.uk google] lol",
        r"[http://www.google.co.uk google]",
    )
    regex_assert.matches(
        W.ExternalLinks, r"http://www.google.co.uk google}}", r"http://www.google.co.uk"
    )
    regex_assert.matches(W.ExternalLinks, r"http://www.google.co.uk}}", r"http://www.google.co.uk")
    regex_assert.matches(
        W.ExternalLinks, r"date=April 2010|url=http://w/010111a.html}}", r"http://w/010111a.html"
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"date=April 2010|url=http://w/010111a.html|location=London}}",
        r"http://w/010111a.html",
    )
    regex_assert.matches(
        W.ExternalLinks,
        r"date=April 2010|url=https://w/010111a.html|location=London}}",
        r"https://w/010111a.html",
    )
    regex_assert.matches(
        W.ExternalLinks, r"lol [http://www.google.co.uk lol", r"http://www.google.co.uk"
    )
    regex_assert.no_match(W.ExternalLinks, r"Google")
    assert W.ExternalLinks.match(r"http://google.co.uk").group(1) == r"http"
    assert W.ExternalLinks.match(r"https://google.co.uk").group(1) == r"https"
    assert W.ExternalLinks.match(r"svn://google.co.uk Google}}").group(1) == r"svn"
    assert W.ExternalLinks.match(r"Http://google.co.uk").group(1) == r"Http"
    assert W.ExternalLinks.match(r"HTTP://google.co.uk").group(1) == r"HTTP"
    assert len(W.ExternalLinks.match(r"[http://google.co.uk Google]").group(1)) == 0


def test_non_httpprotocols() -> None:
    S = W.for_site(EN)
    regex_assert.no_match(W.NonHTTPProtocols, r"http://foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.NonHTTPProtocols, r"https://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"ftp://www.foo.com/asdfasdf/asdf.htm",
        r"ftp://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"mailto://www.foo.com/asdfasdf/asdf.htm",
        r"mailto://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"irc://www.foo.com/asdfasdf/asdf.htm",
        r"irc://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"gopher://www.foo.com/asdfasdf/asdf.htm",
        r"gopher://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"telnet://www.foo.com/asdfasdf/asdf.htm",
        r"telnet://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"nntp://www.foo.com/asdfasdf/asdf.htm",
        r"nntp://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"worldwind://www.foo.com/asdfasdf/asdf.htm",
        r"worldwind://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"news://www.foo.com/asdfasdf/asdf.htm",
        r"news://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"svn://www.foo.com/asdfasdf/asdf.htm",
        r"svn://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.is_match(
        W.NonHTTPProtocols,
        r"SVN://www.foo.com/asdfasdf/asdf.htm",
        r"SVN://www.foo.com/asdfasdf/asdf.htm",
    )


def test_external_links_httponly() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.ExternalLinksHTTPOnly, r"http://google.co.uk", r"http://google.co.uk")
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"http://google-here.co.uk", r"http://google-here.co.uk"
    )
    regex_assert.matches(W.ExternalLinksHTTPOnly, r"https://google.co.uk", r"https://google.co.uk")
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"http://foo.com/asdfasdf/asdf.htm",
        r"http://foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"http://www.google.co.uk", r"http://www.google.co.uk"
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"http://foo.com/asdfasdf/asdf.htm",
        r"http://foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"https://www.foo.com/asdfasdf/asdf.htm",
        r"https://www.foo.com/asdfasdf/asdf.htm",
    )
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"ftp://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"mailto://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"irc://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"gopher://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"telnet://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"nntp://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"worldwind://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"news://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"svn://www.foo.com/asdfasdf/asdf.htm")
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"lol http://www.google.co.uk lol", r"http://www.google.co.uk"
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"[http://www.google.co.uk]", r"[http://www.google.co.uk]"
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"[http://www.google.co.uk google]",
        r"[http://www.google.co.uk google]",
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"lol [http://www.google.co.uk] lol", r"[http://www.google.co.uk]"
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"lol [http://www.google.co.uk google] lol",
        r"[http://www.google.co.uk google]",
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"http://www.google.co.uk google}}", r"http://www.google.co.uk"
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"http://www.google.co.uk}}", r"http://www.google.co.uk"
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"date=April 2010|url=http://w/010111a.html}}",
        r"http://w/010111a.html",
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly,
        r"date=April 2010|url=http://w/010111a.html|location=London}}",
        r"http://w/010111a.html",
    )
    regex_assert.matches(
        W.ExternalLinksHTTPOnly, r"lol [http://www.google.co.uk lol", r"http://www.google.co.uk"
    )
    regex_assert.no_match(W.ExternalLinksHTTPOnly, r"Google")
    assert W.ExternalLinksHTTPOnly.match(r"http://google.co.uk").group(1) == r"http"
    assert W.ExternalLinksHTTPOnly.match(r"Http://google.co.uk").group(1) == r"Http"
    assert W.ExternalLinksHTTPOnly.match(r"HTTP://google.co.uk").group(1) == r"HTTP"
    assert len(W.ExternalLinksHTTPOnly.match(r"[http://google.co.uk Google]").group(1)) == 0


def test_possible_interwikis() -> None:
    S = W.for_site(EN)
    regex_assert.matches(W.PossibleInterwikis, r"foo[[en:bar]]", r"[[en:bar]]")
    regex_assert.matches(W.PossibleInterwikis, r"[[en:bar]][[ru:", r"[[en:bar]]")
    regex_assert.matches(
        W.PossibleInterwikis,
        r"foo[[en:bar:quux]][[ru:boz test]]",
        r"[[en:bar:quux]]",
        r"[[ru:boz test]]",
    )
    regex_assert.matches(W.PossibleInterwikis, r"foo[[en::bar]]", r"[[en::bar]]")
    regex_assert.no_match(W.PossibleInterwikis, r"[[:en:foo]]")
    regex_assert.no_match(W.PossibleInterwikis, r"[[:ru:foo]]")
    regex_assert.no_match(W.PossibleInterwikis, r"[[:foo]]")
    regex_assert.no_match(W.PossibleInterwikis, r"[[File:foo]]")
    regex_assert.no_match(W.PossibleInterwikis, r"[[MOS:foo]]")
    assert W.PossibleInterwikis.match(r"[[ en :bar]]").group(1) == r"en"
    assert W.PossibleInterwikis.match(r"[[en: bar ]]").group(2) == r"bar"
    assert W.PossibleInterwikis.match(r"[[en: bar ]] <!--comm-->").group(3) == r" <!--comm-->"
    regex_assert.no_match(W.PossibleInterwikis, r"[[e:foo]]")
    regex_assert.no_match(W.PossibleInterwikis, "[[Something:\r\n[[other]]\r\n]]")
    regex_assert.no_match(W.PossibleInterwikis, r"[[abcdefghijlkmnop:foo]]")
    regex_assert.matches(
        W.PossibleInterwikis, r"foo[[en:bar]] <!--comm-->", r"[[en:bar]] <!--comm-->"
    )


def test_untemplated_quotes() -> None:
    S = W.for_site(EN)
    assert r'"very fast"' not in W.UntemplatedQuotes.replace(r' "very fast" ', r"1")
    assert r'"very fast"' not in W.UntemplatedQuotes.replace(r'"very fast" ', r"1")
    assert r"« very fast »" not in W.UntemplatedQuotes.replace(r" « very fast » ", r"1")
    assert r"‘very fast‘" not in W.UntemplatedQuotes.replace(r" ‘very fast‘ ", r"1")
    assert r"’ very fast ’" not in W.UntemplatedQuotes.replace(r" ’ very fast ’ ", r"")
    assert r"“ very fast “" not in W.UntemplatedQuotes.replace(r" “ very fast “ ", r"")
    assert r"” very fast ”" not in W.UntemplatedQuotes.replace(r" ” very fast ” ", r"")
    assert r"‛ very fast ‛" not in W.UntemplatedQuotes.replace(r" ‛ very fast ‛ ", r"")
    assert r"‟ very fast‟" not in W.UntemplatedQuotes.replace(r" ‟ very fast‟ ", r" ")
    assert r"‹ very fast ›" not in W.UntemplatedQuotes.replace(r" ‹ very fast › ", r"")
    assert r"“ very fast ”" not in W.UntemplatedQuotes.replace(r" “ very fast ” ", r"")
    assert r"„ very fast „" not in W.UntemplatedQuotes.replace(r" „ very fast „ ", r"")
    assert r"„ very fast „" not in W.UntemplatedQuotes.replace(r" „ very fast „ ", r"")
    assert r"‘ very fast ‘" not in W.UntemplatedQuotes.replace(r" ‘ very fast ‘ ", r"")
    assert r"’ very fast ’" not in W.UntemplatedQuotes.replace(r" ’ very fast ’ ", r"")
    assert r"“ very fast ”" not in W.UntemplatedQuotes.replace(r" “ very fast ” ", r"")
    assert r"` very fast `" not in W.UntemplatedQuotes.replace(r" ` very fast ` ", r"")
    assert r"’ very fast ‘" not in W.UntemplatedQuotes.replace(r" ’ very fast ‘ ", r"")
    assert " „very\r\nfast„ " not in W.UntemplatedQuotes.replace(" „very\r\nfast„ ", r"")
    assert r"but not pretty" in W.UntemplatedQuotes.replace(r" “ very fast ” but not pretty ", r"")
    assert r"but not pretty“" in W.UntemplatedQuotes.replace(
        r" “ very fast ” but not pretty“ ", r""
    )
    assert r" and " in W.UntemplatedQuotes.replace(r" “ very fast ” and “ very well ” ", r"")
    assert r"not pretty but " in W.UntemplatedQuotes.replace(r"not pretty but “ very fast ” ", r"")
    assert r"very fast" in W.UntemplatedQuotes.replace(r" very fast ", r"")
    assert r"'very fast'" in W.UntemplatedQuotes.replace(r" 'very fast' ", r"")
    assert r"''very fast''" in W.UntemplatedQuotes.replace(r" ''very fast'' ", r"")
    assert r"''very fast''" in W.UntemplatedQuotes.replace(r" ''very fast'' ", r"")
    assert r",very fast," in W.UntemplatedQuotes.replace(r" ,very fast, ", r"")
    assert r"Now it’s a shame as it’s a" in W.UntemplatedQuotes.replace(
        r"Now it’s a shame as it’s a", r""
    )


def test_curly_double_quotes() -> None:
    S = W.for_site(EN)
    assert W.CurlyDoubleQuotes.is_match(r" ‟very fast‟")
    assert not (W.CurlyDoubleQuotes.is_match(r"very fast „"))


def test_rfrom_modification() -> None:
    S = W.for_site(EN)
    assert tools.nested_template_regex(W.RFromModificationList, S.site).is_match(
        r"{{R from modification}}"
    )
    assert tools.nested_template_regex(W.RFromModificationList, S.site).is_match(
        r"{{ r from modification}}"
    )
    assert tools.nested_template_regex(W.RFromModificationList, S.site).is_match(r"{{R mod }}")
    assert tools.nested_template_regex(W.RFromModificationList, S.site).is_match(
        r"{{R from alternate punctuation}}"
    )
    assert tools.nested_template_regex(W.RFromModificationList, S.site).is_match(
        r"{{R from alternative punctuation}}"
    )


def test_rfrom_title_without_diacritics() -> None:
    S = W.for_site(EN)
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R to accents}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{Redirects from title without diacritics}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{RDiacr}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{r to unicode name}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{ R to unicode}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R to unicode  }}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R to title with diacritics}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R to diacritics}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R to diacritic}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R from name without diacritics}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R from title without diacritics}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R from original name without diacritics}}"
    )
    assert tools.nested_template_regex(W.RFromTitleWithoutDiacriticsList, S.site).is_match(
        r"{{R without diacritics}}"
    )


def test_more_no_footnotes_tests() -> None:
    S = W.for_site(EN)
    assert W.MoreNoFootnotes.is_match(r"{{morefootnotes}}")
    assert W.MoreNoFootnotes.is_match(r"{{Morefootnotes}}")
    assert W.MoreNoFootnotes.is_match(r"{{More footnotes}}")
    assert W.MoreNoFootnotes.is_match(r"{{Nofootnotes}}")
    assert W.MoreNoFootnotes.is_match(r"{{No footnotes}}")
    assert W.MoreNoFootnotes.is_match(r"{{nofootnotes}}")
    assert W.MoreNoFootnotes.is_match(r"{{nofootnotes|section}}")
    assert not (W.MoreNoFootnotes.is_match(r"{{NOFOOTNOTES}}"))


def test_references_template_tests() -> None:
    S = W.for_site(EN)
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{reflist}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{reflist|2}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{Reflist}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{ref-list}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{Reflink}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{reflink}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{References}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{references}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> <references/>")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> <references />")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> <references responsive/>")
    assert W.ReferencesTemplate.is_match(r'Hello<ref>Fred</ref> <references responsive="0"/>')
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> <References />")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{Listaref|2}}")
    assert W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref> {{ listaref | 2}}")
    assert W.ReferencesTemplate.is_match("<references>\r\n<ref name =Fred>Fred</ref> </references>")
    assert W.ReferencesTemplate.is_match(
        "<  references >\r\n<ref name =Fred>Fred</ref> </  references  >"
    )
    assert not (W.ReferencesTemplate.is_match(r"Hello<ref>Fred</ref>"))
    assert not (W.ReferencesTemplate.is_match(r'Hello<ref name="F">Fred</ref>'))
    assert not (W.ReferencesTemplate.is_match(r"Hello world"))
    assert W.ReferencesTemplate.is_match(
        "{{Reflist|refs=\r\n<ref name=modern>{{cite news |first=William }}\r\n        }}"
    )


def test_cite_template() -> None:
    S = W.for_site(EN)
    assert W.CiteTemplate.is_match(r"{{cite web|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite web}}")
    assert W.CiteTemplate.is_match(r"{{ cite web|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{Cite web|url=a|title=b and {{foo}} there}}")
    assert W.CiteTemplate.is_match(r"{{cite news|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite book|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite conference|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite manual|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite paper|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite press release|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite encyclopedia|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite AV media|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{vcite2 journal}}")
    assert W.CiteTemplate.is_match(r"{{cite magazine|url=a|title=b}}")
    assert W.CiteTemplate.is_match(r"{{cite report|url=a|title=b}}")
    assert W.CiteTemplate.match(r"{{cite web|url=a|title=b}}").group(2) == r"cite web"
    assert W.CiteTemplate.match(r"{{ cite web |url=a|title=b}}").group(2) == r"cite web"
    assert W.CiteTemplate.match("{{Cite web\r\n|url=a|title=b}}").group(2) == r"Cite web"
    assert (
        W.CiteTemplate.match(r"{{cite press release|url=a|title=b}}").group(2)
        == r"cite press release"
    )


def test_ref_after_reflist() -> None:
    S = W.for_site(EN)
    assert W.RefAfterReflist.is_match(r"blah <ref>a</ref> ==references== {{reflist}} <ref>b</ref>")
    assert W.RefAfterReflist.is_match(
        r"blah <ref>a</ref> ==references== <references/> <ref>b</ref>"
    )
    assert W.RefAfterReflist.is_match(r"blah <ref>a</ref> ==references== {{Reflist}} <ref>b</ref>")
    assert W.RefAfterReflist.is_match(r"blah <ref>a</ref> ==references== {{reflink}} <ref>b</ref>")
    assert W.RefAfterReflist.is_match(r"blah <ref>a</ref> ==references== {{ref-list}} <ref>b</ref>")
    assert W.RefAfterReflist.is_match(
        "blah <ref>a</ref>\r\n==references== {{reflist}} <ref>b</ref>"
    )
    assert W.RefAfterReflist.is_match(
        "blah <ref>a</ref> ==references== {{reflist}} blah\r\n<ref>b</ref>"
    )
    assert W.RefAfterReflist.is_match(
        r'blah <ref>a</ref> ==references== {{reflist}} <ref name="b">b</ref>'
    )
    assert not (W.RefAfterReflist.is_match(r"blah <ref>a</ref> ==references== {{reflist}}"))
    bug1 = "\r\n==References==\r\n<references />\r\n\r\n{{Northampton County, Pennsylvania}}\r\n\r\n[[Category:Boroughs in Pennsylvania]]\r\n[[Category:Northampton County, Pennsylvania]]\r\n[[Category:Settlements established in 1790]]\r\n\r\n[[ht:Tatamy, Pennsilvani]]\r\n[[nl:Tatamy]]\r\n[[pt:Tatamy]]\r\n[[vo:Tatamy]]"
    assert not (W.RefAfterReflist.is_match(bug1))


def test_ibid_op_citation() -> None:
    S = W.for_site(EN)
    assert W.IbidLocCitation.is_match(r"ibid")
    assert W.IbidLocCitation.is_match(r"Ibid")
    assert W.IbidLocCitation.is_match(r"IBID")
    assert W.IbidLocCitation.is_match(r"loc cit")
    assert W.IbidLocCitation.is_match(r"loc.cit")
    assert W.IbidLocCitation.is_match(r"Loc. cit")
    assert W.IbidLocCitation.is_match("Loc\r\ncit")
    assert not (W.IbidLocCitation.is_match(r"Libid was"))
    assert not (W.IbidLocCitation.is_match(r"The loc was later cit"))


def test_ibid() -> None:
    S = W.for_site(EN)
    assert W.Ibid.is_match(r"{{ibid}}")
    assert W.Ibid.is_match(r"{{ Ibid }}")
    assert W.Ibid.is_match(r"{{ibid|date=May 2009}}")
    assert W.Ibid.is_match(r"{{ibid | date=May 2009}}")
    assert W.Ibid.is_match(r"{{Ibid|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}")
    assert W.Ibid.is_match(r"{{ibid|date=May 2009|foo=bar}}")
    assert W.Ibid.is_match(r"{{ibid|}}")
    assert not (W.Ibid.is_match(r"Libid was"))
    assert not (W.Ibid.is_match(r"{{IBID}}"))
    assert not (W.Ibid.is_match(r"{{Ibidate}}"))


def test_dablinks_tests() -> None:
    S = W.for_site(EN)
    assert W.Dablinks.is_match(r"{{For|Fred the dancer|Fred (dancer)}}")
    assert W.Dablinks.is_match(r"{{for|Fred the dancer|Fred (dancer)}}")
    assert W.Dablinks.is_match(r"{{other people|Fred the dancer|Fred Smith (dancer)}}")
    assert W.Dablinks.is_match(r"{{For|Fred the dancer|Fred Smith (dancer)}}")
    assert W.Dablinks.is_match(r"{{redirect2|Fred the dancer|Fred Smith (dancer)}}")
    assert W.Dablinks.is_match("{{For\r\n    |Fred the dancer\r\n    |Fred (dancer)}}")
    assert W.Dablinks.is_match("{{For|\r\n    Fred the dancer|\r\n    Fred (dancer)}}")
    assert W.Dablinks.is_match(r"{{other uses|something}}")
    assert W.Dablinks.is_match(r"{{other uses}}")
    assert W.Dablinks.is_match(r"{{self-reference|something}}")
    assert W.Dablinks.is_match(r"{{Redirect-distinguish|something}}")
    assert W.Dablinks.is_match(r"{{Redirect-distinguish-text|something}}")
    assert W.Dablinks.is_match(r"{{About-distinguish}}"), r"{{About-distinguish}}"
    assert W.Dablinks.is_match(r"{{about}}"), r"{{about}}"
    assert W.Dablinks.is_match(r"{{distinguish}}"), r"{{distinguish}}"
    assert W.Dablinks.is_match(r"{{for}}"), r"{{for}}"
    assert W.Dablinks.is_match(r"{{for-multi}}"), r"{{for-multi}}"
    assert W.Dablinks.is_match(r"{{further}}"), r"{{further}}"
    assert W.Dablinks.is_match(r"{{hatnote}}"), r"{{hatnote}}"
    assert W.Dablinks.is_match(r"{{other people}}"), r"{{other people}}"
    assert W.Dablinks.is_match(r"{{other places}}"), r"{{other places}}"
    assert W.Dablinks.is_match(r"{{Other Pennsylvania townships}}"), (
        r"{{Other Pennsylvania townships}}"
    )
    assert W.Dablinks.is_match(r"{{other ships}}"), r"{{other ships}}"
    assert W.Dablinks.is_match(r"{{other uses of}}"), r"{{other uses of}}"
    assert W.Dablinks.is_match(r"{{other uses}}"), r"{{other uses}}"
    assert W.Dablinks.is_match(r"{{redirect-distinguish}}"), r"{{redirect-distinguish}}"
    assert W.Dablinks.is_match(r"{{redirect-several}}"), r"{{redirect-several}}"
    assert W.Dablinks.is_match(r"{{redirect-multi}}"), r"{{redirect-multi}}"
    assert W.Dablinks.is_match(r"{{redirect-synonym}}"), r"{{redirect-synonym}}"
    assert W.Dablinks.is_match(r"{{redirect2}}"), r"{{redirect2}}"
    assert W.Dablinks.is_match(r"{{redirect}}"), r"{{redirect}}"
    assert W.Dablinks.is_match(r"{{see also}}"), r"{{see also}}"
    assert W.Dablinks.is_match(r"{{self-reference}}"), r"{{self-reference}}"
    assert W.Dablinks.is_match(r"{{Similar names}}"), r"{{Similar names}}"
    assert W.Dablinks.is_match(r"{{Technical reasons}}"), r"{{Technical reasons}}"
    assert W.Dablinks.is_match(r"{{Confused journal}}"), r"{{Confused journal}}"
    assert not (W.Dablinks.is_match(r"{{For fake template|Fred the dancer|Fred(dancer)}}"))
    assert not (W.Dablinks.is_match(r"{{REDIRECT2|Fred the dancer|Fred Smith (dancer)}}"))
    assert not (W.Dablinks.is_match(r"{{Otheruse2|something}}"))


def test_sister_links_tests() -> None:
    S = W.for_site(EN)
    assert W.SisterLinks.is_match(r"{{wiktionary}}")
    assert W.SisterLinks.is_match(r"{{ wiktionary }}")
    assert W.SisterLinks.is_match(r"{{sisterlinks}}")
    assert W.SisterLinks.is_match(r"{{sister links}}")
    assert W.SisterLinks.is_match(r"{{sister project links}}")
    assert W.SisterLinks.is_match(r"{{wikibooks}}")
    assert W.SisterLinks.is_match(r"{{wikimedia}}")
    assert W.SisterLinks.is_match(r"{{wikiversity}}")


def test_unreferenced() -> None:
    S = W.for_site(EN)
    assert W.Unreferenced.is_match(r"{{unreferenced}}")
    assert W.Unreferenced.is_match(r"{{  Unreferenced}}")
    assert W.Unreferenced.is_match(r"{{unreferenced  }}")
    assert W.Unreferenced.is_match(r"{{unreferenced|date=May 2009}}")
    assert W.Unreferenced.is_match(r"{{unreferenced stub|date=May 2009}}")
    assert not (W.Unreferenced.is_match(r"{{unreferenced-stub}}"))


def test_portal_template_tests() -> None:
    S = W.for_site(EN)
    assert W.PortalTemplate.is_match(r"{{portal}}")
    assert W.PortalTemplate.is_match(r"{{portal|Foo}}")
    assert W.PortalTemplate.is_match(r"{{ portal}}")
    assert W.PortalTemplate.is_match(r"{{Portal}}")
    assert W.PortalTemplate.is_match(r"{{portal|Science}}")
    assert W.PortalTemplate.is_match(r"{{portal|Spaceflight|RocketSunIcon.svg|break=yes}}")
    assert not (W.PortalTemplate.is_match(r"{{PORTAL}}"))
    assert not (W.PortalTemplate.is_match(r"{{portalos}}"))
    assert not (W.PortalTemplate.is_match(r"{{portalparity}}"))
    assert not (W.PortalTemplate.is_match(r"{{Spanish portal|game}}"))


def test_infobox_tests() -> None:
    S = W.for_site(EN)
    check_match(W.InfoBox, r" {{Infobox hello| bye}} ", r"{{Infobox hello| bye}}", r"Infobox hello")
    check_match(
        W.InfoBox, r" {{ Infobox hello | bye}} ", r"{{ Infobox hello | bye}}", r"Infobox hello"
    )
    check_match(W.InfoBox, r" {{infobox hello| bye}} ", r"{{infobox hello| bye}}", r"infobox hello")
    check_match(
        W.InfoBox,
        r" {{Infobox hello| bye {{a}} was}} ",
        r"{{Infobox hello| bye {{a}} was}}",
        r"Infobox hello",
    )
    check_match(
        W.InfoBox,
        r" {{hello Infobox| bye {{a}} was}} ",
        r"{{hello Infobox| bye {{a}} was}}",
        r"hello Infobox",
    )
    check_match(
        W.InfoBox,
        r" {{hello_Infobox| bye {{a}} was}} ",
        r"{{hello_Infobox| bye {{a}} was}}",
        r"hello_Infobox",
    )
    assert W.InfoBox.is_match(r" {{infobox hello| bye}} ")
    assert W.InfoBox.is_match(r" {{Template:infobox hello| bye}} ")
    assert W.InfoBox.is_match(" {{infobox hello\r\n| bye}} ")
    assert W.InfoBox.is_match(r" {{Infobox_play| bye}} ")
    assert W.InfoBox.is_match(r" {{some infobox| hello| bye}} ")
    assert W.InfoBox.is_match(r" {{Some Infobox| hello| bye}} ")
    assert W.InfoBox.match(" {{Infobox\r\n| hello| bye}} ").group(1) == r"Infobox"
    assert W.InfoBox.is_match(r" {{Chembox|field=value}} ")
    assert W.InfoBox.is_match(r" {{Chembox Properties|field=value}} ")
    assert W.InfoBox.is_match(r" {{Chembox Structure|field=value}} ")
    assert not (W.InfoBox.is_match(r" {{Cleanup infobox|date=November 2020}} "))
    assert not (W.InfoBox.is_match(r" {{cleanup-infobox|date=November 2020}} "))
    assert not (W.InfoBox.is_match(r" {{Incomplete infobox|date=November 2020}} "))


def test_display_lower_case_italic_title_tests() -> None:
    S = W.for_site(EN)
    assert W.DisplayLowerCaseItalicTitle.is_match(r"{{DISPLAYTITLE:foo}}"), r"DISPLAYTITLE"
    assert W.DisplayLowerCaseItalicTitle.is_match(r"{{Display title:foo}}"), r"Display title"
    assert W.DisplayLowerCaseItalicTitle.is_match(r"{{Displaytitle:foo}}"), r"Displaytitle"
    assert W.DisplayLowerCaseItalicTitle.is_match(r"{{italic title}}"), r"italic title"
    assert W.DisplayLowerCaseItalicTitle.is_match(r"{{lowercase title}}"), r"lowercase title"


def test_template_end_tests() -> None:
    S = W.for_site(EN)
    assert W.TemplateEnd.match(r"{{foo}}").value == r"}}"
    assert W.TemplateEnd.match(r"{{foo }}").value == r" }}"
    assert W.TemplateEnd.match("{{foo\r\n}}").value == "\r\n}}"
    assert W.TemplateEnd.match("{{foo\r\n}}").group(1) == "\r\n"
    assert W.TemplateEnd.match("{{foo\r\n }}").value == "\r\n }}"


def test_pstyles_tests() -> None:
    S = W.for_site(EN)
    assert W.Pstyles.is_match(
        r'<p style="margin:0px;font-size:100%"><span style="color:#00ff00">▪</span> <small>Francophone minorities</small></p>'
    )
    assert W.Pstyles.is_match(r'<p style="font-family:monospace; line-height:130%">hello</p>')
    assert W.Pstyles.is_match(r'<p style="font-family:monospace; line-height:130%">hello</P>')
    assert W.Pstyles.is_match(r'<p style="font-family:monospace; line-height:130%">hello</P>')
    assert W.Pstyles.is_match('<p style = "font-family:monospace; line-height:130%">\r\nhello</P>')


def test_first_section() -> None:
    S = W.for_site(EN)
    assert W.ZerothSection.is_match(r"article")
    assert W.ZerothSection.is_match(r"article ==heading==")
    assert W.ZerothSection.is_match(r"article ===heading===")
    assert W.ZerothSection.replace(r"article ==heading==", r"") == r"==heading=="
    assert (
        W.ZerothSection.replace(
            "{{wikify}}\r\n{{Infobox hello | bye=yes}}\r\narticle words, '''bold''' blah.\r\n==heading== words ==another heading==",
            r"",
        )
        == r"==heading== words ==another heading=="
    )
    assert not (W.ZerothSection.is_match(r""))


def test_heading_level_two_tests() -> None:
    S = W.for_site(EN)
    assert W.HeadingLevelTwo.is_match("article\r\n==heading==\r\na")
    assert W.HeadingLevelTwo.match("article\r\n==heading==\r\na").group(1) == r"heading"
    assert W.HeadingLevelTwo.is_match("article\r\n== heading ==\r\na")
    assert W.HeadingLevelTwo.match("article\r\n== heading ==\r\na").group(1) == r" heading "
    assert W.HeadingLevelTwo.is_match("article\r\n== heading ==\r\nwords")
    assert W.HeadingLevelTwo.is_match("article\r\n==H==\r\na")
    assert W.HeadingLevelTwo.is_match("article\r\n==Hi==\r\na")
    assert W.HeadingLevelTwo.is_match("article\r\n==Here and=there==\r\na")
    assert not (W.HeadingLevelTwo.is_match("article ==\r\nheading=="))
    assert not (W.HeadingLevelTwo.is_match("article\r\n==heading== words"))
    assert not (W.HeadingLevelTwo.is_match(r"article ===heading=="))
    assert not (W.HeadingLevelTwo.is_match("article\r\n====heading===\r\nwords"))


def test_heading_level_three_tests() -> None:
    S = W.for_site(EN)
    assert W.HeadingLevelThree.is_match("article\r\n===heading===\r\na")
    assert W.HeadingLevelThree.match("article\r\n===heading===\r\na").group(1) == r"heading"
    assert W.HeadingLevelThree.is_match("article\r\n=== heading ===\r\na")
    assert W.HeadingLevelThree.match("article\r\n=== heading ===\r\na").group(1) == r" heading "
    assert W.HeadingLevelThree.is_match("article\r\n=== heading ===\r\nwords")
    assert W.HeadingLevelThree.is_match("article\r\n===H===\r\na")
    assert W.HeadingLevelThree.is_match("article\r\n===Hi===\r\na")
    assert W.HeadingLevelThree.is_match("article\r\n===Here and=there===\r\na")
    assert not (W.HeadingLevelThree.is_match("article ===\r\nheading==="))
    assert not (W.HeadingLevelThree.is_match("article\r\n===heading=== words"))
    assert not (W.HeadingLevelThree.is_match(r"article ====heading==="))
    assert not (W.HeadingLevelThree.is_match("article\r\n=====heading====\r\nwords"))


def test_section_level_two_tests() -> None:
    S = W.for_site(EN)
    assert W.SectionLevelTwo.is_match(
        "== heading a ==\r\nwords\r\n=== subsection ===\r\nwords\r\nwords2\r\n== heading b ==\r\n"
    )
    assert not (W.SectionLevelTwo.is_match("=== subsection ===\r\nwords\r\nwords2"))
    assert not (
        W.SectionLevelTwo.is_match(
            "=== heading a ==\r\nwords\r\n=== subsection ===\r\nwords\r\nwords2"
        )
    )
    assert not (
        W.SectionLevelTwo.is_match(
            "= heading a =\r\nwords\r\n=== subsection ===\r\nwords\r\nwords2"
        )
    )


def test_article_to_first_level_two_heading_tests() -> None:
    S = W.for_site(EN)
    assert W.ArticleToFirstLevelTwoHeading.is_match("words\r\n== heading a ==\r\n")
    assert not (W.ArticleToFirstLevelTwoHeading.is_match("words\r\n=== heading a ===\r\n"))


def test_multiple_issues_tests() -> None:
    S = W.for_site(EN)
    assert W.MultipleIssues.is_match(r"{{Multiple issues|wikify=May 2008|a=b|c=d}}"), r"with space"
    assert W.MultipleIssues.is_match(r"{{Multipleissues|wikify=May 2008|a=b|c=d}}"), r"unspaced"
    assert W.MultipleIssues.is_match(r"{{multipleissues|wikify=May 2008|a=b|c=d}}"), (
        r"unspaced no capitals"
    )
    assert W.MultipleIssues.is_match(r"{{Multiple issues | wikify=May 2008|a=b|c=d}}"), (
        r"with spaces in parameters"
    )
    assert W.MultipleIssues.is_match(
        "{{Multiple issues\r\n           | wikify=May 2008|a=b|c=d}}"
    ), r"with break lines"
    assert W.MultipleIssues.is_match(r"{{Multiple issues|}}"), r"empty"
    assert W.MultipleIssues.is_match(r"{{Multipleissues}}"), r"empty too"
    assert W.MultipleIssues.is_match(r"{{ multiple issues|wikify=May 2008|a=b|c=d}}")
    assert W.MultipleIssues.is_match(
        r"{{ multiple issues|wikify={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}|orphan={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}|c=d}}"
    )
    assert not (W.MultipleIssues.is_match(r"{{ARTICLEISSUES }}"))
    assert not (W.MultipleIssues.is_match(r"{{Bert|Multipleissues }}"))


def test_non_dead_end_page_templates_tests() -> None:
    S = W.for_site(EN)
    assert W.NonDeadEndPageTemplates.is_match(r"{{Events by year for decade|31}}")
    assert W.NonDeadEndPageTemplates.is_match(r"{{Events by year for decade BC|31}}")
    assert W.NonDeadEndPageTemplates.is_match(
        r"{{SCOTUSRow | case name = Arizona v. Inter Tribal Council of Ariz., Inc. | docket = 12-71 | decision date = June 17 | decision year = 2013}}"
    )
    assert W.NonDeadEndPageTemplates.is_match(
        r"{{Portal:Current events/Month Inclusion|2009 February}}"
    )


def test_word_apostrophe_tests() -> None:
    S = W.for_site(EN)
    assert W.RegexWordApostrophes.is_match(r"Rachel")
    assert W.RegexWordApostrophes.is_match(r"Rachel's")
    assert W.RegexWordApostrophes.is_match(r"Rachel’s"), r"curly apostrophe"
    assert W.RegexWordApostrophes.is_match(r"Kwakwaka'wakw")
    assert len(W.RegexWordApostrophes.replace(r"Kwakwaka'wakw", r"")) == 0


def test_deaths_or_living_category_tests() -> None:
    S = W.for_site(EN)
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:653 deaths|Honorius]]"), (
        r"xxx deaths with sortkey"
    )
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:839 deaths]]"), r"xxx deaths"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:5th-century BC deaths]]"), (
        r"centure BC deaths"
    )
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:1209 deaths]]"), r"xxxx deaths"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:2018 suicides]]"), r"xxxx suicides"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Living people]]"), r"living people"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Possibly living people]]"), (
        r"possibly living people"
    )
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:221 BC deaths]]"), r"xxx BC deaths"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Year of death missing]]"), r"YOD missing"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Year of death unknown]]"), r"YOD unknown"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Date of death unknown]]"), r"DOD unknown"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Year of death uncertain]]"), (
        r"YOD uncertain"
    )
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:Missing people]]"), r"Mising people"
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:People declared dead in absentia]]"), (
        r"People declared dead in absentia"
    )
    assert W.DeathsOrLivingCategory.is_match(r"[[Category:839 deaths ]]"), r"xxx deaths with space"
    assert not (W.DeathsOrLivingCategory.is_match(r""))
    assert not (W.DeathsOrLivingCategory.is_match(r"[[Category:strange deaths]]"))
    assert not (W.DeathsOrLivingCategory.is_match(r"[[Category:Missing people organizations]]"))
    assert not (W.DeathsOrLivingCategory.is_match(r"1990 deaths"))


def test_births_category_tests() -> None:
    S = W.for_site(EN)
    assert W.BirthsCategory.is_match(r"[[Category:12th-century births]]")
    assert W.BirthsCategory.is_match(r"[[Category:1299 births]]")
    assert W.BirthsCategory.is_match(r"[[Category:110 BC births]]")
    assert W.BirthsCategory.is_match(r"[[Category:1st-century births]]")
    assert not (W.BirthsCategory.is_match(r"[[Category:strange births]]"))
    assert not (W.BirthsCategory.is_match(r"1960 births"))
    assert not (W.BirthsCategory.is_match(r""))


def test_people_from_category_tests() -> None:
    S = W.for_site(EN)
    assert W.PeopleFromCategory.is_match(r"[[Category:People from x]]")
    assert W.PeopleFromCategory.is_match(r"[[Category:People from x|y]]")
    assert not (W.PeopleFromCategory.is_match(r"[[Category:People who x]]"))


def test_date_birth_and_age_tests() -> None:
    S = W.for_site(EN)
    assert W.DateBirthAndAge.is_match(r"{{Birth date|1972|02|18}}")
    assert W.DateBirthAndAge.is_match(r"{{Birth date and age|1972|02|18}}")
    assert W.DateBirthAndAge.is_match(r"{{Birth date| 1972 |02|18}}")
    assert W.DateBirthAndAge.is_match(r"{{birth date and age|mf=yes|1980|3|9}}")
    assert W.DateBirthAndAge.is_match(r"{{bda|mf=yes|1980|3|9}}")
    assert W.DateBirthAndAge.match(r"{{birth-date|1975}}").group(1) == r"1975", (
        r"extract year from birth-date"
    )
    assert W.DateBirthAndAge.match(r"{{birth-date|   1975}}").group(1) == r"1975", r"spacing"
    assert (
        W.DateBirthAndAge.match(r"{{birth date and age|year=1984|month=2|day=6}}").group(1)
        == r"1984"
    )
    assert (
        W.DateBirthAndAge.match(r"{{Birth date|1972|02|18}}").value == r"{{Birth date|1972|02|18}}"
    )
    assert W.DateBirthAndAge.match(r"{{birth-date and age|1975}}").group(1) == r"1975", (
        r"extract year from birth-date and age"
    )


def test_date_death_and_age_tests() -> None:
    S = W.for_site(EN)
    assert W.DeathDate.is_match(r"{{Death date|1972|02|18}}")
    assert W.DeathDate.is_match(r"{{Death date and age|1972|02|18}}")
    assert W.DeathDate.is_match(r"{{Death date| 1972 |02|18}}")
    assert W.DeathDate.is_match(r"{{death date and age|mf=yes|1980|3|9}}")
    assert W.DeathDate.match(r"{{death-date|1975}}").group(1) == r"1975"
    assert W.DeathDate.match(r"{{death-date|   1975}}").group(1) == r"1975"
    assert W.DeathDate.match(r"{{death date and age|year=1984|month=2|day=6}}").group(1) == r"1984"
    assert W.DeathDate.match(r"{{death date and age|1911|12|12|1821|10|02}}").group(1) == r"1911"


def test_death_date_and_age() -> None:
    S = W.for_site(EN)
    assert (
        W.DeathDateAndAge.match(r"{{death date and age|1911|12|12|1821|10|02}}").group(1) == r"1911"
    )
    assert (
        W.DeathDateAndAge.match(r"{{death-date and age|1911|12|12|1821|10|02}}").group(1) == r"1911"
    )
    assert W.DeathDateAndAge.match(r"{{dda|1911|12|12|1821|10|02}}").group(1) == r"1911"
    assert (
        W.DeathDateAndAge.match(r"{{death date and age|1911|12|12|1821|10|02}}").group(2) == r"1821"
    )


def test_bare_external_link_tests() -> None:
    S = W.for_site(EN)
    assert W.BareExternalLink.is_match("* http://www.site.com\r\n")
    assert W.BareExternalLink.is_match("* http://www.site.com\r\n")
    assert W.BareExternalLink.is_match("*   http://www.site.com\r\n")
    assert W.BareExternalLink.is_match("* http://www.site.com/great/a.htm\r\n")
    assert W.BareExternalLink.is_match("* https://www.site.com\r\n")
    assert W.BareExternalLink.is_match("* ftp://www.site.com\r\n")
    assert not (W.BareExternalLink.is_match("* [http://www.site.com text]\r\n"))
    assert not (W.BareExternalLink.is_match("<ref>http://www.site.com</ref>\r\n"))


def test_bare_ref_external_link() -> None:
    S = W.for_site(EN)
    check_match(
        W.BareRefExternalLink, r"<ref>[http://news.bbc.co.uk/hi/England/story4384.htm]</ref>"
    )
    check_match(
        W.BareRefExternalLink, r"<ref>[http://news.bbc.co.uk/hi/England/story4384.htm]]</ref>"
    )
    check_match(W.BareRefExternalLink, r"<ref>http://news.bbc.co.uk/hi/England/story4384.htm</ref>")
    check_match(
        W.BareRefExternalLink,
        "< REF > [   http://news.bbc.co.uk/hi/England/story4384.htm]\r\n< / ref  >",
    )
    check_match(
        W.BareRefExternalLink,
        r"<ref name=hello>[http://news.bbc.co.uk/hi/England/story4384.htm]</ref>",
    )
    check_match(
        W.BareRefExternalLink,
        r"<ref>[   http://news.bbc.co.uk/hi/England/story4384.htm   ]   </ref>",
    )
    check_match(
        W.BareRefExternalLink,
        r"<ref>[http://news.bbc.co.uk/hi/England/story4384.htm title here]</ref>",
        False,
    )
    check_matches(
        W.BareRefExternalLink, r"<ref>[http://news.bbc.co.uk/hi/England/story4384.htm</ref>", 0
    )
    assert (
        W.BareRefExternalLink.match(
            r"<ref>[ http://news.bbc.co.uk/hi/England/story4384.htm ] </ref>"
        ).group(1)
        == r"http://news.bbc.co.uk/hi/England/story4384.htm"
    )
    assert (
        W.BareRefExternalLink.match(
            r"<ref>[ http://news.bbc.co.uk/hi/England/story4384.htm] </ref>"
        ).group(1)
        == r"http://news.bbc.co.uk/hi/England/story4384.htm"
    )
    assert (
        W.BareRefExternalLink.match(
            r"<ref>[ http://news.bbc.co.uk/hi/England/story4384.htm]. </ref>"
        ).group(1)
        == r"http://news.bbc.co.uk/hi/England/story4384.htm"
    )


def test_bare_ref_external_link_bot_gen_title() -> None:
    S = W.for_site(EN)
    check_match(
        W.BareRefExternalLinkBotGenTitle,
        r"<ref>[http://news.bbc.co.uk/hi/England/story4384.htm]</ref>",
    )
    check_match(
        W.BareRefExternalLinkBotGenTitle,
        r"<ref>http://news.bbc.co.uk/hi/England/story4384.htm</ref>",
    )
    check_match(
        W.BareRefExternalLinkBotGenTitle,
        r"<ref>[http://www.independent.co.uk/news/people/bo-johnson-30403.html Boris Johnson: People - The Independent<!-- Bot generated title -->]</ref>",
    )
    check_match(
        W.BareRefExternalLinkBotGenTitle,
        r"<ref>Smith, Fred [http://www.independent.co.uk/news/people/bo-johnson-30403.html Boris Johnson: People - The Independent<!-- Bot generated title -->]</ref>",
        False,
    )
    check_match(
        W.BareRefExternalLinkBotGenTitle,
        r"<ref>[http://www.independent.co.uk/news/people/bo-johnson-30403.html Boris Johnson: People - The Independent]</ref>",
        False,
    )
    assert W.BareRefExternalLinkBotGenTitle.is_match(
        r"attack<ref>http://www.news.com.au/heraldsun/story/0,21985,23169580-5006022,00.html</ref> was portrayed"
    )
    assert (
        W.BareRefExternalLinkBotGenTitle.match(
            r"<ref>[http://news.bbc.co.uk/hi/England/story4384.htm]</ref>"
        ).group(1)
        == r"http://news.bbc.co.uk/hi/England/story4384.htm"
    )
    assert (
        W.BareRefExternalLinkBotGenTitle.match(
            r'<ref>[http://news.bbc.co.uk/hi/England/story4384.htm]"</ref>'
        ).group(1)
        == r"http://news.bbc.co.uk/hi/England/story4384.htm"
    )
    assert (
        W.BareRefExternalLinkBotGenTitle.match(
            r"<ref> [ http://news.bbc.co.uk/hi/England/story4384.htm]. </ref>"
        ).group(1)
        == r"http://news.bbc.co.uk/hi/England/story4384.htm"
    )
    assert (
        W.BareRefExternalLinkBotGenTitle.match(
            r"<ref> [ http://news.bbc.co.uk/hi/England/story4384.htm Foo<!--bot generated title-->]. </ref>"
        ).group(2)
        == r"Foo"
    )


def test_bold_italic_tests() -> None:
    S = W.for_site(EN)
    assert W.Bold.match(r"'''foo'''").group(1) == r"foo"
    assert W.Bold.match(r"'''foo bar'''").group(1) == r"foo bar"
    assert W.Bold.match(r"'''foo's bar'''").group(1) == r"foo's bar"
    assert W.Bold.match(r"'''''foo's bar'''''").group(1) == r"", r"no match on bold italics"
    assert W.Italics.match(r"''foo''").group(1) == r"foo"
    assert W.Italics.match(r"''foo bar''").group(1) == r"foo bar"
    assert W.Italics.match(r"''foo's bar''").group(1) == r"foo's bar"
    assert W.Italics.match(r"'''foo's bar'''").group(1) == r"", r"no match on bold"
    assert W.Italics.match(r"'''''foo's bar'''''").group(1) == r"", r"no match on bold italics"
    assert (
        W.Italics.match(r"'''Tyrone Station''' is an by Amtrak's ''[[foo]]'', which").group(1)
        == r"[[foo]]"
    )
    assert W.BoldItalics.match(r"''''' foo'''''").group(1) == r" foo"
    assert W.BoldItalics.match(r"'''''foo bar'''''").group(1) == r"foo bar"
    assert W.BoldItalics.match(r"'''''foo's bar'''''").group(1) == r"foo's bar"
    assert W.Italics.match(r"''f''").group(1) == r"f"
    assert W.Italics.match(r"''f'' nar ''abc''").group(1) == r"f"
    assert W.Bold.match(r"'''f''' nar '''abc'''").group(1) == r"f"
    assert not (W.Italics.is_match(r"'''foo'''"))
    assert not (W.Italics.is_match(r"'''''foo'''''"))
    assert not (W.Bold.is_match(r"''foo'''"))
    assert not (W.Bold.is_match(r"''foo''"))
    assert not (W.BoldItalics.is_match(r"''foo''"))
    assert not (W.BoldItalics.is_match(r"'''foo'''"))
    assert not (W.BoldItalics.is_match(r"'''''foo''"))


def test_star_rows_tests() -> None:
    S = W.for_site(EN)
    assert W.StarRows.match("*foo bar\r\nBert").group(1) == r"*"
    assert W.StarRows.match("*foo bar\r\nBert").group(2) == "foo bar\r"
    assert W.StarRows.match(r"    *foo bar").group(1) == r"*"
    assert W.StarRows.match(r" *foo bar").group(2) == r"foo bar"


def test_circa_template() -> None:
    S = W.for_site(EN)
    assert W.CircaTemplate.is_match(r"{{circa}}")
    assert W.CircaTemplate.is_match(r"{{ circa}}")
    assert W.CircaTemplate.is_match(r"{{Circa}}")
    assert W.CircaTemplate.is_match(r"{{circa|foo=yes}}")


def test_reference_list() -> None:
    S = W.for_site(EN)
    S = W.for_site(EN.with_lang_code(r"fr"))
    assert S.ReferenceList.is_match(r"{{références}}")
    assert S.ReferenceList.is_match(r"{{references}}")
    assert S.ReferenceList.is_match(r"{{reflist}}")
    S = W.for_site(EN.with_lang_code(r"en"))
    assert S.ReferenceList.is_match(r"{{reflist}}")
    assert S.ReferenceList.is_match(r"{{references-small}}")
    assert S.ReferenceList.is_match(r"{{references-2column}}")


def test_simple_wiki() -> None:
    S = W.for_site(EN)
    S = W.for_site(EN.with_lang_code(r"simple"))
    assert S.SeeAlso.is_match(r"==Related pages==")
    assert S.SeeAlso.is_match(r"==related pages==")
    assert S.SeeAlso.is_match(r"==See also==")
    assert S.ExternalLinksHeader.is_match(r"==Other websites==")
    assert S.ExternalLinksHeader.is_match(r"==External links==")
    S = W.for_site(EN.with_lang_code(r"en"))
    assert not (S.SeeAlso.is_match(r"==Related pages=="))
    assert S.SeeAlso.is_match(r"==See also==")
    assert S.ExternalLinksHeader.is_match(r"==External links==")


def test_surname_clarification_templates() -> None:
    S = W.for_site(EN)
    assert W.SurnameClarificationTemplates.is_match(r"{{Malay name}}")
    assert W.SurnameClarificationTemplates.is_match(r"{{Malay_name}}")
    assert W.SurnameClarificationTemplates.is_match(r"{{Chinese name}}")
    assert not (W.SurnameClarificationTemplates.is_match(r"{{Eastern name order}}"))


def test_reversed_italics() -> None:
    S = W.for_site(EN)
    assert W.ReversedItalics.is_match(r"</i>foo<i>")
    assert W.ReversedItalics.is_match(r"</i>foo< i >")
    assert W.ReversedItalics.is_match(r"< /i >foo<i>")
    assert W.ReversedItalics.match(r"</i>foo<i>").group(1) == r"foo"
    assert not (W.ReversedItalics.is_match(r"<i>foo</i>"))
    assert not (W.ReversedItalics.is_match(r"<i>foo<i>"))
    assert not (W.ReversedItalics.is_match(r"<i>foo</i> and <i>foo</i>"))


def test_short_pages_monitor() -> None:
    S = W.for_site(EN)
    LC = r"{{Short pages monitor}}<!-- This long comment was added to the page to prevent it from being listed on Special:Shortpages. It and the accompanying monitoring template were generated via Template:Long comment. Please do not remove the monitor template without removing the comment as well.-->"
    assert W.ShortPagesMonitor.is_match(LC)
    assert W.ShortPagesMonitor.is_match(LC.replace(r"{{S", r"{{s")), (
        r"handles template name first letter case insensitive"
    )
    assert W.ShortPagesMonitor.is_match(r"{{Short pages monitor}}<!-- any old comment-->")


def test_good_featured_article_templates() -> None:
    S = W.for_site(EN)
    assert W.GoodFeaturedArticleTemplates.is_match(r"{{Featured list}}")
    assert W.GoodFeaturedArticleTemplates.is_match(r"{{Featured article}}")
    assert W.GoodFeaturedArticleTemplates.is_match(r"{{Good article}}")


def test_use_dates_english_templates() -> None:
    S = W.for_site(EN)
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use American English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Antiguan and Barbudan English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Australian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Bangladeshi English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use British English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Oxford spelling}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Canadian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Ghanaian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Hiberno-English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Hong Kong English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Indian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Jamaican English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Kenyan English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Liberian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Malaysian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use New Zealand English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Nigerian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Pakistani English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Philippine English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Singapore English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use South African English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Sri Lankan English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Tanzanian English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Trinidad and Tobago English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{Use Ugandan English}}")
    assert W.UseDatesEnglishTemplates.is_match(r"{{EngvarB}}")
