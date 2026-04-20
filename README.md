# MagTag Literary Quote Clock

A literary quote clock for the [Adafruit MagTag](https://www.adafruit.com/product/4800), based on the [Adafruit Learn Guide](https://learn.adafruit.com/magtag-literary-quote-clock/).

This fork is modified to run on battery power for extended periods. The original example runs in a loop with `time.sleep()`, keeping WiFi active and draining the battery quickly. This version uses deep sleep and minimizes network usage to make battery operation practical.

## Changes from the Original

### Deep Sleep Instead of `time.sleep()`
The original code stays awake in a loop, sleeping between updates with `time.sleep()`. This version uses `alarm.exit_and_deep_sleep_until_alarms()` to put the MagTag into deep sleep between quote changes, drastically reducing power consumption.

### Smart Wake Scheduling
Instead of waking every 60 seconds, the code calculates when the next quote is available and sleeps until exactly that time. This minimizes the number of wake cycles.

### RTC + NVM Time Caching
On first boot (or when the date changes), the code fetches the time from Adafruit IO over WiFi and sets the onboard RTC. The current date is saved to non-volatile memory (NVM). On subsequent wakes, if the NVM date matches the RTC date, the code skips WiFi entirely and reads the time from the RTC. This avoids a network round-trip on every single wake. This also means the clock automatically resyncs with the internet once per day at midnight, when the RTC date rolls over and no longer matches the saved NVM date.

### Raw Socket HTTP Instead of `adafruit_io` Library
Time is fetched via a direct HTTPS request to the Adafruit IO REST API using built-in modules (`ssl`, `socketpool`, `json`). This eliminates the need for `adafruit_io`, `adafruit_minimqtt`, `adafruit_requests`, `adafruit_connection_manager`, `adafruit_datetime`, and `adafruit_ticks` — saving significant RAM and flash space.

### Battery Voltage Display
When the exact current time doesn't have a quote and a fallback is shown, the battery percentage is displayed in the corner of the screen. This can be triggered on demand by pressing any button between quote times to wake the device — since the current time won't match a quote, the fallback path runs and the battery level is shown.

### Button Wake Support
All four MagTag buttons (D11, D12, D14, D15) are configured as pin alarms, so pressing any button wakes the device from deep sleep and refreshes the display.

## Setup

1. Copy the contents of the `CircuitPython 10.x` folder to your CIRCUITPY drive.
2. Create a `settings.toml` file on the CIRCUITPY drive with:

```toml
CIRCUITPY_WIFI_SSID = "YourWiFiName"
CIRCUITPY_WIFI_PASSWORD = "YourWiFiPassword"
ADAFRUIT_AIO_USERNAME = "your_adafruit_username"
ADAFRUIT_AIO_KEY = "aio_xxxxxxxxxxxxxxxxxxxx"
TIMEZONE = "America/New_York"
```

Create a free account at [io.adafruit.com](https://io.adafruit.com) to get your username and API key. Use a valid [TZ database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for the timezone.

## Required Libraries

Only three libraries are needed in the `lib/` folder (available from the [Adafruit CircuitPython Bundle](https://circuitpython.org/libraries)):

- `adafruit_bitmap_font`
- `adafruit_display_text`
- `adafruit_display_shapes`

All other imports (`alarm`, `json`, `microcontroller`, `rtc`, `ssl`, `socketpool`, `wifi`, `board`, `analogio`, `displayio`) are CircuitPython built-ins.