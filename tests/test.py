import asyncio
import logging
import sys
import threading
import time

sys.path.append("../")

from pysmarlaapi import Connection, Federwiege

try:
    from config import AUTH_TOKEN_B64, HOST
except ImportError:
    print("config.py or mandatory variables missing, please add in root folder...")
    sys.exit()

logging.basicConfig(level=20)

loop = asyncio.get_event_loop()
async_thread = threading.Thread(target=loop.run_forever)

connection = Connection(url=HOST, token_b64=AUTH_TOKEN_B64)

federwiege = Federwiege(loop, connection)


def main():
    async_thread.start()
    federwiege.register()
    federwiege.connect()

    while not (federwiege.connected and federwiege.available):
        time.sleep(1)

    swing_active_prop = federwiege.get_property("babywiege", "swing_active")
    intensity_prop = federwiege.get_property("babywiege", "intensity")

    oscillation_prop = federwiege.get_property("analyser", "oscillation")
    swing_count_prop = federwiege.get_property("analyser", "swing_count")

    display_name_prop = federwiege.get_property("info", "display_name")
    version_prop = federwiege.get_property("info", "version")

    time.sleep(1)

    print(display_name_prop.get())
    print(version_prop.get())
    print(swing_count_prop.get())

    value = swing_active_prop.get()
    print(f"Swing Active: {value}")
    intensity = intensity_prop.get()
    print(f"Intensity: {intensity}%")
    oscillation = oscillation_prop.get()
    print(f"Amplitude: {oscillation[0]}mm Period: {oscillation[1]}ms")

    swing_active_prop.set(True)
    intensity_prop.set(60)

    time.sleep(1)

    value = swing_active_prop.get()
    print(f"Swing Active: {value}")
    intensity = intensity_prop.get()
    print(f"Intensity: {intensity}%")
    oscillation = oscillation_prop.get()
    print(f"Amplitude: {oscillation[0]}mm Period: {oscillation[1]}ms")

    time.sleep(1)

    while True:
        value = swing_active_prop.get()
        print(f"Swing Active: {value}")
        intensity = intensity_prop.get()
        print(f"Intensity: {intensity}%")
        oscillation = oscillation_prop.get()
        print(f"Amplitude: {oscillation[0]}mm Period: {oscillation[1]}ms")
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    federwiege.disconnect()
    while federwiege.connected:
        time.sleep(1)
    loop.call_soon_threadsafe(loop.stop)
