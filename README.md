# MagTag Literary Quote Clock

A literary quote clock for the [Adafruit MagTag](https://www.adafruit.com/product/4800), based on the [Adafruit Learn Guide](https://learn.adafruit.com/magtag-literary-quote-clock/).

This fork is modified to run on battery power for extended periods. The original example runs in a loop with `time.sleep()`, keeping WiFi active and draining the battery quickly. This version uses deep sleep and minimizes network usage to make battery operation practical.

## Changes from the Original

### Deep Sleep Instead of `time.sleep()`
The original code stays awake in a loop, sleeping between updates with `time.sleep()`. This version uses `alarm.exit_and_deep_sleep_until_alarms()` to put the MagTag into deep sleep between quote changes, drastically reducing power consumption.

### Smart Wake Scheduling
Instead of waking every 60 seconds, the code calculates when the next quote is available and sleeps until that time. Sleep duration is capped at `RESYNC_INTERVAL_MINUTES` (default 30) so the clock can periodically resync with the internet to correct RTC drift.

### Button Wake
All four MagTag buttons (A–D) are configured as wake sources. Pressing any button during deep sleep wakes the device immediately, which will display the current quote along with clock time and battery status.

### RTC + NVM Time Caching
On first boot (or when the date changes), the code fetches the time from Adafruit IO over WiFi and sets the onboard RTC. The current date is saved to non-volatile memory (NVM) with a magic cookie header (`LitC`) and version byte for robustness. On subsequent wakes, if the NVM date matches the RTC date, the code skips WiFi entirely and reads the time from the RTC. This avoids a network round-trip on every single wake.

The clock also resyncs with the internet every 30 minutes (configurable via `RESYNC_INTERVAL_MINUTES`) to correct RTC drift, in addition to the automatic resync at midnight when the date rolls over.

### Smart Display Updates
The last displayed quote is tracked in NVM. If the device wakes and the same quote would be shown again, the e-ink refresh is skipped to save power and reduce display wear. A button press always forces a refresh.

### Author/Title vs. Status Bar
By default, the bottom of the screen shows the book title and author for the displayed quote. On cold boot, button wake, or when battery is below 20%, it switches to showing the current clock time and battery percentage instead.

### WiFi Shutdown
WiFi is disabled immediately after the time is fetched and the RTC is set. The NeoPixel status LED is also turned off at the same time. This avoids the radio idling during the e-ink display refresh, which takes several seconds.

### Watchdog Timer
A 60-second hardware watchdog timer is enabled at startup to prevent the device from hanging indefinitely (e.g. if a network call stalls). If any operation takes longer than 60 seconds, the device hard-resets and restarts. The watchdog is disabled immediately before entering deep sleep.

### Error Handling
If `quotes.csv` is missing or empty, an error message is displayed on the e-ink screen and the device deep sleeps indefinitely (until reset).

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
- `adafruit_minimqtt`
- `adafruit_ntp`
- `adafruit_portalbase`
- `adafruit_requests`
- `adafruit_ticks`
- `neopixel`
- `simpleio`

All other imports (`alarm`, `microcontroller`, `watchdog`, `wifi`, `board`, `displayio`, `time`) are CircuitPython built-ins.