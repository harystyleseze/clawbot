from __future__ import annotations

from datetime import UTC, date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    telegram_handle: Mapped[str | None] = mapped_column(String(100))
    ton_wallet_address: Mapped[str | None] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Paris")
    opening_time: Mapped[time] = mapped_column(Time, default=time(12, 0))
    closing_time: Mapped[time] = mapped_column(Time, default=time(23, 0))
    default_slot_duration: Mapped[int] = mapped_column(Integer, default=120)
    deposit_amount_ton: Mapped[float] = mapped_column(Float, default=2.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    tables: Mapped[list[Table]] = relationship(back_populates="restaurant")
    time_slots: Mapped[list[TimeSlot]] = relationship(back_populates="restaurant")
    bookings: Mapped[list[Booking]] = relationship(back_populates="restaurant")
    faq_responses: Mapped[list[FaqResponse]] = relationship(
        back_populates="restaurant"
    )
    upsell_packages: Mapped[list[UpsellPackage]] = relationship(
        back_populates="restaurant"
    )


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    restaurant: Mapped[Restaurant] = relationship(back_populates="tables")


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    slot_start: Mapped[time] = mapped_column(Time, nullable=False)
    slot_end: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    restaurant: Mapped[Restaurant] = relationship(back_populates="time_slots")

    @property
    def label(self) -> str:
        return f"{self.slot_start.strftime('%H:%M')}-{self.slot_end.strftime('%H:%M')}"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("table_id", "time_slot_id", "date", name="uq_booking_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"))
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    guest_name: Mapped[str | None] = mapped_column(String(200))
    guest_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guest_telegram_username: Mapped[str | None] = mapped_column(String(100))
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    special_requests: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en")
    deposit_tx_hash: Mapped[str | None] = mapped_column(String(200))
    deposit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    upsells: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="bookings")
    table: Mapped[Table] = relationship()
    time_slot: Mapped[TimeSlot] = relationship()


class FaqResponse(Base):
    __tablename__ = "faq_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    question_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")

    restaurant: Mapped[Restaurant] = relationship(back_populates="faq_responses")


class UpsellPackage(Base):
    __tablename__ = "upsell_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_ton: Mapped[float | None] = mapped_column(Float)
    price_eur: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    restaurant: Mapped[Restaurant] = relationship(back_populates="upsell_packages")
