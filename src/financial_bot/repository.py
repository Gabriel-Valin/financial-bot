"""Expense data access. Plain functions, no LLM code."""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from financial_bot.categories import Category
from financial_bot.db import Expense

Source = Literal["text", "audio", "receipt"]


@dataclass(frozen=True)
class Summary:
    start: date
    end: date
    total_cents: int
    count: int
    by_category: dict[str, int] = field(default_factory=dict)


def to_cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_brl(cents: int) -> str:
    """Format cents as Brazilian Real, e.g. 123456 -> 'R$ 1.234,56'."""
    sign = "-" if cents < 0 else ""
    reais, centavos = divmod(abs(cents), 100)
    return f"{sign}R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"


def format_expense(expense: Expense) -> str:
    return (
        f"#{expense.id} {format_brl(expense.amount_cents)} - {expense.description} "
        f"({Category(expense.category).label}) em {expense.spent_on:%d/%m/%Y}"
    )


def add_expense(
    session: Session,
    *,
    amount: Decimal,
    description: str,
    category: Category,
    spent_on: date,
    source: Source,
) -> Expense:
    expense = Expense(
        amount_cents=to_cents(amount),
        description=description.strip(),
        category=category.value,
        spent_on=spent_on,
        source=source,
    )
    session.add(expense)
    session.flush()  # assigns expense.id
    return expense


def list_expenses(
    session: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    category: Category | None = None,
    limit: int = 50,
) -> list[Expense]:
    query = select(Expense)
    if start:
        query = query.where(Expense.spent_on >= start)
    if end:
        query = query.where(Expense.spent_on <= end)
    if category:
        query = query.where(Expense.category == category.value)
    query = query.order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(limit)
    return list(session.scalars(query))


def summarize(session: Session, *, start: date, end: date) -> Summary:
    rows = session.execute(
        select(Expense.category, func.sum(Expense.amount_cents), func.count())
        .where(Expense.spent_on >= start, Expense.spent_on <= end)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount_cents).desc())
    ).all()
    by_category = {category: int(total) for category, total, _ in rows}
    return Summary(
        start=start,
        end=end,
        total_cents=sum(by_category.values()),
        count=sum(int(count) for _, _, count in rows),
        by_category=by_category,
    )


def delete_expense(session: Session, expense_id: int) -> Expense | None:
    expense = session.get(Expense, expense_id)
    if expense is not None:
        session.delete(expense)
    return expense
