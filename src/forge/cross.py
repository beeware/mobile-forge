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
    PLATFORM_TRIPLET = {
        "android": "linux-android",
        "iphoneos": "apple-ios",
        "iphonesimulator": "apple-ios-simulator",
        "appletvos": "apple-tvos",
        "appletvsimulator": "apple-tvos-simulator",
        "watchos": "apple-watchos",
        "watchsimulator": "apple-watchos-simulator",
    }

    def __init__(self, platform, platform_version, arch):
        self.platform = platform
        self.platform_version = platform_version
        self.arch = arch

        self.platform_identifier = self._platform_identifier(
            platform, platform_version, arch
        )
        self.tag = self.platform_identifier.replace("-", "_").replace(".", "_")
        self.venv_name = f"venv3.{sys.version_info.minor}-{self.tag}"
        self.platform_triplet = f"{self.arch}-{self.PLATFORM_TRIPLET[platform]}"

        # Prime the on-demand variable cache
        self._sysconfig_data = None
        self._install_root = None

    def __str__(self):
        return self.venv_name

    def exists(self) -> bool:
        """Does the cross environment exist?"""
        return self.venv_path.is_dir()

    @property
    def venv_path(self) -> Path:
        """The location of the cross environment on disk."""
        return Path.cwd() / self.venv_name

    @property
    def sysconfig_data(self) -> dict[str, str]:
        """The sysconfig data for the cross environment."""
        if self._sysconfig_data is None:
            # Run a script in the cross-venv that outputs the config variables
            config_var_repr = self.check_output(
                [
                    "python",
                    "-c",
                    "import sysconfig; print(sysconfig.get_config_vars())",
                ],
                encoding="UTF-8",
            )

            # Parse the output of the previous command as Python,
            # turning it back into a dict.
            config = {}
            exec(f"data = {config_var_repr}", config, config)
            self._sysconfig_data = config["data"]

        return self._sysconfig_data

    @property
    def install_root(self) -> Path:
        """The path that serves as the installation root for native libraries.

        This is the /opt folder inside the site-packages of the cross environment, so
        that native libraries can be installed as wheels.
        """
        if self._install_root is None:
            # Run a script to get the last element of the cross-venv's sys.path.
            # This should be the site-packages folder of the cross environment.
            cross_site_packages = self.check_output(
                [
                    "python",
                    "-c",
                    "import sys; print(sys.path[-1])",
                ],
                encoding="UTF-8",
            ).strip()
            self._install_root = Path(cross_site_packages) / "opt"
            if self.venv_path not in self._install_root.parents:
                raise RuntimeError(
                    f"Install root {self._install_root} doesn't appear to be "
                    "in the cross environment"
                )

        return self._install_root

    @classmethod
    def _platform_identifier(self, platform, version, arch):
        if platform == "android":
            if version is None:
                version = 21
            identifier = f"{platform}-{version}-{arch}"
        elif platform in {"iphoneos", "iphonesimulator"}:
            if version is None:
                version = "12.0"
            identifier = f"ios-{version}-{platform}-{arch}"
        elif platform in {"appletvos", "appletvsimulator"}:
            if version is None:
                version = "7.0"
            identifier = f"tvos-{version}-{platform}-{arch}"
        elif platform in {"watchos", "watchsimulator"}:
            if version is None:
                version = "4.0"
            identifier = f"watchos-{version}-{platform}-{arch}"
        else:
            raise ValueError(f"Don't know how to build wheels for {platform}")
        return identifier

    @classmethod
    def create(cls, host_python: Path, platform, platform_version, arch, clean=False):
        """Create a new cross compilation virtual environment.

        :param host_python: The path to the ``python`` binary for the host platform.
        :param platform: The host platform for the cross environment.
        :param platform_version: The minimum compatibility version for the cross environment.
        :param arch: The architecture for the cross environment.
        :param clean: Should a pre-existing environment matching the same descriptor
            be removed and recreated?
        :raises: ``RuntimeError`` if an environment matching the requested host already
            exists, and ``clean=False``.
        """
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
        # Ensure the cross environment has the most recent tools
        cross_venv.pip_install(["pip"], update=True)
        cross_venv.pip_install(["setuptools"], update=True)

        # Ensure the build environment has the most recent tools
        cross_venv.pip_install(["pip"], update=True, build=True)
        cross_venv.pip_install(["setuptools"], update=True, build=True)
        cross_venv.pip_install(["build", "wheel"], build=True)

        print()
        print(f"Cross platform-environment {cross_venv} created.")

    def verify(self):
        # python returns the cross-platform host tag.
        output = self.check_output(
            ["python", "-c", "import sysconfig; print(sysconfig.get_platform())"],
            encoding="UTF-8",
        ).strip()
        if output != self.platform_identifier:
            raise RuntimeError(
                f"Cross platform python should be {self.platform_identifier}; got {output}"
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
        if output != self.platform_identifier:
            raise RuntimeError(
                f"Cross platform cross-python should be {self.platform_identifier}; got {output}"
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
        env = venv_kwargs.get("env", {})

        # Remove the current venv from the path, and add the cross-env and the build-env
        path = os.getenv("PATH").split(":", 1)[1]
        env["PATH"] = os.pathsep.join(
            [
                str(self.venv_path / "bin"),
                str(self.venv_path / self.venv_path.name / "bin"),
                path,
            ]
        )

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
        """Run a command in the cross environment.

        This passes the provided arguments directly to invocation of ``subprocess.run``;
        however, the ``kwargs`` will be modified to make the process appear to be in an
        activated virtual environment. This will:

        * Prepend the cross-env ``bin`` and virtual environment ``bin`` to the ``PATH``,
          and remove the current virtualenv path.
        * Set the ``VIRTUAL_ENV`` environment variable
        * Remove the ``PYTHONHOME`` environment variable, if it exists.

        If ``env`` is passed in as a keyword argument, the values in that environment
        will be augmented by the virtualenv changes.

        :param args: The list of command line arguments
        :param kwargs: Any extra arguments to pass to the ``subprocess.run`` invocation.
        """
        print()
        print(f">>> {shlex.join(args)}")
        for key, value in kwargs.get("env", {}).items():
            print(f"    {key} = {shlex.quote(value)}")
        print()
        return subprocess.run(args, **self.cross_kwargs(kwargs))

    def pip_install(self, packages, update=False, build=False, wheels_path=None):
        """Install packages into the cross environment.

        :param packages: The list of package names/specifiers to install.
        :param update: Should the package be updated ("-U")
        :param build: Should the package be installed in the build environment? Defaults
            to installing in the host environment.
        :param wheels_path: A path to search for additional wheels ("--find-links").
        """
        # build-pip is a script; pip is a shim with a hashbang that points
        # at a python interpreter, which we can't invoke with subprocess.
        self.run(
            (["build-pip"] if build else ["python", "-m", "pip"])
            + ["install"]
            + (["-U"] if update else [])
            + (["--find-links", str(wheels_path)] if wheels_path else [])
            + packages,
            check=True,
        )


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
            host_python=Path(args.host_python),
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
