"""Entry point loaded by `langgraph dev` (see langgraph.json)."""

import logging

from langchain.agents import create_agent

from financial_bot.config import get_settings
from financial_bot.middleware import MultimodalInputMiddleware, today_prompt
from financial_bot.tools import TOOLS

logging.basicConfig(level=logging.INFO)

agent = create_agent(
    model=get_settings().chat_model,
    tools=TOOLS,
    middleware=[MultimodalInputMiddleware(), today_prompt],
    name="financial-bot",
)
