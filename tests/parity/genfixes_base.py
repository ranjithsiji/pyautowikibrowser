"""Port of AWB's GenfixesTestsBase (UnitTests/GenfixesTests.cs): runs text through the Article
general-fixes pipeline, as AWB does when saving a page with general fixes on."""

from pyawb.core.article import Article, SkipOptions
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.parsers import Parsers


class GenfixesTestsBase:
    def __init__(self) -> None:
        self.parser = Parsers()
        self._a = Article("Test")
        self._h = HideText(False, True, True)
        self._s = SkipOptions()

    def gen_fixes(self, arg: bool | str = True) -> None:
        """AWB's GenFixes(), GenFixes(replaceReferenceTags) and GenFixes(articleTitle)."""
        replace_reference_tags = True
        if isinstance(arg, str):
            self._a = Article(arg, self._a.article_text)
        else:
            replace_reference_tags = arg
        self._a.perform_general_fixes(
            self.parser, self._h, self._s, replace_reference_tags, False, False
        )

    def talk_gen_fixes(self) -> None:
        self._a.perform_talk_general_fixes(self._h)

    @property
    def article_text(self) -> str:
        return self._a.article_text

    @article_text.setter
    def article_text(self, value: str) -> None:
        self._a = Article(self._a.name, value)

    def assert_change(self, text: str, expected: str) -> None:
        self.article_text = text
        self.gen_fixes()
        assert self.article_text == expected

    def assert_not_changed(
        self, text: str, article_title: str | None = None, message: str = "unit test"
    ) -> None:
        self.article_text = text
        if article_title is None:
            self.gen_fixes()
            assert self.article_text == text
        else:
            self.gen_fixes(article_title)
            assert self.article_text == text, message


genFixes = GenfixesTestsBase()
