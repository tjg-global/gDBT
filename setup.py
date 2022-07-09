import os, sys
import glob
import setuptools

setuptools.setup(
    name='gdbt',
    version='1.3.1',
    description='Global DBT packages',
    author='Tim Golden',
    author_email='tim.golden@global.com',
    packages = ["gdbt"],
    entry_points = {
        "console_scripts" : ["gdbt=gdbt.gdbt:command_line"]
    }
)
