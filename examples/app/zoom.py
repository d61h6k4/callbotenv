import asyncio
import base64
import logging
from pathlib import Path

import nodriver
from nodriver.core.browser import urllib

_LOGGER = logging.getLogger()


def get_meeting_id(url: str) -> str:
    """Extracts meeting id from the given url"""
    url_parsed = urllib.parse.urlparse(url)
    return url_parsed.path.split(sep="/")[-1]


async def get_browser():
    browser_config = nodriver.Config(
        headless=False,
        sandbox=False,
        browser_args=[
            "--auto-accept-camera-and-microphone-capture",
            "--window-size=960x540",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-plugins",
            "--log-path=/tmp/chrome.log",
            "--verbose"
        ],
    )
    _LOGGER.info(
        {
            "message": "Configuration of the browser",
            "config": repr(browser_config),
        }
    )

    # warm up browser start
    attempts = 5
    while attempts > 0:
        try:
            browser = await nodriver.start(config=browser_config)
            break
        except Exception:
            attempts -= 1

    try:
        browser = await nodriver.start(config=browser_config)
    except Exception as e:
        raise RuntimeError("Failed to start browser.") from e

    await browser.wait()
    await browser.grant_all_permissions()

    return browser


class ZoomOperator:
    def __init__(
        self,
        browser: nodriver.Browser,
        email: str = "some@gmail",
        password: str = "pwd",
        screenshots_dir: Path = Path("/tmp"),
        name: str = "AI-kit Meeting Bot",
    ):
        self.browser = browser
        self.email = email
        self.password = password
        self.session_id = base64.b64encode(email.encode("utf8")).decode("utf8")
        self.screenshots_dir = screenshots_dir / self.session_id
        self.name = name

        self.tab = None

        self._view_changed = False
        self._stop_video = False
        self._audio_muted = False

    def convert_to_web_join(self, url: str) -> str:
        """Converts a given zoom meeting url to join with web client url.

        https://devforum.zoom.us/t/is-there-a-way-to-make-the-zoom-url-join-link-to-always-use-the-browser-and-stop-prompting-use-of-the-zoom-app-software/62381/3
        """
        url_schema = urllib.parse.urlparse(url)
        meeting_id = get_meeting_id(url)
        return url_schema._replace(
            netloc="zoom.us", path=f"/wc/join/{meeting_id}"
        ).geturl()

    async def join(self, url: str):
        _LOGGER.info(
            {
                "message": "Joining the meeting",
                "session_id": self.session_id,
                "url": url,
                "web_join_url": self.convert_to_web_join(url),
            }
        )
        self.tab = await self.browser.get(self.convert_to_web_join(url))
        await self.tab.wait()
        await self.tab.fullscreen()

        await self.accept_cookies(self.tab)
        await self.tab.wait()
        await self.agree_with_terms(self.tab)
        await self.tab.wait()
        await self.set_name(self.tab)
        await self.tab.wait()
        await self.ask_to_join(self.tab)
        await self.tab.wait()

        screenshot_path = self.screenshots_dir / "on_a_call.jpg"
        await self.tab.save_screenshot(filename=screenshot_path)

        await self.change_view(self.tab)
        await self.join_audio(self.tab)
        await self.mute_audio(self.tab)

    async def post_join(self, n: int = 5):
        assert self.tab is not None, "Call post_join after join"

        while n > 0:
            # await self.unmute_audio(self.tab)
            # await self.mute_audio(self.tab)
            await self.change_view(self.tab)
            await self.disable_incoming_video(self.tab)

            await self.press_any_text(self.tab, "OK")
            await self.press_any_text(self.tab, "Allow")
            await self.press_any_text(self.tab, "Got it")

            await asyncio.sleep(300)
            n -= 1

    async def set_name(self, tab: nodriver.Tab):
        """Set name use to join a meeting"""
        _LOGGER.info(
            {
                "message": "Setting name to join the meeting",
                "sesison_id": self.session_id,
            }
        )
        try:
            set_name_input = await tab.wait_for("input#input-for-name")
        except asyncio.TimeoutError as e:
            _LOGGER.error({"message": "Failed to find input name", "error": repr(e)})
            return

        if not set_name_input:
            screenshot_path = self.screenshots_dir / "set_name_input.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find input with placeholder 'Your name' text on it. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await set_name_input.send_keys(self.name)

    async def exit(self):
        if self.tab is not None:
            await self.tab.close()

    async def accept_cookies(self, tab: nodriver.Tab):
        """Click on accept cookie button."""
        _LOGGER.info({"message": "Accept cookies.", "session_id": self.session_id})
        try:
            accept_btn = await tab.select("button#onetrust-accept-btn-handler")
        except TimeoutError:
            _LOGGER.error({"message": "Faield to find cookies accept btn"})
            accept_btn = None

        if not accept_btn:
            screenshot_path = self.screenshots_dir / "accept_cookies.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button accept cookies.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await accept_btn.click()

    async def agree_with_terms(self, tab: nodriver.Tab):
        """Click on I agree button."""
        _LOGGER.info({"message": "Agree with terms.", "session_id": self.session_id})
        try:
            btn = await tab.select("button#wc_agree1")
        except TimeoutError:
            _LOGGER.warning({"message": "Could not find the agree with terms button."})
            btn = None

        if not btn:
            screenshot_path = self.screenshots_dir / "agree_with_terms.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button I agree. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await btn.click()

    async def ask_to_join(self, tab: nodriver.Tab):
        """Click the button 'Join'"""
        _LOGGER.info(
            {
                "message": "Asking to join the meeting",
                "session_id": self.session_id,
            }
        )

        ask_to_join_btn = await tab.select("button.preview-join-button")
        if not ask_to_join_btn or ask_to_join_btn.tag != "button":
            screenshot_path = self.screenshots_dir / "ask_to_join_btn.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button of 'Join' span. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await ask_to_join_btn.click()

    async def join_audio(self, tab: nodriver.Tab):
        """Find and press 'Join Audio by Computer'."""
        _LOGGER.info(
            {
                "message": "Trying to press join audio button",
                "session_id": self.session_id,
            }
        )

        attempts = 3
        while attempts > 0:
            join_audio_btn = await tab.wait_for(
                text="Join Audio by Computer", timeout=30
            )

            if not join_audio_btn or join_audio_btn.tag != "button":
                screenshot_path = self.screenshots_dir / "join_audio_btn.jpg"
                await tab.save_screenshot(filename=screenshot_path)
                _LOGGER.error(
                    {
                        "message": "Expected to find button with 'Join Audio by Computer' text on it. See screenshot.",
                        "screenshot_path": screenshot_path,
                        "session_id": self.session_id,
                        "tag": join_audio_btn.tag,
                    }
                )
                await tab.sleep(t=1)
                attempts -= 1
            else:
                await join_audio_btn.click()
                return

    async def change_view(self, tab: nodriver.Tab):
        """Find view and change to Gallery."""
        if self._view_changed:
            return

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                {
                    "message": "Trying to change view",
                    "session_id": self.session_id,
                }
            )

        view_btn = await tab.query_selector("button[aria-label^='View']")
        if not view_btn:
            screenshot_path = self.screenshots_dir / "view_btn.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button with 'View'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return

        await view_btn.click()

        galery_view_selectors = [
            "a[aria-label^='Gallery View']",
            "a[aria-label^='Side-by-side: Gallery']",
        ]

        for selector in galery_view_selectors:
            gallery_view_link = await tab.query_selector(selector)

            if not gallery_view_link:
                screenshot_path = self.screenshots_dir / "gallery_view_a.jpg"
                await tab.save_screenshot(filename=screenshot_path)
                html = await tab.get_content()
                (self.screenshots_dir / "gallery_view_a.html").write_text(html)

                _LOGGER.error(
                    {
                        "message": "Expected to find a with 'Gallery View'. See screenshot.",
                        "screenshot_path": screenshot_path,
                        "session_id": self.session_id,
                    }
                )
                continue

            await gallery_view_link.click()
            self._view_changed = True

    async def press_any_text(self, tab: nodriver.Tab, text: str):
        """Find and press 'OK'."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                {
                    "message": f"Trying to press any {text} button",
                    "session_id": self.session_id,
                }
            )

        ok_btn = await tab.find_element_by_text(text=text)
        if ok_btn:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    {"message": f"Find element with {text} ", "tag": ok_btn.tag}
                )
            if ok_btn.tag != "button":
                await ok_btn.click()

    async def disable_incoming_video(self, tab: nodriver.Tab):
        if self._stop_video:
            return

        _LOGGER.info(
            {
                "message": "Trying to disable incoming video",
                "session_id": self.session_id,
            }
        )

        more_btn = await tab.query_selector(
            "button[aria-label^='More meeting control']"
        )
        if not more_btn:
            screenshot_path = self.screenshots_dir / "more_btn.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button with 'mOre meeting control'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return

        await more_btn.click()

        stop_video_link = await tab.query_selector(
            "a[aria-label^='Stop Incoming Video']"
        )

        if not stop_video_link:
            screenshot_path = self.screenshots_dir / "stop_video_link.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find a with 'Stop Incoming Video'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await stop_video_link.click()
        self._stop_video = True

    async def mute_audio(self, tab: nodriver.Tab):
        """Find and press 'Unmute'."""
        if self._audio_muted:
            return

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                {
                    "message": "Trying to mute my microphone",
                    "session_id": self.session_id,
                }
            )

        mute_btn = await tab.query_selector("button[aria-label^='mute my microphone']")

        if not mute_btn:
            screenshot_path = self.screenshots_dir / "mute_btn.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button with 'Mute'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await mute_btn.click()
        self._audio_muted = True

    async def unmute_audio(self, tab: nodriver.Tab):
        """Find and press 'Unmute'."""
        if not self._audio_muted:
            return

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                {
                    "message": "Trying to unmute my microphone",
                    "session_id": self.session_id,
                }
            )

        unmute_btn = await tab.query_selector(
            "button[aria-label^='unmute my microphone']"
        )

        if not unmute_btn:
            screenshot_path = self.screenshots_dir / "unmute_btn.jpg"
            await tab.save_screenshot(filename=screenshot_path)
            _LOGGER.error(
                {
                    "message": "Expected to find button with 'Unmute'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await unmute_btn.click()
        self._audio_muted = False

    async def select_speakers(self, tab: nodriver.Tab):
        """Find and press 'Speaker'."""

        _LOGGER.info(
            {
                "message": "Selecting speakers",
                "session_id": self.session_id,
            }
        )

        more_audio_controls_btn = await tab.query_selector(
            "button[aria-label^='More audio controls']"
        )

        if not more_audio_controls_btn:
            screenshot_path = self.screenshots_dir / "more_audio_controls.jpg"
            await tab.save_screenshot(filename=screenshot_path)

            html = await tab.get_content()
            (self.screenshots_dir / "more_audio_controls.html").write_text(html)

            _LOGGER.error(
                {
                    "message": "Expected to find button with 'More audio controls'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return
        await more_audio_controls_btn.click()

        system_speaker_link = await tab.query_selector(
            "a[aria-label^='Select a speaker Same as System selected']"
        )

        if not system_speaker_link:
            screenshot_path = self.screenshots_dir / "system_speaker_link.jpg"
            await tab.save_screenshot(filename=screenshot_path)

            html = await tab.get_content()
            (self.screenshots_dir / "system_speaker_link.html").write_text(html)

            _LOGGER.error(
                {
                    "message": "Expected to find a with 'Select a speaker Same as System selected'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return

        unrecognized_speaker_link = await tab.query_selector(
            "a[aria-label^='Select a speaker Unrecognized speaker1 unselect']"
        )

        if not unrecognized_speaker_link:
            screenshot_path = self.screenshots_dir / "unrecognized_speaker_link.jpg"
            await tab.save_screenshot(filename=screenshot_path)

            html = await tab.get_content()
            (self.screenshots_dir / "unrecognized_speaker_link.html").write_text(html)

            _LOGGER.error(
                {
                    "message": "Expected to find a with 'Select a speaker Same as System selected'. See screenshot.",
                    "screenshot_path": screenshot_path,
                    "session_id": self.session_id,
                }
            )
            return

        await unrecognized_speaker_link.click()
        await system_speaker_link.click()
