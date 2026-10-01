"""Keyword-based intent classification for the Lab 3B cooking assistant."""

from __future__ import annotations

import re


RESPONSES = {
    "noodles": "Would you like stir-fried noodles or soup noodles?",
    "stir_fried": (
        "First, boil the noodles until they are almost cooked, then drain the water."
    ),
    "soup_noodles": (
        "First, boil some water or broth, then add the noodles and your other ingredients."
    ),
    "next_step": (
        "Heat some oil in a pan, add your vegetables or meat, and stir-fry them first."
    ),
    "add_noodles": (
        "Add the noodles after the vegetables and meat are mostly cooked. "
        "Then add some sauce and mix everything together."
    ),
    "too_dry": "Add a small amount of water or sauce and keep mixing.",
    "too_soft": (
        "Turn off the heat and remove the noodles from the pan "
        "so they do not keep cooking."
    ),
    "cooking_time": (
        "Usually a few minutes, but check the package because different noodles "
        "need different cooking times."
    ),
    "unknown": "Sorry, I didn't understand that. Could you say it again?",
}

SCREEN_MESSAGES = {
    "stir_fried": "Step 1: Boil the noodles until almost cooked.",
    "next_step": "Step 2: Stir-fry vegetables or meat.",
    "too_dry": "Tip: Add a little water or sauce.",
    "unknown": "I did not understand.",
}


def classify_intent(transcript: str) -> str:
    """Return one supported intent label for a recognized transcript."""
    text = re.sub(r"[^a-z0-9']+", " ", transcript.lower()).strip()
    text = re.sub(r"\s+", " ", text)

    if any(phrase in text for phrase in ("too dry", "getting dry", "it's dry", "need more sauce")):
        return "too_dry"
    if any(phrase in text for phrase in ("too soft", "overcooked", "over cooked")):
        return "too_soft"
    if "stir fried" in text or "stir-fried" in transcript.lower() or "fried noodles" in text:
        return "stir_fried"
    if "soup" in text:
        return "soup_noodles"
    if any(phrase in text for phrase in ("when do i add", "should i add", "add the noodles now")):
        return "add_noodles"
    if any(phrase in text for phrase in ("next step", "what's next", "what is next", "what should i do next", "then what")):
        return "next_step"
    if any(phrase in text for phrase in ("how long", "how many minutes", "how long do", "cooking time")):
        return "cooking_time"
    if any(phrase in text for phrase in ("repeat", "say that again", "what did you say")):
        return "repeat"
    if "noodle" in text:
        return "noodles"
    return "unknown"


def response_for_intent(intent: str, previous_response: str | None = None) -> str:
    """Return the response for an intent, using the prior response for repeat."""
    if intent == "repeat":
        return previous_response or RESPONSES["unknown"]
    return RESPONSES.get(intent, RESPONSES["unknown"])


def screen_message_for_intent(intent: str, response: str) -> str:
    """Return the screen prompt associated with an intent or its spoken reply."""
    return SCREEN_MESSAGES.get(intent, response)
