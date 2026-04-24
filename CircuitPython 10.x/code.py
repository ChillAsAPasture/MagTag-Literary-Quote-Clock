# SPDX-FileCopyrightText: 2022 Eva Herrada for Adafruit Industries
# SPDX-FileCopyrightText: 2026 ChillAsAPasture - power aware modifications
# SPDX-License-Identifier: MIT

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
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
timezone = getenv("TIMEZONE")

if None in [getenv("CIRCUITPY_WIFI_SSID"), getenv("CIRCUITPY_WIFI_PASSWORD"),
           getenv("ADAFRUIT_AIO_USERNAME"), getenv("ADAFRUIT_AIO_KEY"), timezone]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME', 'ADAFRUIT_AIO_KEY' and 'TIMEZONE'."
    )

peripherals = Peripherals()

# ---------------------------------------------------------------------------
# Display setup
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Display helper functions
# ---------------------------------------------------------------------------
def display_error_and_sleep(message):
    """Show an error message on screen and deep sleep forever."""
    print(message)
    quote.text = message
    time.sleep(display.time_to_refresh + 0.1)
    display.refresh()
    alarm.exit_and_deep_sleep_until_alarms()


def get_width(font, text):
    """Return the pixel width of text rendered in the given font."""
    return sum(font.get_glyph(ord(char)).shift_x for char in text)


def smart_split(text, font, width):
    """Insert a line break before the word that would exceed the display width."""
    words = ""
    word_list = text.split(" ")
    for idx, word in enumerate(word_list):
        words += f" {word}"
        lwidth = get_width(font, words)
        if width + lwidth > 276:
            word_list[idx] = "\n" + word_list[idx]
            text = " ".join(word_list)
            break
    return text


def update_text(hour_min, show_battery=False, clock_time=None):
    """Lay out and display a quote for the given time, then refresh the screen."""

    # -- Clear all labels --
    quote.text = ""
    time_label.text = ""
    time_label_2.text = ""
    after_label.text = ""
    after_label_2.text = ""
    battery_label.text = ""

    # -- Parse the quote into before/time/after segments --
    before, time_text, after = quotes[hour_min][0].split("^")

    # -- Render the "before" text (prose leading up to the time reference) --
    text = adafruit_display_text.wrap_text_to_pixels(before, 276, font=arial)
    quote.text = "\n".join(text)

    # -- Measure the last line's width so the time label can continue inline --
    for line in text:
        width = get_width(arial, line)

    # -- Render the bold time text, splitting to a new line if it overflows --
    time_text = smart_split(time_text, bold, width)
    split_time = time_text.split("\n")

    if time_text[0] != "\n":
        # Time starts on the same line as the preceding text
        time_label.x = time_x = QUOTE_X + width
        time_label.y = time_y = QUOTE_Y + int((len(text) - 1) * HEIGHT * LINE_SPACING)
        time_label.text = split_time[0]

    if "\n" in time_text:
        # Time wraps to a second line
        time_label_2.x = time_x = QUOTE_X
        time_label_2.y = time_y = QUOTE_Y + int(len(text) * HEIGHT * LINE_SPACING)
        wrapped = adafruit_display_text.wrap_text_to_pixels(
            split_time[1], 276, font=arial
        )
        time_label_2.text = "\n".join(wrapped)

    # Track where the time text ends for positioning the "after" text
    width = get_width(bold, split_time[-1]) + time_x - QUOTE_X

    # -- Render the "after" text (prose following the time reference) --
    if after:
        after = smart_split(after, arial, width)
        split_after = after.split("\n")

        if after[0] != "\n":
            # After text starts on the same line as the time
            after_label.x = QUOTE_X + width
            after_label.y = time_y
            after_label.text = split_after[0]

        if "\n" in after:
            # After text wraps to a second line
            after_label_2.x = QUOTE_X
            after_label_2.y = time_y + int(HEIGHT * LINE_SPACING)
            wrapped = adafruit_display_text.wrap_text_to_pixels(
                split_after[1], 276, font=arial
            )
            after_label_2.text = "\n".join(wrapped)

    # -- Render the author/book attribution --
    author = f"{quotes[hour_min][2]} - {quotes[hour_min][1]}"
    wrapped_author = adafruit_display_text.wrap_text_to_pixels(
        author, 276, font=arial
    )
    author_label.text = "\n".join(wrapped_author)
    if len(wrapped_author) > 1:
        author_label.y = 103
    else:
        author_label.y = 115

    # -- Render the status bar (clock time and battery) --
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

    # -- Refresh the e-ink display --
    time.sleep(display.time_to_refresh + 0.1)
    display.refresh()


# ---------------------------------------------------------------------------
# Quote data
# ---------------------------------------------------------------------------
quotes = {}
try:
    with open("quotes.csv", "r", encoding="UTF-8") as csv_file:
        for quote_line in csv_file:
            split = quote_line.split("|")
            quotes[split[0]] = split[1:]
except OSError:
    display_error_and_sleep("quotes.csv not found.")
if not quotes:
    display_error_and_sleep("No quotes found.\nCheck quotes.csv.")


# ---------------------------------------------------------------------------
# NVM (non-volatile memory) functions
# ---------------------------------------------------------------------------
# NVM layout:
#   bytes 0-3: magic cookie "LitC"
#   byte  4:   major version
#   byte  5:   minor version
#   bytes 6-7: year (big-endian uint16)
#   byte  8:   month
#   byte  9:   day
#   byte 10:   hour
#   byte 11:   minute
#   byte 12:   last displayed quote hour
#   byte 13:   last displayed quote minute
NVM_MAGIC = b"LitC"
NVM_VERSION_MAJOR = 1
NVM_VERSION_MINOR = 0
NVM_DATA_OFFSET = 6


def nvm_is_valid():
    """Check that NVM has a valid magic cookie and compatible version."""
    nvm = microcontroller.nvm
    if bytes(nvm[0:4]) != NVM_MAGIC:
        return False
    if nvm[4] < NVM_VERSION_MAJOR:
        return False
    return True


def get_nvm_date():
    """Read the saved date/time from NVM. Returns (year, month, day, hour, minute)."""
    nvm = microcontroller.nvm
    if not nvm_is_valid():
        return 0, 0, 0, 0, 0
    base = NVM_DATA_OFFSET
    year = (nvm[base] << 8) | nvm[base + 1]
    return year, nvm[base + 2], nvm[base + 3], nvm[base + 4], nvm[base + 5]


def save_nvm(now, quote_key):
    """Write all NVM data: header, date/time, and last displayed quote."""
    nvm = microcontroller.nvm
    nvm[0:4] = NVM_MAGIC
    nvm[4] = NVM_VERSION_MAJOR
    nvm[5] = NVM_VERSION_MINOR
    base = NVM_DATA_OFFSET
    nvm[base] = now.tm_year >> 8
    nvm[base + 1] = now.tm_year & 0xFF
    nvm[base + 2] = now.tm_mon
    nvm[base + 3] = now.tm_mday
    nvm[base + 4] = now.tm_hour
    nvm[base + 5] = now.tm_min
    quote_hour, quote_min = (int(x) for x in quote_key.split(":"))
    nvm[base + 6] = quote_hour
    nvm[base + 7] = quote_min


# ---------------------------------------------------------------------------
# Time synchronization
# ---------------------------------------------------------------------------
def get_current_time():
    """Get the current time, fetching from the network if needed.

    Returns (hour, minute, second, time_fetched) where time_fetched is True
    if the time was synced from the network (and NVM should be updated).
    """
    rtc_now = time.localtime()
    nvm_year, nvm_month, nvm_day, _, _ = get_nvm_date()
    if (nvm_year >= 2025 and rtc_now.tm_year == nvm_year
            and rtc_now.tm_mon == nvm_month
            and rtc_now.tm_mday == nvm_day):
        # RTC is trustworthy, use it directly
        print(f"RTC time: {rtc_now.tm_hour:02}:{rtc_now.tm_min:02}:{rtc_now.tm_sec:02}")
        return rtc_now.tm_hour, rtc_now.tm_min, rtc_now.tm_sec, False
    # Date mismatch — fetch from internet and sync RTC
    try:
        net = Network(status_neopixel=peripherals.neopixels)
        net.get_local_time(location=timezone)
        now = time.localtime()
        wifi.radio.enabled = False
        peripherals.neopixels.fill(0)
        print(f"Fetched time: {now.tm_hour:02}:{now.tm_min:02}:{now.tm_sec:02}")
        return now.tm_hour, now.tm_min, now.tm_sec, True
    except (OSError, RuntimeError, ValueError) as e:
        print(f"Failed to fetch time: {e}, using RTC value")
        return rtc_now.tm_hour, rtc_now.tm_min, rtc_now.tm_sec, False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
current_hour, current_minute, current_second, time_fetched = get_current_time()
current_minutes = current_hour * 60 + current_minute
current_time_key = f"{current_hour:02}:{current_minute:02}"
displayed_quote = None
if current_time_key in quotes:
    print(f"Displaying quote for {current_time_key} (current time {current_hour:02}:{current_minute:02}:{current_second:02})")
    update_text(current_time_key, clock_time=f"{current_hour:02}:{current_minute:02}:{current_second:02}")
    displayed_quote = current_time_key
else:
    # Find the most recent quote before now
    for offset in range(1, 1441):
        candidate = (current_minutes - offset) % 1440
        candidate_hour, candidate_min = divmod(candidate, 60)
        candidate_key = f"{candidate_hour:02}:{candidate_min:02}"
        if candidate_key in quotes:
            print(f"No quote at {current_time_key} (current time {current_hour:02}:{current_minute:02}:{current_second:02}), showing most recent: {candidate_key}")
            update_text(candidate_key, show_battery=True, clock_time=f"{current_hour:02}:{current_minute:02}:{current_second:02}")
            displayed_quote = candidate_key
            break

# Re-read seconds: the e-ink display refresh alone takes several seconds,
# plus CSV parsing and layout, so the original second value is stale
current_second = time.localtime().tm_sec

# Find the next quote time
sleep_seconds = None
for offset in range(1, 1441):  # check up to 24 hours ahead
    candidate = (current_minutes + offset) % 1440
    candidate_hour, candidate_min = divmod(candidate, 60)
    candidate_key = f"{candidate_hour:02}:{candidate_min:02}"
    if candidate_key in quotes:
        sleep_seconds = offset * 60 - current_second
        print(f"Next quote at {candidate_key}, sleeping {sleep_seconds}s ({offset}m)")
        break

if sleep_seconds is None:
    display_error_and_sleep("No quotes found.\nCheck quotes.csv.")

save_nvm(time.localtime(), displayed_quote)

time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
