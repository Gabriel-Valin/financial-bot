import pytest
from pydantic import ValidationError

from financial_bot.config import today
from financial_bot.tools import add_expense, delete_expense, list_expenses, summarize_expenses


def test_add_expense_defaults_to_today() -> None:
    result = add_expense.invoke({"amount": 48.9, "description": "iFood", "category": "alimentacao"})
    assert result == f"Despesa registrada: #1 R$ 48,90 - iFood (Alimentação) em {today():%d/%m/%Y}"


def test_add_expense_accepts_receipt_date() -> None:
    result = add_expense.invoke(
        {
            "amount": "700.00",
            "description": "Supermercado Dia",
            "category": "mercado",
            "spent_on": "2026-11-01",
            "source": "receipt",
        }
    )
    assert "R$ 700,00" in result
    assert "01/11/2026" in result


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": 0, "description": "x", "category": "mercado"},
        {"amount": -5, "description": "x", "category": "mercado"},
        {"amount": 10, "description": "x", "category": "inexistente"},
        {"amount": 10, "description": "", "category": "mercado"},
    ],
)
def test_add_expense_rejects_bad_input(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        add_expense.invoke(payload)


def test_list_summarize_delete_flow() -> None:
    assert list_expenses.invoke({}) == "Nenhuma despesa encontrada."
    add_expense.invoke({"amount": 100, "description": "Gasolina", "category": "transporte"})
    add_expense.invoke({"amount": 700, "description": "Compra do mês", "category": "mercado"})

    assert "Gasolina" in list_expenses.invoke({"category": "transporte"})

    summary = summarize_expenses.invoke({})
    assert "R$ 800,00 em 2 despesa(s)" in summary
    assert "- Mercado: R$ 700,00" in summary.splitlines()[1]

    assert "apagada" in delete_expense.invoke({"expense_id": 1})
    assert "não encontrada" in delete_expense.invoke({"expense_id": 1})
