from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

import jinja2
import jsonschema
import yaml

from forge.build import (
    Builder,
    CMakePackageBuilder,
    PythonPackageBuilder,
    SimplePackageBuilder,
)
from forge.cross import CrossVEnv


class Package:
    def __init__(
        self, package_name_or_recipe: str, version: str | None, build_number: str | None
    ):
        if "/" in package_name_or_recipe:
            self.recipe_path = Path(package_name_or_recipe)
        else:
            self.recipe_path = Path.cwd() / "packages" / package_name_or_recipe

        if not (self.recipe_path / "meta.yaml").exists():
            raise ValueError(
                f"{package_name_or_recipe} does not appear to be a valid recipe."
            )

        self.meta = self.load_meta(
            override_version=version, override_build=build_number
        )

        # Extract some useful properties from the metadata
        self.name = self.meta["package"]["name"]
        self.version = self.meta["package"]["version"]

    def __str__(self):
        return f"{self.name} {self.version}"

    def load_meta(self, override_version, override_build):
        # http://python-jsonschema.readthedocs.io/en/latest/faq/
        def with_defaults(validator_cls):
            def set_defaults(validator, properties, instance, schema):
                for name, subschema in properties.items():
                    if "default" in subschema:
                        instance.setdefault(name, deepcopy(subschema["default"]))
                yield from validator_cls.VALIDATORS["properties"](
                    validator, properties, instance, schema
                )

            return jsonschema.validators.extend(
                validator_cls, {"properties": set_defaults}
            )

        # Validate the meta-schema
        Validator = jsonschema.Draft4Validator
        with (Path(__file__).parent / "schema" / "meta-schema.yaml").open(
            encoding="utf-8"
        ) as f:
            schema = yaml.safe_load(f)
        Validator.check_schema(schema)

        with (self.recipe_path / "meta.yaml").open(encoding="utf-8") as f:
            meta_template = f.read()
            if override_version:
                # If there's an override version, look for any {% set version... %}
                # content in the template, and ensure it is replaced with the
                # override version.
                meta_template = re.sub(
                    r'{% set version = ".*?" %}',
                    f'{{% set version = "{override_version}" %}}',
                    meta_template,
                )

        # Render the meta template.
        meta_str = jinja2.Template(meta_template).render()

        # Parse the rendered meta template
        meta = yaml.safe_load(meta_str)

        # If there's a version override, set it in the package metadata.
        # If there's a build number override, set it; otherwise purge
        # the build number (since it won't match the override version)
        if override_version:
            try:
                meta["package"]["version"] = override_version
                if override_build:
                    meta.setdefault("build", {})["number"] = override_build
                else:
                    del meta["build"]["number"]
            except KeyError:
                pass

        # Validate the metadata against the schema.
        with_defaults(Validator)(schema).validate(meta)

        return meta

    def builder(self, cross_venv: CrossVEnv) -> Builder:
        """Return a builder for this package in the given cross-platform environment.

        :param cross_venv: The cross-platform environment to use for the build
        :returns: A builder for the package.
        """
        if self.meta["source"] == "pypi":
            return PythonPackageBuilder(cross_venv=cross_venv, package=self)
        else:
            if "cmake" in self.meta["requirements"]["build"]:
                self.meta["requirements"]["build"].remove("cmake")
                return CMakePackageBuilder(cross_venv=cross_venv, package=self)
            else:
                return SimplePackageBuilder(cross_venv=cross_venv, package=self)
