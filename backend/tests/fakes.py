"""In-memory implementations of the integration ports for tests."""

import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import timedelta

from app.integrations.ports import (
    CaptchaResult,
    ChatMessage,
    Completion,
    EmailMessage,
    EmbeddingKind,
    Place,
    PresignedUpload,
    TokenUsage,
)


@dataclass
class FakeStorage:
    objects: dict[str, tuple[bytes, str]] = field(default_factory=dict)

    async def presign_upload(
        self, key: str, *, content_type: str, expires_in: timedelta
    ) -> PresignedUpload:
        return PresignedUpload(
            url=f"https://storage.test/{key}?expires={int(expires_in.total_seconds())}",
            headers={"Content-Type": content_type},
        )

    async def presign_download(self, key: str, *, expires_in: timedelta) -> str:
        return f"https://storage.test/{key}?expires={int(expires_in.total_seconds())}"

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@dataclass
class FakeEmailSender:
    outbox: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)


@dataclass
class FakeCaptcha:
    result: CaptchaResult = field(default_factory=lambda: CaptchaResult(success=True, score=0.9))

    async def verify(self, token: str, *, remote_ip: str | None = None) -> CaptchaResult:
        return self.result


@dataclass
class FakeGeocoder:
    places: dict[str, Place] = field(default_factory=dict)

    async def resolve_place(self, place_id: str) -> Place | None:
        return self.places.get(place_id)


@dataclass
class FakeLLM:
    reply: str = "fake reply"
    model: str = "fake-model"
    calls: list[Sequence[ChatMessage]] = field(default_factory=list)

    async def complete(
        self, messages: Sequence[ChatMessage], *, system: str, max_tokens: int
    ) -> Completion:
        self.calls.append(messages)
        return Completion(
            text=self.reply,
            model=self.model,
            usage=TokenUsage(input_tokens=len(messages), output_tokens=len(self.reply.split())),
        )

    async def stream(
        self, messages: Sequence[ChatMessage], *, system: str, max_tokens: int
    ) -> AsyncIterator[str]:
        self.calls.append(messages)
        for word in self.reply.split():
            yield word + " "


@dataclass
class FakeEmbeddings:
    size: int = 8

    @property
    def dimensions(self) -> int:
        return self.size

    async def embed(self, texts: Sequence[str], *, kind: EmbeddingKind) -> list[list[float]]:
        # Deterministic: the same text always maps to the same vector.
        return [[float((hash(text) >> i) & 1) for i in range(self.size)] for text in texts]


@dataclass
class FakeAuthMailer:
    verification: list[uuid.UUID] = field(default_factory=list)
    password_reset: list[uuid.UUID] = field(default_factory=list)
    login_codes: list[str] = field(default_factory=list)

    async def send_verification(self, user_id: uuid.UUID) -> None:
        self.verification.append(user_id)

    async def send_password_reset(self, user_id: uuid.UUID) -> None:
        self.password_reset.append(user_id)

    async def send_login_code(self, challenge_id: str) -> None:
        self.login_codes.append(challenge_id)
