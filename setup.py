from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, "airtable", "__version__.py"), mode="r") as f:
    exec(f.read(), about)

setup_requires = ["pytest-runner"]
install_requires = ["requests>=2", "six>=1.10"]
tests_require = ["requests-mock", "requests", "mock"]

setup(
    name=about["__name__"],
    description=about["__description__"],
    author=about["__author__"],
    author_email=about["__authoremail__"],
    url=about["__url__"],
    version=about["__version__"],
    packages=["airtable"],
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    keywords=["airtable", "api"],
    license=about["__license__"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
