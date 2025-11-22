#!/usr/bin/env python3
"""
Setup script for ClaudeCW - Amateur Radio CW Practice Bot
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with requirements_file.open() as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="claudecw",
    version="1.0.0",
    description="Amateur Radio CW Practice Bot using Claude AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ClaudeCW Contributors",
    url="https://github.com/morria/ClaudeCW",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cw_claude=claudecw.__main__:cli_main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Communications :: Ham Radio",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="morse code cw ham radio amateur radio ai claude",
)
