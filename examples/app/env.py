import logging
import os
import hashlib
import shlex
import socket
import subprocess
import time
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


class Xvfb:
    SLEEP_TIME_BEFORE_START = 0.1

    def __init__(
        self, width: int = 1280, height: int = 720, depth: int = 24, display: str = ":0"
    ):
        self._cmd = [
            "Xvfb",
            display,
            "-screen",
            "0",
            f"{width}x{height}x{depth}",
            "-ac",
            "-auth",
            "~/.Xauthority",
            "-dpi",
            "96",
            "-f",
            "0",
            "-nolisten",
            "tcp",
            "+extension",
            "RANDR",
            "+extension",
            "GLX"
        ]

        self.proc = None


    def __enter__(self):

        self.proc = subprocess.Popen(
            self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        _LOGGER.info(
            f"Xvfb started at {self.proc.pid} (returncode = {self.proc.returncode})"
        )
        # give Xvfb time to start
        time.sleep(self.__class__.SLEEP_TIME_BEFORE_START)
        ret_code = self.proc.poll()
        if ret_code is not None:
            _, err = self.proc.communicate()
            raise RuntimeError(
                f"Xvfb did not start ({ret_code}): {shlex.join(self._cmd)}\n{err.decode('utf8')}"
            )
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()


class XAuth:
    def __init__(
        self, display: str = ":0"
    ):
        self._cmd = ["xauth", "add", display, ".", self.generate_mcookie()]
        self.proc = None

    @staticmethod
    def generate_mcookie():
        """
        Generate a cookie string suitable for xauth.
        """
        data = os.urandom(16)  # 16 bytes = 128 bit
        return hashlib.md5(data).hexdigest()

    def __enter__(self):
        Path("/home/nonroot/.Xauthority").touch()

        self.proc = subprocess.Popen(
            self._cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _LOGGER.info(
            f"XAuth started at {self.proc.pid} (returncode = {self.proc.returncode})"
        )

        ret_code = self.proc.poll()
        if ret_code is not None:
            _, err = self.proc.communicate()
            raise RuntimeError(
                f"Xauth did not start ({ret_code}): {shlex.join(self._cmd)}\n{err.decode('utf8')}"
            )

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()



class Fluxbox:
    def __init__(self, display: str = ":0"):
        self._cmd = ["fluxbox", "-screen", "0", "-display", display]

        self.proc = None

    def __enter__(self):
        self.proc = subprocess.Popen(
            self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        _LOGGER.info(
            f"Fluxbox started at {self.proc.pid} (returncode = {self.proc.returncode})"
        )

        ret_code = self.proc.poll()
        if ret_code is not None:
            _, err = self.proc.communicate()
            raise RuntimeError(
                f"Fluxbox did not start ({ret_code}): {shlex.join(self._cmd)}\n{err.decode('utf8')}"
            )

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()


class DBus:
    SLEEP_TIME_BEFORE_START = 0.5

    def __init__(self, bus_address: str):
        self._cmd = [
            "dbus-daemon",
            "--session",
            "--fork",
            "--nosyslog",
            "--nopidfile",
            "--address",
            bus_address,
        ]
        bus_address_path = bus_address.split("=")[1]
        self.dbus_session_address = Path(bus_address_path)

        assert self.dbus_session_address.parent.exists(), (
            f"{self.dbus_session_address.parent} expected to be exist"
        )
        self.proc = None

    def __enter__(self):
        s = socket.socket(socket.AF_UNIX)
        s.bind(str(self.dbus_session_address))

        self.proc = subprocess.Popen(
            self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        _LOGGER.info(
            f"DBus started at {self.proc.pid} (returncode = {self.proc.returncode})"
        )

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()


class Pulseaudio:
    SLEEP_TIME_BEFORE_START = 0.5

    def __init__(self):
        self._cmd = [
            "pulseaudio",
            "--start",
            "--exit-idle-time=-1",
            "--disallow-exit",
            "--log-level=4",
            "--log-target=newfile:/home/nonroot/tmp/pulseaudio.log",
        ]

        self.proc = None

    def run_cmd(self, cmd: str):
        try:
            _ = subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            _LOGGER.error(
                {
                    "message": "Failed to execute the command",
                    "cmd": cmd,
                    "error": repr(e),
                }
            )
            raise RuntimeError("Failed to prepare env")

    def __enter__(self):
        self.run_cmd("mkdir -p ~/.config/pulse")
        self.run_cmd(
            "echo -n 'gIvST5iz2S0J1+JlXC1lD3HWvg61vDTV1xbmiGxZnjB6E3psXsjWUVQS4SRrch6rygQgtpw7qmghDFTaekt8qWiCjGvB0LNzQbvhfs1SFYDMakmIXuoqYoWFqTJ+GOXYByxpgCMylMKwpOoANEDePUCj36nwGaJNTNSjL8WBv+Bf3rJXqWnJ/43a0hUhmBBt28Dhiz6Yqowa83Y4iDRNJbxih6rB1vRNDKqRr/J9XJV+dOlM0dI+K6Vf5Ag+2LGZ3rc5sPVqgHgKK0mcNcsn+yCmO+XLQHD1K+QgL8RITs7nNeF1ikYPVgEYnc0CGzHTMvFR7JLgwL2gTXulCdwPbg=='| base64 -d>~/.config/pulse/cookie"
        )

        self.proc = subprocess.Popen(
            self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        _LOGGER.info(
            f"Pulseaudio started at {self.proc.pid} (returncode = {self.proc.returncode})"
        )

        time.sleep(self.__class__.SLEEP_TIME_BEFORE_START)
        ret_code = self.proc.poll()
        if ret_code is not None and ret_code != 0:
            _, err = self.proc.communicate()
            raise RuntimeError(
                f"Pulseaudio did not start ({ret_code}): {shlex.join(self._cmd)}\n{err.decode('utf8')}"
            )
        settings = [
            "pactl unload-module module-suspend-on-idle",
            "pactl load-module module-native-protocol-tcp",
            # Create a virtual speaker output
            'pactl load-module module-null-sink sink_name=SpeakerOutput sink_properties=device.description="Dummy_Output"',
            # Create a virtual microphone
            "pactl set-default-source SpeakerOutput.monitor",
            "pactl set-default-sink SpeakerOutput",
            # set volume
            "pactl set-sink-volume SpeakerOutput 100%",
            "pactl set-source-volume SpeakerOutput.monitor 100%",
        ]
        for cmd in settings:
            self.run_cmd(cmd)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()


class FFmpeg:
    def __init__(self, width: int = 1280, height: int = 720, display: str = ":0"):
        self._cmd = [
            "ffmpeg",
            "-video_size",
            f"{width}x{height}",
            "-framerate",
            "25",
            "-f",
            "x11grab",
            "-i",
            display,
            "-f",
            "pulse",
            "-ac",
            "2",
            "-i",
            "default",
            "/home/nonroot/tmp/output.mp4",
        ]
        self.proc = None

    def __enter__(self):
        self.proc = subprocess.Popen(self._cmd, stdin=subprocess.PIPE)

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        self.proc.communicate(input=b"q")
