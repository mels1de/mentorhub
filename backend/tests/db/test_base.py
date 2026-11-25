import uuid

from sqlalchemy import CheckConstraint, ForeignKey, MetaData, UniqueConstraint
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.base import (
    NAMING_CONVENTION,
    TYPE_ANNOTATION_MAP,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


# A separate registry: test models must not leak into Base.metadata (Alembic reads it).
class _Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = TYPE_ANNOTATION_MAP


class _Owner(UUIDPrimaryKeyMixin, _Base):
    __tablename__ = "owners"


class _Widget(UUIDPrimaryKeyMixin, TimestampMixin, _Base):
    __tablename__ = "widgets"
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        CheckConstraint("price >= 0", name="price_non_negative"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owners.id"), index=True)
    name: Mapped[str]
    price: Mapped[int]


WIDGETS = _Base.metadata.tables["widgets"]
# SQLAlchemy's dialect constructors carry no type hints.
PG_DIALECT = PGDialect()  # type: ignore[no-untyped-call]


def _ddl(element: CreateTable | CreateIndex) -> str:
    return str(element.compile(dialect=PG_DIALECT))


def test_constraints_follow_naming_convention() -> None:
    ddl = _ddl(CreateTable(WIDGETS))

    assert "CONSTRAINT pk_widgets PRIMARY KEY (id)" in ddl
    assert "CONSTRAINT uq_widgets_owner_id_name UNIQUE (owner_id, name)" in ddl
    assert "CONSTRAINT ck_widgets_price_non_negative CHECK (price >= 0)" in ddl
    assert "CONSTRAINT fk_widgets_owner_id_owners FOREIGN KEY(owner_id)" in ddl


def test_index_follows_naming_convention() -> None:
    (index,) = WIDGETS.indexes

    assert _ddl(CreateIndex(index)) == "CREATE INDEX ix_widgets_owner_id ON widgets (owner_id)"


def test_columns_are_native_uuid_and_tz_aware_timestamps() -> None:
    ddl = _ddl(CreateTable(WIDGETS))

    assert "id UUID NOT NULL" in ddl
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl
    assert "updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl
