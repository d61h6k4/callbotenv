import asyncio
import base64
import textwrap
import time
import urllib.parse
from pathlib import Path

import logging
from python.runfiles import runfiles  # pyright: ignore

_LOGGER = logging.getLogger(__name__)

_ZOOM_CONFIG = textwrap.dedent("""
            [General]
            GeoLocale=system
            SensitiveInfoMaskOn=true
            AudioAutoAdjust=false
            autoPlayGif=false
            autoScale=true
            bForceMaximizeWM=false
            blockUntrustedSSLCert=false
            captureHDCamera=true
            chatListPanelLastWidth=230
            conf.webserver=https://zoom.us
            currentMeetingId=
            deviceID=
            enable.host.auto.grab=true
            enableAlphaBuffer=true
            enableCloudSwitch=false
            enableLog=true
            enableMiniWindow=false
            enableQmlCache=true
            enableScreenSaveGuard=false
            enableStartMeetingWithRoomSystem=false
            enableTestMode=false
            enableWaylandShare=false
            enablegpucomputeutilization=false
            fake.version=
            flashChatTime=0
            forceEnableTrayIcon=true
            forceSSOURL=
            host.auto.grab.interval=10
            isTransCoding=false
            logLevel=info
            MuteVoipWhenJoin=true
            newMeetingWithVideo=true
            playSoundForNewMessage=false
            scaleFactor=1
            shareBarTopMargin=0
            sso_domain=.zoom.us
            sso_gov_domain=.zoomgov.com
            system.audio.type=default
            upcoming_meeting_header_image=
            useSystemTheme=false
            userEmailAddress=
            [AS]
            showframewindow=true
            [CodeSnippet]
            lastCodeType=0
            wrapMode=0
            [chat.recent]
            recentlast.session=
            [zoom_new_im]
            is_landscape_mode=false
            main_frame_pixel_pos_narrow=
            main_frame_pixel_pos_wide=
            """)


class ZoomApp:
    def __init__(
        self,
        proc: asyncio.subprocess.Process,
        logger: logging.Logger,
        name: str = "Debug bot",
    ):
        self.proc = proc
        self.logger = logger
        self.name = name

        self._view_changed = False
        self._changed_to_fullscreen = False
        self._stop_video = False
        self._audio_muted = False

        self.r = runfiles.Create()

        self._pyautogui = None

    @property
    def pyautogui(self):
        if not self._pyautogui:
            import pyautogui

            self._pyautogui = pyautogui
        return self._pyautogui

    @classmethod
    async def create(
        cls,
        logger
    ):
        configs = Path("/home/nonroot/.config")
        configs.mkdir(parents=True, exist_ok=True)
        Path("/home/nonroot/.config/zoomus.conf").write_text(_ZOOM_CONFIG)

        proc = await asyncio.subprocess.create_subprocess_exec(
            "zoom", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"Zoom started at {proc.pid} (returncode = {proc.returncode})")

        if proc.returncode is not None:
            _, err = await proc.communicate()
            raise RuntimeError(
                f"Zoom did not start ({proc.returncode}): zoom\n{err.decode('utf8')}"
            )

        return cls(
            proc,
            logger,
        )

    async def exit(self):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()

    @staticmethod
    def extract_meeting_id_and_pwd(url):
        url_parsed = urllib.parse.urlparse(url)
        qs_parsed = urllib.parse.parse_qs(url_parsed.query)
        pwd = qs_parsed.get("pwd", [None])[0]
        meeting_id = url_parsed.path.split("/")[-1]

        return meeting_id, pwd

    def _wait_for(self, element_image: Path, attempts: int = 30):
        assert element_image.exists(), f"{element_image} doesn't exist"
        # Wait for zoom is started
        while attempts > 0:
            try:
                self.pyautogui.locateCenterOnScreen(str(element_image), confidence=0.8)
            except Exception as e:
                time.sleep(1)
                attempts -= 1
            else:
                break
        else:
            raise RuntimeError(f"Failed to find element {element_image}")

    def _get_image_by_name(self, name: str) -> Path:
        return Path(
            self.r.Rlocation(f"_main/examples/app/zoom_elements/{name}.png")
        )

    def _click_on_element(self, element_image: Path):
        x, y = self.pyautogui.locateCenterOnScreen(str(element_image), confidence=0.9)
        try:
            self.pyautogui.click(x, y)
        except TypeError as e:
            raise RuntimeError(f"Failed to click on {element_image}") from e

    def _join(self):
        join_meeting = self._get_image_by_name("join_meeting")
        self._wait_for(join_meeting)
        self._click_on_element(join_meeting)

        # Wait join a meeting form
        join_meeting_form = self._get_image_by_name("join_meeting_form")
        self._wait_for(join_meeting_form)
        # Fill join a meeting form
        # Insert meeting id
        self.pyautogui.press("tab")
        self.pyautogui.press("tab")
        self.pyautogui.write(self.meeting_id, interval=0.1)

        # Insert name
        self.pyautogui.press("tab")
        self.pyautogui.hotkey("ctrl", "a")
        self.pyautogui.write(self.name, interval=0.1)

        # Configure
        self.pyautogui.press("tab")
        self.pyautogui.press("space")
        self.pyautogui.press("tab")
        self.pyautogui.press("tab")
        self.pyautogui.press("space")
        self.pyautogui.press("tab")
        # Press join
        self.pyautogui.press("tab")
        self.pyautogui.press("space")

        if self.pwd is not None:
            # Wait the password form
            password_form = self._get_image_by_name("password_form")
            self._wait_for(password_form)
            self.pyautogui.write(self.pwd, interval=0.1)

            join = self._get_image_by_name("join")
            self._click_on_element(join)

        # Accept the agreement
        i_agree = self._get_image_by_name("i_agree")
        try:
            self._wait_for(i_agree)
        except RuntimeError:
            # If the agreement is not shown, it means that the meeting is already started
            self.logger.info("No agreement form shown")
        else:
            self._click_on_element(i_agree)

        # Wait for audio/video devices form
        av_device_select_form = self._get_image_by_name("av_device_select_form")
        self._wait_for(av_device_select_form)

        join = self._get_image_by_name("join")
        self._click_on_element(join)

    async def join(self, meeting_url):
        self.meeting_id, self.pwd = self.extract_meeting_id_and_pwd(meeting_url)
        loop = asyncio.get_running_loop()
        _ = await loop.run_in_executor(None, self._join)
        return

    async def post_join(self):
        loop = asyncio.get_running_loop()

        # Wait for audio options form
        join_with_computer_audio = self._get_image_by_name("join_with_computer_audio")
        while True:
            try:
                _ = await loop.run_in_executor(None, self._wait_for, join_with_computer_audio)
            except RuntimeError:
                wait_to_join = self._get_image_by_name("wait_room")
                try:
                    _ = await loop.run_in_executor(None, self._wait_for, wait_to_join)
                except RuntimeError:
                    if not await loop.run_in_executor(None, self._check_banners):
                        await asyncio.sleep(3)
                        continue
                else:
                    await asyncio.sleep(3)
                    continue
            else:
                break

        _ = await loop.run_in_executor(None, self._click_on_element, join_with_computer_audio)

        # Enter fullscreen
        with self.pyautogui.hold('alt'):
            self.pyautogui.press('f11')

        # Disable entering to the gallery view, because during sharing screen
        # speaker's image is too big.
        # _ = await loop.run_in_executor(None, self._gallery_view)
        while True:
            _ = await loop.run_in_executor(None, self._check_banners)
            _ = await loop.run_in_executor(None, self._sbs_speaker_view)
            _ = await loop.run_in_executor(None, self._fullscreen)
            await asyncio.sleep(30)

    def _fullscreen(self):
        if self._changed_to_fullscreen:
            return

        view = self._get_image_by_name("view")
        try:
            self._click_on_element(view)
        except Exception:
            # Seems zoom hasn't been in fullscreen yet
            # so we can't find the view button
            # Enter fullscreen
            with self.pyautogui.hold('alt'):
                self.pyautogui.press('f11')
            return

        # Hide window
        try:
            self._click_on_element(view)
        except Exception:
            ...

        # fullscreen = self._get_image_by_name("fullscreen")
        # try:
        #     self._wait_for(fullscreen, attempts=3)
        #     self._click_on_element(fullscreen)
        #     self._changed_to_fullscreen = True
        # except Exception:
        #     return

    def _gallery_view(self):
        if self._view_changed:
            return

        view = self._get_image_by_name("view")
        try:
            self._click_on_element(view)
        except Exception:
            return

        gallery_view = self._get_image_by_name("gallery_view")
        try:
            self._wait_for(gallery_view, attempts=3)
            self._click_on_element(gallery_view)
            self._view_changed = True
        except Exception:
            ...


    def _sbs_speaker_view(self):
        view = self._get_image_by_name("view")
        try:
            self._click_on_element(view)
        except Exception:
            return

        # In screen share mode the gallery view called side-by-side gallery
        side_by_side_gallery_view = self._get_image_by_name("side_by_side_speaker")
        try:
            self._wait_for(side_by_side_gallery_view, attempts=3)
            self._click_on_element(side_by_side_gallery_view)
        except Exception:
            # Click on the view again to hide it
            # if the view is not changed
            try:
                self._click_on_element(view)
            except Exception:
                return

    def _check_banners(self):
        ok = self._get_image_by_name("ok")
        try:
            self._click_on_element(ok)
            return True
        except Exception:
            ...

        got_it = self._get_image_by_name("got_it")
        try:
            self._click_on_element(got_it)
            return True
        except Exception:
            ...

        i_agree = self._get_image_by_name("i_agree")
        try:
            self._click_on_element(i_agree)
            return True
        except Exception:
            ...

        return False


    def _show_toolbars(self):
        # Mouse move to show toolbar
        width, height = self.pyautogui.size()
        y = (height / 2)
        self.pyautogui.moveTo(0, y, duration=0.5)
        self.pyautogui.moveTo(width - 1, y, duration=0.5)
