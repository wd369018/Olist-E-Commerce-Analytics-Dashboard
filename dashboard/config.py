"""Project-wide configuration and constants for the Olist dashboard."""
from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

from . import theme

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "processed" / "olist_ecommerce.db"
FALLBACK_DB_PATH = PROJECT_ROOT / "olist_ecommerce.db"

APP_TITLE = "Olist Commerce Intelligence"
APP_SUBTITLE = "Brazilian marketplace performance, customers, operations and satisfaction"
CURRENCY = "R$"


class _ThemeColors(Mapping[str, str]):
    """Palette entries resolved at render time so they follow the active theme."""

    _ALIASES = {
        "ink": "ink",
        "muted": "muted",
        "line": "line",
        "teal": "brand",
        "teal_light": "brand_bright",
        "blue": "blue",
        "violet": "violet",
        "amber": "amber",
        "red": "red",
        "green": "green",
        "slate": "text",
    }

    def __getitem__(self, key: str) -> str:
        try:
            token = self._ALIASES[key]
        except KeyError as exc:
            raise KeyError(key) from exc
        return str(theme.tokens()[token])

    def __iter__(self) -> Iterator[str]:
        return iter(self._ALIASES)

    def __len__(self) -> int:
        return len(self._ALIASES)


class _ThemePalette(Sequence[str]):
    """Chart colour sequence that follows the active theme."""

    def __getitem__(self, index: int) -> str:  # type: ignore[override]
        return str(theme.tokens()["chart_palette"][index])

    def __len__(self) -> int:
        return len(theme.tokens()["chart_palette"])

    def __iter__(self) -> Iterator[str]:
        return iter(theme.tokens()["chart_palette"])


COLORS: Mapping[str, str] = _ThemeColors()
PALETTE: Sequence[str] = _ThemePalette()

STATUS_LABELS = {
    "delivered": "Delivered",
    "shipped": "Shipped",
    "canceled": "Canceled",
    "unavailable": "Unavailable",
    "invoiced": "Invoiced",
    "processing": "Processing",
    "created": "Created",
    "approved": "Approved",
}

PAYMENT_LABELS = {
    "credit_card": "Credit card",
    "boleto": "Boleto",
    "voucher": "Voucher",
    "debit_card": "Debit card",
    "not_defined": "Not defined",
}

STATE_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

SENTINEL_VALUES = {"", "0", "nan", "none", "null", "na", "n/a"}

# Metric definitions shown in the UI and documented in the README.
METRIC_HELP = {
    "total_orders": "Distinct orders placed in the selected period and filters.",
    "delivered_orders": "Orders whose status is 'delivered'.",
    "product_revenue": "Sum of item prices (excluding freight) on non-canceled, non-unavailable orders.",
    "gross_revenue": "Sum of item prices plus freight on non-canceled, non-unavailable orders.",
    "aov": "Product revenue divided by orders containing at least one item and not canceled/unavailable.",
    "cancellation_rate": "Canceled orders divided by all orders in scope.",
    "repeat_rate": "Customers with 2+ valid orders divided by customers with at least one valid order.",
    "delivery_days": "Days from purchase to delivery for delivered orders with valid dates.",
    "late_rate": "Delivered orders where actual delivery was later than the estimated delivery date.",
    "review_score": "Average of the latest review per order (one review per order).",
}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
}


def resolve_db_path() -> Path:
    """Resolve the SQLite database path without modifying any project data."""
    env_path = os.getenv("OLIST_DB_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend([DEFAULT_DB_PATH, FALLBACK_DB_PATH])

    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate.resolve()

    searched = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(
        "Could not find a non-empty Olist SQLite database. Searched:\n"
        f"{searched}\n"
        "Set the OLIST_DB_PATH environment variable to the correct .db file."
    )
