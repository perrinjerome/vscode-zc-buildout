"""zc.buildout language server
"""

from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
  long_description = f.read()

with open(path.join(here, 'CHANGELOG.md'), encoding='utf-8') as f:
  long_description += f.read()

setup(
    name='zc.buildout.languageserver',
    version='0.9.3',
    description='A language server for zc.buildout',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Framework :: Buildout',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords='zc.buildout languageserver',
    packages=['buildoutls'],
    python_requires='>=3.7',
    install_requires=[
        'aiohttp',
        'cachetools',
        'packaging',
        'pygls >= 1.0',
        'typing-extensions',
        'zc.buildout',
    ],
    extras_require={
        'test': [
            'aioresponses',
            'asynctest; python_version < "3.8"',
            'coverage',
            'mock;  python_version < "3.8"',
            'mypy',
            'pylint',
            'pytest-asyncio',
            'pytest-benchmark',
            'pytest-cov',
            'pytest',
            'types-cachetools',
            'types-mock;  python_version < "3.8"',
            'types-setuptools',
            'types-toml',
            'yapf',
        ],
    },
    entry_points={
        'console_scripts': [
            'buildoutls=buildoutls.cli:main',
        ],
    },
)
