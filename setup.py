from setuptools import setup
from airtable.airtable import __version__
setup(
    name='airtable-python-wrapper',
    description='Python API Wrapper for the Airtable API',
    author='Gui Talarico',
    url='https://github.com/gtalarico/airtable-python-wrapper',
    version=__version__,
    packages=['airtable'],
    install_requires=['requests>=2.18.3'],
    keywords=['airtable', 'api'],
    license='The MIT License (MIT)',
)
