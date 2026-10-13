"""Logging in from a profile, with the password from or to the keychain."""

import pytest

from pyawb.api import connect
from pyawb.api.session import LoginException, WikiSession
from pyawb.api.siteinfo import base_site_config
from pyawb.settings.appconfig import Profile

from .fakes import FakeTransport, userinfo
from .test_credentials import MemoryKeyring


class LoginTransport(FakeTransport):
    def login(self, username: str, password: str) -> None:
        if password != "secret":
            raise LoginException("wrong password")

    def logout(self) -> None:
        pass


def session() -> WikiSession:
    t = LoginTransport()
    t.responses[("meta", "userinfo")] = userinfo("Example")
    t.pages["Wikipedia:AutoWikiBrowser/CheckPage/VersionJSON"] = "{}"
    return WikiSession(t, base_site_config("ml", "wikipedia"))


PROFILE = Profile("ml", lang="ml", username="Example@PyAWB", remember_password=True)
KEY = ("pyawb", "Example@PyAWB@https://ml.wikipedia.org/w")


def test_remembers_a_working_password() -> None:
    kr = MemoryKeyring()
    with pytest.raises(LoginException):
        connect.log_in(session(), PROFILE, "wrong", keyring=kr)
    assert kr.store == {}  # a failed password is not remembered
    user = connect.log_in(session(), PROFILE, "secret", keyring=kr)
    assert user.name == "Example"
    assert kr.store == {KEY: "secret"}
    # next time no password is needed
    assert connect.log_in(session(), PROFILE, keyring=kr).name == "Example"


def test_forgets_when_not_remembering() -> None:
    kr = MemoryKeyring()
    kr.store[KEY] = "secret"
    profile = Profile("ml", lang="ml", username="Example@PyAWB", remember_password=False)
    connect.log_in(session(), profile, keyring=kr)
    assert kr.store == {}


def test_needs_user_name_and_password() -> None:
    with pytest.raises(LoginException, match="no user name"):
        connect.log_in(session(), Profile("x"), "secret", keyring=MemoryKeyring())
    with pytest.raises(LoginException, match="no password"):
        connect.log_in(session(), PROFILE, keyring=MemoryKeyring())
