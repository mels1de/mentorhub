"""Ports: what business code needs from the outside world, independent of any vendor.

Adapters implement these with explicit timeouts and raise `IntegrationError` subclasses;
tests use in-memory fakes. Vendor SDK types never cross this boundary.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal, Protocol

# --- object storage (S3 / RustFS / R2) -------------------------------------------------


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    # The browser must send exactly these headers, or the signature check fails.
    headers: dict[str, str] = field(default_factory=dict)


class ObjectStorage(Protocol):
    async def presign_upload(
        self, key: str, *, content_type: str, expires_in: timedelta
    ) -> PresignedUpload: ...

    async def presign_download(self, key: str, *, expires_in: timedelta) -> str: ...

    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    async def delete(self, key: str) -> None: ...


# --- email ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


# --- captcha (reCAPTCHA v3 / Turnstile) ------------------------------------------------


@dataclass(frozen=True)
class CaptchaResult:
    success: bool
    # reCAPTCHA v3 only; Turnstile gives a plain pass/fail.
    score: float | None = None
    action: str | None = None


class CaptchaVerifier(Protocol):
    async def verify(self, token: str, *, remote_ip: str | None = None) -> CaptchaResult: ...


# --- geocoding -----------------------------------------------------------------------


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lng: float


@dataclass(frozen=True)
class Place:
    place_id: str
    point: GeoPoint
    formatted_address: str
    city: str | None = None
    country: str | None = None


class Geocoder(Protocol):
    async def resolve_place(self, place_id: str) -> Place | None: ...


# --- LLM & embeddings ----------------------------------------------------------------


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    usage: TokenUsage


class LLMClient(Protocol):
    async def complete(
        self, messages: Sequence[ChatMessage], *, system: str, max_tokens: int
    ) -> Completion: ...

    def stream(
        self, messages: Sequence[ChatMessage], *, system: str, max_tokens: int
    ) -> AsyncIterator[str]: ...


# Retrieval models embed documents and search queries differently.
type EmbeddingKind = Literal["document", "query"]


class EmbeddingClient(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: Sequence[str], *, kind: EmbeddingKind) -> list[list[float]]: ...
