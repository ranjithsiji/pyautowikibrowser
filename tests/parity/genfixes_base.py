"""Stand-in for AWB's GenfixesTestsBase until the Article general-fixes pipeline is ported.

AWB's helper runs the whole pipeline (Article.PerformGeneralFixes). Tests that use it are marked
as expected failures at that point, so the rest of each test file still runs and the dependency
stays visible.
"""

from collections.abc import Callable
from typing import NoReturn

import pytest

_REASON = "needs the Article general-fixes pipeline (not ported yet)"


class GenfixesTestsBase:
    def __getattr__(self, name: str) -> Callable[..., NoReturn]:
        def pending(*args: object, **kwargs: object) -> NoReturn:
            pytest.xfail(_REASON)

        return pending


genFixes = GenfixesTestsBase()
