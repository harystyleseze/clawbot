from __future__ import annotations


def generate_deposit_link(
    wallet_address: str,
    amount_ton: float,
    booking_id: int,
) -> str:
    amount_nanoton = int(amount_ton * 1_000_000_000)
    comment = f"booking-{booking_id}"
    return (
        f"ton://transfer/{wallet_address}"
        f"?amount={amount_nanoton}"
        f"&text={comment}"
    )
