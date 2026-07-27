"""
budget.py
=========
Deterministic budget arithmetic.

**Nothing in this module calls an LLM.** The model proposes line items with a
``unit_cost`` and a ``quantity``; every multiplication, subtotal, contingency,
per-head figure and variance against the target is computed here in Python.

This separation is the single most defensible design decision in the project.
Language models are unreliable at multi-step arithmetic — they will happily
return a set of line items whose stated total is wrong by thousands. By treating
the model as a *proposer of structured estimates* and Python as the *calculator*,
the budget is guaranteed internally consistent no matter what the model returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import prompts


@dataclass
class BudgetLine:
    """One costed line item."""

    category: str
    item: str
    unit_cost: float
    quantity: float
    unit: str = "item"
    notes: str = ""

    @property
    def total(self) -> float:
        return round(self.unit_cost * self.quantity, 2)


@dataclass
class BudgetSummary:
    """A fully computed budget."""

    lines: list[BudgetLine] = field(default_factory=list)
    subtotal: float = 0.0
    contingency_pct: float = 10.0
    contingency: float = 0.0
    grand_total: float = 0.0
    per_head: float = 0.0
    target: float = 0.0
    variance: float = 0.0          # grand_total - target
    variance_pct: float = 0.0
    by_category: dict[str, float] = field(default_factory=dict)
    category_pct: dict[str, float] = field(default_factory=dict)
    over_budget: bool = False
    warnings: list[str] = field(default_factory=list)


def _to_float(value, default: float = 0.0) -> float:
    """Coerce whatever the model returned into a number.

    Models often emit "1,500", "₹2000", "2000 INR" or "approx 500" instead of a
    bare number, so strip everything that is not part of a numeric literal.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
    # Guard against strings like "1.2.3" or a lone "-".
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = parts[0] + "." + "".join(parts[1:])
    try:
        return float(cleaned) if cleaned not in ("", "-", ".", "-.") else default
    except ValueError:
        return default


def build_budget(
    raw_items: list[dict],
    target: float = 0.0,
    attendees: int = 1,
    contingency_pct: float = 10.0,
) -> BudgetSummary:
    """Turn raw model output into a fully computed, internally consistent budget."""
    summary = BudgetSummary(contingency_pct=contingency_pct, target=target)

    allowed = set(prompts.BUDGET_CATEGORIES)

    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue

        item_name = str(raw.get("item") or "").strip()
        if not item_name:
            continue

        category = str(raw.get("category") or "Miscellaneous").strip()
        if category not in allowed:
            # Try a case-insensitive match before giving up.
            match = next((c for c in allowed if c.lower() == category.lower()), None)
            category = match or "Miscellaneous"

        unit_cost = _to_float(raw.get("unit_cost"))
        quantity = _to_float(raw.get("quantity"), 1.0)

        if quantity <= 0:
            quantity = 1.0
        if unit_cost < 0:
            unit_cost = 0.0

        summary.lines.append(
            BudgetLine(
                category=category,
                item=item_name,
                unit_cost=round(unit_cost, 2),
                quantity=quantity,
                unit=str(raw.get("unit") or "item").strip() or "item",
                notes=str(raw.get("notes") or "").strip(),
            )
        )

    # ---- the arithmetic, all in Python ----
    summary.subtotal = round(sum(line.total for line in summary.lines), 2)
    summary.contingency = round(summary.subtotal * contingency_pct / 100.0, 2)
    summary.grand_total = round(summary.subtotal + summary.contingency, 2)
    summary.per_head = round(summary.grand_total / max(attendees, 1), 2)

    for line in summary.lines:
        summary.by_category[line.category] = round(
            summary.by_category.get(line.category, 0.0) + line.total, 2
        )

    if summary.subtotal > 0:
        summary.category_pct = {
            cat: round(amount / summary.subtotal * 100, 1)
            for cat, amount in summary.by_category.items()
        }

    if target > 0:
        summary.variance = round(summary.grand_total - target, 2)
        summary.variance_pct = round(summary.variance / target * 100, 1)
        summary.over_budget = summary.grand_total > target

        if summary.over_budget:
            summary.warnings.append(
                f"The plan exceeds the stated budget by {abs(summary.variance):,.0f} "
                f"({abs(summary.variance_pct):.1f}%). Use 'Cut Costs 20%' or raise the budget."
            )
        elif summary.variance_pct < -35:
            summary.warnings.append(
                f"The plan uses only {100 + summary.variance_pct:.0f}% of the budget. "
                "There is room to upgrade — try 'Make It Premium'."
            )

    # Sanity checks a human planner would make.
    if summary.lines:
        biggest = max(summary.by_category.items(), key=lambda kv: kv[1])
        if summary.subtotal > 0 and biggest[1] / summary.subtotal > 0.6:
            summary.warnings.append(
                f"{biggest[0]} accounts for {biggest[1] / summary.subtotal * 100:.0f}% "
                "of the budget. Check whether that concentration is intentional."
            )
    else:
        summary.warnings.append("No budget lines were produced. Try regenerating the plan.")

    return summary


def rescale(lines: list[BudgetLine], factor: float) -> list[BudgetLine]:
    """Scale every unit cost by a factor — used by the local ± budget sliders."""
    return [
        BudgetLine(
            category=line.category,
            item=line.item,
            unit_cost=round(line.unit_cost * factor, 2),
            quantity=line.quantity,
            unit=line.unit,
            notes=line.notes,
        )
        for line in lines
    ]


def fit_to_target(lines: list[BudgetLine], target: float, contingency_pct: float = 10.0) -> float:
    """
    Return the scaling factor that would make the budget hit the target exactly.

    Lets the UI offer "fit to my budget" without another model call.
    """
    subtotal = sum(line.total for line in lines)
    if subtotal <= 0 or target <= 0:
        return 1.0
    grand = subtotal * (1 + contingency_pct / 100.0)
    return round(target / grand, 4)
