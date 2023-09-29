Mobile Forge
============

This is a forge-like environment that can be used to build wheels for mobile platforms.
It is currently only tested for iOS, but in theory, it should also be usable for
Android. Contributions to verify Android support, and to add more package recipes, are
definitely encouraged.

Usage
-----

Before using Mobile Forge, you'll need to compile Python for your build platform (e.g.,
your laptop), and for host platform (e.g., for iOS). It may be helpful to use a project
like `Python-Apple-support <https://github.com/beeware/Python-Apple-support>`__ to
manage this compilation process.

Using Python-Apple-support
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you *do* use Python-Apple-support, this repo contains an activation script that will
configure your environment so it's ready to use.

1. Set an environment variable declaring the location of your Python-Apple-support
   checkout::

    $ export PYTHON_APPLE_SUPPORT=/path/to/Python-Apple-support

2. Clone this repository, and run the activate script for the Python version you want to
   use::

    $ git clone https://github.com/beeware/mobile-forge.git
    $ cd mobile-forge
    $ source ./setup-iOS.sh 3.11

This will create a Python virtual environment, install mobile forge, and provide
some hints at forge commands you can run.

If a virtual environment already exists, it will be activated, and the same hints
displayed.

The hard way
~~~~~~~~~~~~

If you're *not* using Python-Apple-support, the setup process requires more manual steps::

1. Create and activate a virtual environment using the Python build platform, using the
   build platform Python compiled in step 1.

2. Clone this repository, and install it into your freshly created virtual environment::

    (venv3.11) $ git clone https://github.com/beeware/mobile-forge.git
    (venv3.11) $ cd mobile-forge
    (venv3.11) $ pip install -e .

3. Ensure your ``PATH`` contains any tools that were necessary to compile the host CPython,
   and does *not* contain any macOS development libraries. Mobile-forge will clean the ``PATH``
   to remove known problematic paths (e.g., paths added by Homebrew, rbenv, npm, etc).

4. Set environment variables that define the location of the Python executable for each
   of the **host** platforms you intend to target. For iOS, this means defining
   3 environment variables::

    (venv3.11) $ export MOBILE_FORGE_IPHONEOS_ARM64=...
    (venv3.11) $ export MOBILE_FORGE_IPHONESIMULATOR_ARM64=...
    (venv3.11) $ export MOBILE_FORGE_IPHONESIMULATOR_X86_64=...

5. Build a package. The ``packages`` folder contains recipes for packages. ``lru-dict``
   is a good first package to try::

    (venv3.11) $ forge iOS lru-dict

   Or, to build a wheel for a single architecture::

    (venv3.11) $ forge iphonesimulator:12.0:arm64 lru-dict

Once this command completes, there should be a wheel for each platform in the ``dist``
folder.

The special snowflakes
~~~~~~~~~~~~~~~~~~~~~~

Mobile Forge is trying to support multiple packages, building on multiple Python
versions, for multiple architectures; and some of those Python versions were released
before the release of ARM64 macOS hardware. As a result, some versions of some packages
have some quirks that must be taken into account.

Pandas
^^^^^^

Pandas uses a meta-package named ``oldest-supported-numpy`` to ensure ABI compatibility
during compilation. However, this can install a different version of numpy, depending on
the platform. This is especially problematic for Python 3.9, because the minimum
supported version for Python 3.9 on ARM64 is different to the version that is installed
for x86_64. Mobile-forge produces a replacement ``oldest-supported-numpy`` package, tagged
as version 2999.1.1, which ensures that consistent versions are available for build
purposes; however, this wheel *should not* be published.

Cryptography
^^^^^^^^^^^^

Cryptography currently builds a *very* old version (3.4.8). This is the last version
that could be built without a Rust compiler. The recipe works as is on all Python
versions *except* Python 3.8 on ARM64, because there was no ARM64-compatible wheel
published for cffi 1.15.1. However, if you run::

    $ pip wheel -w dist --no-deps cffi==1.15.1

you can build a universal Python3.8 CFFI wheel for CFFI 1.15.1, which can be used to
satisfy this build-time requirement.

What now?
---------

To include these wheels in a test project, you can add the ``dist`` folder as a links
source in your ``requires`` definition in your Briefcase ``pyproject.toml``. For
example, the following will install the ``lru-dict`` wheels you've just compiled::

    requires = [
        "--find-links", "/path/to/mobile-forge/dist",
        "lru-dict",
    ]

Adding your own packages
------------------------

If there's a package that you want that doesn't have an existing recipe, you can add a
recipe for that package.

Create a directory in ``recipes``. The name of the directory must be in PyPI normalized
form (PEP 503). Alternatively, you can create this directory somewhere else, and pass
its path when calling ``forge``.

Inside the recipe directory, add the following files.

* A `meta.yaml` file. This supports a subset of Conda syntax, defined in `meta-schema.yaml`.
* A `test.py` file (or `test` package), to run on a target installation. This should contain a
  pytest suite which imports the package and does some basic checks.
* Optionally, one or more patch files in a folder named ``patches``. These patches will be
  applied when the source code is unpacked for a given platform.
* For non-Python packages, a ``build.sh`` script. This is the script that will be executed
  in the build environment build the package. This script should invoke any ``configure``,
  ``make``, or any other compilation steps needed to build the package. This script will be
  executed in an environment that defines the following environment variables:

    - ``AR`` - the ``AR`` value used to compile the host Python, as determined from
      ``sysconfig``
    - ``CC`` - the ``CC`` value used to compile the host Python, as determined from
      ``sysconfig``.
    - ``CFLAGS`` - the ``CFLAGS`` value used to compile the host Python, as determined
      from ``sysconfig``, augmented with the include paths for the SDK, and
      ``opt/include`` in the host environment's site-packages.
    - ``LDFLAGS`` - the ``CFLAGS`` value used to compile the host Python, as determined
      from ``sysconfig``, augmented with the library paths for the SDK, and
      ``opt/lib`` in the host environment's site-packages.
    - ``CPU_COUNT`` - The number of CPUs that are available, as determined by
      ``multiprocessing.cpu_count()``
    - ``HOST_TRIPLET`` - the GCC compiler triplet for the host platform (e.g.,
      ``aarch64-apple-ios12.0-simulator``)
    - ``BUILD_TRIPLET`` - the GCC compiler triplet for the build platform (e.g.,
      ``aarch64-apple-darwin``)
    - ``CARGO_BUILD_TARGET`` - the Rust cargo build target for the platform
    - ``PREFIX`` - a location where the compiled package can be installed in preparation
      for packaging.

  This script should install the package into ``$PREFIX``. Mobile Forge will package any
  content installed into ``$PREFIX`` into a "wheel" that can be installed as a host
  requirement.

Python-based projects
~~~~~~~~~~~~~~~~~~~~~

All Python projects are compiled using ``python -m build``, using a clean `crossenv
<https://github.com/benfogle/crossenv>`__ virtual environment for each platform of a
package. Any PEP518 build requirements will be included in both the host and build
environments.

If you're lucky, all you'll need to do is define a ``meta.yaml`` that describes the
package name and version: e.g.,::

    package:
      name: blis
      version: 0.4.1

If this doesn't result in a successful build, it will likely be for one of 3 reasons:

1. **The build process has a dependency on a system library**. For example, Pillow has a
   dependency on ``libjpeg``. ``libjpeg`` isn't available on PyPI; but it *is* possible
   to build a "wheel" for ``libjpeg``, so it can be specified as a requirement.

   A non-python "wheel" is constructed by compiling the package for your target platform,
   then installing it into a folder named ``opt``. As a result of this "install", you'll
   usually end up with an ``opt/include`` and ``opt/lib`` folder; Mobile Forge will then
   wrap up this ``opt`` folder in a wheel, along with Python wheel metadata.

   When this "wheel" is specified as a host requirement, the "wheel" will be unpacked
   into the site packages folder of your cross-compilation host environment. This path
   the ``include`` and ``lib`` paths will be automatically included in the
   ``CFLAGS``/``LDFLAGS`` environment variables when the Python build is executed.

2. **The build process has a dependency on external tooling**. Mobile Forge will
   configure a C and C++ compiler using the same configuration that was used to compile
   the support libraries; however a package may require addition build tooling (e.g., a
   Fortran compiler) to complete the build. If this is the case, you'll need to find a
   version of the tool that can target mobile platforms, and work out how to modify the
   build process to apply any necessary compiler flags.

3. **The build script has platform-specific logic**. For example,
   if the ``setup.py`` file contain an ``if sys.platform == ...`` clauses, it is unlikely
   that a mobile platform will trigger the right logic.

If you need to make any alterations to a project's source code for a build to succeed,
you can provide those patches by putting them in one or more files in a folder named
``patches`` in the recipe folder. These patches will be applied once the source code
has been unpacked.

Configure-based projects
~~~~~~~~~~~~~~~~~~~~~~~~

If the project includes a `configure` script, you will likely need to provide a patch
for `config.sub`. `config.sub` is the tools used by `configure` to identify the
architecture and machine type; however, it doesn't currently recognize the host triples
used by Apple. If you get the error::

    checking host system type... Invalid configuration `arm64-apple-ios': machine `arm64-apple' not recognized
    configure: error: /bin/sh config/config.sub arm64-apple-ios failed

you will need to patch `config.sub`. There are several examples of patched `config.sub`
scripts in the packages contained in this repository, and in the Python-Apple-support
project; it is quite possible one of those patches can be used for the library you are
trying to compile. The `config.sub` script has a datestamp at the top of the file; that
can be used to identify which patch you will need.

Community
---------

Mobile Forge is part of the `BeeWare suite`_. You can talk to the community through:

* `@beeware@fosstodon.org on Mastodon <https://fosstodon.org/@beeware>`__

* `Discord <https://beeware.org/bee/chat/>`__

* The Mobile Forge `Github Discussions forum <https://github.com/beeware/mobile-forge/discussions>`__

We foster a welcoming and respectful community as described in our
`BeeWare Community Code of Conduct`_.

Contributing
------------

If you experience problems with Mobile Forge, `log them on GitHub`_. If you
want to contribute code, please `fork the code`_ and `submit a pull request`_.

.. _BeeWare suite: http://beeware.org
.. _Read The Docs: https://briefcase.readthedocs.io
.. _BeeWare Community Code of Conduct: http://beeware.org/community/behavior/
.. _log them on Github: https://github.com/beeware/mobile-forge/issues
.. _fork the code: https://github.com/beeware/mobile-forge
.. _submit a pull request: https://github.com/beeware/mobile-forge/pulls

Acknowledgements
----------------

This project draws significantly on the implementation and knowledge developed in the
`Chaquopy package builder
<https://github.com/chaquo/chaquopy/tree/master/server/pypi>`__. Although this is
largely a "clean room" reimplementation of that project, many details from that project
have been used in the development of this one.
