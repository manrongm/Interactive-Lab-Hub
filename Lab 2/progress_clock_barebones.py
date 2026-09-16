import time
from datetime import datetime, timedelta
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789



cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

BAUDRATE = 64000000

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

height = disp.width
width = disp.height

image = Image.new("RGB", (width, height))
rotation = 90

draw = ImageDraw.Draw(image)


title_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    22
)

small_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    16
)



backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True


while True:

    now = datetime.now()

    # Beginning of today
    start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    # Beginning of tomorrow
    end = start + timedelta(days=1)

    total_seconds = (end - start).total_seconds()
    passed_seconds = (now - start).total_seconds()

    progress = passed_seconds / total_seconds

    percentage = progress * 100

    remaining = end - now

    remaining_hours = int(
        remaining.total_seconds() // 3600
    )

    remaining_minutes = int(
        (remaining.total_seconds() % 3600) // 60
    )


    # Clear screen
    draw.rectangle(
        (0, 0, width, height),
        fill=(0, 0, 0)
    )


    # Title
    draw.text(
        (82, 10),
        "TODAY",
        font=title_font,
        fill=(255, 255, 255)
    )


    # Percentage
    percent_text = f"{percentage:.1f}%"

    draw.text(
        (88, 42),
        percent_text,
        font=title_font,
        fill=(255, 255, 255)
    )


    # Progress bar background
    bar_x = 20
    bar_y = 78
    bar_width = 200
    bar_height = 18

    draw.rectangle(
        (
            bar_x,
            bar_y,
            bar_x + bar_width,
            bar_y + bar_height
        ),
        outline=(255, 255, 255),
        fill=(40, 40, 40)
    )


    # Progress bar fill
    filled_width = int(bar_width * progress)

    draw.rectangle(
        (
            bar_x,
            bar_y,
            bar_x + filled_width,
            bar_y + bar_height
        ),
        fill=(100, 200, 255)
    )


    # Remaining time
    remaining_text = (
        f"{remaining_hours}h "
        f"{remaining_minutes}m left"
    )

    draw.text(
        (55, 108),
        remaining_text,
        font=small_font,
        fill=(255, 255, 255)
    )


    # Send image to display
    disp.image(image, rotation)

    time.sleep(1)