"""zc.buildout language server"""

from os import path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
  long_description = f.read()

with open(path.join(here, "CHANGELOG.md"), encoding="utf-8") as f:
  long_description += f.read()

setup(
  name="zc.buildout.languageserver",
  version="0.13.0",
  description="A language server for zc.buildout",
  long_description=long_description,
  long_description_content_type="text/markdown",
  classifiers=[
    "Intended Audience :: Developers",
    "Topic :: Software Development",
    "Framework :: Buildout",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
  ],
  keywords="zc.buildout languageserver",
  packages=find_packages(),
  python_requires=">=3.8",
  install_requires=[
    "aiohttp",
    "cachetools",
    "packaging",
    "pygls >= 1.1.1",
    "pygments",
    "typing-extensions",
    "zc.buildout",
  ],
  extras_require={
    "test": [
      "aioresponses",
      "coverage",
      "mypy",
      "pylint",
      "pytest-asyncio",
      "pytest-benchmark",
      "pytest-cov",
      "pytest",
      "types-cachetools",
      "types-pygments",
      "types-setuptools",
      "types-toml",
      "ruff",
    ],
  },
  entry_points={
    "console_scripts": [
      "buildoutls=buildoutls.cli:main",
    ],
  },
)
