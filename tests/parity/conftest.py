from collections.abc import Iterator

import pytest

from awb_x.core.site import SiteConfig, use_site


@pytest.fixture(autouse=True)
def _english_wikipedia() -> Iterator[None]:
    """Each AWB test starts on English Wikipedia; set_lang() changes are undone afterwards."""
    with use_site(SiteConfig.english()):
        yield


@pytest.fixture(autouse=True, scope="session")
def _unit_test_mode() -> Iterator[None]:
    """AWB's RequiresInitialization sets Globals.UnitTestMode: Tagger uses fixed test values
    instead of asking the wiki (tests.parity.helpers.unit_test)."""
    from awb_x.core.parsers import tagger
    from tests.parity.helpers import unit_test

    tagger.set_default_tagger_lookups(unit_test)
    yield
    tagger.set_default_tagger_lookups(tagger.OfflineTaggerLookups())
