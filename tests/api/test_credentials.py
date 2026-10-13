"""Credentials go to the keychain, keyed by wiki and account."""

import keyring.errors

from pyawb.api import credentials


class MemoryKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.store.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.store[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        if (service_name, username) not in self.store:
            raise keyring.errors.PasswordDeleteError("not found")
        del self.store[(service_name, username)]


def test_save_load_forget() -> None:
    kr = MemoryKeyring()
    credentials.save_password("https://ml.wikipedia.org/w/", "Alice@PyAWB", "s3cret", kr)
    assert kr.store == {("pyawb", "Alice@PyAWB@https://ml.wikipedia.org/w"): "s3cret"}
    assert credentials.load_password("https://ml.wikipedia.org/w", "Alice@PyAWB", kr) == "s3cret"
    assert credentials.load_password("https://en.wikipedia.org/w/", "Alice@PyAWB", kr) is None
    credentials.forget_password("https://ml.wikipedia.org/w/", "Alice@PyAWB", kr)
    credentials.forget_password("https://ml.wikipedia.org/w/", "Alice@PyAWB", kr)  # no error
    assert kr.store == {}
