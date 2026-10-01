"""Complete Lab 3B prototype: face detection, speech, screen, and replies."""

from __future__ import annotations

import argparse
import time

import cv2
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from PIL import ImageFont

from camera_screen_listen_test import (
    DEFAULT_CAMERA_DEVICE,
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    GREETING,
    SAMPLE_RATE,
    build_vad,
    create_display,
    show_status,
    speak_text,
)
from intents import classify_intent, response_for_intent, screen_message_for_intent
from logger import DEFAULT_LOG_PATH, log_interaction


DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
CONFIRM_FRAMES = 3
FACE_CONFIRM_FRAMES = 3
LEAVE_GRACE_SECONDS = 6.0
FACE_MIN_SIZE = (45, 45)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-device", default=DEFAULT_CAMERA_DEVICE)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--participant-id", default="P1")
    parser.add_argument(
        "--debug-presence",
        action="store_true",
        help="print periodic camera face-presence diagnostics",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=1.3,
        help="silence required to end a spoken turn (default: 1.3 seconds)",
    )
    return parser.parse_args()


def build_face_detector() -> cv2.CascadeClassifier:
    frontal_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(frontal_path)
    if detector.empty():
        raise RuntimeError(f"Could not load frontal face detector: {frontal_path}")
    return detector


def face_detected(
    detector: cv2.CascadeClassifier,
    frame: np.ndarray,
) -> bool:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_frame = cv2.equalizeHist(gray_frame)
    faces = detector.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=FACE_MIN_SIZE,
    )
    return len(faces) > 0


def listen_for_one_utterance(
    camera: cv2.VideoCapture,
    detector: cv2.CascadeClassifier,
    display,
    font,
    recognizer: WhisperModel,
    vad,
    window: int,
    voice: str,
    participant_id: str,
    previous_response: str,
    debug_presence: bool,
) -> tuple[bool, str]:
    samples_per_read = int(0.1 * SAMPLE_RATE)
    audio_buffer = np.empty(0, dtype=np.float32)
    show_status(display, font, "Hi! I am\nlistening.")
    print("Listening. Speak a sentence, then pause.")
    last_face_seen = time.monotonic()
    last_debug_print = last_face_seen
    consecutive_face_frames = 0

    with sd.InputStream(channels=1, dtype="float32", samplerate=SAMPLE_RATE) as stream:
        while True:
            camera_ok, frame = camera.read()
            now = time.monotonic()
            if camera_ok:
                small_frame = cv2.resize(frame, (320, 240))
                if face_detected(detector, small_frame):
                    consecutive_face_frames += 1
                    if consecutive_face_frames >= FACE_CONFIRM_FRAMES:
                        last_face_seen = now
                        face_status = "face confirmed"
                    else:
                        face_status = "face candidate"
                else:
                    consecutive_face_frames = 0
                    face_status = "no face detected"
            else:
                face_status = "camera frame unavailable"

            if debug_presence and now - last_debug_print >= 1.0:
                absent_for = now - last_face_seen
                print(f"Presence debug: {face_status}; absent {absent_for:.1f}s")
                last_debug_print = now

            if now - last_face_seen >= LEAVE_GRACE_SECONDS:
                print(
                    "No face detected for "
                    f"{LEAVE_GRACE_SECONDS:.0f} seconds; ending this conversation."
                )
                return False, previous_response

            chunk, _ = stream.read(samples_per_read)
            audio_buffer = np.concatenate([audio_buffer, chunk.reshape(-1)])

            while len(audio_buffer) > window:
                vad.accept_waveform(audio_buffer[:window])
                audio_buffer = audio_buffer[window:]

            if vad.empty():
                continue

            utterance = np.array(vad.front.samples, dtype=np.float32)
            vad.pop()
            show_status(display, font, "Thinking...")
            response_started = time.perf_counter()
            segments, _ = recognizer.transcribe(utterance, beam_size=1)
            text = " ".join(segment.text.strip() for segment in segments)
            print(f"Heard: {text or '[no speech recognized]'}")

            intent = classify_intent(text)
            response = response_for_intent(intent, previous_response)
            screen_message = screen_message_for_intent(intent, response)
            show_status(display, font, screen_message)
            response_time = time.perf_counter() - response_started
            log_interaction(
                participant_id=participant_id,
                user_present=True,
                transcript=text,
                detected_intent=intent,
                system_response=response,
                response_time_seconds=response_time,
            )
            print(f"Intent: {intent}")
            print(f"Response: {response}")
            speak_text(voice, response)
            return True, response


def main() -> None:
    args = parse_args()
    display, backlight = create_display()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    camera = cv2.VideoCapture(args.camera_device, cv2.CAP_V4L2)
    if not camera.isOpened():
        backlight.value = False
        raise RuntimeError(f"Could not open USB camera: {args.camera_device}")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    print(f"Loading Whisper model: {args.model}")
    recognizer = WhisperModel(args.model, device="cpu", compute_type="int8")
    vad, window = build_vad(args.min_silence)
    detector = build_face_detector()
    print(f"Microphone: {sd.query_devices(sd.default.device[0])['name']}")
    print(f"Participant ID: {args.participant_id}")
    print(f"Interaction dataset: {DEFAULT_LOG_PATH}")
    show_status(display, font, "Waiting for\nsomeone...")
    print("Complete camera conversation is running. Press Ctrl+C to stop.")

    person_present = False
    detected_count = 0

    try:
        while True:
            success, frame = camera.read()
            if not success:
                time.sleep(0.1)
                continue

            small_frame = cv2.resize(frame, (320, 240))
            present_now = face_detected(detector, small_frame)
            if present_now:
                detected_count += 1
            else:
                detected_count = 0

            if not person_present and detected_count >= CONFIRM_FRAMES:
                person_present = True
                show_status(display, font, "Hi! I am\nlistening.")
                print(f"Person detected. Saying: {GREETING}")
                speak_text(args.voice, GREETING)
                previous_response = GREETING
                while person_present:
                    person_present, previous_response = listen_for_one_utterance(
                        camera,
                        detector,
                        display,
                        font,
                        recognizer,
                        vad,
                        window,
                        args.voice,
                        args.participant_id,
                        previous_response,
                        args.debug_presence,
                    )

                show_status(display, font, "User left")
                print("User left")
                time.sleep(2)
                show_status(display, font, "Waiting for\nsomeone...")
                detected_count = 0

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping complete camera conversation.")
    finally:
        camera.release()
        backlight.value = False


if __name__ == "__main__":
    main()
