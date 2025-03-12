load("@container_structure_test//:defs.bzl", "container_structure_test")
load("@aspect_bazel_lib//lib:transitions.bzl", "platform_transition_filegroup")
load("@aspect_bazel_lib//lib:tar.bzl", "tar", "mtree_spec")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_distroless//distroless:defs.bzl", "cacerts", "group", "home", "passwd")
load("@rules_distroless//distroless:defs.bzl", "locale")



passwd(
    name = "passwd",
    entries = [
        {
            "uid": 0,
            "gid": 0,
            "home": "/root",
            "shell": "/bin/bash",
            "username": "root",
        },
        {
            "uid": 1000,
            "gid": 1000,
            "home": "/home/nonroot",
            "shell": "/bin/bash",
            "username": "nonroot",
        },
    ],
)


group(
    name = "group",
    entries = [
        {
            "name": "root",
            "gid": 0,
        },
        {
            "name": "nonroot",
            "gid": 1000,
        }
    ]
)

home(
    name = "home",
    dirs = [
        {
            "home": "/root",
            "uid": 0,
            "gid": 0,
        },
        {
            "home": "/home/nonroot",
            "uid": 1000,
            "gid": 1000,
        },
    ],
)

tar(
    name = "sh",
    mtree = [
        # needed as dpkg assumes sh is installed in a typical debian installation.
        "./bin/sh type=link link=/bin/bash",
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
       "./tmp uid=0 gid=0 mode=1777 time=1672560000 type=dir",
       "./home/nonroot uid=1000 gid=1000 mode=0755 time=1672560000 type=dir",
       "./home/nonroot/0 uid=1000 gid=1000 mode=0755 time=1672560000 type=dir",
       "./home/nonroot/tmp uid=1000 gid=1000 mode=0755 time=1672560000 type=dir",
        "./run/dbus uid=1000 gid=1000 mode=0755 time=1672560000 type=dir",
        "./var/lib/dbus/machine-id uid=0 gid=0 time=1672560000 mode=0755 type=file content=$(location :dbus_uuidgen)"
    ]
)

tar(
    name = "fix_ffmpeg_arm64",
    mtree = [
        "./usr/lib/aarch64-linux-gnu/libblas.so.3 type=link link=/usr/lib/aarch64-linux-gnu/blas/libblas.so.3",
        "./usr/lib/aarch64-linux-gnu/liblapack.so.3 type=link link=/usr/lib/aarch64-linux-gnu/lapack/liblapack.so.3",
    ]
)

tar(
    name = "fix_ffmpeg_x86_64",
    mtree = [
        "./usr/lib/x86_64-linux-gnu/libblas.so.3 type=link link=/usr/lib/x86_64-linux-gnu/blas/libblas.so.3",
        "./usr/lib/x86_64-linux-gnu/liblapack.so.3 type=link link=/usr/lib/x86_64-linux-gnu/lapack/liblapack.so.3",
    ]
)

tar(
    name = "app_layer",
    srcs = ["//examples/app:main"]
)

genrule(
    name = "zoom_layer",
    srcs = ["@zoom//:data.tar.xz"],
    outs = ["layer.tar.gz"],
    cmd = """
    # Per the dpkg-dev man page:
    # https://manpages.debian.org/bookworm/dpkg-dev/deb.5.en.html
    #
    # Debian data.tar files can be:
    #  - .tar uncompressed, supported since dpkg 1.10.24
    #  - .tar compressed with
    #    *  gzip: .gz
    #    * bzip2: .bz2, supported since dpkg 1.10.24
    #    *  lzma: .lzma, supported since dpkg 1.13.25
    #    *    xz: .xz, supported since dpkg 1.15.6
    #    *  zstd: .zst, supported since dpkg 1.21.18
    #
    # ZSTD_BIN can decompress all formats except bzip2
    #
    # The OCI image spec supports .tar and .tar compressed with gzip or zstd.
    # Bazel needs the output filename to be fixed in advanced so we settle for
    # gzip compression.

    data_file="$<"
    layer="$@"

    case "$$data_file" in
        *data.tar.gz)
            mv "$$data_file" "$$layer"
        ;;
        *data.tar)
            $(ZSTD_BIN) --compress --format=gzip "$$data_file" > "$$layer"
        ;;
        *data.tar.xz|*data.tar.zst|*data.tar.lzma)
            $(ZSTD_BIN) --force --decompress --stdout "$$data_file" |
            $(ZSTD_BIN) --compress --format=gzip - > "$$layer"
        ;;
        *)
            echo "ERROR: data file not supported: $$data_file"
            exit 1
        ;;
    esac
    """,
    toolchains = ["@zstd_toolchains//:resolved_toolchain"],
    visibility = ["//visibility:public"],
)


oci_image(
    name = "image",
    base = "@distroless_base",
    entrypoint = ["/examples/app/main"],
    tars = [
        ":passwd",
        ":group",
        ":home",
        ":sh",
        # This target contains all the installed packages.
        "@bookworm//:flat",
        ":machine_id",
        ":app_layer",
    ] + select({
        "@platforms//cpu:arm64": [":fix_ffmpeg_arm64"],
        "@platforms//cpu:x86_64": [":fix_ffmpeg_x86_64", ":zoom_layer"],
    }),
    user = "nonroot",
    env = {
        # tells any program you run where to find a nonroot-specific directory
        # in which it can store small temporary files.
        "XDG_RUNTIME_DIR": "/home/nonroot/0",
        "DISPLAY": ":1.0",
        "DBUS_STARTER_BUS_TYPE": "session",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/dbus/system_bus_socket",
        "TEMP": "/home/nonroot/tmp",
        "XAUTHORITY": "/home/nonroot/.Xauthority",
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
