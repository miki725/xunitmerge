from __future__ import unicode_literals, print_function
import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname), 'rb') \
        .read().decode('utf-8')


setup(
    name='xunitmerge',
    version='1.0',
    author='Miroslav Shubernetskiy',
    author_email='miroslav@miki725.com',
    description='Utility for merging multiple XUnit xml reports '
                'into a single xml report.',
    long_description=read('README.rst') + read('LICENSE.rst'),
    url='https://github.com/miki725/xunitmerge',
    packages=find_packages(exclude=['test', 'test.*']),
    scripts=['bin/xunitmerge'],
    install_requires=[
        'six',
    ],
    keywords=' '.join([
        'xunit',
        'reports',
    ]),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
    ],
    license='MIT',
)
