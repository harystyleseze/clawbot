from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.db.models import TimeSlot


def date_keyboard() -> InlineKeyboardMarkup:
    today = date.today()
    buttons = []
    for i in range(7):
        d = today + timedelta(days=i)
        if i == 0:
            label = f"Today ({d.strftime('%d %b')})"
        elif i == 1:
            label = f"Tomorrow ({d.strftime('%d %b')})"
        else:
            label = d.strftime("%A %d %b")
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"date:{d.isoformat()}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_slots_keyboard(slots: list[TimeSlot]) -> InlineKeyboardMarkup:
    buttons = []
    for slot in slots:
        label = f"{slot.slot_start.strftime('%H:%M')} - {slot.slot_end.strftime('%H:%M')}"
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"timeslot:{slot.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def party_size_keyboard() -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text=str(n), callback_data=f"party:{n}")
        for n in range(1, 5)
    ]
    row2 = [
        InlineKeyboardButton(text=str(n), callback_data=f"party:{n}")
        for n in range(5, 9)
    ]
    row3 = [InlineKeyboardButton(text="9+", callback_data="party:9")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, row3])


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Confirm", callback_data="confirm:yes")],
            [
                InlineKeyboardButton(text="Change Date", callback_data="confirm:change_date"),
                InlineKeyboardButton(text="Change Time", callback_data="confirm:change_time"),
            ],
            [InlineKeyboardButton(text="Cancel", callback_data="confirm:cancel")],
        ]
    )


def deposit_keyboard(
    ton_link: str, booking_id: int, allow_skip: bool = True
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Pay TON Deposit", url=ton_link)],
    ]
    if allow_skip:
        rows.append(
            [InlineKeyboardButton(
                text="Skip Deposit",
                callback_data=f"skip_deposit:{booking_id}",
            )]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows
    )
