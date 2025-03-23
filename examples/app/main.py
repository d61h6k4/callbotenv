import asyncio
import logging
import os

from examples.app.env import DBus, FFmpeg, Fluxbox, Pulseaudio, XAuth, Xvfb
from examples.app.zoom_app import ZoomApp

_LOGGER = logging.getLogger(__name__)


async def main():
    display = os.getenv("DISPLAY", ":0")
    bus_address = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    assert bus_address is not None
    url = os.getenv("MEETING_URL")
    assert url is not None

    with Xvfb(display=display):
        with XAuth(display=display):
            with Fluxbox(display=display):
                with DBus(bus_address=bus_address):
                    with Pulseaudio():
                        with FFmpeg(display=display):
                            with ZoomApp(url) as zoom:
                                loop = asyncio.get_running_loop()


                                zoom.join()
                                zoom.post_join()
                                try:
                                    n = 180
                                    while n > 0:
                                        await asyncio.sleep(1)
                                        n -= 1
                                        _LOGGER.info(f"Waiting... {n}")
                                        _ = await loop.run_in_executor(None, zoom.check_banners)
                                        _ = await loop.run_in_executor(None, zoom.show_toolbars)
                                except Exception as e:
                                    _LOGGER.info(f"Leaving... {repr(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
