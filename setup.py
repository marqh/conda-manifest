#!/usr/bin/env python
import os
from distutils.core import setup

setup(name='conda_manifest',
      version='0.1',
      author='Phil Elson',
      author_email='pelson.pub@gmail.com',
      packages=['conda_manifest'],
#      scripts=[os.path.join('conda-build-missing')],
     )
