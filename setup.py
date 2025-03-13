# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         setup
# Purpose:      Setup script for SpiderFoot
#
# Author:       Steve Micallef <steve@binarypool.com>
#
# Created:      15/05/2012
# Copyright:    (c) Steve Micallef 2012
# Licence:      MIT
# -------------------------------------------------------------------------------

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="SpiderFoot",
    version="4.0",
    author="Steve Micallef",
    author_email="steve@binarypool.com",
    description="SpiderFoot is an open source intelligence (OSINT) automation tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/smicallef/spiderfoot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "cherrypy>=18.6.0",
        "mako>=1.1.4",
        "networkx>=2.5",
        "nltk>=3.5",
        "phonenumbers>=8.12.18",
        "pyOpenSSL>=20.0.1",
        "requests>=2.25.1",
        "beautifulsoup4>=4.9.3",
        "lxml>=4.6.2",
        "ipwhois>=1.1.0",
        "dnspython>=2.1.0",
        "pyyaml>=5.4.1",
        "publicsuffix2>=2.20191221",
        "pycountry>=20.7.3",
        "maxminddb>=2.0.3",
        "geoip2>=4.1.0",
        "pysocks>=1.7.1",
        "html2text>=2020.1.16",
        "pdfminer.six>=20201018",
        "pillow>=8.0.1",
        "pygments>=2.7.2",
        "pycryptodome>=3.9.9",
        "pytz>=2020.4",
        "pyparsing>=2.4.7",
        "pyjwt>=1.7.1",
        "pygments>=2.7.2",
        "pymisp>=2.4.166",
        "cryptography>=3.4.8",
        "python-dateutil>=2.8.2"
    ],
    extras_require={
        "misp": [
            "pymisp>=2.4.166",
            "cryptography>=3.4.8",
            "python-dateutil>=2.8.2"
        ],
    },
    entry_points={
        "console_scripts": [
            "sfcli=spiderfoot.sfcli:main",
            "sfweb=spiderfoot.sfweb:main",
        ],
    },
)