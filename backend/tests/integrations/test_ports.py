from app.integrations.ports import (
    CaptchaVerifier,
    ChatMessage,
    EmailSender,
    EmbeddingClient,
    Geocoder,
    LLMClient,
    ObjectStorage,
)
from tests.fakes import (
    FakeCaptcha,
    FakeEmailSender,
    FakeEmbeddings,
    FakeGeocoder,
    FakeLLM,
    FakeStorage,
)

# Checked by mypy: a fake that drifts from its port fails type-checking here.
storage: ObjectStorage = FakeStorage()
email: EmailSender = FakeEmailSender()
captcha: CaptchaVerifier = FakeCaptcha()
geocoder: Geocoder = FakeGeocoder()
llm: LLMClient = FakeLLM()
embeddings: EmbeddingClient = FakeEmbeddings()


async def test_fake_llm_streams_the_reply() -> None:
    llm = FakeLLM(reply="hello there")
    messages = [ChatMessage(role="user", content="hi")]

    chunks = [chunk async for chunk in llm.stream(messages, system="be brief", max_tokens=10)]

    assert "".join(chunks).strip() == "hello there"
    assert llm.calls == [messages]


async def test_fake_embeddings_are_deterministic() -> None:
    embeddings = FakeEmbeddings(size=4)

    first, second = await embeddings.embed(["a", "a"], kind="document")

    assert first == second
    assert len(first) == embeddings.dimensions
