import re
from pathlib import Path

from setuptools import setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    version = Path(package, "__version__.py").read_text()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", version).group(1)


def get_long_description():
    """
    Return the README.
    """
    long_description = ""
    with open("README.md", encoding="utf8") as f:
        long_description += f.read()
    long_description += "\n\n"
    with open("CHANGELOG.md", encoding="utf8") as f:
        long_description += f.read()
    return long_description


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [str(path.parent) for path in Path(package).glob("**/__init__.py")]

def get_requirements():
    """
    Return list of requirements
    """
    with open("requirements.txt", encoding="utf-8") as f:
        requirements = f.read()
    return requirements.splitlines()


setup(
    name="ws_auth",
    python_requires=">=3.7",
    version=get_version("ws_auth"),
    url="https://github.com/newvicx/ws_auth",
    project_urls={
        "Changelog": "https://github.com/newvicx/ws_auth/blob/master/CHANGELOG.md",
        "Source": "https://github.com/newvicx/ws_auth",
    },
    license="MIT",
    description="Custom protocol for python websockets client that supports HTTPX style auth flows",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Chris Newville",
    author_email="chrisnewville1396@gmail.com",
    package_data={"ws_auth": ["py.typed"]},
    packages=get_packages("ws_auth"),
    include_package_data=True,
    zip_safe=False,
    install_requires=get_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
)