"""Test face presence detection with the USB camera and MiniPiTFT."""

from __future__ import annotations

import argparse
import time

import board
import cv2
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789


DEFAULT_CAMERA_DEVICE = "/dev/video0"
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135
SCREEN_ROTATION = 90
CONFIRM_FRAMES = 2
ABSENCE_FRAMES = 8


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
        (12, 45), status, font=font, fill="white", anchor="lm", align="center"
    )
    display.image(image, SCREEN_ROTATION)


def face_detected(detector: cv2.CascadeClassifier, frame) -> bool:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_frame = cv2.equalizeHist(gray_frame)
    faces = detector.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(35, 35),
    )
    return len(faces) > 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-device", default=DEFAULT_CAMERA_DEVICE)
    args = parser.parse_args()

    display, backlight = create_display()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    camera = cv2.VideoCapture(args.camera_device, cv2.CAP_V4L2)
    if not camera.isOpened():
        backlight.value = False
        raise RuntimeError(f"Could not open USB camera: {args.camera_device}")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    face_cascade_path = (
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    detector = cv2.CascadeClassifier(face_cascade_path)
    if detector.empty():
        raise RuntimeError(f"Could not load face detector: {face_cascade_path}")
    show_status(display, font, "Waiting for\nsomeone...")
    print("Face presence test is running. Press Ctrl+C to stop.")

    detected_count = 0
    absent_count = 0
    person_present = False

    try:
        while True:
            success, frame = camera.read()
            if not success:
                time.sleep(0.1)
                continue

            present_now = face_detected(detector, frame)
            if present_now:
                detected_count += 1
                absent_count = 0
            else:
                detected_count = 0
                absent_count += 1

            if not person_present and detected_count >= CONFIRM_FRAMES:
                person_present = True
                show_status(display, font, "Hi! I am\nlistening.")
                print("Person detected")

            if person_present and absent_count >= ABSENCE_FRAMES:
                person_present = False
                show_status(display, font, "User left")
                print("User left")
                time.sleep(2)
                show_status(display, font, "Waiting for\nsomeone...")
                print("Waiting for someone")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping human presence test.")
    finally:
        camera.release()
        backlight.value = False


if __name__ == "__main__":
    main()
