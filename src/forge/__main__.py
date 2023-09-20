from __future__ import annotations

import argparse
import sys

from forge.cross import CrossVEnv
from forge.package import Package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Log more detail")

    parser.add_argument(
        "host",
        help=(
            "The host platform(s) to target. One of the top-level platform (android, "
            "iOS, tvOS, watchOS); or a platform:version:arch triple (e.g., "
            "iphonesimulator:12.0:x86_64 or android:21:arm64-v8a)."
        ),
    )
    parser.add_argument(
        "package_name_or_recipe",
        help="Name of a package in ./packages; or if it contains a slash, path to a recipe directory",
    )
    parser.add_argument(
        "--version",
        nargs="?",
        default=None,
        help="Package version to build (Optional; overrides version in meta.yaml)",
    )
    parser.add_argument(
        "--build_number",
        type=int,
        nargs="?",
        default=None,
        help="Package build number to build (Optional; overrides version in meta.yaml)",
    )

    args = parser.parse_args()

    try:
        platforms = [
            (abi, CrossVEnv.BASE_VERSION[args.host], arch)
            for abi, arch in CrossVEnv.HOST_PLATFORMS[args.host]
        ]
    except KeyError:
        parts = args.host.split(":")
        if len(parts) == 2:
            # Derive the base version from the provided ABI
            OS_MAP = {
                platform[0]: os_name
                for os_name, platforms in CrossVEnv.HOST_PLATFORMS.items()
                for platform in platforms
            }
            host = OS_MAP[parts[0]]
            platforms = [(parts[0], CrossVEnv.BASE_VERSION[host], parts[1])]
        elif len(parts) == 3:
            platforms = [parts]
        else:
            print()
            print("Invalid host. Host should be:")
            print(
                "  * the name of an operating system (android, iOS, tvOS, watchOS); or"
            )
            print("  * a tuple of abi:arch (e.g., iphoneos:arm64); or")
            print("  * a triple of abi:version:arch (e.g., iphoneos:12.0:arm64).")
            print()
            sys.exit(1)

    cross_venvs = []
    for platform in platforms:
        cross_venv = CrossVEnv(*platform)
        if not cross_venv.exists():
            print(
                f"""
Cross-environment {cross_venv} does not exist.
To create an environment, run:

    forge-env <path to python install> {platform[0]} {platform[1]} {platform[2]}
"""
            )
            sys.exit(1)

        cross_venvs.append(cross_venv)

    package = Package(
        args.package_name_or_recipe,
        version=args.version,
        build_number=args.build_number,
    )

    for cross_venv in cross_venvs:
        print("=" * 80)
        print(f"Building {package} for {cross_venv}")
        print("=" * 80)
        builder = package.builder(cross_venv)
        builder.prepare()
        print(f"\n[{cross_venv}] Build package")
        builder.build()


if __name__ == "__main__":
    main()
