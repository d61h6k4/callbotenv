import logging
import urllib.parse
import time
from pathlib import Path
import shlex
import subprocess
import textwrap


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
            enableMiniWindow=true
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
    def __init__(self, meeting_url: str):
        self._cmd = ["zoom"]

        self.proc = None
        self._pyautogui = None

        self.r = runfiles.Create()
        self.meeting_id, self.pwd = self.extrac_meeting_id_and_pwd(meeting_url)

    @property
    def pyautogui(self):
        if not self._pyautogui:
            import pyautogui
            self._pyautogui = pyautogui
        return self._pyautogui

    def __enter__(self):
        configs = Path("/home/nonroot/.config")
        configs.mkdir(parents=True, exist_ok=True)
        Path("/home/nonroot/.config/zoomus.conf").write_text(_ZOOM_CONFIG)

        self.proc = subprocess.Popen(
            self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        _LOGGER.info(
            f"Zoom started at {self.proc.pid} (returncode = {self.proc.returncode})"
        )

        ret_code = self.proc.poll()
        if ret_code is not None:
            _, err = self.proc.communicate()
            raise RuntimeError(
                f"Zoom did not start ({ret_code}): {shlex.join(self._cmd)}\n{err.decode('utf8')}"
            )

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()

    @staticmethod
    def extrac_meeting_id_and_pwd(url):
        url_parsed = urllib.parse.urlparse(url)
        qs_parsed = urllib.parse.parse_qs(url_parsed.query)
        pwd = qs_parsed.get('pwd', [None])[0]
        meeting_id = url_parsed.path.split('/')[-1]

        return meeting_id, pwd

    def join(self):
        join_meeting = self.r.Rlocation("_main/examples/app/zoom_elements/join_meeting.png")
        assert Path(join_meeting).exists()
        # Wait for zoom is started
        attempts = 30
        while attempts > 0:
            try:
                self.pyautogui.locateCenterOnScreen(join_meeting, confidence=0.8)
            except Exception as e:
                _LOGGER.error(f"Zoom not ready yet!")
                time.sleep(1)
                attempts -= 1
            else:
                break
        else:
            _LOGGER.error("Faield to start zoom")
            raise RuntimeError("Failed to start zoom")

        _LOGGER.info("Zoom is ready")


        _LOGGER.info("Join a meeting by ID..")

        join_meeting = self.r.Rlocation("_main/examples/app/zoom_elements/join_meeting.png")
        x, y = self.pyautogui.locateCenterOnScreen(join_meeting, confidence=0.9)

        try:
            self.pyautogui.click(x, y)
        except TypeError as e:
            raise RuntimeError(f"Failed to join the meeting: {self.meeting_id}") from e

        # Wait join a meeting form
        join_meeting_form = self.r.Rlocation("_main/examples/app/zoom_elements/join_meeting_form.png")
        assert Path(join_meeting_form).exists()
        # Wait for zoom is started
        attempts = 30
        while attempts > 0:
            try:
                self.pyautogui.locateCenterOnScreen(join_meeting_form, confidence=0.8)
            except Exception as e:
                _LOGGER.error(f"Zoom join meeting form is not ready yet!")
                time.sleep(1)
                attempts -= 1
            else:
                break
        else:
            raise RuntimeError("Faield to find join meeting form")

        _LOGGER.info("Zoom join meeting form is ready")

        # Fill join a meeting form
        # Insert meeting id
        self.pyautogui.press('tab')
        self.pyautogui.press('tab')
        self.pyautogui.write(self.meeting_id, interval=0.1)

        # Insert name
        self.pyautogui.press('tab')
        self.pyautogui.hotkey('ctrl', 'a')
        self.pyautogui.write("NAME OF THE BOT", interval=0.1)

        # Configure
        self.pyautogui.press('tab')
        self.pyautogui.press('space')
        self.pyautogui.press('tab')
        self.pyautogui.press('tab')
        self.pyautogui.press('space')
        self.pyautogui.press('tab')
        # Press join
        self.pyautogui.press('tab')
        self.pyautogui.press('space')

        # Wait the password form
        password_form = self.r.Rlocation("_main/examples/app/zoom_elements/password_form.png")
        assert Path(password_form).exists()
        # Wait for zoom is started
        attempts = 30
        while attempts > 0:
            try:
                self.pyautogui.locateCenterOnScreen(password_form, confidence=0.8)
            except Exception as e:
                _LOGGER.error(f"Zoom password form is not ready yet!")
                time.sleep(1)
                attempts -= 1
            else:
                break
        else:
            raise RuntimeError("Faield to find password form")

        _LOGGER.info("Zoom password form is ready")
        self.pyautogui.write(self.pwd, interval=0.1)

        join = self.r.Rlocation("_main/examples/app/zoom_elements/join.png")
        try:
            x, y = self.pyautogui.locateCenterOnScreen(join, minSearchTime=2, confidence=0.9)
            self.pyautogui.click(x, y)
        except TypeError as e:
            raise RuntimeError(f"Failed to join the meeting: {meet_id}") from e

        # Wait for audio/video devices form
        av_device_select_form = self.r.Rlocation("_main/examples/app/zoom_elements/av_device_select_form.png")
        attempts = 30
        while attempts > 0:
            try:
                self.pyautogui.locateCenterOnScreen(av_device_select_form, confidence=0.8)
            except Exception as e:
                _LOGGER.error(f"Zoom Audio/Video select device form is not ready yet!")
                time.sleep(1)
                attempts -= 1
            else:
                break
        else:
            raise RuntimeError("Faield to find Audio/Video select device form")

        try:
            x, y = self.pyautogui.locateCenterOnScreen(join, minSearchTime=2, confidence=0.9)
            self.pyautogui.click(x, y)
        except TypeError as e:
            raise RuntimeError(f"Failed to join the meeting: {meet_id}") from e

    def post_join(self):
        # Wait for audio options form
        join_with_computer_audio = self.r.Rlocation("_main/examples/app/zoom_elements/join_with_computer_audio.png")
        while True:
            attempts = 10
            while attempts > 0:
                try:
                    self.pyautogui.locateCenterOnScreen(join_with_computer_audio, confidence=0.9)
                except Exception as e:
                    _LOGGER.error(f"Zoom join with computer audio form is not ready yet!")
                    time.sleep(1)
                    attempts -= 1
                else:
                    break
            else:
                wait_to_join = self.r.Rlocation("_main/examples/app/zoom_elements/wait_room.png")
                try:
                    self.pyautogui.locateCenterOnScreen(wait_to_join, confidence=0.8)
                except Exception as e:
                    if not self.check_banners():
                        time.sleep(30)
                        continue
                else:
                    time.sleep(10)
                    continue
            break

        try:
            x, y = self.pyautogui.locateCenterOnScreen(join_with_computer_audio, confidence=0.9)
            _LOGGER.info("Join with computer audio..")
            self.pyautogui.click(x, y)
        except TypeError:
            _LOGGER.error("Could not join with computer audio!")

    def check_banners(self):
        ok = self.r.Rlocation("_main/examples/app/zoom_elements/ok.png")

        try:
            x, y = self.pyautogui.locateCenterOnScreen(ok, confidence=0.9)
            _LOGGER.info("Press OK button ..")
            self.pyautogui.click(x, y)
            return True
        except Exception as e:
            _LOGGER.error(repr(e))
            ...

        got_it = self.r.Rlocation("_main/examples/app/zoom_elements/got_it.png")

        try:
            x, y = self.pyautogui.locateCenterOnScreen(got_it, confidence=0.9)
            _LOGGER.info("Press OK button ..")
            self.pyautogui.click(x, y)
            return True
        except Exception as e:
            _LOGGER.error(repr(e))

        return False
