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
#
# Ported from AutoWikiBrowser WikiFunctions/API/ApiExceptions.cs and ApiEdit.CheckForErrors
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""API errors. MediaWiki error codes map to the exception classes AWB has, so the UI can react to
each kind (wait on maxlag, log in again, show the spam blacklist entry, ...)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pyawb.core import rx

_MaxLag = rx.DotNetRegex(r": (\d+(?:\.\d+)?) seconds lagged", rx.DotNetOptions.IGNORE_CASE)


class ApiException(Exception):
    """Something went wrong talking to the wiki."""


class ApiBlankException(ApiException):
    """The wiki returned an empty response."""


class BrokenResponseException(ApiException):
    """The response could not be understood (AWB's BrokenXmlException)."""


class AbortedException(ApiException):
    """The operation was cancelled by the user."""


class LoggedOffException(ApiException):
    """The session was logged off (wrnotloggedin, assertuserfailed)."""


class ApiErrorException(ApiException):
    """The wiki returned an error code."""

    def __init__(self, code: str, info: str, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {info}")
        self.code = code
        self.info = info
        self.extra: Mapping[str, Any] = extra or {}


class MaxlagException(ApiErrorException):
    """The servers are lagged: wait retry_after seconds and try again."""

    def __init__(self, code: str, info: str, maxlag: float, retry_after: int = 10) -> None:
        super().__init__(code, info)
        self.maxlag = maxlag
        self.retry_after = retry_after


class SpamlistException(ApiErrorException):
    """The text contains a link on the spam blacklist."""


class SharedRepoException(ApiErrorException):
    """A file of this name exists on the shared repository (Commons)."""


class MediaWikiSaysNoException(ApiErrorException):
    """An extension (abuse filter, hook) refused the edit."""


class MediaWikiReadOnlyException(ApiErrorException):
    """The wiki is read-only."""


class FeatureDisabledException(ApiErrorException):
    """The API module or feature is disabled on this wiki."""


class TranslationPageEditException(ApiErrorException):
    """Translation pages (Extension:Translate) cannot be edited directly."""


class EditConflictException(ApiErrorException):
    """Someone else saved the page since it was opened."""


class CaptchaException(ApiException):
    """The wiki asks for a captcha, which PyAutoWikiBrowser cannot answer."""


class ReadApiDeniedException(ApiErrorException):
    """A private wiki: log in before reading anything."""


class InvalidTitleException(ApiException):
    """The title is not valid on this wiki."""


def api_error(code: str, info: str, extra: Mapping[str, Any] | None = None) -> ApiErrorException:
    """The exception for a MediaWiki error code (ApiEdit.CheckForErrors)."""
    extra = extra or {}
    lower = code.lower()
    match lower:
        case "maxlag":
            lag = extra.get("lag")
            if lag is None:
                m = _MaxLag.match(info)
                lag = float(m.group(1)) if m else 0.0
            return MaxlagException(code, info, float(lag))
        case "wrnotloggedin" | "assertuserfailed" | "assertbotfailed":
            return _logged_off(code, info)
        case "spamdetected" | "spamblacklist" | "spamprotectiontext":
            return SpamlistException(code, info, extra)
        case "fileexists-sharedrepo-perm":
            return SharedRepoException(code, info, extra)
        case "hookaborted" | "abusefilter-disallowed" | "abusefilter-warning":
            return MediaWikiSaysNoException(code, info, extra)
        case "readonly":
            reason = extra.get("readonlyreason", "")
            text = info + ("\n\nReason: " + str(reason) if reason else "")
            return MediaWikiReadOnlyException(code, text, extra)
        case "editconflict":
            return EditConflictException(code, info, extra)
        case "readapidenied":
            return ReadApiDeniedException(code, info, extra)
        case _:
            if "disabled" in lower:
                return FeatureDisabledException(code, info, extra)
            if info == 'Unknown error: "tpt-target-page"' or lower == "tpt-target-page":
                return TranslationPageEditException(code, info, extra)
            return ApiErrorException(code, info, extra)


class _LoggedOff(LoggedOffException, ApiErrorException):
    pass


def _logged_off(code: str, info: str) -> ApiErrorException:
    return _LoggedOff(code, info)


def check_errors(result: Mapping[str, Any]) -> Mapping[str, Any]:
    """Raise the matching exception if an API response (JSON, formatversion=2) has an error."""
    if not result:
        raise ApiBlankException("the wiki returned an empty response")
    error = result.get("error")
    if isinstance(error, Mapping):
        e: Mapping[str, Any] = error
        extra = {k: v for k, v in e.items() if k not in ("code", "info")}
        raise api_error(str(e.get("code", "")), str(e.get("info", "")), extra)
    return result
