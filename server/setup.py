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
    version='0.6.2',
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
    python_requires='>=3.7.*',
    install_requires=[
        'cachetools',
        'pygls >= 0.10.1',
        'requests',
        'packaging',
        'zc.buildout',
        'typing-extensions',
    ],
    extras_require={
        'test': [
            'coverage',
            'pytest',
            'pytest-asyncio',
            'responses',
        ],
    },
    entry_points={
        'console_scripts': [
            'buildoutls=buildoutls.cli:main',
        ],
    },
)
