# CallBot Environment

CallBot Environment is a setup designed to run a Zoom meeting bot on Linux. It utilizes `xvfb`, `fluxbox`, `pulseaudio`, and `chromium`, and employs `ffmpeg` to capture both audio and video output.

## Prerequisites

Ensure that you have [Bazel](https://bazel.build/) installed on your system before proceeding with the usage instructions.

## Usage

1. Run the following Bazel command to build and load the necessary image:

   ```bash
   bazel run //examples:image_load
   ```
2. Create a temporary directory to store the output video file:
   ```bash
   mkdir tmp
   ```
3. Execute the Docker command to run the Zoom meeting bot. Replace the MEETING_URL with your specific Zoom meeting link:
   ```bash
   docker run --volume `pwd`/tmp:/home/nonroot/tmp --rm -e "MEETING_URL=<your-zoom-meeting-url>" gcr.io/examples:latest
   ```
This command will run the bot and save the output video file in the `tmp` folder.

### Output
The output video file will be located in the tmp directory you created.
