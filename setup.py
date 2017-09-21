from setuptools import setup

__version__ = '0.7.1-alpha'

__name__ = 'airtable-python-wrapper'
__description__ = 'Python API Wrapper for the Airtable API'
__url__ = 'https://github.com/gtalarico/airtable-python-wrapper'
__author__ = 'Gui Talarico'
__license__ = 'The MIT License (MIT)'
__copyright__ = 'Copyright 2017 Gui Talarico'

setup(
    name=__name__,
    description=__description__,
    author=__author__,
    url=__url__,
    version=__version__,
    packages=['airtable'],
    install_requires=['requests>=2.18.3', 'six>=1.10.0'],
    keywords=['airtable', 'api'],
    license=__license__,
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
