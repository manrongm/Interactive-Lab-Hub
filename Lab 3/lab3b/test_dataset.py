"""Unit tests for Lab 3B intent classification and interaction CSV logging."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from intents import classify_intent, response_for_intent, screen_message_for_intent
from logger import FIELDNAMES, log_interaction


EXAMPLES = {
    "noodles": [
        "I want noodles.",
        "I want to make noodles.",
        "Can I cook noodles?",
    ],
    "stir_fried": [
        "Stir-fried noodles.",
        "I want fried noodles.",
        "Let's make stir-fried noodles.",
    ],
    "soup_noodles": ["Soup noodles.", "I want noodle soup."],
    "next_step": [
        "What's next?",
        "What should I do next?",
        "Next step?",
        "Okay, then what?",
    ],
    "add_noodles": [
        "When do I add the noodles?",
        "Should I add the noodles now?",
    ],
    "too_dry": [
        "The noodles are too dry.",
        "My noodles are getting dry.",
        "It's too dry.",
        "I need more sauce.",
    ],
    "too_soft": ["The noodles are too soft.", "I overcooked the noodles."],
    "cooking_time": [
        "How long should I cook it?",
        "How many minutes?",
        "How long do the noodles cook?",
    ],
    "repeat": [
        "Repeat that.",
        "Can you say that again?",
        "What did you say?",
    ],
}


class IntentTests(unittest.TestCase):
    def test_all_user_examples(self) -> None:
        for expected_intent, examples in EXAMPLES.items():
            for transcript in examples:
                with self.subTest(intent=expected_intent, transcript=transcript):
                    self.assertEqual(classify_intent(transcript), expected_intent)

    def test_unknown_and_repeat(self) -> None:
        self.assertEqual(classify_intent("Tell me a joke."), "unknown")
        self.assertEqual(
            response_for_intent("repeat", "Previous answer."), "Previous answer."
        )

    def test_required_screen_prompts(self) -> None:
        self.assertEqual(
            screen_message_for_intent("stir_fried", "unused"),
            "Step 1: Boil the noodles until almost cooked.",
        )
        self.assertEqual(
            screen_message_for_intent("next_step", "unused"),
            "Step 2: Stir-fry vegetables or meat.",
        )
        self.assertEqual(
            screen_message_for_intent("too_dry", "unused"),
            "Tip: Add a little water or sauce.",
        )


class LoggerTests(unittest.TestCase):
    def test_creates_csv_header_and_appends_escaped_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data" / "interactions.csv"
            log_interaction(
                participant_id="P1",
                user_present=True,
                transcript="I need noodles, please",
                detected_intent="noodles",
                system_response="Would you like stir-fried noodles or soup noodles?",
                response_time_seconds=1.1,
                log_path=path,
            )
            log_interaction(
                participant_id="P1",
                user_present=True,
                transcript="Second turn",
                detected_intent="unknown",
                system_response="Please repeat.",
                response_time_seconds=0.25,
                log_path=path,
            )

            with path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(len(rows), 2)
            self.assertEqual(list(rows[0]), FIELDNAMES)
            self.assertEqual(rows[0]["user_present"], "true")
            self.assertEqual(rows[0]["transcript"], "I need noodles, please")
            self.assertEqual(rows[0]["response_time_seconds"], "1.10")


if __name__ == "__main__":
    unittest.main()
