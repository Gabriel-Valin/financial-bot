from datetime import date
from decimal import Decimal

from financial_bot import repository
from financial_bot.categories import Category
from financial_bot.db import session_scope


def test_format_brl() -> None:
    assert repository.format_brl(4890) == "R$ 48,90"
    assert repository.format_brl(123456) == "R$ 1.234,56"
    assert repository.format_brl(100000000) == "R$ 1.000.000,00"
    assert repository.format_brl(5) == "R$ 0,05"


def test_to_cents_rounds_half_up() -> None:
    assert repository.to_cents(Decimal("48.90")) == 4890
    assert repository.to_cents(Decimal("0.005")) == 1
    assert repository.to_cents(Decimal("100")) == 10000


def _add(amount: str, category: Category, spent_on: date) -> int:
    with session_scope() as s:
        return repository.add_expense(
            s,
            amount=Decimal(amount),
            description="x",
            category=category,
            spent_on=spent_on,
            source="text",
        ).id


def test_list_filters_and_order() -> None:
    _add("10", Category.MERCADO, date(2026, 10, 1))
    newest = _add("20", Category.TRANSPORTE, date(2026, 11, 2))
    _add("30", Category.MERCADO, date(2026, 11, 1))

    with session_scope() as s:
        all_items = repository.list_expenses(s)
        assert all_items[0].id == newest
        nov_market = repository.list_expenses(s, start=date(2026, 11, 1), category=Category.MERCADO)
        assert [e.amount_cents for e in nov_market] == [3000]


def test_summarize_groups_by_category() -> None:
    _add("700", Category.MERCADO, date(2026, 11, 3))
    _add("48.90", Category.ALIMENTACAO, date(2026, 11, 4))
    _add("51.10", Category.ALIMENTACAO, date(2026, 11, 5))
    _add("999", Category.LAZER, date(2026, 10, 31))  # outside period

    with session_scope() as s:
        summary = repository.summarize(s, start=date(2026, 11, 1), end=date(2026, 11, 30))
    assert summary.total_cents == 80000
    assert summary.count == 3
    assert summary.by_category == {"mercado": 70000, "alimentacao": 10000}


def test_delete() -> None:
    expense_id = _add("10", Category.OUTROS, date(2026, 11, 1))
    with session_scope() as s:
        assert repository.delete_expense(s, expense_id) is not None
    with session_scope() as s:
        assert repository.delete_expense(s, expense_id) is None
