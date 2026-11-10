from enum import StrEnum


class Category(StrEnum):
    ALIMENTACAO = "alimentacao"  # restaurantes, delivery (iFood), lanches
    MERCADO = "mercado"  # supermercado, compra do mês, feira
    TRANSPORTE = "transporte"  # gasolina, Uber, ônibus, estacionamento
    MORADIA = "moradia"  # aluguel, condomínio, luz, água, internet
    SAUDE = "saude"  # farmácia, consultas, plano de saúde
    LAZER = "lazer"  # cinema, viagens, bares
    EDUCACAO = "educacao"  # cursos, livros, escola
    COMPRAS = "compras"  # roupas, eletrônicos, casa
    SERVICOS = "servicos"  # assinaturas, streaming, serviços
    OUTROS = "outros"

    @property
    def label(self) -> str:
        """Human-readable PT-BR name, e.g. 'Alimentação'."""
        return _LABELS[self]


_LABELS = {
    Category.ALIMENTACAO: "Alimentação",
    Category.MERCADO: "Mercado",
    Category.TRANSPORTE: "Transporte",
    Category.MORADIA: "Moradia",
    Category.SAUDE: "Saúde",
    Category.LAZER: "Lazer",
    Category.EDUCACAO: "Educação",
    Category.COMPRAS: "Compras",
    Category.SERVICOS: "Serviços",
    Category.OUTROS: "Outros",
}
