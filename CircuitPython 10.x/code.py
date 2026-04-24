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
# The MagTag's 296x128 e-ink display, with a white background rectangle
# and labels for each segment of the quote layout:
#   quote        - the prose before the time reference
#   time_label   - the bold time text (first line)
#   time_label_2 - the bold time text (overflow to second line)
#   after_label  - the prose after the time reference (first line)
#   after_label_2- the prose after the time reference (overflow)
#   author_label - book/author attribution at bottom-left
#   battery_label- clock time and battery % at bottom-right
display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

arial = bitmap_font.load_font("fonts/Arial-12.pcf")
bold = bitmap_font.load_font("fonts/Arial-Bold-12.pcf")
LINE_SPACING = 0.8
HEIGHT = arial.get_bounding_box()[1]  # line height in pixels
QUOTE_X = 10   # left margin
QUOTE_Y = 7    # top margin (label y is baseline-centered)

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


def get_battery_pct():
    """Read the battery voltage and return the charge percentage (0-100)."""
    voltage = peripherals.battery
    # Map voltage to percentage: 3.2V = 0%, 4.2V = 100% (LiPo range)
    pct = max(0, min(100, int((voltage - 3.2) / (4.2 - 3.2) * 100)))
    print(f"Battery: {voltage:.2f}V ({pct}%)")
    return pct


def should_show_status(battery_pct):
    """Decide whether to show clock/battery instead of author/title.

    Returns True (show status) on cold boot, button wake, or low battery.
    Otherwise returns False (show author/title).
    """
    # Cold boot: wake_alarm is None on first power-on or hard reset
    if alarm.wake_alarm is None:
        print("Cold boot — showing status")
        return True
    # Button press
    if isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
        print("Button wake — showing status")
        return True
    # Low battery
    if battery_pct < 20:
        print(f"Low battery ({battery_pct}%) — showing status")
        return True
    return False


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


def update_text(hour_min, show_status=False, clock_time=None, battery_pct=None):
    """Lay out and display a quote for the given time, then refresh the screen.

    If show_status is True, the bottom bar shows clock time and battery.
    Otherwise it shows the author and book title.
    """

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

    # -- Render the bottom bar: either author/title or clock/battery --
    if show_status:
        # Show clock time and battery percentage
        status_parts = []
        if clock_time:
            status_parts.append(clock_time)
        if battery_pct is not None:
            status_parts.append(f"{battery_pct}%")
        if status_parts:
            battery_label.text = " ".join(status_parts)
            battery_label.x = 296 - QUOTE_X - get_width(arial, battery_label.text)
    else:
        # Show author and book title
        author = f"{quotes[hour_min][2]} - {quotes[hour_min][1]}"
        wrapped_author = adafruit_display_text.wrap_text_to_pixels(
            author, 276, font=arial
        )
        author_label.text = "\n".join(wrapped_author)
        if len(wrapped_author) > 1:
            author_label.y = 103
        else:
            author_label.y = 115

    # -- Refresh the e-ink display --
    # Must wait for the display's minimum refresh interval before calling refresh
    time.sleep(display.time_to_refresh + 0.1)
    display.refresh()


# ---------------------------------------------------------------------------
# Quote data
# ---------------------------------------------------------------------------
# Each line is "HH:MM|before^time^after|author|title"
# Keyed by HH:MM so we can look up quotes by time of day
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
# NVM persists across deep sleep resets, unlike RAM. We use it to:
# 1. Store the date so we can tell if the RTC is still valid (avoiding
#    unnecessary WiFi time fetches that drain battery)
# 2. Track the last displayed quote to skip redundant e-ink refreshes
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


def get_nvm_last_quote():
    """Read the last displayed quote time from NVM. Returns 'HH:MM' or None."""
    nvm = microcontroller.nvm
    if not nvm_is_valid():
        return None
    base = NVM_DATA_OFFSET
    return f"{nvm[base + 6]:02}:{nvm[base + 7]:02}"


def should_update_display(quote_key):
    """Return True if the display should be refreshed for this quote.

    Skips the update if the same quote is already showing, unless
    a button press woke us from deep sleep.
    """
    woke_from_button = isinstance(alarm.wake_alarm, alarm.pin.PinAlarm)
    if woke_from_button:
        print("Button wake — forcing display update")
        return True
    last_quote = get_nvm_last_quote()
    if last_quote == quote_key:
        print(f"Quote {quote_key} already displayed — skipping refresh")
        return False
    return True


# ---------------------------------------------------------------------------
# Time synchronization
# ---------------------------------------------------------------------------
def get_current_time():
    """Get the current time, fetching from the network if needed.

    Returns (hour, minute, second, time_fetched) where time_fetched is True
    if the time was synced from the network (and NVM should be updated).

    The RTC keeps time during deep sleep but loses it on power loss.
    We compare the RTC date against the NVM-saved date to decide whether
    the RTC is trustworthy or we need to fetch time over WiFi.
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
        # Disable WiFi immediately after sync to save power
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
current_minutes = current_hour * 60 + current_minute  # minutes since midnight
current_time_key = f"{current_hour:02}:{current_minute:02}"  # "HH:MM" for quote lookup
displayed_quote = None
if current_time_key in quotes:
    displayed_quote = current_time_key
else:
    # Find the most recent quote before now
    # Scans backwards through all 1440 minutes in a day (wrapping at midnight)
    for offset in range(1, 1441):
        candidate = (current_minutes - offset) % 1440
        candidate_hour, candidate_min = divmod(candidate, 60)
        candidate_key = f"{candidate_hour:02}:{candidate_min:02}"
        if candidate_key in quotes:
            displayed_quote = candidate_key
            break

# Determine bottom bar content once, used by both display paths
battery_pct = get_battery_pct()
show_status = should_show_status(battery_pct)

# show_status is passed to update_text to choose author/title vs clock/battery
if displayed_quote and should_update_display(displayed_quote):
    if displayed_quote == current_time_key:
        print(f"Displaying quote for {current_time_key} (current time {current_hour:02}:{current_minute:02}:{current_second:02})")
        update_text(displayed_quote, show_status=show_status, clock_time=f"{current_hour:02}:{current_minute:02}:{current_second:02}", battery_pct=battery_pct)
    else:
        print(f"No quote at {current_time_key} (current time {current_hour:02}:{current_minute:02}:{current_second:02}), showing most recent: {displayed_quote}")
        update_text(displayed_quote, show_status=show_status, clock_time=f"{current_hour:02}:{current_minute:02}:{current_second:02}", battery_pct=battery_pct)

# Re-read seconds: the e-ink display refresh alone takes several seconds,
# plus CSV parsing and layout, so the original second value is stale
current_second = time.localtime().tm_sec

# Find the next quote time
# Scans forward through all 1440 minutes to find when to wake up next
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

# Save state to NVM before sleeping so the next wake can check
# whether the RTC is still valid and whether the display needs updating
save_nvm(time.localtime(), displayed_quote)

# -- Set up alarms: wake on next quote time or any button press --
# Peripherals holds references to the button pins; release them first
peripherals.deinit()
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)
# value=False, pull=True: buttons are active-low with internal pull-ups
button_alarms = [
    alarm.pin.PinAlarm(pin=board.D11, value=False, pull=True),  # Button A
    alarm.pin.PinAlarm(pin=board.D12, value=False, pull=True),  # Button B
    alarm.pin.PinAlarm(pin=board.D14, value=False, pull=True),  # Button C
    alarm.pin.PinAlarm(pin=board.D15, value=False, pull=True),  # Button D
]
# Deep sleep until either the timer fires or a button is pressed.
# This is a terminal call — execution resumes from the top of code.py.
alarm.exit_and_deep_sleep_until_alarms(time_alarm, *button_alarms)
