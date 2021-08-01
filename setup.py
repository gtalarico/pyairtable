from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))


about = {}
init_path = os.path.join(here, "airtable", "__init__.py")
with open(init_path, mode="r") as f:
    for line in f.readlines():
        if line.startswith("__"):
            exec(line, about)

setup_requires = ["pytest-runner"]
install_requires = ["requests>=2"]
tests_require = ["requests-mock", "requests", "mock", "pytest", "pytest-cov"]

setup(
    name=about["__name__"],
    description=about["__description__"],
    author=about["__author__"],
    author_email=about["__authoremail__"],
    url=about["__url__"],
    version=about["__version__"],
    packages=["airtable", "airtable.api", "airtable.orm"],
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    python_requires="!=2.7.*, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
    keywords=["airtable", "api", "client"],
    license=about["__license__"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
