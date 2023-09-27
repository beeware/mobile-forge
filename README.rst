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

What now?
---------

To include these wheels in a test project, you can add the ``dist`` folder as a links
source in your ``requires`` definition in your Briefcase ``pyproject.toml``. For
example, the following will install the ``lru-dict`` wheels you've just compiled::

    requires = [
        "--find-links", "/path/to/mobile-forge/dist",
        "lru-dict",
    ]

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
