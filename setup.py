"""Setup configuration for robotframework-mock package."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="robotframework-mock",
    version="0.1.0",
    author="Lajos Olah",
    author_email="lajos.olah.jr@gmail.com",
    description="A Robot Framework library for mocking keywords in unit tests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/olesz/robotframework-mock",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Framework :: Robot Framework",
        "Framework :: Robot Framework :: Library",
    ],
    python_requires=">=3.7",
    install_requires=[
        "robotframework>=7.0",
    ],
)
