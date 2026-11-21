"""Budget and caps: what the swarm is allowed to spend, checked before every ask."""

from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Budget:
    """A single run's money, spendable only within hard caps."""

    total_usd: float
    max_per_ask: float = 0.05
    spent_usd: float = 0.0
    purchases: int = 0
    history: list[float] = field(default_factory=list)

    @property
    def remaining(self) -> float:
        return round(self.total_usd - self.spent_usd, 6)

    def can_afford(self, price: float) -> bool:
        return price <= self.max_per_ask and price <= self.remaining

    def charge(self, price: float) -> None:
        if price > self.max_per_ask:
            raise BudgetExceeded(f"ask costs ${price:.4f}, over the ${self.max_per_ask:.2f} per-ask cap")
        if price > self.remaining:
            raise BudgetExceeded(f"ask costs ${price:.4f}, only ${self.remaining:.4f} left in the budget")
        self.spent_usd = round(self.spent_usd + price, 6)
        self.purchases += 1
        self.history.append(price)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "total_usd": self.total_usd,
            "spent_usd": self.spent_usd,
            "remaining_usd": self.remaining,
            "purchases": self.purchases,
        }
