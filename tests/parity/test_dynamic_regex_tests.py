"""Port of AWB UnitTests/DynamicRegexTests.cs: per-wiki regexes.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from pyawb.core import genfixes, namespace, tools
from pyawb.core import wikiregexes as W
from pyawb.core.dotnet_regex import DotNetOptions as O
from pyawb.core.parsers.parsers import DateLocale
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_project, set_site, utc_month_year
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_category_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Category, r"[[Category:Test]]", r"Simple case")
    regex_assert.is_match(S.CategoryQuick, r"[[Category:Test]]")
    regex_assert.is_match(S.Category, r"[[Category:Test|{{PAGENAME}}]]", r" use of {{PAGENAME}}")
    regex_assert.is_match(
        S.Category, r"[[Category:Test|{{subst:PAGENAME}}]]", r" use of {{subst:PAGENAME}}"
    )
    regex_assert.is_match(S.Category, r"[[Category:Test now]]", r"Space in name")
    regex_assert.is_match(S.Category, r"[[Category:Test|Key]]", r"Simple sortkey")
    regex_assert.is_match(S.Category, r"[[ Category : Test now| Key]]", r"Spaced sortkey")
    regex_assert.is_match(S.Category, r"[[CATEGORY :Test]]", r"Uppercase")
    regex_assert.is_match(S.Category, r"[[Category:_Test]]", r"Leading underscore in name")
    regex_assert.is_match(S.Category, r"[[_Category:Test]]", r"leading underscore")
    regex_assert.is_match(S.Category, r"[[_Category:Test_]]", r"Trailing underscores")
    regex_assert.is_match(S.CategoryQuick, r"[[_Category:Test_]]")
    regex_assert.no_match(S.Category, r"[[Test]]", r"Wikilink")
    regex_assert.no_match(S.Category, r"[[Image:Test.jpg]]", r"Image link")
    regex_assert.no_match(S.Category, "[[Category:\r\n1910 births]]", r"Newline in category name")
    regex_assert.no_match(S.Category, "[[Category:1910 births\r\n]]", r"newline in category name 2")
    assert S.Category.match(r"[[Category:Test now]]").group(1) == r"Test now", (
        r"Group 1 is category name"
    )
    assert S.Category.match(r"[[Category: Test now ]]").group(1) == r"Test now", (
        r"Group 1 is category name, trimmed"
    )
    assert len(S.Category.match(r"[[Category: Test now ]]").group(2)) == 0, (
        r"Group 2 is optional sort key"
    )
    assert S.Category.match(r"[[Category: Test now|Bar]]").group(2) == r"Bar", (
        r"Group 2 is sort key"
    )
    S = set_lang(r"sv")
    S = set_site(
        namespaces={**current_site().namespaces, Namespace.CATEGORY: "Kategori:"}
    )  # AWB: NamespacesCaseInsensitive[...] = '[Kk]ategori:'
    regex_assert.is_match(S.Category, r"[[Kategori:Test]]")
    regex_assert.is_match(S.CategoryQuick, r"[[Kategori:Test]]")
    S = set_lang(r"el")
    S = set_site(
        namespaces={**current_site().namespaces, Namespace.CATEGORY: "Κατηγορία:"}
    )  # AWB: NamespacesCaseInsensitive[...] = '[Κκ]ατηγορία:'
    regex_assert.is_match(S.Category, r"[[Κατηγορία:Δοκιμή]]")
    regex_assert.is_match(S.CategoryQuick, r"[[Κατηγορία:Δοκιμή]]")
    S = set_lang(r"en")
    S = set_site(
        namespaces={**current_site().namespaces, Namespace.CATEGORY: "Category:"}
    )  # AWB: NamespacesCaseInsensitive[...] = '(?i:Category)\\s*:'
    regex_assert.is_match(S.Category, r"[[Category:Test]]")
    regex_assert.is_match(S.CategoryQuick, r"[[Category:Test]]")


def test_loose_category_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.LooseCategory, r"[[Category :Test]]")
    regex_assert.is_match(S.LooseCategory, r"[[ category :Test]]")
    regex_assert.is_match(S.LooseCategory, r"[[CATEGORY :Test]]")
    regex_assert.is_match(S.LooseCategory, r"[[ Category: Test]]")
    regex_assert.is_match(S.LooseCategory, r"[[_Category: Test]]")
    regex_assert.is_match(S.LooseCategory, r"[[ Category :Test|here]]")
    regex_assert.is_match(S.LooseCategory, "[[Category:\r\n1910 births]]")
    regex_assert.is_match(S.LooseCategory, r"[[Category::Test]]")
    regex_assert.no_match(S.LooseCategory, r"[[Test]]")
    regex_assert.no_match(S.LooseCategory, r"[[Category")
    regex_assert.no_match(S.LooseCategory, r"[[Image:Test.jpg]]")


def test_image_tests_standard() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Images, r"[[File:Test.JPG]]")
    regex_assert.is_match(S.Images, r"[[File:Test.jpg]]")
    regex_assert.is_match(S.Images, r"[[File:Test of the.ogg]]")
    regex_assert.matches(S.Images, r"[[File:Test of the.ogg]]", r"[[File:Test of the.ogg]]")
    regex_assert.is_match(S.Images, r"[[File:Test_of_the.ogg]]")
    regex_assert.is_match(S.Images, r"[[Image:Test.JPG]]")
    regex_assert.is_match(S.Images, r"[[Image:Beijing, 6–18 October, 1860.jpg]]")
    regex_assert.is_match(S.Images, r"[[File:test.jpg|thumbnail|Some description [[here]], 1987]]")
    regex_assert.is_match(
        S.Images, r"[[Image:Test here.png|right|200px|Some description [[here]] or there]]"
    )
    regex_assert.is_match(
        S.Images,
        "[[Image:Test here.png|right|200px|Some description [[here]] or there\r\n over lines]]",
    )
    regex_assert.is_match(S.Images, r"[[File:Test.JPG")
    regex_assert.no_match(S.Images, r"[[File Test.JPG]]")
    bef = r"[[File:Miguel.jpg|thumb|[[Miguel (privateer)|Miguel]]]] [[File:Demetrio.jpg|thumb|[[Demetrio]]]]"
    assert (
        S.Images.replace(bef, r"_")
        == r"_thumb|[[Miguel (privateer)|Miguel]]]] _thumb|[[Demetrio]]]]"
    ), r"Image on same line handling"


def test_image_tests_infoboxes() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\nbar = a|\r\nimage = [[File:Test.JPG]]\r\n| there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  image2 = [[File:Test.JPG]]\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  img = [[File:Test.JPG]]\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  img = Test.JPEG\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  cover = [[Image:Test.JPG]]\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  cover art = Test2.png\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images,
        "{{Infobox foo|\r\n  bar = a|\r\n  1 = Test2.png\r\n  | there=here}}",
        r"1-character parameter name",
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  cover_ar = Test.JPG\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|map=[[File:Test.JPG]]\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a| map = [[File:Test.JPG]]\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\n  bar = a|\r\n  strangename = Test.JPEG\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.Images, "{{Infobox foo|\r\nbar = a|\r\npicture = Test.JPG\r\n| there=here}}"
    )
    regex_assert.matches(
        S.Images,
        "{{Infobox foo|\r\n  bar = a|\r\n  picture = Test.JPG\r\n  | there=here}}",
        r" Test.JPG",
    )
    regex_assert.no_match(
        S.Images,
        "{{Infobox foo|\r\n  bar = a|\r\n  url = http://apageof.com/a.html\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.Images, "{{double image\r\n|right|\r\nBob D.jpg|120|Florence.jpg|120|Mmm}}"
    )


def test_image_tests_gallery_tag() -> None:
    S = W.for_site(EN)
    regex_assert.matches(S.Images, "<gallery>\r\nFile:Foo.png\r\n</gallery>", r"File:Foo.png")
    regex_assert.matches(
        S.Images, "<gallery>\r\nFile:Foo.png|description\r\n</gallery>", r"File:Foo.png|"
    )
    regex_assert.matches(
        S.Images, "<gallery>\r\nImage:Foo.png|description\r\n</gallery>", r"Image:Foo.png|"
    )
    regex_assert.matches(
        S.Images, "<gallery>\r\nImage : Foo.png |description\r\n</gallery>", r"Image : Foo.png |"
    )
    regex_assert.matches(
        S.Images, "<GALLERY>\r\nImage:Foo.png|description\r\n</GALLERY>", r"Image:Foo.png|"
    )
    regex_assert.matches(
        S.Images,
        "<gallery name=bar style=silver>\r\nFile:Foo.png|description<br>text\r\n</gallery>",
        r"File:Foo.png|",
    )
    regex_assert.matches(S.Images, "< gallery >\r\nFile:Foo.png\r\n< /gallery >", r"File:Foo.png")
    regex_assert.matches(
        S.Images,
        "< gallery >\r\nFile:9th of May_street, Bacău.jpg\r\n< /gallery >",
        r"File:9th of May_street, Bacău.jpg",
    )
    mc = S.Images.matches(
        "<gallery>\r\nImage:Foo.png|description\r\nImage:Foo2.png|description2\r\n</gallery>"
    )
    assert mc[0].value == r"Image:Foo.png|"
    assert mc[1].value == r"Image:Foo2.png|"
    regex_assert.is_match(S.Images, r"File:Foo.png|description")
    regex_assert.no_match(S.Images, "<gallery>\r\n\r\n</gallery>\r\nImage here")


def test_image_tests_gallery_template() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(
        S.Images,
        "{{Gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}",
    )
    regex_assert.is_match(
        S.Images,
        "{{ gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}",
    )


def test_images_count_only_tests_standard() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.ImagesCountOnly, r"[[File:Test.JPG]]")
    regex_assert.is_match(S.ImagesCountOnly, r"[[File:Test.jpg]]")
    regex_assert.is_match(S.ImagesCountOnly, r"[[File:Test of the.ogg]]")
    regex_assert.matches(
        S.ImagesCountOnly, r"[[File:Test of the.ogg]]", r"[[File:Test of the.ogg]]"
    )
    regex_assert.is_match(S.ImagesCountOnly, r"[[File:Test_of_the.ogg]]")
    regex_assert.is_match(S.ImagesCountOnly, r"[[Image:Test.JPG]]")
    regex_assert.is_match(
        S.ImagesCountOnly, r"[[Image:Test here.png|right|200px|Some description [[here]] or there]]"
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "[[Image:Test here.png|right|200px|Some description [[here]] or there\r\n over lines]]",
    )
    regex_assert.is_match(S.ImagesCountOnly, r"[[File:Test.JPG")
    regex_assert.no_match(S.ImagesCountOnly, r"[[File Test.JPG]]")


def test_images_count_only_tests_infoboxes() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\nbar = a|\r\nimage = [[File:Test.JPG]]\r\n| there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  image2 = [[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  img = [[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly, "{{Infobox foo|\r\n  bar = a|\r\n  img = Test.JPEG\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  cover = [[Image:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  cover art = Test2.png\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  cover_ar = Test.JPG\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly, "{{Infobox foo|\r\n  bar = a|map=[[File:Test.JPG]]\r\n  | there=here}}"
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a| map = [[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  strangename = Test.JPEG\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly, "{{Infobox foo|\r\nbar = a|\r\npicture = Test.JPG\r\n| there=here}}"
    )
    regex_assert.matches(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  picture = Test.JPG\r\n  | there=here}}",
        "|\r\n  picture = Test.JPG",
    )
    regex_assert.no_match(
        S.ImagesCountOnly,
        "{{Infobox foo|\r\n  bar = a|\r\n  url = http://apageof.com/a.html\r\n  | there=here}}",
    )


def test_images_count_only_tests_gallery_tag() -> None:
    S = W.for_site(EN)
    regex_assert.matches(
        S.ImagesCountOnly, "<gallery>\r\nFile:Foo.png\r\n</gallery>", r"File:Foo.png"
    )
    regex_assert.matches(
        S.ImagesCountOnly, "<gallery>\r\nFile:Foo.png|description\r\n</gallery>", r"File:Foo.png|"
    )
    regex_assert.matches(
        S.ImagesCountOnly, "<gallery>\r\nImage:Foo.png|description\r\n</gallery>", r"Image:Foo.png|"
    )
    regex_assert.matches(
        S.ImagesCountOnly,
        "<gallery>\r\nImage : Foo.png |description\r\n</gallery>",
        r"Image : Foo.png |",
    )
    regex_assert.matches(
        S.ImagesCountOnly, "<GALLERY>\r\nImage:Foo.png|description\r\n</GALLERY>", r"Image:Foo.png|"
    )
    regex_assert.matches(
        S.ImagesCountOnly,
        "<gallery name=bar style=silver>\r\nFile:Foo.png|description<br>text\r\n</gallery>",
        r"File:Foo.png|",
    )
    regex_assert.matches(
        S.ImagesCountOnly, "< gallery >\r\nFile:Foo.png\r\n< /gallery >", r"File:Foo.png"
    )
    regex_assert.matches(
        S.ImagesCountOnly,
        "< gallery >\r\nFile:9th of May_street, Bacău.jpg\r\n< /gallery >",
        r"File:9th of May_street, Bacău.jpg",
    )
    mc = S.ImagesCountOnly.matches(
        "<gallery>\r\nImage:Foo.png|description\r\nImage:Foo2.png|description2\r\n</gallery>"
    )
    assert mc[0].value == r"Image:Foo.png|"
    assert mc[1].value == r"Image:Foo2.png|"
    regex_assert.is_match(S.ImagesCountOnly, r"File:Foo.png|description")
    regex_assert.no_match(S.ImagesCountOnly, "<gallery>\r\n\r\n</gallery>\r\nImage here")


def test_images_count_only_tests_gallery_template() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{Gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}",
    )
    regex_assert.is_match(
        S.ImagesCountOnly,
        "{{ gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}",
    )


def test_images_not_templates_tests_standard() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.ImagesNotTemplates, r"[[File:Test.JPG]]")
    regex_assert.is_match(S.ImagesNotTemplates, r"[[File:Test.jpg]]")
    regex_assert.is_match(S.ImagesNotTemplates, r"[[File:Test of the.ogg]]")
    regex_assert.matches(
        S.ImagesNotTemplates, r"[[File:Test of the.ogg]]", r"[[File:Test of the.ogg]]"
    )
    regex_assert.is_match(S.ImagesNotTemplates, r"[[File:Test_of_the.ogg]]")
    regex_assert.is_match(S.ImagesNotTemplates, r"[[Image:Test.JPG]]")
    regex_assert.is_match(
        S.ImagesNotTemplates,
        r"[[Image:Test here.png|right|200px|Some description [[here]] or there]]",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "[[Image:Test here.png|right|200px|Some description [[here]] or there\r\n over lines]]",
    )
    regex_assert.is_match(S.ImagesNotTemplates, r"[[File:Test.JPG")
    regex_assert.no_match(S.ImagesNotTemplates, r"[[File Test.JPG]]")
    regex_assert.matches(
        S.ImagesNotTemplates,
        r"[[Image:Shane Bernagh’s Chair. 28th may 2007 -2.jpg]]",
        r"[[Image:Shane Bernagh’s Chair. 28th may 2007 -2.jpg]]",
    )


def test_images_not_templates_tests_infoboxes() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\nbar = a|\r\nimage = [[File:Test.JPG]]\r\n| there=here}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  image2 = [[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  img = [[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  img = File:Test.JPG\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  cover = [[Image:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|map=[[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a| map = [[File:Test.JPG]]\r\n  | there=here}}",
    )
    regex_assert.no_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  img = Test.JPEG\r\n  | there=here}}",
    )
    regex_assert.no_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  cover art = Test2.png\r\n  | there=here}}",
    )
    regex_assert.no_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  cover_ar = Test.JPG\r\n  | there=here}}",
    )
    regex_assert.no_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  strangename = Test.JPEG\r\n  | there=here}}",
    )
    regex_assert.no_match(
        S.ImagesNotTemplates, "{{Infobox foo|\r\nbar = a|\r\npicture = Test.JPG\r\n| there=here}}"
    )
    regex_assert.no_match(
        S.ImagesNotTemplates,
        "{{Infobox foo|\r\n  bar = a|\r\n  picture = Test.JPG\r\n  | there=here}}",
        "|\r\n  picture = Test.JPG",
    )


def test_images_not_templates_tests_gallery_tag() -> None:
    S = W.for_site(EN)
    regex_assert.matches(
        S.ImagesNotTemplates, "<gallery>\r\nFile:Foo.png\r\n</gallery>", r"File:Foo.png"
    )
    regex_assert.matches(
        S.ImagesNotTemplates,
        "<gallery>\r\nFile:Foo.png|description\r\n</gallery>",
        r"File:Foo.png|",
    )
    regex_assert.matches(
        S.ImagesNotTemplates,
        "<gallery>\r\nImage:Foo.png|description\r\n</gallery>",
        r"Image:Foo.png|",
    )
    regex_assert.matches(
        S.ImagesNotTemplates,
        "<gallery>\r\nImage : Foo.png |description\r\n</gallery>",
        r"Image : Foo.png |",
    )
    regex_assert.matches(
        S.ImagesNotTemplates,
        "<GALLERY>\r\nImage:Foo.png|description\r\n</GALLERY>",
        r"Image:Foo.png|",
    )
    regex_assert.matches(
        S.ImagesNotTemplates,
        "<gallery name=bar style=silver>\r\nFile:Foo.png|description<br>text\r\n</gallery>",
        r"File:Foo.png|",
    )
    regex_assert.matches(
        S.ImagesNotTemplates, "< gallery >\r\nFile:Foo.png\r\n< /gallery >", r"File:Foo.png"
    )
    regex_assert.matches(
        S.ImagesNotTemplates,
        "< gallery >\r\nFile:9th of May_street, Bacău.jpg\r\n< /gallery >",
        r"File:9th of May_street, Bacău.jpg",
    )
    mc = S.ImagesNotTemplates.matches(
        "<gallery>\r\nImage:Foo.png|description\r\nImage:Foo2.png|description2\r\n</gallery>"
    )
    assert mc[0].value == r"Image:Foo.png|"
    assert mc[1].value == r"Image:Foo2.png|"
    regex_assert.is_match(S.ImagesNotTemplates, r"File:Foo.png|description")
    regex_assert.no_match(S.ImagesNotTemplates, "<gallery>\r\n\r\n</gallery>\r\nImage here")


def test_images_not_templates_tests_gallery_template() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{Gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}",
    )
    regex_assert.is_match(
        S.ImagesNotTemplates,
        "{{ gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}",
    )


def test_loose_image_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.LooseImage, r"[[File:Test.JPG]]")
    regex_assert.is_match(S.LooseImage, r"[[ File:Test.JPG]]")
    regex_assert.is_match(S.LooseImage, r"[[ File :Test.JPG]]")
    regex_assert.is_match(S.LooseImage, r"[[File:Test.jpg]]")
    regex_assert.is_match(S.LooseImage, r"[[File:Test of the.ogg]]")
    regex_assert.is_match(S.LooseImage, r"[[File:Test_of_the.ogg]]")
    regex_assert.is_match(S.LooseImage, r"[[Image:Test.JPG]]")
    regex_assert.is_match(S.LooseImage, r"[[  Image: Test.JPG]]")
    regex_assert.is_match(
        S.LooseImage, r"[[Image:Test here.png|right|200px|Some description [[here]] or there]]"
    )
    regex_assert.is_match(
        S.LooseImage,
        "[[Image:Test here.png|right|200px|Some description [[here]] or there\r\n over lines]]",
    )
    regex_assert.no_match(S.LooseImage, r"[[File:Test.JPG")


def test_file_namespace_link_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.FileNamespaceLink, r"[[File:Test.JPG]]")
    regex_assert.is_match(S.FileNamespaceLink, r"[[ File:Test.JPG]]")
    regex_assert.is_match(S.FileNamespaceLink, r"[[ File :Test.JPG]]")
    regex_assert.is_match(S.FileNamespaceLink, r"[[File:Test.jpg]]")
    regex_assert.is_match(S.FileNamespaceLink, r"[[File:Test of the.ogg]]")
    regex_assert.is_match(S.FileNamespaceLink, r"[[File:Test_of_the.ogg]]")
    regex_assert.is_match(S.FileNamespaceLink, r"[[Image:Test.JPG]]")
    regex_assert.is_match(
        S.FileNamespaceLink,
        r"[[Image:Test here.png|right|200px|Some description [[here]] or there]]",
    )
    regex_assert.is_match(
        S.FileNamespaceLink,
        "[[Image:Test here.png|right|200px|Some description [[here]] or there\r\n over lines]]",
    )
    regex_assert.no_match(S.FileNamespaceLink, r"[[File:Test.JPG")
    regex_assert.no_match(S.FileNamespaceLink, r"[[File Test.JPG]]")
    assert S.FileNamespaceLink.match(r"[[ File :Test.JPG]]").group(1) == r"Test.JPG"


def test_user_signature() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.UserSignature, r"[[User:")
    regex_assert.is_match(S.UserSignature, r"[[User talk:")
    regex_assert.is_match(S.UserSignature, r"[[User talk :")
    regex_assert.is_match(S.UserSignature, r"[[User_talk:")


def test_stub_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Stub, r"{{footballer-bio-stub}}")
    regex_assert.is_match(S.Stub, r"{{ footballer-bio-stub}}")
    regex_assert.is_match(S.Stub, r"{{ Footballer-Bio-Stub}}")
    regex_assert.is_match(S.Stub, r"{{bio-stub}}")
    regex_assert.is_match(S.Stub, r"{{ bio-stub }}")
    regex_assert.is_match(S.Stub, r"{{stub}}")
    regex_assert.is_match(S.Stub, r"{{ stub}}")
    regex_assert.is_match(S.Stub, r"{{Stub}}")
    regex_assert.is_match(S.Stub, r"{{-stub}}")
    regex_assert.is_match(S.Stub, r"{{Japan-spacecraft-stub|nocat=yes}}")
    regex_assert.is_match(S.Stub, r"{{Japan-spacecraft-stub|date=August 2012}}")
    regex_assert.is_match(S.Stub, r"{{Uncategorized stub}}")
    regex_assert.is_match(S.Stub, r"{{Uncategorized stub|date=March 2013}}")
    regex_assert.no_match(
        S.Stub,
        r"{{Uncategorized stub|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}",
        r"stub does not match templates with nesting",
    )
    regex_assert.no_match(S.Stub, r"{{now stubborn}}")
    regex_assert.no_match(S.Stub, r"{{stubby}}")
    regex_assert.no_match(S.Stub, r"{{foo|stub}}")
    regex_assert.no_match(S.Stub, r":{{main|stub (electronics)#Short circuited stub|l1=stub}}")
    S = set_lang(r"ar")
    regex_assert.is_match(S.Stub, r"{{بذرة}}")
    regex_assert.is_match(S.Stub, r"{{stub}}")
    regex_assert.is_match(S.Stub, r"{{قالب:بذرة أعلام البرتغال}}")
    regex_assert.is_match(S.Stub, r"{{قالب:بذرة كرة سلة}}")
    regex_assert.is_match(S.Stub, r"{{بذرة غير مصنفة}}")
    S = set_lang(r"arz")
    regex_assert.is_match(S.Stub, r"{{بذرة}}")
    regex_assert.is_match(S.Stub, r"{{تقاوى}}")
    regex_assert.is_match(S.Stub, r"{{stub}}")
    regex_assert.is_match(S.Stub, r"{{قالب:تقاوى تونس}}")
    regex_assert.is_match(S.Stub, r"{{تقاوى مش متصنفه}}")
    S = set_lang(r"sv")
    regex_assert.is_match(S.Stub, r"{{1920-talsstub}}")
    regex_assert.is_match(S.Stub, r"{{1910-talsstub-USA}}")
    regex_assert.is_match(S.Stub, r"{{stub}}")
    regex_assert.is_match(S.Stub, r"{{Robotskapad stub om hjuldjur}}")
    regex_assert.is_match(S.Stub, r"{{Robotskapad djurstub}}")
    regex_assert.no_match(S.Stub, r"{{uncategorized stub}}")
    regex_assert.no_match(S.Stub, r"{{wordwithstubin}}")
    regex_assert.no_match(S.Stub, r"{{substub}}")
    regex_assert.no_match(S.Stub, r"{{stubbmall}}")
    regex_assert.no_match(S.Stub, r"{{ Stubbmall }}")
    regex_assert.no_match(S.Stub, r"{{Stubavsnitt}}")
    S = set_lang(r"zh")
    regex_assert.is_match(S.Stub, r"{{保加利亞地理小作品}}")
    regex_assert.is_match(S.Stub, r"{{Germany-geo-stub}}")
    S = set_lang(r"sco")
    regex_assert.is_match(S.Stub, r"{{Stub/foo}}")
    regex_assert.is_match(S.Stub, r"{{Stub/foo bar}}")
    regex_assert.is_match(S.Stub, r"{{foo-stub}}")
    S = set_project(r"en", "wikipedia")


def test_possibly_commented_stub_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{footballer-bio-stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{ footballer-bio-stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{ Footballer-Bio-Stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{ Footballer-Bio-Stub|date=May 2012}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{bio-stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{ bio-stub }}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{ stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"{{Stub}}")
    regex_assert.is_match(S.PossiblyCommentedStub, r"<!--{{Stub}}-->")
    regex_assert.is_match(
        S.PossiblyCommentedStub,
        r"{{Uncategorized stub|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}",
    )
    regex_assert.no_match(S.PossiblyCommentedStub, r"{{now stubborn}}")
    regex_assert.no_match(S.PossiblyCommentedStub, r"{{stubby}}")


def test_template_call_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.TemplateCall, r"{{now stubborn}}")
    regex_assert.is_match(S.TemplateCall, r"{{ now stubborn}}")
    regex_assert.is_match(S.TemplateCall, "{{\r\nnow stubborn}}")
    regex_assert.is_match(S.TemplateCall, r"{{now stubborn|abc|derf=gh|ijk}}")
    regex_assert.is_match(S.TemplateCall, r"{{Template:now stubborn}}")
    regex_assert.is_match(S.TemplateCall, r"{{template:now stubborn}}")
    regex_assert.no_match(S.TemplateCall, r"[[Test]]")
    regex_assert.no_match(S.TemplateCall, r"Test")
    regex_assert.no_match(S.TemplateCall, r"[[Image:Test.jpg]]")
    regex_assert.is_match(
        S.TemplateCall,
        "{{cite book|url=http://www.site.com\r\n|pages = 50{{ndash}}70\r\n|year=2009",
    )


def test_dates_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Dates, r"1 May")
    regex_assert.is_match(S.Dates, r"1 June")
    regex_assert.is_match(S.Dates, r"01 May")
    regex_assert.is_match(S.Dates, r"11 May")
    regex_assert.is_match(S.Dates, r"31 May")
    regex_assert.no_match(S.Dates, r"33 May")
    regex_assert.no_match(S.Dates, r"May 13")
    regex_assert.no_match(S.Dates, r"3 Maybe")
    regex_assert.no_match(S.Dates, r"3 may")


def test_dates2_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Dates2, r"May 1")
    regex_assert.is_match(S.Dates2, r"June 1")
    regex_assert.is_match(S.Dates2, r"May 01")
    regex_assert.is_match(S.Dates2, r"May 11")
    regex_assert.is_match(S.Dates2, r"May 31")
    regex_assert.no_match(S.Dates2, r"May 33")
    regex_assert.no_match(S.Dates2, r"13 May")
    regex_assert.no_match(S.Dates2, r"MigMay 3")
    regex_assert.no_match(S.Dates2, r"may 3")


def test_redirect_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Redirect, r"#REDIRECT:[[Foo]]")
    regex_assert.is_match(S.Redirect, r"#redirect:[[Foo]]")
    regex_assert.is_match(S.Redirect, r"#redirect [[Foo]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT [[Foo]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT   :   [[Foo]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT:[[Foo bar]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT:[[ Foo bar]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT:[[ :Foo bar]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT:[[Foo bar|the best]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT:[[Foo bar#best]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT=[[Foo]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT = [[Foo bar#best]]")
    regex_assert.is_match(S.Redirect, r"#REDIRECT[[Foo]] {{R from move}}")
    regex_assert.no_match(S.Redirect, r"#  REDIRECT:[[Foo]]")


def test_orphan_tests() -> None:
    S = W.for_site(EN)
    assert S.Orphan.is_match(r"{{orphan}}")
    assert S.Orphan.is_match(r"{{Orphan}}")
    assert S.Orphan.is_match(r"{{orphan|date=May 2008}}")
    assert S.Orphan.is_match(r"{{Orphan| date = May 2008}}")
    assert S.Orphan.is_match(r"{{Orphan | date = May 2008}}")
    assert S.Orphan.is_match(r"{{orphan|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}")
    assert not (S.Orphan.is_match(r"{{orphanblahblah}}"))
    S = set_lang(r"ar")
    assert not (S.Orphan.is_match(r"{{orphan}}"))
    assert S.Orphan.is_match(r"{{يتيمة}}")
    S = set_lang(r"arz")
    assert not (S.Orphan.is_match(r"{{orphan}}"))
    assert S.Orphan.is_match(r"{{يتيمه}}")
    S = set_lang(r"hy")
    assert not (S.Orphan.is_match(r"{{orphan}}"))
    assert S.Orphan.is_match(r"{{Որբ}}")
    S = set_lang(r"ru")
    assert S.Orphan.is_match(r"{{orphan|date=февраль 2016}}")
    assert S.Orphan.is_match(r"{{изолированная статья}}")
    assert S.Orphan.is_match(r"{{Сирота}}")
    S = set_lang(r"sv")
    assert not (S.Orphan.is_match(r"{{orphan}}"))
    assert S.Orphan.is_match(r"{{föräldralös}}")
    assert S.Orphan.is_match(r"{{Föräldralös}}")
    S = set_lang(r"zh")
    assert S.Orphan.is_match(r"{{orphan}}")
    assert S.Orphan.is_match(r"{{orphan|time=2014-03-07}}")
    S = set_lang(r"fr")
    assert S.Orphan.is_match(r"{{orphan}}")
    assert S.Orphan.is_match(r"{{orphelin}}")
    S = set_lang(r"en")


def test_wikify_tests() -> None:
    S = W.for_site(EN)
    assert S.Wikify.is_match(r"{{wikify}}")
    assert S.Wikify.is_match(r"{{underlinked}}")
    assert S.Wikify.is_match(r"{{wikify|date=March 2009}}")
    assert S.Wikify.is_match(r"{{underlinked|date=March 2009}}")
    assert S.Wikify.is_match(r"{{Wikify}}")
    assert S.Wikify.is_match(r"{{Wikify|date=March 2009}}")
    assert S.Wikify.is_match(r"{{wikify|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}")
    assert not (S.Wikify.is_match(r"{{wikifyworldblah}}"))
    S = set_lang(r"sv")
    assert not (S.Wikify.is_match(r"{{wikify}}"))
    assert S.Wikify.is_match(r"{{ickewiki}}")
    S = set_lang(r"ar")
    assert not (S.Wikify.is_match(r"{{wikify}}"))
    assert S.Wikify.is_match(r"{{وصلات قليلة}}")
    S = set_lang(r"arz")
    assert not (S.Wikify.is_match(r"{{wikify}}"))
    assert S.Wikify.is_match(r"{{ويكى}}")
    S = set_lang(r"hy")
    assert not (S.Wikify.is_match(r"{{wikify}}"))
    assert S.Wikify.is_match(r"{{Վիքիֆիկացում}}")
    S = set_lang(r"ru")
    assert S.Wikify.is_match(r"{{wikify}}")
    assert S.Wikify.is_match(r"{{underlinked}}")
    S = set_lang(r"fr")
    assert S.Wikify.is_match(r"{{wikify}}")
    assert S.Wikify.is_match(r"{{Underlinked}}")
    assert S.Wikify.is_match(r"{{À wikifier}}")
    S = set_lang(r"en")


def test_dead_end_tests() -> None:
    S = W.for_site(EN)
    assert S.DeadEnd.is_match(r"{{Deadend}}")
    assert S.DeadEnd.is_match(r"{{deadend}}")
    assert S.DeadEnd.is_match(r"{{dead end}}")
    assert S.DeadEnd.is_match(r"{{deadend|date=May 2008}}")
    assert S.DeadEnd.is_match(r"{{Dead end}}")
    assert S.DeadEnd.is_match(r"{{dep}}")
    assert S.DeadEnd.is_match(r"{{dep|date=May 2008|Foobar}}")
    assert S.DeadEnd.is_match(r"{{Dead end|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}")
    S = set_lang(r"ar")
    assert S.DeadEnd.is_match(r"{{dead end}}"), r"ar dead end"
    assert S.DeadEnd.is_match(r"{{internal links}}"), r"ar dead end"
    assert S.DeadEnd.is_match(r"{{نهاية مسدودة}}"), r"ar dead end"
    S = set_lang(r"arz")
    assert S.DeadEnd.is_match(r"{{dead end}}"), r"arz dead end"
    assert not (S.DeadEnd.is_match(r"{{internal links}}")), r"arz dead end"
    assert S.DeadEnd.is_match(r"{{نهايه مسدوده}}"), r"arz dead end"
    S = set_lang(r"hy")
    assert S.DeadEnd.is_match(r"{{dead end}}"), r"hy dead end"
    assert not (S.DeadEnd.is_match(r"{{internal links}}")), r"hy dead end"
    assert S.DeadEnd.is_match(r"{{Փակ}}"), r"hy dead end"
    S = set_lang(r"ru")
    assert S.DeadEnd.is_match(r"{{dead end}}"), r"ru dead end"
    assert not (S.DeadEnd.is_match(r"{{internal links}}")), r"ru dead end"
    assert S.DeadEnd.is_match(r"{{Tупиковая статья}}"), r"ru dead end"
    S = set_lang(r"en")


def test_in_use_tests() -> None:
    S = W.for_site(EN)
    assert S.InUse.is_match(r"{{in use}}")
    assert S.InUse.is_match(r"{{inuse}}")
    assert S.InUse.is_match(r"{{in creation}}")
    assert S.InUse.is_match(r"{{GOCEinuse}}")
    assert S.InUse.is_match(r"{{GOCE in use}}")
    assert S.InUse.is_match(r"{{edited}}")
    assert S.InUse.is_match(r"{{wip}}")
    S = set_lang(r"el")
    assert S.InUse.is_match(r"{{σε χρήση}}"), r"σε χρήση"
    assert S.InUse.is_match(r"{{inuse}}")
    assert not (S.InUse.is_match(r"{{goceinuse}}")), r"goceinuse is en-only"
    S = set_lang(r"en")


def test_date_year_month_parameter_tests() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fr")
    assert S.DateYearMonthParameter == r"date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
    S = set_lang(r"sv")
    assert S.DateYearMonthParameter == r"datum={{subst:CURRENTYEAR}}-{{subst:CURRENTMONTH}}"
    S = set_lang(r"zh")
    assert S.DateYearMonthParameter == r"time={{subst:#time:c}}"
    S = set_lang(r"en")
    assert S.DateYearMonthParameter == r"date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"


def test_uncat_tests() -> None:
    S = W.for_site(EN)
    assert S.Uncategorized.is_match(r"{{Uncat|date=January 2009}}")
    assert S.Uncategorized.is_match(r"{{uncategorised|date=May 2008}}")
    assert S.Uncategorized.is_match(r"{{Uncategorised|date=May 2008}}")
    assert S.Uncategorized.is_match(r"{{Uncategorisedstub|date=May 2008}}")
    assert S.Uncategorized.is_match(r"{{Uncategorisedstub|date = May 2008}}")
    assert S.Uncategorized.is_match(
        r"{{uncategorised|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    )
    assert S.Uncategorized.match(r"{{Uncat}}").group(2) == r"Uncat"
    assert S.Uncategorized.is_match(r"{{+cat}}")
    assert S.Uncategorized.is_match(r"{{Categories missing}}")
    assert S.Uncategorized.is_match(r"{{Categories needed}}")
    assert S.Uncategorized.is_match(r"{{Categories requested}}")
    assert S.Uncategorized.is_match(r"{{Categorise}}")
    assert S.Uncategorized.is_match(r"{{Categorízame}}")
    assert S.Uncategorized.is_match(r"{{Categorize}}")
    assert S.Uncategorized.is_match(r"{{Category needed}}")
    assert S.Uncategorized.is_match(r"{{Categoryneeded}}")
    assert S.Uncategorized.is_match(r"{{Category requested}}")
    assert S.Uncategorized.is_match(r"{{Cat needed}}")
    assert S.Uncategorized.is_match(r"{{Catneeded}}")
    assert S.Uncategorized.is_match(r"{{CatNeeded}}")
    assert S.Uncategorized.is_match(r"{{Cats needed}}")
    assert S.Uncategorized.is_match(r"{{Missing categories}}")
    assert S.Uncategorized.is_match(r"{{Ncat}}")
    assert S.Uncategorized.is_match(r"{{Needs cat}}")
    assert S.Uncategorized.is_match(r"{{Needs categories}}")
    assert S.Uncategorized.is_match(r"{{Needs cats}}")
    assert S.Uncategorized.is_match(r"{{Noc}}")
    assert S.Uncategorized.is_match(r"{{Nocat}}")
    assert S.Uncategorized.is_match(r"{{No categories}}")
    assert S.Uncategorized.is_match(r"{{No category}}")
    assert S.Uncategorized.is_match(r"{{Nocategory}}")
    assert S.Uncategorized.is_match(r"{{nocats}}")
    assert S.Uncategorized.is_match(r"{{No cats}}")
    assert S.Uncategorized.is_match(r"{{Nocats}}")
    assert S.Uncategorized.is_match(r"{{Uncat}}")
    assert S.Uncategorized.is_match(r"{{Uncategorised}}")
    assert S.Uncategorized.is_match(r"{{Uncategorised stub}}")
    assert S.Uncategorized.is_match(r"{{Uncategorisedstub}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized stub}}")
    assert S.Uncategorized.is_match(r"{{Uncategorizedstub}}")
    assert S.Uncategorized.is_match(r"{{Uncat stub}}")
    assert S.Uncategorized.is_match(r"{{Uncat-stub}}")
    assert S.Uncategorized.is_match(r"{{Uncatstub}}")
    assert not (S.Uncategorized.is_match(r"{{Uncategorized other template}}"))
    assert not (S.Uncategorized.is_match(r"{{Uncategorized other template|foo=bar}}"))
    S = set_lang(r"el")
    assert S.Uncategorized.is_match(r"{{ακατηγοριοποίητο}}")
    assert S.Uncategorized.is_match(r"{{Ακατηγοριοποίητο}}")
    S = set_lang(r"hy")
    assert S.Uncategorized.is_match(r"{{Կատեգորիա չկա}}")
    assert S.Uncategorized.is_match(r"{{Կչ}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized}}")
    S = set_lang(r"ru")
    assert S.Uncategorized.is_match(r"{{Нет категорий}}")
    assert S.Uncategorized.is_match(r"{{нет категорий}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized stub}}")
    assert S.Uncategorized.is_match(r"{{Nocat}}")
    S = set_lang(r"sv")
    assert S.Uncategorized.is_match(r"{{okategoriserad}}")
    assert S.Uncategorized.is_match(r"{{okategoriserad|datum=May-2013}}")
    assert S.Uncategorized.is_match(
        r"{{okategoriserad|datum={{subst:CURRENTYEAR}}-{{subst:CURRENTMONTH}}}}"
    )
    assert S.Uncategorized.is_match(r"{{Okategoriserad}}")
    assert S.Uncategorized.is_match(r"{{uncategorizedstub}}")
    assert S.Uncategorized.is_match(r"{{uncategorized stub}}")
    assert S.Uncategorized.is_match(r"{{Uncategorised}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized}}")
    S = set_lang(r"sq")
    assert S.Uncategorized.is_match(r"{{Pa kategori}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized}}")
    S = set_lang(r"ar")
    assert S.Uncategorized.is_match(r"{{غير مصنف}}")
    assert S.Uncategorized.is_match(r"{{غير مصنفة}}")
    assert S.Uncategorized.is_match(r"{{بذرة غير مصنفة}}")
    assert S.Uncategorized.is_match(r"{{Uncategorised}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized}}")
    assert S.Uncategorized.is_match(r"{{Uncategorised stub}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized stub}}")
    assert S.Uncategorized.is_match(r"{{Uncategorizedstub}}")
    S = set_lang(r"arz")
    assert S.Uncategorized.is_match(r"{{مش متصنفه}}")
    assert S.Uncategorized.is_match(r"{{تقاوى مش متصنفه}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized}}")
    assert S.Uncategorized.is_match(r"{{Uncategorized stub}}")
    S = set_lang(r"ckb")
    assert S.Uncategorized.is_match(r"{{داڕێژە:بێ پۆل}}")
    S = set_lang(r"en")


def test_disambigs_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Disambigs, r"{{disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{disambig|surname}}")
    regex_assert.is_match(S.Disambigs, "{{\r\ndisambig|surname\r\n}}")
    regex_assert.is_match(S.Disambigs, r"{{disambig|page=Foo|page2=Bar}}")
    regex_assert.is_match(S.Disambigs, r"{{disamb}}")
    regex_assert.is_match(S.Disambigs, r"{{disamb  }}")
    regex_assert.is_match(S.Disambigs, r"{{disamb|}}")
    regex_assert.is_match(S.Disambigs, r"{{disamb|foo}}")
    regex_assert.is_match(S.Disambigs, r"{{dab}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{disambig-cleanup}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambiguation cleanup}}")
    regex_assert.is_match(S.Disambigs, r"{{Chinese title disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{chinese title disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{chinese title disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Genus disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{genus disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{hndis}}")
    regex_assert.is_match(S.Disambigs, r"{{human name disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Hndis-cleanup}}")
    regex_assert.is_match(S.Disambigs, r"{{Mathdab}}")
    regex_assert.is_match(S.Disambigs, r"{{Mathematical disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Numberdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Number disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{numberdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Letter-NumberCombdisambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Letter-NumberCombDisambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Letter-Number Combination Disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Letter–number combination disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{  disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Template:disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{template:disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{LatinNameDisambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Schooldis}}")
    regex_assert.is_match(S.Disambigs, r"{{School disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{SpeciesLatinNameDisambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Species Latin name disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Species Latin name abbreviation disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Hurricane season disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{airport disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{airport disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Call sign disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Callsigndis}}")
    regex_assert.is_match(S.Disambigs, r"{{Mil-unit-dis}}")
    regex_assert.is_match(S.Disambigs, r"{{Road disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{place name disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{station disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{geodis}}")
    regex_assert.is_match(S.Disambigs, r"{{geo-dis}}")
    regex_assert.is_match(S.Disambigs, r"{{dis}}")
    regex_assert.is_match(S.Disambigs, r"{{WoO number disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambiguation with potential}}")
    regex_assert.no_match(S.Disambigs, r"{{now disambig}}")
    regex_assert.no_match(S.Disambigs, r"{{dablink|foo}}")
    regex_assert.no_match(S.Disambigs, r"{{|foo}}")
    regex_assert.matches(r"{{dab}} <!--comm-->", S.Disambigs, r"{{dab}} <!--comm-->")
    regex_assert.matches(r"{{dab}}<!--comm-->", S.Disambigs, "{{dab}}<!--comm-->\r\nABC")
    regex_assert.is_match(W.DisambigsGeneral, r"{{Disamb}}")
    regex_assert.is_match(W.DisambigsGeneral, r"{{Disambig}}")
    regex_assert.is_match(W.DisambigsGeneral, r"{{Disambiguation}}")
    regex_assert.is_match(W.DisambigsGeneral, r"{{Dab}}")
    regex_assert.is_match(W.DisambigsCleanup, r"{{Disambig-cleanup}}")
    regex_assert.is_match(W.DisambigsCleanup, r"{{Disambig cleanup}}")
    regex_assert.is_match(W.DisambigsCleanup, r"{{Disambiguation cleanup}}")
    regex_assert.is_match(
        W.DisambigsCleanup, r"{{Disambiguation cleanup}} <!-- page needs cleanup-->"
    )
    S = set_lang(r"sv")
    regex_assert.is_match(S.Disambigs, r"{{Förgrening}}")
    regex_assert.is_match(S.Disambigs, r"{{Betydelselista}}")
    regex_assert.is_match(S.Disambigs, r"{{Dab}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Flertydig}}")
    regex_assert.is_match(S.Disambigs, r"{{Förgreningssida}}")
    regex_assert.is_match(S.Disambigs, r"{{gaffel}}")
    regex_assert.is_match(S.Disambigs, r"{{gren}}")
    regex_assert.is_match(S.Disambigs, r"{{Grensida}}")
    regex_assert.is_match(S.Disambigs, r"{{Ortnamn}}")
    regex_assert.is_match(S.Disambigs, r"{{Trebokstavsförgrening}}")
    regex_assert.is_match(S.Disambigs, r"{{4LA}}")
    regex_assert.is_match(S.Disambigs, r"{{Namnförgrening}}")
    regex_assert.is_match(S.Disambigs, r"{{Hndis}}")
    regex_assert.is_match(S.Disambigs, r"{{Namngrensida}}")
    regex_assert.is_match(S.Disambigs, r"{{Efternamn}}")
    regex_assert.is_match(S.Disambigs, r"{{Förnamn}}")
    regex_assert.is_match(S.Disambigs, r"{{Robotskapad förgrening}}")
    S = set_lang(r"de")
    regex_assert.is_match(S.Disambigs, r"{{Begriffsklärung}}")
    S = set_lang(r"ca")
    regex_assert.is_match(S.Disambigs, r"{{Desambiguació}}")
    regex_assert.is_match(S.Disambigs, r"{{Desambigua}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    S = set_lang(r"es")
    regex_assert.is_match(S.Disambigs, r"{{Desambiguación}}")
    regex_assert.is_match(S.Disambigs, r"{{Desambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Des}}")
    regex_assert.is_match(S.Disambigs, r"{{Desambiguacion}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    S = set_lang(r"el")
    regex_assert.is_match(S.Disambigs, r"{{disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Αποσαφήνιση}}")
    regex_assert.is_match(S.Disambigs, r"{{αποσαφήνιση}}")
    regex_assert.is_match(S.Disambigs, r"{{Αποσαφ}}")
    regex_assert.is_match(S.Disambigs, r"{{αποσαφ}}")
    S = set_lang(r"pl")
    regex_assert.is_match(S.Disambigs, r"{{disambig}}")
    S = set_lang(r"ar")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{توضيح}}")
    regex_assert.is_match(S.Disambigs, r"{{صفحة توضيح}}")
    regex_assert.is_match(S.Disambigs, r"{{أسمياء}}")
    S = set_lang(r"arz")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{صفحة توضيح}}")
    regex_assert.is_match(S.Disambigs, r"{{توضيح}}")
    S = set_lang(r"fa")
    regex_assert.is_match(S.Disambigs, r"{{ابهام‌زدایی}}")
    regex_assert.is_match(S.Disambigs, r"{{ابهامزدایی}}")
    regex_assert.is_match(S.Disambigs, r"{{ابهام زدایی}}")
    S = set_lang(r"ru")
    regex_assert.is_match(S.Disambigs, r"{{АТДы}}")
    regex_assert.is_match(S.Disambigs, r"{{Военные части}}")
    regex_assert.is_match(S.Disambigs, r"{{Воинские формирования}}")
    regex_assert.is_match(S.Disambigs, r"{{Воинские части}}")
    regex_assert.is_match(S.Disambigs, r"{{Горы}}")
    regex_assert.is_match(S.Disambigs, r"{{ЖДС}}")
    regex_assert.is_match(S.Disambigs, r"{{Ждс}}")
    regex_assert.is_match(S.Disambigs, r"{{Многозначность}}")
    regex_assert.is_match(S.Disambigs, r"{{НПы}}")
    regex_assert.is_match(S.Disambigs, r"{{Неоднозначность}}")
    regex_assert.is_match(S.Disambigs, r"{{Неоднозначность2}}")
    regex_assert.is_match(S.Disambigs, r"{{Нпы}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноименные фильмы}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые НП}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые воинские части}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые горные объекты}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые горы}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые железнодорожные станции}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые координаты}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые корабли}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые монастыри}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые муниципальные образования}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые муниципальные образования}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые населённые пункты}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые объекты АТД}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые озёра}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые острова}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые памятники}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые площади}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые реки}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые станции}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые станции метро}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые улицы}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые фильмы}}")
    regex_assert.is_match(S.Disambigs, r"{{Одноимённые храмы}}")
    regex_assert.is_match(S.Disambigs, r"{{Однофамильцы-тёзки}}")
    regex_assert.is_match(S.Disambigs, r"{{Озёра}}")
    regex_assert.is_match(S.Disambigs, r"{{Острова}}")
    regex_assert.is_match(S.Disambigs, r"{{Реки}}")
    regex_assert.is_match(S.Disambigs, r"{{Список однофамильцев}}")
    regex_assert.is_match(S.Disambigs, r"{{Список однофамильцев-тёзок}}")
    regex_assert.is_match(S.Disambigs, r"{{Список полных тёзок}}")
    regex_assert.is_match(S.Disambigs, r"{{Список тёзок}}")
    regex_assert.is_match(S.Disambigs, r"{{Список тёзок-однофамильцев}}")
    regex_assert.is_match(S.Disambigs, r"{{Станции}}")
    regex_assert.is_match(S.Disambigs, r"{{Тёзки-однофамильцы}}")
    regex_assert.is_match(S.Disambigs, r"{{Churchdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Coorddis}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambig}}")
    regex_assert.is_match(S.Disambigs, r"{{Disambiguation}}")
    regex_assert.is_match(S.Disambigs, r"{{Metrodis}}")
    regex_assert.is_match(S.Disambigs, r"{{Militarydis}}")
    regex_assert.is_match(S.Disambigs, r"{{Mondis}}")
    regex_assert.is_match(S.Disambigs, r"{{Monumdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Mountaindis}}")
    regex_assert.is_match(S.Disambigs, r"{{Moviedis}}")
    regex_assert.is_match(S.Disambigs, r"{{Placedis}}")
    regex_assert.is_match(S.Disambigs, r"{{Riverdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Roaddis}}")
    regex_assert.is_match(S.Disambigs, r"{{Shipdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Stationdis}}")
    regex_assert.is_match(S.Disambigs, r"{{Surname}}")
    S = set_lang(r"en")


def test_si_as_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.SIAs, r"{{Chemistry index}}")
    regex_assert.is_match(S.SIAs, r"{{Enzyme index}}")
    regex_assert.is_match(S.SIAs, r"{{Lake index}}")
    regex_assert.is_match(S.SIAs, r"{{Media set index}}")
    regex_assert.is_match(S.SIAs, r"{{Molecular formula index}}")
    regex_assert.is_match(S.SIAs, r"{{MolFormIndex}}")
    regex_assert.is_match(S.SIAs, r"{{mountain index}}")
    regex_assert.is_match(S.SIAs, r"{{mountainindex}}")
    regex_assert.is_match(S.SIAs, r"{{Roadindex}}")
    regex_assert.is_match(S.SIAs, r"{{Road index}}")
    regex_assert.is_match(S.SIAs, r"{{Shipindex}}")
    regex_assert.is_match(S.SIAs, r"{{sportindex}}")
    regex_assert.is_match(S.SIAs, r"{{sport index}}")
    regex_assert.is_match(S.SIAs, r"{{storm index}}")
    regex_assert.is_match(S.SIAs, r"{{Painting index}}")
    regex_assert.is_match(S.SIAs, r"{{Locomotive index}}")
    regex_assert.is_match(S.SIAs, r"{{Animal common name}}")
    regex_assert.is_match(S.SIAs, r"{{Fungus common name}}")
    regex_assert.is_match(S.SIAs, r"{{Plant common name}}")
    regex_assert.is_match(S.SIAs, r"{{surname}}")
    regex_assert.is_match(S.SIAs, r"{{surnames}}")
    regex_assert.is_match(S.SIAs, r"{{Nickname}}")
    regex_assert.is_match(S.SIAs, r"{{given name}}")
    regex_assert.is_match(S.SIAs, r"{{SIA}}")
    regex_assert.is_match(S.SIAs, r"{{sia}}")
    regex_assert.is_match(S.SIAs, r"{{set index}}")
    regex_assert.is_match(S.SIAs, r"{{set index article}}")
    regex_assert.no_match(S.SIAs, r"{{surname-stub}}")
    regex_assert.is_match(S.SIAs, r"{{set index article|param}}")
    S = set_lang(r"ar")
    regex_assert.is_match(S.SIAs, r"{{الاسم الشائع للحيوان}}")
    S = set_lang(r"en")


def test_wi_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(W.Wi, r"{{Wiktionary redirect}}")
    regex_assert.is_match(W.Wi, r"{{wiktionary redirect}}")
    regex_assert.is_match(W.Wi, r"{{wi}}")
    regex_assert.is_match(W.Wi, r"{{Wi}}")
    regex_assert.is_match(W.Wi, r"{{Moved to Wiktionary}}")
    regex_assert.is_match(W.Wi, r"{{RedirecttoWiktionary}}")
    regex_assert.is_match(W.Wi, r"{{Seewiktionary}}")
    regex_assert.is_match(W.Wi, r"{{Wikiquote redirect}}")
    regex_assert.is_match(W.Wi, r"{{Wikivoyage redirect}}")


def test_extract_title_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.ExtractTitle, r"https://en.wikipedia.org/wiki/Foo")
    regex_assert.is_match(S.ExtractTitle, r"https://en.wikipedia.org/wiki/Foo_bar")
    assert S.ExtractTitle.match(r"https://en.wikipedia.org/wiki/Foo").group(1) == r"Foo"
    assert (
        S.ExtractTitle.match(r"https://en.wikipedia.org/w/index.php?title=Foo").group(1) == r"Foo"
    )
    assert S.ExtractTitle.match(r"https://en.wikipedia.org/w/index.php/Foo").group(1) == r"Foo"
    assert (
        S.ExtractTitle.match(r"https://en.wikipedia.org/w/index.php/Foo bar here").group(1)
        == r"Foo bar here"
    )
    regex_assert.no_match(S.ExtractTitle, r"https://random.org/wiki/Foo")
    regex_assert.no_match(S.ExtractTitle, r"https://en.wikipedia.org/wikirandom/Foo")


def test_empty_link_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.EmptyLink, r"[[]]")
    regex_assert.is_match(S.EmptyLink, r"[[   ]]")
    regex_assert.is_match(S.EmptyLink, r"[[|]]")
    regex_assert.is_match(S.EmptyLink, r"[[       |    ]]")
    regex_assert.is_match(S.EmptyLink, r"[[Category:]]")
    regex_assert.is_match(S.EmptyLink, r"[[ Category:]]")
    regex_assert.is_match(S.EmptyLink, r"[[Category:|]]")
    regex_assert.is_match(S.EmptyLink, r"[[Category:|A]]")
    regex_assert.is_match(S.EmptyLink, r"[[Image:]]")
    regex_assert.is_match(S.EmptyLink, r"[[File:]]")
    regex_assert.is_match(S.EmptyLink, r"[[File:|]]")
    regex_assert.is_match(S.EmptyLink, r"[[category:]]")
    regex_assert.is_match(S.EmptyLink, r"[[IMAGE:]]")
    regex_assert.is_match(S.EmptyLink, r"[[file:]]")


def test_empty_template_tests() -> None:
    S = W.for_site(EN)
    regex_assert.no_match(S.EmptyTemplate, r"{{TemplateTest}}")
    regex_assert.no_match(S.EmptyTemplate, r"{{Test}}")
    regex_assert.no_match(S.EmptyTemplate, r"{{Test|Parameter}}")
    regex_assert.no_match(S.EmptyTemplate, r"{{Test|}}")
    regex_assert.is_match(S.EmptyTemplate, r"{{Template:}}")
    regex_assert.is_match(S.EmptyTemplate, r"{{Template: }}")
    regex_assert.is_match(S.EmptyTemplate, r"{{template:}}")
    regex_assert.is_match(S.EmptyTemplate, r"{{}}")
    regex_assert.is_match(S.EmptyTemplate, r"{{|}}")
    regex_assert.is_match(S.EmptyTemplate, r"{{          }}")
    regex_assert.is_match(S.EmptyTemplate, r"{{|||||}}")
    regex_assert.is_match(S.EmptyTemplate, r"{{       || }}")


def test_months_tests() -> None:
    S = W.for_site(EN)
    mo = DotNetRegex(S.Months)
    assert mo.match(r"in January there").group(1) == r"January"
    mong = DotNetRegex(S.MonthsNoGroup)
    assert len(mong.match(r"in January there").group(1)) == 0


def test_defaultsort_tests() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.Defaultsort, r"{{DEFAULTSORT:foo}}")
    regex_assert.is_match(S.Defaultsort, r"{{DEFAULTSORT|foo}}")
    regex_assert.is_match(S.Defaultsort, r"{{DEFAULTSORT:foo bar}}")
    regex_assert.is_match(S.Defaultsort, "{{DEFAULTSORT:foo\r\n")
    regex_assert.no_match(S.Defaultsort, r"{{DEFAULTSORT:foo")
    regex_assert.is_match(S.Defaultsort, r"{{DEFAULTSORT:}}")
    assert len(S.Defaultsort.match(r"{{DEFAULTSORT:}}").group(r"key")) == 0
    regex_assert.is_match(S.Defaultsort, "{{DEFAULTSORT:\r\nWangchuck, Tshering Pem}}")
    regex_assert.is_match(S.Defaultsort, "{{DEFAULTSORT:\r\nWangchuck, Tshering Pem\r\n}}")
    assert S.Defaultsort.match(r"{{DEFAULTSORT:foo}}").group(r"key") == r"foo"
    assert S.Defaultsort.match("{{DEFAULTSORT:\r\nfoo}}").group(r"key") == r"foo"
    assert S.Defaultsort.match(r"{{DEFAULTSORT:{{PAGENAME}}}}").group(r"key") == r"{{PAGENAME}}"
    assert S.Defaultsort.match(r"{{DEFAULTSORT:foo}}").value == r"{{DEFAULTSORT:foo}}"
    assert S.Defaultsort.match("{{DEFAULTSORT:foo\r\nnow").value == "{{DEFAULTSORT:foo\r"
    assert (
        S.Defaultsort.match(r"{{DEFAULTSORT:{{PAGENAME}}}}").value
        == r"{{DEFAULTSORT:{{PAGENAME}}}}"
    )
    assert S.Defaultsort.match("{{DEFAULTSORT:foo]]\r\npp").value == r"{{DEFAULTSORT:foo]]" + "\r"
    assert (
        S.Defaultsort.match("{{DEFAULTSORT:foo]]\r\npp\r\n{{x}}\r\n").value
        == r"{{DEFAULTSORT:foo]]" + "\r"
    )
    assert S.Defaultsort.match("{{DEFAULTSORT:foo\r\n}}").value == "{{DEFAULTSORT:foo\r\n}}"
    S = set_lang(r"en")
    ds = list([r"DEFAULTSORT", r"dsort"])
    S = set_site(magic_words={**current_site().magic_words, r"defaultsort": tuple(ds)})
    regex_assert.is_match(S.Defaultsort, r"{{DEFAULTSORT:foo}}")
    regex_assert.is_match(S.Defaultsort, r"{{dsort:foo}}")
    S = set_site(
        magic_words={k: v for k, v in current_site().magic_words.items() if k != r"defaultsort"}
    )
    assert S.Defaultsort.match(r"{{DEFAULTSORT:foo}}<!--comm-->").value == r"{{DEFAULTSORT:foo}}", (
        r"comment after DEFAULTSORT not extracted"
    )
    S = set_lang(r"sv")
    assert S.Defaultsort.match(r"{{DEFAULTSORT:foo}}").value == r"{{DEFAULTSORT:foo}}"
    assert (
        S.Defaultsort.match(r"{{DEFAULTSORT:foo}} <!--comm-->").value
        == r"{{DEFAULTSORT:foo}} <!--comm-->"
    ), r"comment after DEFAULTSORT allowed for sv-wiki"
    assert (
        S.Defaultsort.match(r"{{DEFAULTSORT:foo}}<!--comm-->").value
        == r"{{DEFAULTSORT:foo}}<!--comm-->"
    ), r"comment after DEFAULTSORT allowed for sv-wiki"
    S = set_lang(r"en")


def test_international_dates() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.InternationalDates, r"On 11 July 2009")
    regex_assert.is_match(S.InternationalDates, r"On 11 July  2009")
    regex_assert.is_match(S.InternationalDates, r"On 1 July 1809")
    regex_assert.is_match(S.InternationalDates, r"On 11&nbsp;July 2009")
    regex_assert.no_match(S.InternationalDates, r"On 11 July 44")
    regex_assert.no_match(S.InternationalDates, r"On July 11, 2009 a")


def test_american_dates() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.AmericanDates, r"On July 11, 2009 a")
    regex_assert.is_match(S.AmericanDates, r"On July 11 2009 a")
    regex_assert.is_match(S.AmericanDates, r"On July 11,  1809 a")
    regex_assert.is_match(S.AmericanDates, r"On July&nbsp;11, 2009 a")
    regex_assert.no_match(S.AmericanDates, r"On July 11, 29 a")
    regex_assert.no_match(S.AmericanDates, r"On 11 July 2009")


def test_month_day() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.MonthDay, r"On July 11, 2009 a")
    regex_assert.is_match(S.MonthDay, r"On July 11 a")
    regex_assert.is_match(S.MonthDay, r"On July&nbsp;11 a")
    regex_assert.is_match(S.MonthDay, r"On July 11–12 a")
    regex_assert.is_match(S.MonthDay, r"On July 11,  1809 a")
    regex_assert.no_match(S.MonthDay, r"In July 07, a")
    regex_assert.no_match(S.MonthDay, r"In July 2007, a")


def test_day_month() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.DayMonth, r"On 11 July, 2009 a")
    regex_assert.is_match(S.DayMonth, r"On 11 July 2009 a")
    regex_assert.is_match(S.DayMonth, r"On 11 July a")
    regex_assert.is_match(S.DayMonth, r"On 11&nbsp;July a")
    regex_assert.is_match(S.DayMonth, r"On 11–12 July a")
    regex_assert.is_match(S.DayMonth, r"On 11 July,  1809 a")
    regex_assert.no_match(S.DayMonth, r"In 07 July, a")
    regex_assert.no_match(S.DayMonth, r"In July 27, a")


def test_month_day_range_span() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.MonthDayRangeSpan, r"On July 11–12 a")
    regex_assert.is_match(S.MonthDayRangeSpan, r"On July 11–12, 2004 a")
    regex_assert.is_match(S.MonthDayRangeSpan, r"On July 11–12 2004 a")
    regex_assert.is_match(S.MonthDayRangeSpan, r"On July 11&ndash;12 a")
    regex_assert.is_match(S.MonthDayRangeSpan, r"On July 11{{ndash}}12 a")
    regex_assert.is_match(S.MonthDayRangeSpan, r"On July 11/12 a")
    regex_assert.no_match(S.MonthDayRangeSpan, r"On July 11-12 a")
    regex_assert.no_match(S.MonthDayRangeSpan, r"On July 1112 a")
    regex_assert.no_match(S.MonthDayRangeSpan, r"On July 11 12 a")
    regex_assert.no_match(S.MonthDayRangeSpan, r"On 11–12 July a")


def test_day_month_range_span() -> None:
    S = W.for_site(EN)
    regex_assert.is_match(S.DayMonthRangeSpan, r"On 11–12 July a")
    regex_assert.is_match(S.DayMonthRangeSpan, r"On 11–12 July, 2004 a")
    regex_assert.is_match(S.DayMonthRangeSpan, r"On 11&ndash;12 July a")
    regex_assert.is_match(S.DayMonthRangeSpan, r"On 11{{ndash}}12 July a")
    regex_assert.is_match(S.DayMonthRangeSpan, r"On 11/12 July a")
    regex_assert.no_match(S.DayMonthRangeSpan, r"On 11-12 July a")
    regex_assert.no_match(S.DayMonthRangeSpan, r"On 1112 July a")
    regex_assert.no_match(S.DayMonthRangeSpan, r"On  11 12 July a")
    regex_assert.no_match(S.DayMonthRangeSpan, r"On July 11–12 a")


def test_link_fg_as() -> None:
    S = W.for_site(EN)
    assert S.LinkFGAs.is_match(r"foo {{Link FA|ar}}")
    assert S.LinkFGAs.is_match(r"foo {{Link GA|ar}}")
    assert S.LinkFGAs.is_match(r"foo {{link FA|ar}}")
