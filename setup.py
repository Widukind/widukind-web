# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from widukind_web.version import version_str

setup(
    name='widukind-web',
    version=version_str(),
    description='Web user interface for the `DB.nomics project',
    author='DB.nomics Team',
    url='https://git.nomics.world/dbnomics/widukind-web',
    zip_safe=False,
    license='AGPLv3',
    include_package_data=True,
    packages=find_packages(),
    test_suite='nose.collector',
    tests_require=[
        'nose',
    ],
    entry_points={
        'console_scripts': [
            'widukind-web = widukind_web.manager:main',
        ],
    },
)
