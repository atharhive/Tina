"""Wallet loading for Tina.

The private key is read at call time and never written to a log, receipt file,
memo or command line. Tina only ever prints the public address.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from eth_account import Account

DEFAULT_WALLET = Path.home() / ".telegraph" / "wallet.json"


class WalletError(RuntimeError):
    pass


@dataclass(frozen=True)
class Wallet:
    address: str
    _key: str

    @property
    def key(self) -> str:
        return self._key


def load_wallet(path: str | None = None) -> Wallet:
    """Load the signing key from the Telegraph wallet file or the environment.

    Order: TINA_PRIVATE_KEY -> TELEGRAPH_PRIVATE_KEY -> wallet file.
    """
    env_key = os.environ.get("TINA_PRIVATE_KEY") or os.environ.get("TELEGRAPH_PRIVATE_KEY")
    if env_key:
        return _wallet_from_key(env_key)

    wallet_path = Path(path) if path else DEFAULT_WALLET
    if not wallet_path.exists():
        raise WalletError(
            f"no wallet at {wallet_path}. Run `npx -y @telegraphprotocol/telegraph-protocol-mcp setup` "
            "or set TINA_PRIVATE_KEY."
        )
    try:
        data = json.loads(wallet_path.read_text())
    except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
        raise WalletError(f"{wallet_path} is not readable JSON: {exc}") from exc

    key = data.get("privateKey") or data.get("private_key")
    if not key:
        raise WalletError(f"{wallet_path} has no privateKey field")
    return _wallet_from_key(key)


def _wallet_from_key(key: str) -> Wallet:
    key = key.strip()
    if not key.startswith("0x"):
        key = "0x" + key
    try:
        acct = Account.from_key(key)
    except Exception as exc:  # noqa: BLE001
        raise WalletError(f"invalid private key: {exc.__class__.__name__}") from exc
    return Wallet(address=acct.address, _key=key)
