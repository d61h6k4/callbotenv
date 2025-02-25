load("@container_structure_test//:defs.bzl", "container_structure_test")
load("@aspect_bazel_lib//lib:transitions.bzl", "platform_transition_filegroup")
load("@aspect_bazel_lib//lib:tar.bzl", "tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")


tar(
    name = "app_layer",
    srcs = ["//examples/app:main"]
)

oci_image(
    name = "image",
    base = "@distroless_base",
    entrypoint = ["examples/app/main"],
    tars = [
        # This target contains all the installed packages.
        "@bookworm//:flat",
        ":app_layer",
    ],
    user = "nobody",
    env = {
        "DISPLAY": ":1.0",
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
