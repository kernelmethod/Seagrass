#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    install_requires = f.readlines()

setup(
    name="seagrass",
    version="0.9.1",
    description="Auditing and profiling multi-tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="kernelmethod",
    author_email="17100608+kernelmethod@users.noreply.github.com",
    project_urls={
        "Source Code": "https://github.com/kernelmethod/Seagrass",
        "Bug Tracker": "https://github.com/kernelmethod/Seagrass/issues",
        "Documentation": "https://seagrass.readthedocs.io/en/latest/",
    },
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    url="https://github.com/kernelmethod/Seagrass/",
    package_data={"seagrass": ["py.typed"]},
    packages=find_packages(exclude=["tests"]),
    install_requires=install_requires,
    python_requires=">=3.7.0",
    license="BSD",
)
