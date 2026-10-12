from collections.abc import Iterator

import pytest

from awb_l.core.site import SiteConfig, use_site


@pytest.fixture(autouse=True)
def _english_wikipedia() -> Iterator[None]:
    """Each AWB test starts on English Wikipedia; set_lang() changes are undone afterwards."""
    with use_site(SiteConfig.english()):
        yield
