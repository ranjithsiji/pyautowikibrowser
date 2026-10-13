"""Port of the ListMakerTests, ListComparerTests and ListBoxArticleTests fixtures in AWB
UnitTests/MiscellaneousTests.cs: the page list model (pyawb.lists.listmaker).

ListMakerTests converted by tools/porting/nunit2py.py, then edited by hand; the other two are ported
by hand, with AWB's ListBox controls replaced by plain lists: compare_lists returns the three lists
AWB filled in, and ArticleList holds the selection ListBoxArticle had. The Mono-only branches in AWB
are left out.
"""

from pyawb.core.article import Article
from pyawb.lists.listmaker import ArticleList as ListMaker
from pyawb.lists.listmaker import compare_lists

big = 10000
big = 500


def test_normalize_title() -> None:
    LMaker = ListMaker()
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&diff=3&oldid=4")
        == r"Foo"
    )
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&diff=3&curid=4")
        == r"Foo"
    )
    assert (
        LMaker.normalize_title(
            r"https://en.wikipedia.org/w/index.php?title=Health_effects_of_chocolate&diff=4018&oldid=40182"
        )
        == r"Health effects of chocolate"
    )
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&action=history")
        == r"Foo"
    )
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&action=edit")
        == r"Foo"
    )
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&oldid=5") == r"Foo"
    )
    assert (
        LMaker.normalize_title(
            r"https://en.wikipedia.org/w/index.php?title=Science%20%28journal%29&action=history"
        )
        == r"Science (journal)"
    )
    assert (
        LMaker.normalize_title(
            r"https://en.wikipedia.org/w/index.php?title=Wikipedia:AutoWikiBrowser/Sandbox&action=edit"
        )
        == r"Wikipedia:AutoWikiBrowser/Sandbox"
    )
    assert (
        LMaker.normalize_title(
            r"en.wikipedia.org/w/index.php?title=Wikipedia:AutoWikiBrowser/Sandbox&action=edit"
        )
        == r"Wikipedia:AutoWikiBrowser/Sandbox"
    )
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo#References")
        == r"Foo"
    )
    assert LMaker.normalize_title(r"   Foo") == r"Foo", (
        r"cleans spacing from Firefox Category paste"
    )
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&pe=1&#Date_on")
        == r"Foo"
    )
    assert LMaker.normalize_title(r"Foo‎") == r"Foo", r"title has left-to-right mark at the end"
    assert (
        LMaker.normalize_title(
            r"https://en.wikipedia.org/w/index.php?title=Foo&offset=20130214190000&action=history"
        )
        == r"Foo"
    ), r"cleans spacing from Firefox Category paste"
    assert LMaker.normalize_title(r"https://en.wikipedia.org/w/?title=Foo") == r"Foo"
    assert LMaker.normalize_title(r"https://en.wikipedia.org/wiki/Foo") == r"Foo"
    assert LMaker.normalize_title(r"http://en.wikipedia.org/wiki/Foo") == r"Foo", (
        r"HTTP not HTTPS support"
    )
    assert (
        LMaker.normalize_title(r"//en.wikipedia.org/w/index.php?title=Foo&action=history") == r"Foo"
    ), r"Protocol-relative support"
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&redirect=no")
        == r"Foo"
    )
    assert (
        LMaker.normalize_title(
            r"https://en.wikipedia.org/w/index.php?title=Foo&type=revision&diff=75558108&oldid=65316243"
        )
        == r"Foo"
    )
    assert LMaker.normalize_title(r"#[[Foo]]") == r"#[[Foo]]", r"#wikilinked"
    assert LMaker.normalize_title(r"Foo#bar") == r"Foo", r"#wikilinked"
    assert (
        LMaker.normalize_title(
            r"https://en.wikipedia.org/w/index.php?title=Sandeep+Nayak&diff=prev&oldid=1320026009"
        )
        == r"Sandeep Nayak"
    )


def test_normalize_title_secure() -> None:
    LMaker = ListMaker()
    assert (
        LMaker.normalize_title(r"https://en.wikipedia.org/w/index.php?title=Foo&diff=3&oldid=4")
        == r"Foo"
    )


def test_remove_list_duplicates_simple() -> None:
    LMakerRLD = ListMaker()
    LMakerRLD.add(Article(r"A"))
    LMakerRLD.add(Article(r"B"))
    LMakerRLD.add(Article(r"C"))
    LMakerRLD.add(Article(r"A"))
    LMakerRLD.remove_list_duplicates()
    assert len(LMakerRLD) == 3, r"Duplicate removed"
    for a in LMakerRLD:
        assert str(a) == r"A", r"Duplicates removed from end of list"
        break


def test_remove_list_duplicates10_k() -> None:
    # Hand-ported (for loop)
    big = 10000
    LMakerLarge = ListMaker()
    LMakerLarge.clear()
    for i in range(1, big):
        LMakerLarge.add(Article(str(i)))
    LMakerLarge.add(Article("1"))
    assert LMakerLarge.count == big
    LMakerLarge.remove_list_duplicates()
    assert LMakerLarge.count == big - 1, "Duplicate removed"
    assert LMakerLarge.contains(Article("1")), "First instance of article retained"


def test_filter_non_main_articles_volume() -> None:
    # Hand-ported (for loop)
    big = 500
    LMakerLarge = ListMaker()
    LMakerLarge.clear()
    for i in range(1, big):
        LMakerLarge.add(str(i))
    LMakerLarge.add("Talk:Me")
    LMakerLarge.filter_non_main_articles()
    assert LMakerLarge.count == big - 1, "Non-mainspace article removed"


def test_filter_non_main_articles() -> None:
    LMaker = ListMaker()
    LMaker.add(r"One")
    LMaker.add(r"Two")
    LMaker.add(r"Talk:Three")
    LMaker.add(r"Four")
    LMaker.add(r"Talk:Five")
    LMaker.add(r"Talk:Five2")
    LMaker.add(r"Six")
    LMaker.filter_non_main_articles()
    assert LMaker.number_of_articles == 4


def test_add_list() -> None:
    LMaker = ListMaker()
    l = []
    l.append(Article(r"A"))
    l.append(Article(r"B"))
    LMaker.add(r"A")
    LMaker.add(r"B")
    LMaker.filter_duplicates = True
    LMaker.add(l)
    assert LMaker.number_of_articles == 2
    l.append(Article(r"C"))
    LMaker.add(l)
    assert LMaker.number_of_articles == 3
    l.append(Article(r"C"))
    l.append(Article(r"C"))
    l.append(Article(r"C"))
    l.append(Article(r"C"))
    LMaker.add(r"D")
    LMaker.add(l)
    assert LMaker.number_of_articles == 4


def test_get_article_list() -> None:
    LMaker = ListMaker()
    LMaker.add(r"A")
    LMaker.add(r"B")
    assert len(LMaker.get_article_list()) == 2
    LMaker.set_selected(0, True)
    LMaker.set_selected(1, True)
    assert len(LMaker.get_selected_article_list()) == 2
    LMaker.set_selected(1, False)
    assert len(LMaker.get_selected_article_list()) == 1
    assert len(LMaker.get_article_list()) == 2


def test_list_comparer_simple() -> None:
    LMaker = ListMaker()
    LMaker.add(Article("A"))
    LMaker.add(Article("B"))
    LMaker.add(Article("C"))
    LMaker.add(Article("C"))  # duplicate, removed during compare
    articles = [Article("A"), Article("D"), Article("E")]
    lb1, lb2, lb3 = compare_lists(LMaker.get_article_list(), articles)
    # unique in 1
    assert "B" in lb1
    assert "C" in lb1
    assert "A" not in lb1
    assert len(lb1) == 2
    # unique in 2
    assert "A" not in lb2
    assert "D" in lb2
    assert "E" in lb2
    assert len(lb2) == 2
    # common to both
    assert "A" in lb3
    assert len(lb3) == 1


def test_list_comparer10_k() -> None:
    big = 10000
    LMakerC10K = ListMaker()
    for i in range(big):
        LMakerC10K.add(Article(str(i)))
    LMakerC10K.add(Article("A"))
    LMakerC10K.add(Article("B"))
    articlesC = [Article(str(i)) for i in range(big)]
    articlesC.append(Article("C"))
    articlesC.append(Article("D"))
    lb1, lb2, lb3 = compare_lists(LMakerC10K.get_article_list(), articlesC)
    # unique in 1
    assert "A" in lb1
    assert "B" in lb1
    # unique in 2
    assert "C" in lb2
    assert "D" in lb2
    # common to both
    assert "1" in lb3
    assert len(lb3) == big


def test_remove_selected() -> None:
    lbArticles = ListMaker()
    big, sel = 70000, 5000

    # sequential block deletion performance
    for i in range(big):
        lbArticles.add(Article(str(i)))
    for j in range(sel, 0, -1):
        lbArticles.set_selected(big - j, True)
    lbArticles.remove_selected(True)
    assert lbArticles.count == big - sel

    # single selected item deletion performance
    lbArticles.clear()
    for i in range(big * 3):
        lbArticles.add(Article(str(i)))
    lbArticles.set_selected(big // 2, True)
    lbArticles.remove_selected(True)
    assert lbArticles.count == big * 3 - 1

    # non-sequential deletion
    lbArticles.clear()
    for i in range(10):
        lbArticles.add(Article(str(i)))
    lbArticles.set_selected(1, True)
    lbArticles.set_selected(3, True)
    lbArticles.remove_selected(True)
    assert Article("1") not in lbArticles
    assert Article("3") not in lbArticles
    assert Article("2") in lbArticles

    lbArticles.clear()
    for i in range(10):
        lbArticles.add(Article(str(i)))
    lbArticles.set_selected(1, True)
    lbArticles.set_selected(5, True)
    lbArticles.remove_selected(True)
    assert Article("1") not in lbArticles
    assert Article("5") not in lbArticles
    assert Article("2") in lbArticles

    lbArticles.clear()
    lbArticles.add(Article("A"))
    lbArticles.add(Article("A"))
    lbArticles.add(Article("B"))
    lbArticles.set_selected(2, True)
    lbArticles.remove_selected(False)
    assert lbArticles.count == 2, "Duplicates not removed if not in duplicate mode"

    lbArticles.clear()
    lbArticles.add(Article("A"))
    lbArticles.add(Article("B"))
    lbArticles.add(Article("C"))
    lbArticles.set_selected(0, True)
    lbArticles.set_selected(1, True)
    lbArticles.set_selected(2, True)
    lbArticles.remove_selected(False)
    assert lbArticles.count == 0, "List cleared if all items selected and removed"
