import datetime
import json
import ssl
import sys
from functools import lru_cache
from urllib.request import urlopen

import certifi

START_YEAR = datetime.datetime.now().year - 3


@lru_cache
def get_pypi_releases(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"

    # ensure we're using a root certificate that works with PyPI
    context = ssl.create_default_context(cafile=certifi.where())
    releases = json.load(urlopen(url, context=context))["releases"]

    return releases


def get_pypi_versions(package_name, year=START_YEAR):
    """Return 'all versions' for the package.

    This isn't really "all" versions - it's all versions:
    * Published since `year` (last 3 years by default)
    * for which there is a macOS wheel published
    * for the current version of python

    :param name: The PyPI name of the package to query.
    """
    releases = get_pypi_releases(package_name)

    versions = set()
    for version, release in releases.items():
        for package in release:
            if (
                package["packagetype"] == "bdist_wheel"
                and "-macosx_" in package["filename"]
                and int(package["upload_time"].split("-")[0]) >= year
                and not any(c.isalpha() for c in version)
                and package["python_version"] == f"cp3{sys.version_info.minor}"
            ):
                versions.add(version)

    return sorted(versions)


@lru_cache
def get_pypi_source_urls(package_name):
    """Get the download source URLs for a PyPI package.

    :param name: The PyPI name of the package to query.
    :returns: a dictionary URLs for of all non-yanked source distributions for the
        project, keyed by version number.
    """
    releases = get_pypi_releases(package_name)

    urls = {}
    for version, release in releases.items():
        for package in release:
            if package["packagetype"] == "sdist" and not package["yanked"]:
                urls[version] = package["url"]

    return urls
