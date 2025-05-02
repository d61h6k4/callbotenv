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
                            zoom = await ZoomApp.create(logger=_LOGGER)

                            try:
                                _ = await zoom.join(url)
                            except RuntimeError as e:
                                import shutil
                                shutil.copytree("/home/nonroot/.zoom", "/home/nonroot/tmp/zoom")
                                _LOGGER.info("Leaving... {repr(e)}")
                                return

                            asyncio.create_task(zoom.post_join())
                            asyncio.create_task(zoom.send_welcome_message("Hello, world!"))
                            try:
                                n = 180
                                while n > 0:
                                    await asyncio.sleep(1)
                                    n -= 1
                                    _LOGGER.info(f"Waiting... {n}")
                            except Exception as e:
                                import shutil
                                shutil.copytree("/home/nonroot/.zoom", "/home/nonroot/tmp/zoom")
                                _LOGGER.info(f"Leaving... {repr(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
