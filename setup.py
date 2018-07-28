from codecs import open
from setuptools import setup, find_packages
from os import path

REQUIREMETS_DEV_FILE = 'requirements_dev.txt'
REQUIREMETS_FILE = 'requirements.txt'
PROJECTNAME = 'aioorm'
VERSION = '0.1.4'
DESCRIPTION = 'a simple orm suport asyncio,fork of aiopeewee'
URL = 'https://github.com/Python-Tools/aioorm'
AUTHOR = 'hsz'
AUTHOR_EMAIL = 'hsz1273327@gmail.com'
LICENSE = 'Mozilla'
CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Documentation :: Sphinx',
]
KEYWORDS = ['orm', 'asyncio', 'peewee']
PACKAGES = find_packages(exclude=['contrib', 'docs', 'test'])
ZIP_SAFE = False

HERE = path.abspath(path.dirname(__file__))
with open(path.join(HERE, 'README.rst'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()
REQUIREMETS_DIR = path.join(HERE, "requirements")

with open(path.join(REQUIREMETS_DIR, REQUIREMETS_FILE), encoding='utf-8') as f:
    REQUIREMETS = f.readlines()

with open(path.join(REQUIREMETS_DIR, REQUIREMETS_DEV_FILE), encoding='utf-8') as f:
    REQUIREMETS_DEV = f.readlines()

setup(
    name=PROJECTNAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    url=URL,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,
    packages=PACKAGES,
    include_package_data=True,
    install_requires=REQUIREMETS,
    extras_require={
        'dev': REQUIREMETS_DEV
    },

    zip_safe=ZIP_SAFE,
    data_files=[
        (
            'requirements',
            [
                'requirements/requirements.txt',
                'requirements/requirements_dev.txt'
            ]
        )
    ]
)
