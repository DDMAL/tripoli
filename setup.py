from setuptools import setup
from tripoli.tripoli import __version__

setup(
    name='tripoli',
    packages=['tripoli'],
    version=__version__,
    license='https://opensource.org/licenses/MIT',
    description='IIIF document validation.',
    author='Alex Parmentier',
    author_email='a.g.parmentier@gmail.com',
    url='https://github.com/DDMAL/tripoli',
    download_url='https://github.com/DDMAL/tripoli/tarball/master',
    keywords=['validator', 'IIIF'],
    classifiers=[],
)