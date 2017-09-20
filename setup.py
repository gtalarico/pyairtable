from setuptools import setup
from airtable.airtable import __version__
setup(
    name='airtable-python-wrapper',
    description='Python API Wrapper for the Airtable API',
    author='Gui Talarico',
    url='https://github.com/gtalarico/airtable-python-wrapper',
    version=__version__,
    packages=['airtable'],
    install_requires=['requests>=2.18.3', 'six>=1.10.0'],
    keywords=['airtable', 'api'],
    license='The MIT License (MIT)',
    classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Programming Language :: Python',
            'Topic :: Software Development',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
    ],
)
