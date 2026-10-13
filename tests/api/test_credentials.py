"""Credentials go to the keychain, keyed by wiki and account."""

import keyring.errors

from awb_x.api import credentials


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
    credentials.save_password("https://ml.wikipedia.org/w/", "Alice@AWB-X", "s3cret", kr)
    assert kr.store == {("awb-x", "Alice@AWB-X@https://ml.wikipedia.org/w"): "s3cret"}
    assert credentials.load_password("https://ml.wikipedia.org/w", "Alice@AWB-X", kr) == "s3cret"
    assert credentials.load_password("https://en.wikipedia.org/w/", "Alice@AWB-X", kr) is None
    credentials.forget_password("https://ml.wikipedia.org/w/", "Alice@AWB-X", kr)
    credentials.forget_password("https://ml.wikipedia.org/w/", "Alice@AWB-X", kr)  # no error
    assert kr.store == {}
