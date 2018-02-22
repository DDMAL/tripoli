# Copyright (c) 2016–2018 Alex Parmentier, Andrew Hankinson

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import sys
from setuptools import setup, find_packages
from codecs import open

from tripoli.tripoli import __version__

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist bdist_wheel upload')
    sys.exit()

with open('README.rst', 'r', 'utf-8') as f:
    read_me = f.read()

with open('HISTORY.rst', 'r', 'utf-8') as f:
    history = f.read()

setup(
    name='tripoli',
    packages=find_packages(),
    version=__version__,
    license='https://opensource.org/licenses/MIT',
    description='IIIF document validation.',
    long_description=read_me + "\n\n" + history,
    author='Alex Parmentier, Andrew Hankinson',
    author_email='andrew.hankinson@bodleian.ox.ac.uk',
    url='https://github.com/DDMAL/tripoli',
    download_url='https://github.com/DDMAL/tripoli/tarball/master',
    keywords=['validator', 'IIIF'],
    python_requires='>=3.5',
    install_requires=['defusedxml'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Multimedia :: Graphics :: Presentation",
        "Intended Audience :: Developers",
        "Environment :: Web Environment",
        "Programming Language :: Python"],
    test_suite='tests'
)
