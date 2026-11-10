import os

# Must be set before financial_bot modules read settings.
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator

import pytest

from financial_bot.db import Base, get_engine


@pytest.fixture(autouse=True)
def clean_db() -> Iterator[None]:
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
