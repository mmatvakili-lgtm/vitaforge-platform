"""Market prices live apart from food composition: they change, differ by region and are only trusted while fresh. Never invented."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, Optional, Tuple

MAX_PRICE_AGE_DAYS = 45


@dataclass(frozen=True)
class PriceQuote:
    food_id: str
    region: str                          # e.g. IR-ISF
    currency: str                        # e.g. IRR, USD
    price_per_kg: float
    observed_on: date
    source: str                          # who observed/provided it (user entry, survey id, ...)
    confidence: str = "user_reported"    # user_reported | survey | official_statistics


class PriceBook:
    def __init__(self, quotes: Iterable[PriceQuote] = (), max_age_days: int = MAX_PRICE_AGE_DAYS):
        self._q: Dict[Tuple[str, str, str], PriceQuote] = {}
        self.max_age_days = max_age_days
        for q in quotes:
            self.add(q)

    def add(self, q: PriceQuote) -> None:
        if q.price_per_kg <= 0 or not q.source or not q.currency or not q.region:
            raise ValueError("invalid price quote (positive price, source, currency, region required)")
        k = (q.food_id, q.region, q.currency)
        if k not in self._q or self._q[k].observed_on <= q.observed_on:
            self._q[k] = q

    def fresh(self, food_id: str, region: str, currency: str, today: date) -> Optional[PriceQuote]:
        q = self._q.get((food_id, region, currency))
        return q if q and 0 <= (today - q.observed_on).days <= self.max_age_days else None

    def cost(self, food_id: str, grams: float, region: str, currency: str, today: date) -> Optional[float]:
        q = self.fresh(food_id, region, currency, today)
        return None if q is None else q.price_per_kg * grams / 1000.0
