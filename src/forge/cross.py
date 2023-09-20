from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import sysconfig
from os.path import abspath
from pathlib import Path


class CrossVEnv:
    BASE_VERSION = {
        "android": "21",
        "iOS": "12.0",
        "tvOS": "7.0",
        "watchOS": "4.0",
    }

    HOST_PLATFORMS = {
        "android": [
            ("android", "armeabi-v7a"),
            ("android", "arm64-v8a"),
            ("android", "x86"),
            ("android", "x86_64"),
        ],
        "iOS": [
            ("iphoneos", "arm64"),
            ("iphonesimulator", "arm64"),
            ("iphonesimulator", "x86_64"),
        ],
        "tvOS": [
            ("appletvos", "arm64"),
            ("appletvsimulator", "arm64"),
            ("appletvsimulator", "x86_64"),
        ],
        "watchOS": [
            ("watchos", "arm64_32"),
            ("watchsimulator", "arm64"),
            ("watchsimulator", "x86_64"),
        ],
    }

    def __init__(self, platform, platform_version, arch):
        self.platform = platform
        self.platform_version = platform_version
        self.arch = arch

        self.tag = self._tag(platform, platform_version, arch)
        self.venv_name = f"venv3.{sys.version_info.minor}-{self.tag.replace('-', '_').replace('.', '_')}"

    def __str__(self):
        return self.venv_name

    def exists(self):
        return self.venv_path.is_dir()

    @property
    def venv_path(self):
        return Path.cwd() / self.venv_name

    @classmethod
    def _tag(self, platform, version, arch):
        if platform == "android":
            if version is None:
                version = 21
            tag = f"{platform}-{version}-{arch}"
        elif platform in {"iphoneos", "iphonesimulator"}:
            if version is None:
                version = "12.0"
            tag = f"ios-{version}-{platform}-{arch}"
        elif platform in {"appletvos", "appletvsimulator"}:
            if version is None:
                version = "7.0"
            tag = f"tvos-{version}-{platform}-{arch}"
        elif platform in {"watchos", "watchsimulator"}:
            if version is None:
                version = "4.0"
            tag = f"watchos-{version}-{platform}-{arch}"
        else:
            raise ValueError(f"Don't know how to build wheels for {platform}")
        return tag

    @classmethod
    def create(cls, host_python, platform, platform_version, arch, clean=False):
        host_python = Path(host_python)

        cross_venv = CrossVEnv(platform, platform_version, arch)

        if cross_venv.exists():
            if clean:
                print(f"Removing old {cross_venv} environment...")
                shutil.rmtree(cross_venv.venv_path)
            else:
                raise RuntimeError(f"Environment {cross_venv} already exists.")

        print(f"Creating {cross_venv}...")
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "crossenv",
                    str(host_python),
                    cross_venv.venv_name,
                ],
                encoding="UTF-8",
                check=True,
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                f"Unable to create cross platform environment {cross_venv}."
            )

        print("Verifying cross-platform environment...")
        cross_venv.verify()
        print("done.")

        print("Updating cross-platform tools...")
        cross_venv.run(["build-pip", "install", "-U", "pip"])
        cross_venv.run(["build-pip", "install", "-U", "setuptools"])
        cross_venv.run(["build-pip", "install", "build", "wheel"])

        print()
        print(f"Cross platform-environment {cross_venv} created.")

    def verify(self):
        # python returns the cross-platform host tag.
        output = self.check_output(
            ["python", "-c", "import sysconfig; print(sysconfig.get_platform())"],
            encoding="UTF-8",
        ).strip()
        if output != self.tag:
            raise RuntimeError(
                f"Cross platform python should be {self.tag}; got {output}"
            )

        # python is the same version as the local python
        local_python_version = sys.version.split(" ")[0]
        python_version = self.check_output(
            ["python", "-c", "import sys; print(sys.version.split(' ')[0])"],
            encoding="UTF-8",
        ).strip()
        if python_version != local_python_version:
            raise RuntimeError(
                f"Cross platform python should be {local_python_version!r}; got {python_version!r}"
            )

        # build-python returns the build environment tag.
        output = self.check_output(
            ["build-python", "-c", "import sysconfig; print(sysconfig.get_platform())"],
            encoding="UTF-8",
        ).strip()
        if output != sysconfig.get_platform():
            raise RuntimeError(
                f"Cross platform build-python should be {sysconfig.get_platform()}; got {output}"
            )

        # build-python is the same version as the local python
        build_python_version = self.check_output(
            ["build-python", "-c", "import sys; print(sys.version.split(' ')[0])"],
            encoding="UTF-8",
        ).strip()
        if build_python_version != local_python_version:
            raise RuntimeError(
                f"Cross platform build-python should be {local_python_version}; got {build_python_version}"
            )

        # cross-python returns the cross-platform host tag.
        output = self.check_output(
            ["cross-python", "-c", "import sysconfig; print(sysconfig.get_platform())"],
            encoding="UTF-8",
        ).strip()
        if output != self.tag:
            raise RuntimeError(
                f"Cross platform cross-python should be {self.tag}; got {output}"
            )

        # cross-python is the same version as the local python
        cross_python_version = self.check_output(
            ["cross-python", "-c", "import sys; print(sys.version.split(' ')[0])"],
            encoding="UTF-8",
        ).strip()
        if cross_python_version != local_python_version:
            raise RuntimeError(
                f"Cross platform python should be {local_python_version}; got {cross_python_version}"
            )

    def cross_kwargs(self, kwargs):
        venv_kwargs = kwargs.copy()
        env = venv_kwargs.get("ENV", {})

        # Remove the current venv from the path, and add the cross-env and the build-env
        path = os.getenv("PATH").split(":", 1)[1]
        env[
            "PATH"
        ] = f"{self.venv_path / 'bin'}:{self.venv_path / self.venv_path.name / 'bin'}:{path}"

        # Set VIRTUALENV to the active venv
        env["VIRTUAL_ENV"] = self.venv_path / self.venv_path.name

        # Remove PYTHONHOME if it's set
        try:
            del env["PYTHONHOME"]
        except KeyError:
            pass

        venv_kwargs["env"] = env
        return venv_kwargs

    def check_output(self, args, **kwargs):
        return subprocess.check_output(args, **self.cross_kwargs(kwargs))

    def run(self, args, **kwargs):
        print()
        print(f">>> {shlex.join(args)}")
        print()
        return subprocess.run(args, **self.cross_kwargs(kwargs))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Log more detail")

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Create a clean cross-platform virtual environment",
    )

    parser.add_argument(
        "--platform",
        choices=sorted(
            {
                platform[0]
                for platforms in CrossVEnv.HOST_PLATFORMS.values()
                for platform in platforms
            }
        ),
        required=True,
        help="The host platform to target.",
    )
    parser.add_argument(
        "--platform-version",
        default=None,
        help="The compatibility version for the host platform.",
    )
    parser.add_argument(
        "--arch", required=True, help="The CPU architecture for the host platform."
    )
    parser.add_argument(
        "host_python",
        metavar="DIR",
        type=abspath,
        help="Path to the python executable of the Python built for the host platform.",
    )

    args = parser.parse_args()

    try:
        CrossVEnv.create(
            host_python=args.host_python,
            platform=args.platform,
            platform_version=args.platform_version,
            arch=args.arch,
            clean=args.clean,
        )
    except RuntimeError as e:
        print()
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
