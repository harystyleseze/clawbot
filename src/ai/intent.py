from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from src.ai.client import AIClient
from src.ai.prompts import INTENTS, RESTAURANT_CONTEXT


@dataclass
class IntentResult:
    intent: str
    date: str | None
    time: str | None
    party_size: int | None
    special_requests: str | None
    detected_language: str
    response: str  # AI-generated response to show the user

    @property
    def has_all_booking_entities(self) -> bool:
        return all([self.date, self.time, self.party_size])


# Single combined prompt — classifies intent AND generates response in one call
COMBINED_PROMPT = """ClawBot, Lobster Cave, Cannes. Hours: 12:00-23:00 daily. Location: La Croisette.
{faq_context}
Date: {current_datetime}

Reply ONLY with JSON:
{{"intent":"new_booking"or"faq"or"greeting"or"cancel_booking","date":"YYYY-MM-DD"or null,"time":"HH:MM"or null,"party_size":int or null,"detected_language":"en"or"fr","response":"your 1-2 sentence reply IN SAME LANGUAGE as customer"}}

8pm=20:00, 9pm=21:00, tonight=today, demain=next day. Answer FAQs with real facts from above."""


async def classify_and_respond(
    client: AIClient,
    message: str,
    faq_data: str = "",
    user_context: dict | None = None,
) -> IntentResult:
    now = datetime.now(ZoneInfo("Europe/Paris"))

    prompt = COMBINED_PROMPT.format(
        faq_context=faq_data,
        current_datetime=now.strftime("%Y-%m-%d (%A)"),
    )

    try:
        raw = await client.chat(
            system=prompt,
            user_message=message,
            max_tokens=200,
        )

        # Parse JSON from response
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)

        intent = data.get("intent", "faq")
        extracted_time = data.get("time")
        extracted_date = data.get("date")
        party_size = data.get("party_size")
        response_text = data.get("response", "")

        # Post-processing: fix PM times from user message
        msg_lower = message.lower()
        pm_match = re.search(r'(\d{1,2})\s*pm', msg_lower)
        if pm_match and extracted_time:
            user_hour = int(pm_match.group(1))
            if user_hour < 12:
                extracted_time = f"{user_hour + 12}:00"

        # Strip spurious entities from non-booking intents
        if intent in ("greeting", "faq", "check_status"):
            extracted_time = None
            extracted_date = None
            party_size = None

        if intent not in INTENTS:
            intent = "faq"

        return IntentResult(
            intent=intent,
            date=extracted_date,
            time=extracted_time,
            party_size=party_size,
            special_requests=data.get("special_requests"),
            detected_language=data.get("detected_language", "en"),
            response=response_text,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse AI response: {e}, raw: {raw[:200] if 'raw' in dir() else 'N/A'}")
        # If JSON parsing fails, use the raw text as the response
        return IntentResult(
            intent="faq",
            date=None,
            time=None,
            party_size=None,
            special_requests=None,
            detected_language="en",
            response=raw if 'raw' in dir() else "I'm sorry, please try again!",
        )
    except Exception as e:
        logger.error(f"AI call failed: {e}")
        return IntentResult(
            intent="faq",
            date=None,
            time=None,
            party_size=None,
            special_requests=None,
            detected_language="en",
            response="I'm sorry, I'm having a moment. Please try again!",
        )
