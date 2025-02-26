load("@container_structure_test//:defs.bzl", "container_structure_test")
load("@aspect_bazel_lib//lib:transitions.bzl", "platform_transition_filegroup")
load("@aspect_bazel_lib//lib:tar.bzl", "tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@bazel_skylib//rules:write_file.bzl", "write_file")

tar(
    name = "sh",
    mtree = [
        # needed as dpkg assumes sh is installed in a typical debian installation.
        "./bin/sh type=link link=/bin/bash",
    ],
)

tar(
    name = "awk",
    mtree = [
        "./usr/bin/awk type=link link=/usr/bin/mawk",
    ],
)

write_file(
    name = "dbus_uuidgen",
    out = "machine-id",
    content = ["e51fbc66123907e0a195a21967bef7e4"]
)

tar(
    name = "machine_id",
    srcs = [":dbus_uuidgen"],
    mtree = [
        "./home/nonroot/0 uid=65532 gid=65532 mode=0755 time=1672560000 type=dir",
        "./run/dbus uid=65532 gid=65532 mode=0755 time=1672560000 type=dir",
        "./var/lib/dbus/machine-id uid=0 gid=0 time=1672560000 mode=0755 type=file content=$(location :dbus_uuidgen)"
    ]
)

tar(
    name = "fix_ffmpeg",

    mtree = select({
        "@platforms//cpu:arm64": [
        "./usr/lib/aarch64-linux-gnu/libblas.so.3 type=link link=/usr/lib/aarch64-linux-gnu/blas/libblas.so.3",
        "./usr/lib/aarch64-linux-gnu/liblapack.so.3 type=link link=/usr/lib/aarch64-linux-gnu/lapack/liblapack.so.3",
    ],
        "@platforms//cpu:x86_64": [
        "./usr/lib/x86_64-linux-gnu/libblas.so.3 type=link link=/usr/lib/x86_64-linux-gnu/blas/libblas.so.3",
        "./usr/lib/x86_64-linux-gnu/liblapack.so.3 type=link link=/usr/lib/x86_64-linux-gnu/lapack/liblapack.so.3",
    ],
    }),
)

tar(
    name = "app_layer",
    srcs = ["//examples/app:main"]
)

oci_image(
    name = "image",
    base = "@distroless_base",
    entrypoint = ["examples/app/main"],
    tars = [
        ":sh",
        ":awk",
        # This target contains all the installed packages.
        "@bookworm//:flat",
        ":machine_id",
        ":app_layer",
        ":fix_ffmpeg",
    ],
    user = "nonroot",
    env = {
        # tells any program you run where to find a nonroot-specific directory
        # in which it can store small temporary files.
        "XDG_RUNTIME_DIR": "/home/nonroot/0",
        "DISPLAY": ":99",
        "DBUS_STARTER_BUS_TYPE": "session",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/dbus/system_bus_socket",
        "TEMP": "/home/nonroot",
    }
)


platform(
    name = "linux_arm64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:arm64",
    ],
)

platform(
    name = "linux_amd64",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
)

platform_transition_filegroup(
    name = "image_platform",
    srcs = [":image"],
    target_platform = select({
        "@platforms//cpu:arm64": ":linux_arm64",
        "@platforms//cpu:x86_64": ":linux_amd64",
    }),
)

# To build the image and load it into it into a local runtime:
# $ bazel run //examples:image_load
# $ docker run --rm gcr.io/examples:latest
oci_load(
    name = "image_load",
    image = ":image_platform",
    repo_tags = ["gcr.io/examples:latest"],
)

container_structure_test(
    name = "test",
    configs = select({
        "@platforms//cpu:arm64": ["test_linux_arm64.yaml"],
        "@platforms//cpu:x86_64": ["test_linux_amd64.yaml"],
    }),
    image = ":image_platform",
    #target_compatible_with = COMPATIBLE_WITH,
)
