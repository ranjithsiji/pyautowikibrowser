# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""Web pages that are not a wiki's API (AWB's Tools.GetHTML): the HTML scraper and CheckWiki list
sources read them. Fetched through pywikibot's HTTP session, so with our User-Agent."""

from __future__ import annotations

from typing import Protocol

from pyawb.api.errors import ApiException
from pyawb.api.transport import load_pywikibot


class WebError(ApiException):
    """The page could not be fetched."""


class WebFetcher(Protocol):
    def get_html(self, url: str) -> str:
        """The page at url as text (decoded per its headers)."""
        ...


class PywikibotWebFetcher:
    """GET through pywikibot.comms.http (User-Agent, retries)."""

    def get_html(self, url: str) -> str:
        load_pywikibot()
        from pywikibot.comms import http

        try:
            response = http.fetch(url)
        except Exception as e:  # requests and pywikibot raise several types
            raise WebError(f"{url}: {e}") from e
        if isinstance(response, Exception):  # pywikibot's typing allows a returned error
            raise WebError(f"{url}: {response}") from response
        if response.status_code >= 400:
            raise WebError(f"{url}: HTTP {response.status_code}")
        return response.text
