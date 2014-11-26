"""Setup for xb_scorm XBlock."""

import os
from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='xb_scorm-xblock',
    version='0.1',
    description='xb_scorm XBlock',   # TODO: write a better description.
    packages=[
        'xb_scorm',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'xb_scorm = xb_scorm:SCORMXBlock',
            'xb_scorm_studiohack = xb_scorm:SCORMXBlockStudioHack',  # don't use this unless you're debugging in the Workbench
        ]
    },
    package_data=package_data("xb_scorm", ["static", "public"]),
)
