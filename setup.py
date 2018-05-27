from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, 'airtable', '__version__.py'),
          mode='r', encoding='utf-8') as f:
    exec(f.read(), about)

with open('README.md', mode='r', encoding='utf-8') as f:
    readme = f.read()
with open('HISTORY.md', mode='r', encoding='utf-8') as f:
    history = f.read()

setup(
    name=about['__name__'],
    description=about['__description__'],
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    author=about['__author__'],
    author_email=about['__authoremail__'],
    url=about['__url__'],
    version=about['__version__'],
    packages=['airtable'],
    install_requires=['requests>=2.18.3', 'six>=1.10.0'],
    keywords=['airtable', 'api'],
    license=about['__license__'],
    classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Programming Language :: Python',
            'Topic :: Software Development',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: Implementation :: CPython',
    ],
)
