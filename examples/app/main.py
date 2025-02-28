import asyncio
import logging
import os

from examples.app.env import DBus, FFmpeg, Fluxbox, Pulseaudio, Xvfb
from examples.app.zoom import ZoomOperator, get_browser

_LOGGER = logging.getLogger(__name__)


async def main():
    display = os.getenv("DISPLAY", ":0")
    bus_address = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    assert bus_address is not None
    url = os.getenv("MEETING_URL")
    assert url is not None

    with Xvfb(display=display):
        with Fluxbox(display=display):
            with DBus(bus_address=bus_address):
                with Pulseaudio():
                    with FFmpeg(display=display):
                        browser = await get_browser()
                        z = ZoomOperator(browser=browser, name="Debugger BOT")
                        await z.join(url)
                        try:
                            await z.post_join(n=20)
                        except KeyboardInterrupt:
                            _LOGGER.info("Leaving...")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
