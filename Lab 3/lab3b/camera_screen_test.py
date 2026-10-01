"""Second Lab 3B test: show camera states on the MiniPiTFT screen."""

from __future__ import annotations

import argparse
import time

import board
import cv2
import digitalio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789


DEFAULT_CAMERA_DEVICE = "/dev/video0"
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 240
DEFAULT_THRESHOLD = 18.0
DEFAULT_CONFIRM_FRAMES = 3
DEFAULT_ABSENCE_FRAMES = 12
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135
SCREEN_ROTATION = 90


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show USB camera detection states on the MiniPiTFT."
    )
    parser.add_argument(
        "--camera-device",
        default=DEFAULT_CAMERA_DEVICE,
        help=f"USB camera device (default: {DEFAULT_CAMERA_DEVICE})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Average frame change needed for detection (default: {DEFAULT_THRESHOLD})",
    )
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
    draw.multiline_text(
        (12, 45),
        status,
        font=font,
        fill="white",
        anchor="lm",
        align="center",
    )
    display.image(image, SCREEN_ROTATION)


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

    status = "Waiting for\nsomeone..."
    show_status(display, font, status)
    print("Camera and screen test is running. Press Ctrl+C to stop.")
    print(f"Camera device: {args.camera_device}")

    try:
        time.sleep(2)
        success, frame = camera.read()
        if not success:
            raise RuntimeError(f"Could not read a frame from {args.camera_device}")
        previous_frame = grayscale(frame)
        detected_frames = 0
        absent_frames = 0

        while True:
            success, frame = camera.read()
            if not success:
                time.sleep(0.1)
                continue

            current_frame = grayscale(frame)
            change = float(np.mean(np.abs(current_frame - previous_frame)))
            previous_frame = current_frame

            if change >= args.threshold:
                detected_frames += 1
                absent_frames = 0
            else:
                detected_frames = 0
                absent_frames += 1

            if detected_frames == DEFAULT_CONFIRM_FRAMES:
                status = "Hi! I am\n listening."
                show_status(display, font, status)
                print("Camera detected movement: showing listening status")

            if absent_frames == DEFAULT_ABSENCE_FRAMES:
                status = "User left"
                show_status(display, font, status)
                print("No recent movement: showing user-left status")
                time.sleep(2)
                status = "Waiting for\nsomeone..."
                show_status(display, font, status)
                print("Waiting for someone")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping camera and screen test.")
    finally:
        camera.release()
        backlight.value = False


if __name__ == "__main__":
    main()
