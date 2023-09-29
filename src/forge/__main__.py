from __future__ import annotations

import argparse
import sys

from forge.cross import CrossVEnv
from forge.package import Package


def main():
    parser = argparse.ArgumentParser(
        description="Build binary wheels for mobile platforms"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log more detail")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean the build folder prior to building.",
    )
    parser.add_argument(
        "-s",
        "--subset",
        choices=[
            "non-py",
            "py",
            "smoke",
            "smoke-non-py",
            "smoke-py",
            "non-smoke",
            "all",
        ],
        default="all",
        help=(
            "The subset of packages to compile. One of: non-py (all non-Python "
            "packages), py (all Python packages), smoke (only packages needed "
            "to do a support testbed check), smoke-non-py (only non-Python "
            "smoke packages), smoke-py (only Python smoke packages), non-smoke "
            "(all non-smoke packages), or all. Defaults to all."
        ),
    )

    parser.add_argument(
        "host",
        help=(
            "The host platform(s) to target. One of the top-level platform (android, "
            "iOS, tvOS, watchOS); or a platform:version:arch triple (e.g., "
            "iphonesimulator:12.0:x86_64 or android:21:arm64-v8a)."
        ),
    )
    parser.add_argument(
        "build_targets",
        nargs="*",
        default=None,
        help=(
            "Name of a package in ./recipes; or if it contains a slash, path "
            "to a recipe directory. Add ':<version>' to override the version; "
            "add '::<build>' to override the build number; add ':<version>:<build>' "
            "to override both the version and the build number."
        ),
    )

    args = parser.parse_args()

    try:
        platforms = [
            (sdk, CrossVEnv.BASE_VERSION[args.host], arch)
            for sdk, arch in CrossVEnv.HOST_SDKS[args.host]
        ]
    except KeyError:
        parts = args.host.split(":")
        if len(parts) == 2:
            # Derive the base version from the provided SDK
            OS_MAP = {
                platform[0]: os_name
                for os_name, platforms in CrossVEnv.HOST_SDKS.items()
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

    if not args.build_targets:
        build_targets = []

        if args.subset in {"all", "non-py", "smoke", "smoke-non-py"}:
            build_targets.extend(
                [
                    "oldest-supported-numpy",
                    "libjpeg",
                    "freetype",
                ]
            )

        if args.subset in {"all", "non-py", "non-smoke"}:
            build_targets.extend(
                [
                    "libpng",
                ]
            )

        # Pandas uses a meta-package called "oldest-supported-numpy" which installs,
        # predictably, the oldest version of numpy known to work on a given Python
        # version. This is done for Python ABI compatibility.
        oldest_supported_numpy = {
            8: "numpy:1.17.3",
            9: "numpy:1.19.3",
            10: "numpy:1.21.6",
            11: "numpy:1.23.2",
        }[sys.version_info.minor]

        if args.subset in {"all", "py", "smoke", "smoke-py"}:
            build_targets.extend(
                [
                    "lru-dict",
                    "pillow",
                    "numpy",
                    oldest_supported_numpy,
                    "pandas",
                    "cffi",
                    "cryptography",
                ]
            )

        if args.subset in {"all", "py", "non-smoke"}:
            build_targets.extend(
                [
                    "aiohttp",
                    "argon2-cffi",
                    "bcrypt",
                    "bitarray",
                    "blis",
                    "brotli",
                    "typed-ast",
                    "yarl",
                ]
            )
    else:
        build_targets = args.build_targets

    for build_target in build_targets:
        parts = build_target.split(":")
        package_name_or_recipe = parts[0]

        try:
            version = parts[1] if parts[1] else None
            try:
                build_number = int(parts[2])
            except IndexError:
                build_number = None
        except IndexError:
            version = None
            build_number = None

        package = Package(
            package_name_or_recipe,
            version=version,
            build_number=build_number,
        )

        for p, (sdk, sdk_version, arch) in enumerate(platforms):
            print("=" * 80)
            print(f"Building {package} for {sdk} {sdk_version} on {arch}")
            print("=" * 80)
            cross_venv = CrossVEnv(sdk=sdk, sdk_version=sdk_version, arch=arch)
            builder = package.builder(cross_venv)
            builder.prepare(clean=args.clean and (p == 0))
            print(f"\n[{cross_venv}] Build package")
            builder.build()


if __name__ == "__main__":
    main()
