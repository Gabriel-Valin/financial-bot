import base64
from typing import Any

from langchain.agents.middleware import AgentState
from langchain.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from financial_bot.middleware import TRANSCRIPT_PREFIX, MultimodalInputMiddleware

AUDIO_B64 = base64.b64encode(b"fake-audio").decode()


class FakeTranscriber:
    def __init__(self, text: str = "gastei trinta reais na farmácia") -> None:
        self.text = text
        self.calls: list[tuple[bytes, str]] = []

    def __call__(self, audio: bytes, mime_type: str) -> str:
        self.calls.append((audio, mime_type))
        return self.text


def _run(mw: MultimodalInputMiddleware, *messages: Any) -> dict[str, Any] | None:
    return mw.before_model(AgentState(messages=list(messages)), Runtime())


def test_transcribes_ui_audio_block_and_keeps_message_id() -> None:
    fake = FakeTranscriber()
    msg = HumanMessage(
        id="m1",
        content=[{"type": "audio", "mimeType": "audio/webm;codecs=opus", "data": AUDIO_B64}],
    )
    update = _run(MultimodalInputMiddleware(fake), msg)

    assert update is not None
    [new] = update["messages"]
    assert new.id == "m1"
    assert new.content == [
        {"type": "text", "text": f"{TRANSCRIPT_PREFIX}: gastei trinta reais na farmácia"}
    ]
    assert fake.calls == [(b"fake-audio", "audio/webm;codecs=opus")]


def test_accepts_langchain_audio_shape() -> None:
    fake = FakeTranscriber()
    msg = HumanMessage(content=[{"type": "audio", "base64": AUDIO_B64, "mime_type": "audio/ogg"}])
    assert _run(MultimodalInputMiddleware(fake), msg) is not None
    assert fake.calls[0][1] == "audio/ogg"


def test_normalizes_ui_image_block() -> None:
    msg = HumanMessage(
        content=[
            {"type": "text", "text": "cupom"},
            {"type": "image", "mimeType": "image/png", "data": "AAAA", "metadata": {"name": "a"}},
        ]
    )
    update = _run(MultimodalInputMiddleware(FakeTranscriber()), msg)
    assert update is not None
    assert update["messages"][0].content[1] == {
        "type": "image",
        "base64": "AAAA",
        "mime_type": "image/png",
    }


def test_no_update_when_nothing_to_change() -> None:
    fake = FakeTranscriber()
    msgs = [
        HumanMessage(content="Gastei 48,90 no Ifood"),
        HumanMessage(content=[{"type": "image", "base64": "AAAA", "mime_type": "image/png"}]),
        AIMessage(content="ok"),
    ]
    assert _run(MultimodalInputMiddleware(fake), *msgs) is None
    assert fake.calls == []


def test_transcription_failure_becomes_text_notice() -> None:
    def broken(audio: bytes, mime_type: str) -> str:
        raise RuntimeError("boom")

    msg = HumanMessage(content=[{"type": "audio", "mimeType": "audio/webm", "data": AUDIO_B64}])
    update = _run(MultimodalInputMiddleware(broken), msg)
    assert update is not None
    assert "Falha ao transcrever" in update["messages"][0].content[0]["text"]
