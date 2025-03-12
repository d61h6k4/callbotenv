import logging
from pathlib import Path
import shlex
import subprocess
import textwrap

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
        self._cmd = ["zoom", "--url", meeting_url]

        self.proc = None
        self._pyautogui = None

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
        out, err = self.proc.communicate()
        _LOGGER.info(f"Zoom stdout: {out.decode('utf8')}")
        _LOGGER.error(f"Zoom stderr: {err.decode('utf8')}")

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()
