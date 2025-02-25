import logging
import os
import shlex
import subprocess
import time

_LOGGER = logging.getLogger(__name__)


class Xvfb:
    SLEEP_TIME_BEFORE_START = 0.1

    def __init__(self, width: int = 960, height: int = 540, depth: int = 24, display: str = ":0"):
        self._cmd = [
            "Xvfb",
            display,
            "-screen",
            "0",
            f"{width}x{height}x{depth}",
            "-dpi",
            "96",
            "-f",
            "0",
            "-nocursor",
            "-nolisten",
            "tcp",
            "-nolisten",
            "unix",
            "+extension",
            "RANDR",
            "+extension",
            "GLX",
        ]
        self.proc = None

    def __enter__(self):
        self.proc = subprocess.Popen(self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        _LOGGER.info(f"Xvfb started at {self.proc.pid} (returncode = {self.proc.returncode})")
        # give Xvfb time to start
        time.sleep(self.__class__.SLEEP_TIME_BEFORE_START)
        ret_code = self.proc.poll()
        if ret_code is not None:
            _, err = self.proc.communicate()
            raise RuntimeError(f"Xvfb did not start ({ret_code}): {shlex.join(self._cmd)}\n{err.decode('utf8')}")

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()


class FFmpeg:
    def __init__(self, width: int = 960, height: int = 540, display: str = ":0"):
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
            "/tmp/output.mp4",
        ]
        self.proc = None

    def __enter__(self):
        subprocess.run(shlex.split("ln -s /usr/lib/aarch64-linux-gnu/blas/libblas.so.3 /usr/lib/aarch64-linux-gnu/"))
        subprocess.run(
            shlex.split("ln -s /usr/lib/aarch64-linux-gnu/lapack/liblapack.so.3 /usr/lib/aarch64-linux-gnu/")
        )
        self.proc = subprocess.Popen(self._cmd)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        assert self.proc is not None
        if self.proc.returncode is not None:
            self.proc.terminate()


def main():
    display = os.getenv("DISPLAY", ":0")
    with Xvfb(display=display):
        with FFmpeg(display=display):
            time.sleep(1.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
