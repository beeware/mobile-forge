from __future__ import annotations

import shutil
import tarfile
from abc import ABC, abstractmethod, abstractproperty
from pathlib import Path
from typing import TYPE_CHECKING

from pypi_simple import PyPISimple, tqdm_progress_factory

if TYPE_CHECKING:
    from forge.cross import CrossVEnv
    from forge.package import Package


class Builder(ABC):
    def __init__(self, cross_venv: CrossVEnv, package: Package):
        self.cross_venv = cross_venv
        self.package = package

    @abstractproperty
    def build_path(self) -> Path:
        ...

    @abstractproperty
    def source_file_path(self) -> Path:
        ...

    def install_host_requirements(self):
        pass

    def install_build_requirements(self):
        pass

    @abstractmethod
    def download_source(self):
        """Download the source tarball."""
        ...

    def unpack_source(self):
        if self.build_path.is_dir():
            print(f"Removing {self.build_path.relative_to(Path.cwd())}...")
            shutil.rmtree(self.build_path)

        print(f"Unpacking {self.source_file_path.relative_to(Path.cwd())}...")

        # This is the equivalent of --strip-components=<strip>
        def members(tf: tarfile.TarFile, strip=1):
            for member in tf.getmembers():
                parts = member.path.split("/", strip)
                try:
                    member.path = parts[strip]
                    yield member
                except IndexError:
                    pass

        with tarfile.open(self.source_file_path) as tar:
            tar.extractall(
                path=self.build_path,
                members=members(tar, strip=1),
            )

    def apply_patches(self):
        pass

    def prepare(self):
        self.install_host_requirements()
        self.install_build_requirements()

        if not self.source_file_path.is_file():
            print(f"\n[{self.cross_venv}] Download package sources")
            self.download_source()

        print(f"\n[{self.cross_venv}] Unpack sources")
        self.unpack_source()
        self.apply_patches()

    @abstractmethod
    def build(self):
        """Build the package."""
        ...


class SimplePackageBuilder(Builder):
    """A builder for projects that have a build.sh entry point."""

    @abstractproperty
    def build_path(self) -> Path:
        return (
            self.package.recipe_path
            / "src"
            / self.package.version
            / self.cross_venv.tag
        )

    @property
    def source_file_path(self) -> Path:
        filename = self.package.meta["sources"]
        return Path.cwd() / "downloads" / filename

    def build(self):
        pass


class CMakePackageBuilder(Builder):
    """A builder for cmake-based projects."""

    def build(self):
        pass


class PythonPackageBuilder(Builder):
    """A builder for projects available on PyPI."""

    @property
    def source_file_path(self) -> Path:
        return (
            Path.cwd()
            / "downloads"
            / f"{self.package.name}-{self.package.version}.tar.gz"
        )

    @property
    def build_path(self) -> Path:
        return self.package.recipe_path / "src" / self.package.version

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
                path=self.source_file_path,
                progress=tqdm_progress_factory(),
            )

    def build(self):
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
        )
