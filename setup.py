import os, sys
import glob
import setuptools

setuptools.setup(
    name='gdbt',
    version='1.3.4',
    description='Global DBT packages',
    author='Tim Golden',
    author_email='tim.golden@global.com',
    packages = ["gdbt"],
    #~ install_requires = [
        #~ "git+https://github.com/tjg-global/xlsxlib"
    #~ ],
    entry_points = {
        "console_scripts" : [
            "gdbt=gdbt.gdbt:command_line",
            "gdbt-logger=gdbt.gdbt_logger:command_line"
        ]
    }
)
