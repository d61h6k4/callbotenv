load("@rules_python//python:defs.bzl", "py_binary", "py_library", "py_test")

py_library(
    name = "env",
    srcs = ["env.py"]
)

py_library(
    name = "zoom",
    srcs = ["zoom.py"],
    deps = [
        "@pip//nodriver",
    ]
)

py_library(
    name = "zoom_app",
    srcs = ["zoom_app.py"],
    data = [
        "//examples/app/new_zoom_elements:images"
    ],
    deps = [
        "@pip//pyautogui",
        "@pip//opencv_python",
        "@pip//pillow",
        "@rules_python//python/runfiles"
    ]
)

py_binary(
  name = "main",
  srcs = ["main.py"],
  deps = [
    ":env",
    ":zoom_app"
  ],
  visibility = ["//visibility:public"]
)
