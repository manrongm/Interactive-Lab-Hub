"""Fourth Lab 3B test: listen and transcribe after the camera greeting."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import textwrap
from pathlib import Path

import board
import cv2
import digitalio
import numpy as np
import sherpa_onnx
import sounddevice as sd
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789


LAB_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CAMERA_DEVICE = "/dev/video0"
DEFAULT_VOICE = "en_US-lessac-medium"
DEFAULT_MODEL = "tiny.en"
DEFAULT_VAD = LAB_DIR / "models" / "silero_vad.onnx"
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 240
DEFAULT_THRESHOLD = 18.0
DEFAULT_CONFIRM_FRAMES = 3
SAMPLE_RATE = 16000
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135
SCREEN_ROTATION = 90
GREETING = "Hi, how can I help you today?"
LAST_RESPONSE = "The next step is to add the sauce."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Greet a person, then listen and transcribe one or more utterances."
    )
    parser.add_argument("--camera-device", default=DEFAULT_CAMERA_DEVICE)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--min-silence", type=float, default=0.7)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    return parser.parse_args()


def grayscale(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)


def create_display() -> tuple[st7789.ST7789, digitalio.DigitalInOut]:
    cs_pin = digitalio.DigitalInOut(board.D5)
    dc_pin = digitalio.DigitalInOut(board.D25)
    display = st7789.ST7789(
        board.SPI(),
        cs=cs_pin,
        dc=dc_pin,
        rst=None,
        baudrate=64_000_000,
        width=135,
        height=240,
        x_offset=53,
        y_offset=40,
    )
    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output(value=True)
    return display, backlight


def show_status(
    display: st7789.ST7789, font: ImageFont.FreeTypeFont, status: str
) -> None:
    image = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "black")
    draw = ImageDraw.Draw(image)
    status = "\n".join(textwrap.wrap(status, width=19))
    draw.multiline_text(
        (12, 45),
        status,
        font=font,
        fill="white",
        anchor="lm",
        align="center",
    )
    display.image(image, SCREEN_ROTATION)


def speak_text(voice: str, text: str) -> None:
    piper = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "piper",
            "--model",
            voice,
            "--data-dir",
            str(LAB_DIR / "voices"),
            "--output-raw",
            "--",
            text,
        ],
        stdout=subprocess.PIPE,
    )
    player = subprocess.Popen(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
        stdin=piper.stdout,
    )
    assert piper.stdout is not None
    piper.stdout.close()
    player.wait()
    piper.wait()
    if player.returncode != 0 or piper.returncode != 0:
        raise RuntimeError("Piper or aplay could not play the greeting")


def response_for(text: str) -> str | None:
    normalized = text.lower()
    if "next step" in normalized or "what should i do" in normalized:
        return "The next step is to add the sauce."
    if "repeat" in normalized:
        return LAST_RESPONSE
    if "dry" in normalized:
        return "Try adding two tablespoons of cooking water."
    if "substitute" in normalized or "instead" in normalized:
        return "You can use broth instead of water."
    return None


def build_vad(min_silence: float) -> tuple[sherpa_onnx.VoiceActivityDetector, int]:
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(DEFAULT_VAD)
    config.silero_vad.min_silence_duration = min_silence
    config.silero_vad.min_speech_duration = 0.25
    config.sample_rate = SAMPLE_RATE
    detector = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)
    return detector, config.silero_vad.window_size


def listen_for_utterances(
    display: st7789.ST7789,
    font: ImageFont.FreeTypeFont,
    recognizer: WhisperModel,
    vad: sherpa_onnx.VoiceActivityDetector,
    window: int,
    voice: str,
) -> None:
    samples_per_read = int(0.1 * SAMPLE_RATE)
    buffer = np.empty(0, dtype=np.float32)
    show_status(display, font, "Hi! I am\nlistening.")
    print("Listening. Speak a sentence, then pause.")

    with sd.InputStream(channels=1, dtype="float32", samplerate=SAMPLE_RATE) as stream:
        while True:
            chunk, _ = stream.read(samples_per_read)
            buffer = np.concatenate([buffer, chunk.reshape(-1)])

            while len(buffer) > window:
                vad.accept_waveform(buffer[:window])
                buffer = buffer[window:]

            while not vad.empty():
                utterance = np.array(vad.front.samples, dtype=np.float32)
                vad.pop()
                show_status(display, font, "Thinking...")
                segments, _ = recognizer.transcribe(utterance, beam_size=1)
                text = " ".join(segment.text.strip() for segment in segments)
                print(f"Heard: {text or '[no speech recognized]'}")
                response = response_for(text)
                if response is None:
                    response = "I did not understand. Could you repeat that?"
                    show_status(display, font, "I did not\nunderstand.")
                else:
                    show_status(display, font, response[:45])
                print(f"Response: {response}")
                speak_text(voice, response)
                show_status(display, font, "Hi! I am\nlistening.")


def main() -> None:
    args = parse_args()
    if not DEFAULT_VAD.is_file():
        raise RuntimeError(f"VAD model not found: {DEFAULT_VAD}")

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
    print(f"Microphone: {sd.query_devices(sd.default.device[0])['name']}")

    show_status(display, font, "Waiting for\nsomeone...")
    print("Camera listening test is running. Press Ctrl+C to stop.")

    try:
        time.sleep(2)
        success, frame = camera.read()
        if not success:
            raise RuntimeError(f"Could not read a frame from {args.camera_device}")
        previous_frame = grayscale(frame)
        detected_frames = 0

        while True:
            success, frame = camera.read()
            if not success:
                time.sleep(0.1)
                continue

            current_frame = grayscale(frame)
            change = float(np.mean(np.abs(current_frame - previous_frame)))
            previous_frame = current_frame
            detected_frames = detected_frames + 1 if change >= args.threshold else 0

            if detected_frames >= DEFAULT_CONFIRM_FRAMES:
                show_status(display, font, "Hi! I am\nlistening.")
                print(f"Person detected. Saying: {GREETING}")
                speak_text(args.voice, GREETING)
                listen_for_utterances(
                    display, font, recognizer, vad, window, args.voice
                )
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping camera listening test.")
    finally:
        camera.release()
        backlight.value = False


if __name__ == "__main__":
    main()
