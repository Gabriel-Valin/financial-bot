"""Tools the agent can call. Each one validates input, then calls the repository."""

from datetime import date
from decimal import Decimal

from langchain.tools import tool
from pydantic import BaseModel, Field

from financial_bot import repository
from financial_bot.categories import Category
from financial_bot.config import today
from financial_bot.db import session_scope
from financial_bot.repository import Source, format_brl, format_expense


class AddExpenseInput(BaseModel):
    amount: Decimal = Field(gt=0, le=10_000_000, description="Valor em reais, ex: 48.90")
    description: str = Field(
        min_length=1, max_length=200, description="Onde/o quê, ex: 'iFood', 'Posto Shell'"
    )
    category: Category
    spent_on: date | None = Field(
        default=None, description="Data da despesa (YYYY-MM-DD). Omita para hoje."
    )
    source: Source = Field(
        default="text", description="'audio' se veio de áudio, 'receipt' se de cupom fiscal"
    )


@tool(args_schema=AddExpenseInput)
def add_expense(
    amount: Decimal,
    description: str,
    category: Category,
    spent_on: date | None = None,
    source: Source = "text",
) -> str:
    """Registra uma nova despesa."""
    with session_scope() as session:
        expense = repository.add_expense(
            session,
            amount=amount,
            description=description,
            category=category,
            spent_on=spent_on or today(),
            source=source,
        )
        return f"Despesa registrada: {format_expense(expense)}"


class ListExpensesInput(BaseModel):
    start_date: date | None = Field(default=None, description="Data inicial (inclusiva)")
    end_date: date | None = Field(default=None, description="Data final (inclusiva)")
    category: Category | None = None


@tool(args_schema=ListExpensesInput)
def list_expenses(
    start_date: date | None = None,
    end_date: date | None = None,
    category: Category | None = None,
) -> str:
    """Lista despesas (mais recentes primeiro, até 50), com filtros opcionais."""
    with session_scope() as session:
        expenses = repository.list_expenses(
            session, start=start_date, end=end_date, category=category
        )
        if not expenses:
            return "Nenhuma despesa encontrada."
        return "\n".join(format_expense(e) for e in expenses)


class SummarizeInput(BaseModel):
    start_date: date | None = Field(
        default=None, description="Data inicial. Omita para o início do mês atual."
    )
    end_date: date | None = Field(default=None, description="Data final. Omita para hoje.")


@tool(args_schema=SummarizeInput)
def summarize_expenses(start_date: date | None = None, end_date: date | None = None) -> str:
    """Resume os gastos de um período: total e total por categoria."""
    end = end_date or today()
    start = start_date or end.replace(day=1)
    with session_scope() as session:
        summary = repository.summarize(session, start=start, end=end)
    header = (
        f"Período {summary.start:%d/%m/%Y} a {summary.end:%d/%m/%Y}: "
        f"{format_brl(summary.total_cents)} em {summary.count} despesa(s)."
    )
    lines = [
        f"- {Category(cat).label}: {format_brl(total)}"
        for cat, total in summary.by_category.items()
    ]
    return "\n".join([header, *lines])


class DeleteExpenseInput(BaseModel):
    expense_id: int = Field(gt=0, description="ID da despesa (o número depois de #)")


@tool(args_schema=DeleteExpenseInput)
def delete_expense(expense_id: int) -> str:
    """Apaga uma despesa pelo ID."""
    with session_scope() as session:
        expense = repository.delete_expense(session, expense_id)
        if expense is None:
            return f"Despesa #{expense_id} não encontrada."
        return f"Despesa apagada: {format_expense(expense)}"


TOOLS = [add_expense, list_expenses, summarize_expenses, delete_expense]
