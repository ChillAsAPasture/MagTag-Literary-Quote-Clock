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

### WiFi Shutdown
WiFi is disabled immediately after the time is fetched and the RTC is set. The NeoPixel status LED is also turned off at the same time. This avoids the radio idling during the e-ink display refresh, which takes several seconds.

### Battery Voltage Display
When the exact current time doesn't have a quote and a fallback is shown, the battery percentage is displayed in the corner of the screen. This can be triggered on demand by pressing any button between quote times to wake the device — since the current time won't match a quote, the fallback path runs and the battery level is shown.

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

The following libraries are needed in the `lib/` folder (available from the [Adafruit CircuitPython Bundle](https://circuitpython.org/libraries)):

- `adafruit_bitmap_font`
- `adafruit_connection_manager`
- `adafruit_display_shapes`
- `adafruit_display_text`
- `adafruit_fakerequests`
- `adafruit_io`
- `adafruit_magtag`
- `adafruit_portalbase`
- `adafruit_requests`
- `neopixel`
- `simpleio`

All other imports (`alarm`, `microcontroller`, `wifi`, `board`, `displayio`, `time`) are CircuitPython built-ins.