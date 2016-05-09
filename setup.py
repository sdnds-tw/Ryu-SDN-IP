try:
    import multiprocessing
except ImportError:
    pass

import setuptools
import re

# read VERSION file
version = None

with open('VERSION', 'r') as version_file:

    if version_file:
        version = version_file.readline().strip()

    if version and not re.match("[0-9]+\\.[0-9]+\\.[0-9]+", version):
        version = None

if version:
    print("Can't read version")

else:
    setuptools.setup(name='Ryu SDN-IP', version=version)
