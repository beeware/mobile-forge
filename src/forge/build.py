from __future__ import annotations

import email
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from abc import ABC, abstractmethod, abstractproperty
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from packaging.utils import canonicalize_name, canonicalize_version
from pypi_simple import PyPISimple, tqdm_progress_factory

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no-cover-if-gte-py310
    import tomli as tomllib


if TYPE_CHECKING:
    from forge.cross import CrossVEnv
    from forge.package import Package


class Builder(ABC):
    def __init__(self, cross_venv: CrossVEnv, package: Package):
        self.cross_venv = cross_venv
        self.package = package

    @abstractproperty
    def build_path(self) -> Path:
        """The path in which all environment and sources for the build will be
        created."""
        ...

    @abstractproperty
    def source_archive_path(self) -> Path:
        """The source archive file for the package."""
        ...

    def install_requirements(self, target):
        requirements = []
        for requirement in self.package.meta["requirements"][target]:
            try:
                package, version = requirement.split()
                specifier = f"{package}=={version}"
            except ValueError:
                specifier = requirement
            requirements.append(specifier)

        if requirements:
            self.cross_venv.pip_install(
                requirements,
                wheels_path=Path.cwd() / "dist",
                build=target == "build",
            )
        else:
            print(f"No {target} requirements.")

    @abstractmethod
    def download_source(self):
        """Download the source tarball."""
        ...

    def unpack_source(self):
        print(f"Unpacking {self.source_archive_path.relative_to(Path.cwd())}...")
        # Some packages (e.g., brotli) have uploaded a .tar.gz file... that is
        # actually a zipfile (!).
        if tarfile.is_tarfile(self.source_archive_path):
            # This is the equivalent of --strip-components=<strip>
            def members(tf: tarfile.TarFile, strip=1):
                for member in tf.getmembers():
                    parts = member.path.split("/", strip)
                    try:
                        if parts[strip]:
                            member.path = parts[strip]
                            yield member
                    except IndexError:
                        pass

            with tarfile.open(self.source_archive_path) as tf:
                tf.extractall(
                    path=self.build_path,
                    members=members(tf, strip=1),
                )
        elif zipfile.is_zipfile(self.source_archive_path):
            # Strip the top level folder.
            zf = zipfile.ZipFile(self.source_archive_path)

            def members(zf, strip=1):
                for member in zf.infolist():
                    parts = member.filename.split("/", strip)
                    try:
                        if parts[strip]:
                            member.filename = parts[strip]
                            yield member
                    except IndexError:
                        pass

            zf.extractall(
                path=self.build_path,
                members=members(zf, strip=1),
            )
        else:
            raise RuntimeError(
                f"Can't identify archive type of {self.source_archive_path}"
            )

    def patch_source(self):
        patched = False
        for patch in self.package.meta["patches"]:
            patchfile = self.package.recipe_path / "patches" / patch
            print(f"Applying {patchfile.relative_to(self.package.recipe_path)}...")
            # This can use a raw subprocess.run because it's a system command,
            # not anything dependent on the Python environment.
            subprocess.run(
                ["patch", "-p1", "--ignore-whitespace", "--input", str(patchfile)],
                cwd=self.build_path,
                check=True,
            )
            patched = True

        if not patched:
            print("No patches to apply.")

    def prepare(self, clean=True):
        if clean and self.build_path.is_dir():
            if clean:
                print(f"\n[{self.cross_venv}] Clean up old builds")
                print(f"Removing {self.build_path.relative_to(Path.cwd())}...")
                shutil.rmtree(self.build_path)

        if not self.source_archive_path.is_file():
            print(f"\n[{self.cross_venv}] Download package sources")
            self.download_source()

        if not self.build_path.is_dir():
            print(f"\n[{self.cross_venv}] Unpack sources")
            self.unpack_source()

            print(f"\n[{self.cross_venv}] Apply patches")
            self.patch_source()

        # Create a clean cross environment.
        print(f"\n[{self.cross_venv}] Create clean build environment")
        self.cross_venv.create(location=self.build_path, clean=True)

        print(f"\n[{self.cross_venv}] Install forge host requirements")
        self.install_requirements("host")

        print(f"\n[{self.cross_venv}] Install forge build requirements")
        self.install_requirements("build")

    def compile_env(self, **kwargs) -> dict[str:str]:
        sysconfig_data = self.cross_venv.sysconfig_data
        install_root = self.cross_venv.install_root
        sdk_root = self.cross_venv.sdk_root

        ar = sysconfig_data["AR"]

        cc = sysconfig_data["CC"]

        cflags = self.cross_venv.sysconfig_data["CFLAGS"]
        # Pre Python 3.11 versions included BZip2 and XZ includes in CFLAGS. Remove them.
        cflags = re.sub(r"-I.*/merge/iOS/.*/bzip2-.*/include", "", cflags)
        cflags = re.sub(r"-I.*/merge/iOS/.*/xs-.*/include", "", cflags)

        # Replace any hard-coded reference to --sysroot=<sysroot> with the actual reference
        cflags = re.sub(r"--sysroot=\w+", f"--sysroot={sdk_root}", cflags)

        # Add the install root and SDK root includes
        if (install_root / "include").is_dir():
            cflags += f" -I{install_root}/include"
        if (sdk_root / "usr" / "include").is_dir():
            cflags += f" -I{sdk_root}/usr/include"

        ldflags = self.cross_venv.sysconfig_data["LDFLAGS"]
        # Pre Python 3.11 versions included BZip2 and XZ includes in CFLAGS. Remove them.
        cflags = re.sub(r"-I.*/merge/iOS/.*/bzip2-.*/include", "", cflags)
        cflags = re.sub(r"-I.*/merge/iOS/.*/xs-.*/include", "", cflags)

        # Replace any hard-coded reference to -isysroot <sysroot> with the actual reference
        cflags = re.sub(r"-isysroot \w+", f"-isysroot={sdk_root}", cflags)

        # Add the install root and SDK root includes
        if (install_root / "lib").is_dir():
            ldflags += f" -L{install_root}/lib"
        if (sdk_root / "usr" / "lib").is_dir():
            ldflags += f" -L{sdk_root}/usr/lib"

        cargo_build_target = {
            "arm64-apple-ios": "aarch64-apple-ios",
            "arm64-apple-ios-simulator": "aarch64-apple-ios-simulator",
            # This one is odd; Rust doesn't provide an `x86_64-apple-ios-simulator`,
            # but there's no such thing as an x86_64 ios *device*.
            "x86_64-apple-ios-simulator": "x86_64-apple-ios",
        }[self.cross_venv.platform_triplet]

        env = {
            "AR": ar,
            "CC": cc,
            "CFLAGS": cflags,
            "LDFLAGS": ldflags,
            "CARGO_BUILD_TARGET": cargo_build_target,
        }
        env.update(kwargs)

        # Add in some user environment keys that are useful
        env.update(
            {
                key: os.environ.get(key)
                for key in [
                    "TMPDIR",
                    "USER",
                    "HOME",
                    "LANG",
                    "TERM",
                ]
            }
        )
        return env

    @abstractmethod
    def build(self):
        """Build the package."""
        ...


class SimplePackageBuilder(Builder):
    """A builder for projects that have a build.sh entry point."""

    @property
    def source_archive_path(self) -> Path:
        url = self.package.meta["source"]["url"]
        filename = url.split("/")[-1]
        return Path.cwd() / "downloads" / filename

    @property
    def build_path(self) -> Path:
        # Generate a separate build path for each platform, since we can't guarantee
        # that the Makefile will do a truly clean build for each platform.
        # The path can be independent of the Python version, because it's not built
        # against the Python ABI.
        return (
            Path.cwd()
            / "build"
            / "any"
            / self.package.name
            / self.package.version
            / self.cross_venv.tag
        )

    def download_source(self):
        url = self.package.meta["source"]["url"]

        print(f"Downloading {url}...", end="", flush=True)
        self.source_archive_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, follow_redirects=True) as response:
            with self.source_archive_path.open("wb") as f:
                for chunk in response.iter_bytes():
                    print(".", end="", flush=True)
                    f.write(chunk)
        print(" done.")

    def prepare(self, clean=True):
        # Always clean a non-Python build.
        super().prepare(clean=True)

        print(f"\n[{self.cross_venv}] Installing wheel-building tools")
        self.cross_venv.pip_install(["wheel"], build=True)

    def write_message_file(self, filename, data):
        msg = email.message.Message()
        for key, value in data.items():
            msg[key] = value

        # I don't know whether maxheaderlen is required, but it's used by bdist_wheel.
        with filename.open("w", encoding="utf-8") as f:
            email.generator.Generator(f, maxheaderlen=0).flatten(msg)

    def make_wheel(self):
        build_num = str(self.package.meta["build"]["number"])
        name = canonicalize_name(self.package.name)
        version = canonicalize_version(self.package.version)
        info_path = self.build_path / "wheel" / f"{name}-{version}.dist-info"

        print(f"\n[{self.cross_venv}] Writing wheel metadata")
        info_path.mkdir()

        # Write the packaging metadata
        self.write_message_file(
            info_path / "WHEEL",
            {
                "Wheel-Version": "1.0",
                "Root-Is-Purelib": "false",
                "Generator": "mobile-forge",
                "Build": build_num,
                "Tag": f"py3-none-{self.cross_venv.tag}",
            },
        )
        self.write_message_file(
            info_path / "METADATA",
            {
                "Metadata-Version": "1.2",
                "Name": self.package.name,
                "Version": self.package.version,
                "Summary": "",  # Compulsory according to PEP 345,
                "Download-URL": "",
            },
        )

        # Re-pack the wheel file
        print(f"\n[{self.cross_venv}] Packing wheel")
        self.cross_venv.run(
            [
                "build-python",
                "-m",
                "wheel",
                "pack",
                str(self.build_path / "wheel"),
                "--dest-dir",
                str(Path.cwd() / "dist"),
                "--build-number",
                str(build_num),
            ],
            check=True,
        )

    def compile(self):
        self.cross_venv.run(
            [
                str(self.package.recipe_path / "build.sh"),
            ],
            cwd=self.build_path,
            env=self.compile_env(
                **{
                    "HOST_TRIPLET": self.cross_venv.platform_triplet,
                    "BUILD_TRIPLET": f"{os.uname().machine}-apple-darwin",
                    "CPU_COUNT": str(multiprocessing.cpu_count()),
                    "PREFIX": str(self.build_path / "wheel" / "opt"),
                }
            ),
            check=True,
        )

    def build(self):
        self.compile()
        self.make_wheel()


class CMakePackageBuilder(SimplePackageBuilder):
    """A builder for cmake-based projects."""

    def build(self):
        pass


class PythonPackageBuilder(Builder):
    """A builder for projects available on PyPI."""

    @property
    def source_archive_path(self) -> Path:
        return (
            Path.cwd()
            / "downloads"
            / f"{self.package.name}-{self.package.version}.tar.gz"
        )

    @property
    def build_path(self) -> Path:
        # Generate a separate build path for each Python version to ensure we have a
        # clean build. SDK versions can co-exist because wheel builds are cleanly
        # separated.
        return (
            Path.cwd()
            / "build"
            / f"cp3{sys.version_info.minor}"
            / self.package.name
            / self.package.version
        )

    def download_source(self):
        with PyPISimple() as client:
            page = client.get_project_page(self.package.name)
            sdists = [
                package
                for package in page.packages
                if package.package_type == "sdist"
                and package.version == self.package.version
            ]

            client.download_package(
                sdists[0],
                path=self.source_archive_path,
                progress=tqdm_progress_factory(),
            )

    def prepare(self, clean=True):
        super().prepare(clean=clean)

        # Install any build requirements (PEP517 or otherwise)
        if (self.build_path / "pyproject.toml").is_file():
            print(f"\n[{self.cross_venv}] Install pyproject.toml build requirements")

            # Install the requirements from pyproject.toml
            with (self.build_path / "pyproject.toml").open("rb") as f:
                pyproject = tomllib.load(f)

                # Install the build requirements in the cross environment
                self.cross_venv.pip_install(
                    ["build"] + pyproject["build-system"]["requires"],
                    wheels_path=Path.cwd() / "dist",
                )

                # Install the build requirements in the build environment
                self.cross_venv.pip_install(
                    ["build"] + pyproject["build-system"]["requires"],
                    wheels_path=Path.cwd() / "dist",
                    build=True,
                )
        else:
            print(f"\n[{self.cross_venv}] Installing non-PEP517 build requirements")
            # Ensure the cross environment has the most recent tools
            self.cross_venv.pip_install(["setuptools"], update=True)
            self.cross_venv.pip_install(["build", "wheel"])

            # Ensure the build environment has the most recent tools
            self.cross_venv.pip_install(["setuptools"], update=True, build=True)
            self.cross_venv.pip_install(["build", "wheel"], build=True)

    def build(self):
        # Set up any additional environment variables needed in the script environment.
        script_env = {}
        for line in self.package.meta["build"]["script_env"]:
            key, value = line.split("=", 1)
            script_env[key] = value.format(**self.cross_venv.scheme_paths)

        # Set the cross host platform in the environment
        script_env["_PYTHON_HOST_PLATFORM"] = self.cross_venv.platform_identifier

        self.cross_venv.run(
            [
                "python",
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                str(Path.cwd() / "dist"),
            ],
            cwd=self.build_path,
            env=self.compile_env(**script_env),
            check=True,
        )
