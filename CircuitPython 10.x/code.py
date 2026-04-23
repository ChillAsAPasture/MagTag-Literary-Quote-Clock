# SPDX-FileCopyrightText: 2022 Eva Herrada for Adafruit Industries
# SPDX-FileCopyrightText: 2026 ChillAsAPasture - power aware modifications
# SPDX-License-Identifier: MIT

from os import getenv
import time
import wifi

import alarm
import microcontroller
import adafruit_display_text
from adafruit_display_text import label
import board
from adafruit_bitmap_font import bitmap_font
from adafruit_magtag.peripherals import Peripherals
from adafruit_magtag.network import Network
import displayio
from adafruit_display_shapes.rect import Rect

# settings.toml must contain these entries:
#
#   CIRCUITPY_WIFI_SSID = "YourWiFiName"
#   CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"
#   ADAFRUIT_AIO_USERNAME = "your_adafruit_username"
#   ADAFRUIT_AIO_KEY = "aio_xxxxxxxxxxxxxxxxxxxx"
#   TIMEZONE = "America/New_York"
#
# Create a free Adafruit IO account at https://io.adafruit.com to get your
# username and key. TIMEZONE must be a valid TZ database name, e.g.
# "America/Chicago", "Europe/London", "Asia/Tokyo". Full list:
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
tz = getenv("TIMEZONE")

if None in [getenv("CIRCUITPY_WIFI_SSID"), getenv("CIRCUITPY_WIFI_PASSWORD"),
           getenv("ADAFRUIT_AIO_USERNAME"), getenv("ADAFRUIT_AIO_KEY"), tz]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME', 'ADAFRUIT_AIO_KEY' and 'TIMEZONE'."
    )

peripherals = Peripherals()

quotes = {}
with open("quotes.csv", "r", encoding="UTF-8") as F:
    for quote_line in F:
        split = quote_line.split("|")
        quotes[split[0]] = split[1:]

display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

arial = bitmap_font.load_font("fonts/Arial-12.pcf")
bold = bitmap_font.load_font("fonts/Arial-Bold-12.pcf")
LINE_SPACING = 0.8
HEIGHT = arial.get_bounding_box()[1]
QUOTE_X = 10
QUOTE_Y = 7

rect = Rect(0, 0, 296, 128, fill=0xFFFFFF, outline=0xFFFFFF)
splash.append(rect)

quote = label.Label(
    font=arial,
    x=QUOTE_X,
    y=QUOTE_Y,
    color=0x000000,
    line_spacing=LINE_SPACING,
)

splash.append(quote)
time_label = label.Label(
    font=bold,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(time_label)

time_label_2 = label.Label(
    font=bold,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(time_label_2)

after_label = label.Label(
    font=arial,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(after_label)

after_label_2 = label.Label(
    font=arial,
    color=0x000000,
    line_spacing=LINE_SPACING,
)
splash.append(after_label_2)

author_label = label.Label(
    font=arial, x=QUOTE_X, y=115, color=0x000000, line_spacing=LINE_SPACING
)
splash.append(author_label)

battery_label = label.Label(
    font=arial, x=250, y=115, color=0xAAAAAA, line_spacing=LINE_SPACING
)
splash.append(battery_label)


def get_width(font, text):
    return sum(font.get_glyph(ord(c)).shift_x for c in text)


def smart_split(text, font, width):
    words = ""
    spl = text.split(" ")
    for i, word in enumerate(spl):
        words += f" {word}"
        lwidth = get_width(font, words)
        if width + lwidth > 276:
            spl[i] = "\n" + spl[i]
            text = " ".join(spl)
            break
    return text


def update_text(hour_min, show_battery=False, clock_time=None):
    quote.text = (
        time_label.text
    ) = time_label_2.text = after_label.text = after_label_2.text = ""
    battery_label.text = ""

    before, time_text, after = quotes[hour_min][0].split("^")
    text = adafruit_display_text.wrap_text_to_pixels(before, 276, font=arial)
    quote.text = "\n".join(text)

    for line in text:
        width = get_width(arial, line)

    time_text = smart_split(time_text, bold, width)

    split_time = time_text.split("\n")
    if time_text[0] != "\n":
        time_label.x = time_x = QUOTE_X + width
        time_label.y = time_y = QUOTE_Y + int((len(text) - 1) * HEIGHT * LINE_SPACING)
        time_label.text = split_time[0]
    if "\n" in time_text:
        time_label_2.x = time_x = QUOTE_X
        time_label_2.y = time_y = QUOTE_Y + int(len(text) * HEIGHT * LINE_SPACING)
        wrapped = adafruit_display_text.wrap_text_to_pixels(
            split_time[1], 276, font=arial
        )
        time_label_2.text = "\n".join(wrapped)
    width = get_width(bold, split_time[-1]) + time_x - QUOTE_X

    if after:
        after = smart_split(after, arial, width)

        split_after = after.split("\n")
        if after[0] != "\n":
            after_label.x = QUOTE_X + width
            after_label.y = time_y
            after_label.text = split_after[0]
        if "\n" in after:
            after_label_2.x = QUOTE_X
            after_label_2.y = time_y + int(HEIGHT * LINE_SPACING)
            wrapped = adafruit_display_text.wrap_text_to_pixels(
                split_after[1], 276, font=arial
            )
            after_label_2.text = "\n".join(wrapped)

    author = f"{quotes[hour_min][2]} - {quotes[hour_min][1]}"
    wrapped_author = adafruit_display_text.wrap_text_to_pixels(
        author, 276, font=arial
    )
    author_label.text = "\n".join(wrapped_author)
    if len(wrapped_author) > 1:
        author_label.y = 103
    else:
        author_label.y = 115
    if show_battery:
        battery_pin = analogio.AnalogIn(board.VOLTAGE_MONITOR)
        voltage = (battery_pin.value * 3.3) / 65536 * 2
        battery_pin.deinit()
        pct = max(0, min(100, int((voltage - 3.2) / (4.2 - 3.2) * 100)))
        print(f"Battery: {voltage:.2f}V ({pct}%)")
        battery_label.text = f"{pct}%"
    status_parts = []
    if clock_time:
        status_parts.append(clock_time)
    voltage = peripherals.battery
    pct = max(0, min(100, int((voltage - 3.2) / (4.2 - 3.2) * 100)))
    print(f"Battery: {voltage:.2f}V ({pct}%)")
    if show_battery or pct < 20:
        status_parts.append(f"{pct}%")
    if status_parts:
        battery_label.text = " ".join(status_parts)
        battery_label.x = 296 - QUOTE_X - get_width(arial, battery_label.text)
    time.sleep(display.time_to_refresh + 0.1)
    display.refresh()


def get_nvm_date():
    """Read the saved date from NVM. Returns (year, month, day)."""
    nvm = microcontroller.nvm
    year = (nvm[0] << 8) | nvm[1]
    return year, nvm[2], nvm[3]


# Check if the RTC date matches the date saved in NVM
rtc_now = time.localtime()
nvm_year, nvm_month, nvm_day = get_nvm_date()
if (nvm_year >= 2025 and rtc_now.tm_year == nvm_year
        and rtc_now.tm_mon == nvm_month
        and rtc_now.tm_mday == nvm_day):
    # RTC is trustworthy, use it directly
    hour, minute, sec = rtc_now.tm_hour, rtc_now.tm_min, rtc_now.tm_sec
    print(f"RTC time: {hour:02}:{minute:02}:{sec:02}")
else:
    # Date mismatch — fetch from internet and sync RTC
    try:
        network = Network(status_neopixel=peripherals.neopixels)
        network.get_local_time(location=tz)
        now = time.localtime()
        wifi.radio.enabled = False
        peripherals.neopixels.fill(0)
        hour, minute, sec = now.tm_hour, now.tm_min, now.tm_sec
        # Save today's date to NVM
        nvm = microcontroller.nvm
        nvm[0] = now.tm_year >> 8
        nvm[1] = now.tm_year & 0xFF
        nvm[2] = now.tm_mon
        nvm[3] = now.tm_mday
        print(f"Fetched time: {hour:02}:{minute:02}:{sec:02}")
    except (OSError, RuntimeError, ValueError) as e:
        print(f"Failed to fetch time: {e}, using RTC value")
        hour, minute, sec = rtc_now.tm_hour, rtc_now.tm_min, rtc_now.tm_sec

current_minutes = hour * 60 + minute
hour_min = f"{hour:02}:{minute:02}"
if hour_min in quotes:
    print(f"Displaying quote for {hour_min} (current time {hour:02}:{minute:02}:{sec:02})")
    update_text(hour_min, clock_time=f"{hour:02}:{minute:02}:{sec:02}")
else:
    # Find the most recent quote before now
    for offset in range(1, 1441):
        candidate = (current_minutes - offset) % 1440
        h, m = divmod(candidate, 60)
        key = f"{h:02}:{m:02}"
        if key in quotes:
            print(f"No quote at {hour_min} (current time {hour:02}:{minute:02}:{sec:02}), showing most recent: {key}")
            update_text(key, show_battery=True, clock_time=f"{hour:02}:{minute:02}:{sec:02}")
            break

# Re-read seconds: the e-ink display refresh alone takes several seconds,
# plus CSV parsing and layout, so the original sec value is stale
sec = time.localtime().tm_sec

# Find the next hour_min that has a quote
sleep_seconds = None
for offset in range(1, 1441):  # check up to 24 hours ahead
    candidate = (current_minutes + offset) % 1440
    h, m = divmod(candidate, 60)
    key = f"{h:02}:{m:02}"
    if key in quotes:
        sleep_seconds = offset * 60 - sec
        print(f"Next quote at {key}, sleeping {sleep_seconds}s ({offset}m)")
        break

if sleep_seconds is None:
    sleep_seconds = 60 - sec
    print(f"No upcoming quotes found, sleeping {sleep_seconds}s")

time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
