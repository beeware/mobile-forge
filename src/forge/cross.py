from __future__ import annotations

import argparse
import itertools
import os
import shutil
import sys
import sysconfig
from pathlib import Path

from forge import subprocess


class CrossVEnv:
    BASE_VERSION = {
        "android": "24",
        "iOS": "13.0",
        "tvOS": "12.0",
        "watchOS": "4.0",
    }

    HOST_SDKS = {
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
    XCFRAMEWORK_SLICES = {
        ("iphonesimulator", "arm64"): "ios-arm64_x86_64-simulator",
        ("iphonesimulator", "x86_64"): "ios-arm64_x86_64-simulator",
        ("iphoneos", "arm64"): "ios-arm64",
        ("appletvsimulator", "arm64"): "tvos-arm64_x86_64-simulator",
        ("appletvsimulator", "x86_64"): "tvos-arm64_x86_64-simulator",
        ("appletvos", "arm64"): "tvos-arm64",
        ("watchsimulator", "arm64"): "watchos-arm64_x86_64-simulator",
        ("watchsimulator", "x86_64"): "watchos-arm64_x86_64-simulator",
        ("watchos", "arm64_32"): "watchos-arm64_32",
    }

    def __init__(self, sdk, sdk_version, arch):
        self.sdk = sdk
        self.sdk_version = sdk_version
        self.arch = arch

        self.host_os = {
            sdk: host_os for host_os, sdks in self.HOST_SDKS.items() for sdk, _ in sdks
        }[self.sdk]
        self.platform_identifier = self._platform_identifier(sdk, sdk_version, arch)
        self.tag = self.platform_identifier.replace("-", "_").replace(".", "_")
        self.venv_name = f"venv3.{sys.version_info.minor}-{self.tag}"
        self.platform_triplet = f"{self.arch}-{self.PLATFORM_TRIPLET[sdk]}"

        # Prime the on-demand variable cache
        self._sysconfig_data = None
        self._install_root = None
        self._sdk_root = None

    def __str__(self):
        return self.venv_name

    def exists(self) -> bool:
        """Does the cross environment exist?"""
        return self.venv_path.is_dir()

    @property
    def host_python_home(self):
        support_path = Path(os.getenv("MOBILE_FORGE_SUPPORT_PATH"))
        return (
            support_path
            / f"3.{sys.version_info.minor}"
            / self.host_os
            / "Python.xcframework"
            / self.XCFRAMEWORK_SLICES[(self.sdk, self.arch)]
        )

    @property
    def venv_path(self) -> Path:
        """The location of the cross environment on disk."""
        if self.location is None:
            raise RuntimeError("Cross environment hasn't been created.")
        return self.location / self.venv_name

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

    @property
    def sdk_root(self) -> Path:
        """The path that contains the platform's SDK.

        This is the root folder where adding `/include` gives the include path, and
        `/lib` give the library path.
        """
        if self._sdk_root is None:
            # Run a script to get the last element of the cross-venv's sys.path.
            # This should be the site-packages folder of the cross environment.
            cross_site_packages = self.check_output(
                ["xcrun", "--show-sdk-path", "--sdk", self.sdk],
                encoding="UTF-8",
            ).strip()
            self._sdk_root = Path(cross_site_packages)

        return self._sdk_root

    @classmethod
    def _platform_identifier(self, sdk, version, arch):
        if sdk == "android":
            if version is None:
                version = 21
            identifier = f"{sdk}-{version}-{arch}"
        elif sdk in {"iphoneos", "iphonesimulator"}:
            if version is None:
                version = "13.0"
            identifier = f"ios-{version}-{arch}-{sdk}"
        elif sdk in {"appletvos", "appletvsimulator"}:
            if version is None:
                version = "12.0"
            identifier = f"tvos-{version}-{arch}-{sdk}"
        elif sdk in {"watchos", "watchsimulator"}:
            if version is None:
                version = "4.0"
            identifier = f"watchos-{version}-{arch}-{sdk}"
        else:
            raise ValueError(f"Don't know how to build wheels for {sdk}")
        return identifier

    def create(
        self,
        location=None,
        clean=False,
    ):
        """Create a new cross compilation virtual environment.

        :param location: The location in which to create the cross env. Defaults to the
            current working directory.
        :param clean: Should a pre-existing environment matching the same descriptor
            be removed and recreated?
        :raises: ``RuntimeError`` if an environment matching the requested host already
            exists, and ``clean=False``.
        """
        host_python = self.host_python_home / f"bin/python3.{sys.version_info.minor}"
        if not host_python.is_file():
            raise RuntimeError(f"Can't find host python {host_python}")

        host_sysconfig = (
            self.host_python_home
            / f"lib/python3.{sys.version_info.minor}"
            / f"_sysconfigdata__{self.host_os.lower()}_{self.arch}-{self.sdk}.py"
        )
        if not host_sysconfig.is_file():
            raise RuntimeError(f"Can't find host sysconfig {host_sysconfig}")

        self.location = Path(location).resolve() if location else Path.cwd()
        if self.exists():
            if clean:
                print(f"Removing old {self} environment...")
                shutil.rmtree(self.venv_path)
            else:
                raise RuntimeError(f"Environment {self} already exists.")

        print(f"Creating {self}...")
        try:
            subprocess.run(
                None,  # Creating the cross venv isn't logged.
                [
                    sys.executable,
                    "-m",
                    "crossenv",
                    "--sysconfigdata-file",
                    str(host_sysconfig),
                    str(host_python),
                    self.venv_path,
                ],
                **self.cross_kwargs({}),
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Unable to create cross platform environment {self}.")

        print("Verifying cross-platform environment...")
        self.verify()
        print("done.")
        print()
        print(f"Cross platform environment {self} created.")

        print()
        print("Updating cross-pip...")
        self.run(
            None,
            [
                "cross-python",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                "pip",
            ],
        )

        print()
        print("Updating build-pip...")
        self.run(
            None,
            [
                "build-python",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                "pip",
            ],
        )

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

        # Ensure the path is clean, and doesn't include any non-iOS paths.
        env["PATH"] = os.pathsep.join(
            [
                str(self.host_python_home / "bin"),
                str(self.venv_path / "bin"),
                str(self.venv_path / "cross" / "bin"),
                str(Path.home() / ".cargo/bin"),
                "/usr/bin",
                "/bin",
                "/usr/sbin",
                "/sbin",
                "/Library/Apple/usr/bin",
            ]
        )

        # Set VIRTUALENV to the active venv
        env["VIRTUAL_ENV"] = str(self.venv_path / "cross")

        # Remove PYTHONHOME if it's set
        try:
            del env["PYTHONHOME"]
        except KeyError:
            pass

        venv_kwargs["env"] = env
        return venv_kwargs

    def check_output(self, args, **kwargs):
        return subprocess.check_output(args, **self.cross_kwargs(kwargs))

    def run(self, logfile, *args, **kwargs):
        """Run a command in the cross environment.

        This passes the provided arguments directly to invocation of ``subprocess.run``;
        however, the ``kwargs`` will be modified to make the process appear to be in an
        activated virtual environment. This will:

        * Modify the ``PATH`` to remove the build virtualenv's bin folder, and add the
          cross-env's ``bin`` folder, and remove any other path that could be a source
          of stray libraries (e.g, Homebrew) and remove the current virtualenv path.
        * Set the ``VIRTUAL_ENV`` environment variable
        * Remove the ``PYTHONHOME`` environment variable, if it exists.

        If ``env`` is passed in as a keyword argument, the values in that environment
        will be augmented by the virtualenv changes.

        For auditing purposes, the final kwargs used at runtime will be output to the
        console.

        :param logfile: An open file handle to which all output will be logged.
        :param args: The list of command line arguments
        :param kwargs: Any extra arguments to pass to the ``subprocess.run`` invocation.
        """
        return subprocess.run(logfile, *args, **self.cross_kwargs(kwargs))

    def pip_install(
        self,
        logfile,
        packages,
        update=False,
        build=False,
        paths=None,
    ):
        """Install packages into the cross environment.

        :param packages: The list of package names/specifiers to install.
        :param update: Should the package be updated ("-U")
        :param build: Should the package be installed in the build environment? Defaults
            to installing in the host environment.
        :param paths: The paths to search for additional wheels ("--find-links").
        """
        # build-pip is a script; pip is a shim with a hashbang that points
        # at a python interpreter, which we can't invoke with subprocess.
        self.run(
            logfile,
            (["build-pip"] if build else ["python", "-m", "pip"])
            + [
                "install",
                "--disable-pip-version-check",
            ]
            # If we're doing a host build, require binary packages.
            # build environment can use non-binary packages.
            + (
                []
                if build
                else [
                    "--only-binary",
                    ":all:",
                ]
            )
            # Update packages if requested
            + (["-U"] if update else [])
            # Include the local wheels paths if provided.
            + (
                list(itertools.chain(*(["--find-links", str(path)] for path in paths)))
                if paths
                else []
            )
            # Finally, the list of packages to install.
            + packages,
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
        "--sdk",
        choices=sorted(
            {sdk[0] for sdks in CrossVEnv.HOST_SDKS.values() for sdk in sdks}
        ),
        required=True,
        help="The host SDK to target.",
    )
    parser.add_argument(
        "--sdk-version",
        default=None,
        help="The compatibility version for the host SDK.",
    )
    parser.add_argument(
        "--arch", required=True, help="The CPU architecture for the host."
    )

    args = parser.parse_args()

    try:
        cross_venv = CrossVEnv(
            sdk=args.sdk,
            sdk_version=args.sdk_version,
            arch=args.arch,
        )
        cross_venv.create(clean=args.clean)
    except RuntimeError as e:
        print()
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
