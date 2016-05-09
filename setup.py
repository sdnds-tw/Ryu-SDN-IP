try:
    import multiprocessing
except ImportError:
    pass

from setuptools import setup, find_packages
import re

# read VERSION file
version = None

with open('VERSION', 'r') as version_file:

    if version_file:
        version = version_file.readline().strip()

    if version and not re.match("[0-9]+\\.[0-9]+\\.[0-9]+", version):
        version = None

if not version:
    print("Can't read version")

else:
    setup(name='Ryu SDN-IP', version=version, packages=find_packages('.'))
