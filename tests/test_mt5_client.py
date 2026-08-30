from __future__ import annotations

from types import SimpleNamespace

from app.config.settings import MT5Settings
from app.data import mt5_client
from app.data.mt5_client import MT5Client


class FakeMT5:
    def __init__(self) -> None:
        self.selected: list[str] = []
        self.shutdown_called = False

    def initialize(self, **options: object) -> bool:
        return True

    def terminal_info(self) -> object:
        return object()

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def symbol_info(self, symbol: str) -> object | None:
        return SimpleNamespace(visible=False) if symbol == "XAUUSD.r" else None

    def symbol_select(self, symbol: str, visible: bool) -> bool:
        self.selected.append(symbol)
        return visible

    def symbol_info_tick(self, symbol: str) -> object:
        return SimpleNamespace(bid=3000.0, ask=3000.5, last=3000.25, time=1_700_000_000)

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_client_connects_finds_symbol_and_returns_tick(monkeypatch: object) -> None:
    fake = FakeMT5()
    monkeypatch.setattr(mt5_client, "mt5", fake)
    client = MT5Client(MT5Settings(None, None, None, None))
    assert client.connect()
    assert client.find_symbol(["MISSING", "XAUUSD.r"]) == "XAUUSD.r"
    assert fake.selected == ["XAUUSD.r"]
    assert client.get_current_tick("XAUUSD.r")["spread"] == 0.5
    client.disconnect()
    assert fake.shutdown_called