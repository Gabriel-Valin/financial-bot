"""Agent middleware.

- `today_prompt`: builds the system prompt with today's date on every model call.
- `MultimodalInputMiddleware`: before the model runs, rewrites user content blocks
  into what the OpenAI chat model accepts:
    * audio -> transcribed to a text block (OpenAI chat models can't take audio here)
    * image/file sent by Agent Chat UI (`mimeType`/`data`) -> LangChain shape
      (`mime_type`/`base64`)
  The rewritten message keeps its id, so it replaces the original in the thread state.
  That means each audio is transcribed only once.
"""

import asyncio
import base64
import logging
from typing import Any, Protocol, override

from langchain.agents.middleware import AgentMiddleware, AgentState, ModelRequest, dynamic_prompt
from langchain.messages import HumanMessage
from langgraph.runtime import Runtime
from openai import OpenAI

from financial_bot.config import get_settings, today
from financial_bot.prompts import build_system_prompt

logger = logging.getLogger(__name__)

TRANSCRIPT_PREFIX = "[Áudio transcrito]"

_AUDIO_EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


class Transcriber(Protocol):
    def __call__(self, audio: bytes, mime_type: str) -> str: ...


class OpenAITranscriber:
    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self.model = model or settings.transcribe_model
        self.client = OpenAI(api_key=settings.openai_api_key.get_secret_value())

    def __call__(self, audio: bytes, mime_type: str) -> str:
        base_type = mime_type.split(";")[0].strip().lower()
        filename = f"audio.{_AUDIO_EXTENSIONS.get(base_type, 'webm')}"
        result = self.client.audio.transcriptions.create(
            model=self.model, file=(filename, audio, base_type), language="pt"
        )
        return result.text.strip()


@dynamic_prompt
def today_prompt(request: ModelRequest) -> str:
    return build_system_prompt(today())


def _mime(block: dict[str, Any]) -> str:
    return str(block.get("mime_type") or block.get("mimeType") or "")


def _base64(block: dict[str, Any]) -> str | None:
    value = block.get("base64") or block.get("data")
    return value if isinstance(value, str) else None


def _is_audio(block: dict[str, Any]) -> bool:
    return block.get("type") == "audio" or (
        block.get("type") == "file" and _mime(block).startswith("audio/")
    )


class MultimodalInputMiddleware(AgentMiddleware):
    def __init__(self, transcriber: Transcriber | None = None) -> None:
        super().__init__()
        self._transcriber = transcriber

    @property
    def transcriber(self) -> Transcriber:
        # Created lazily so importing the agent never needs network or an API key.
        if self._transcriber is None:
            self._transcriber = OpenAITranscriber()
        return self._transcriber

    @override
    def before_model(self, state: AgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        updated = []
        for message in state["messages"]:
            if not isinstance(message, HumanMessage) or not isinstance(message.content, list):
                continue
            content, changed = self._normalize(message.content)
            if changed:
                updated.append(message.model_copy(update={"content": content}))
        return {"messages": updated} if updated else None

    @override
    async def abefore_model(
        self, state: AgentState, runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        # Transcription is a blocking HTTP call: run it off the event loop.
        return await asyncio.to_thread(self.before_model, state, runtime)

    def _normalize(self, content: list[Any]) -> tuple[list[Any], bool]:
        result: list[Any] = []
        changed = False
        for block in content:
            if not isinstance(block, dict):
                result.append(block)
            elif _is_audio(block):
                result.append({"type": "text", "text": self._transcribe(block)})
                changed = True
            elif block.get("type") in ("image", "file") and "mimeType" in block:
                result.append(
                    {"type": block["type"], "base64": _base64(block), "mime_type": _mime(block)}
                )
                changed = True
            else:
                result.append(block)
        return result, changed

    def _transcribe(self, block: dict[str, Any]) -> str:
        data = _base64(block)
        if not data:
            return f"{TRANSCRIPT_PREFIX}: (áudio vazio)"
        try:
            text = self.transcriber(base64.b64decode(data), _mime(block) or "audio/webm")
        except Exception:
            logger.exception("Audio transcription failed")
            return "[Falha ao transcrever o áudio. Peça para o usuário enviar de novo ou digitar.]"
        return f"{TRANSCRIPT_PREFIX}: {text or '(sem fala detectada)'}"
