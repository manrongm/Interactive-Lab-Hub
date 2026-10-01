"""First Lab 3B test: detect movement with a USB camera."""

from __future__ import annotations

import argparse
import time

import cv2
import numpy as np


DEFAULT_CAMERA_DEVICE = "/dev/video0"
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 240
DEFAULT_THRESHOLD = 18.0
DEFAULT_CONFIRM_FRAMES = 3
DEFAULT_ABSENCE_FRAMES = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect movement with a USB camera."
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


def main() -> None:
    args = parse_args()

    try:
        camera = cv2.VideoCapture(args.camera_device, cv2.CAP_V4L2)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        if not camera.isOpened():
            raise RuntimeError(f"Could not open USB camera: {args.camera_device}")

        time.sleep(2)

        success, frame = camera.read()
        if not success:
            raise RuntimeError(f"Could not read a frame from {args.camera_device}")
        previous_frame = grayscale(frame)
        detected_frames = 0
        absent_frames = 0

        print("Camera movement test is running. Press Ctrl+C to stop.")
        print(f"Camera device: {args.camera_device}")
        print(f"Detection threshold: {args.threshold}")

        while True:
            success, frame = camera.read()
            if not success:
                print("Could not read a camera frame; retrying.")
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
                print("Camera detected movement: PERSON DETECTED")

            if absent_frames == DEFAULT_ABSENCE_FRAMES:
                print("No recent movement: NO PERSON DETECTED")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Stopping camera movement test.")
    finally:
        if "camera" in locals():
            camera.release()


if __name__ == "__main__":
    main()
