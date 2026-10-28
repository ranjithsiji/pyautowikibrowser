"""Disambiguation (AWB DabForm.cs / DabControl.cs)."""

from pyawb.rules import disambiguation as dab

TEXT = "Intro.\nThe [[Mercury]] rises. [[mercury|metal]]s are heavy; see [[Mercury (planet)]].\nEnd"


def test_find_links_and_context() -> None:
    links = dab.find_links(TEXT, "Mercury", 10)
    assert [lk.value for lk in links] == ["[[Mercury]]", "[[mercury|metal]]s"]
    first, second = links
    assert first.paragraph.startswith("The [[Mercury]]") and first.paragraph.endswith("]].")
    assert first.visible_link == first.real_link == "Mercury" and not first.start_of_sentence
    assert second.visible_link == "metal" and second.real_link == "mercury"
    assert second.link_trail == "s" and second.start_of_sentence  # after "rises."
    assert TEXT.startswith(first.surroundings, first.surroundings_start)
    last = dab.find_links("See [[Mercury]].", "Mercury", 5)[0]
    assert last.paragraph == "See [[Mercury]]."  # AWB lost the final "."


def test_choices() -> None:
    first, second = dab.find_links(TEXT, "Mercury", 10)
    variants = ["Mercury (planet)", "mercury (element)"]
    assert first.choice(dab.NO_CHANGE, variants) == "[[Mercury]]"
    assert first.choice(dab.UNLINK, variants) == "Mercury"
    assert first.choice(dab.DAB_NEEDED, variants).startswith("[[Mercury]]{{Disambiguation needed|")
    assert first.choice(3, variants) == "[[Mercury (planet)|Mercury]]"
    # start of a sentence: the variant's first letter goes up; the link trail stays outside
    assert second.choice(4, variants) == "[[Mercury (element)|metal]]s"
    assert second.choice(dab.UNLINK, variants) == "metals"


def test_unpipe_and_flip() -> None:
    assert dab.unpipe("[[Mercury (planet)|Mercury]]s") == "[[Mercury (planet)]]s"
    assert dab.flip("[[A|B]]") == "[[B|A]]"


def test_apply_by_position_and_punctuation() -> None:
    text = "[[Mercury]] and [[Mercury]]."
    new, changed = dab.apply(text, "Mercury", [None, "[[Mercury]]" + dab.DAB_NEEDED_TAG])
    assert changed
    assert new == "[[Mercury]] and [[Mercury]]." + dab.DAB_NEEDED_TAG
    assert dab.apply(text, "Mercury", [None, None]) == (text, False)


def test_several_targets_and_variants() -> None:
    links = dab.find_links("[[Foo]] [[bar]] [[Baz]]", "Foo|Bar", 5)
    assert [lk.real_link for lk in links] == ["Foo", "bar"]
    assert dab.variants_from_links(["1999", "2150", "Foo (band)", "١٢"]) == [
        "2150",
        "Foo (band)",
        "١٢",
    ]
    assert dab.clean_variants(["  A ", "", "B"]) == ["A", "B"]


def test_malayalam_link_trail() -> None:
    """AWB's trail is cased letters (Ll, Lu, Lt, Lm) and Pc: scripts without case (Lo, such as
    Malayalam) get no trail, so the text after the link stays outside it."""
    links = dab.find_links("[[കേരളം]]ത്തിൽ", "കേരളം", 5)
    assert links and links[0].real_link == "കേരളം" and links[0].link_trail == ""
