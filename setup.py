from setuptools import setup, find_packages
import os

# Read the README file
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = "Comprehensive E. coli genotyping tool - MLST + Serotyping + Clermont typing"

setup(
    name="ecolityper",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ecolityper=ecoliTyper.ecolityper.cli:main',
        ],
    },
    install_requires=[
        'ezclermont>=0.7.0',
    ],
    python_requires='>=3.6',
    author="Beckley Brown",
    author_email="brownbeckley94@gmail.com",
    description="Comprehensive E. coli genotyping tool - MLST + Serotyping + Clermont typing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bbeckley-hub/ecoliTyper",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    # Include package data (non-Python files)
    include_package_data=True,
    package_data={
        'ecoliTyper': [
            'database/mlst/bin/mlst',
            'database/mlst/perl5/*',
            'database/serotypefinder/serotypefinder.py',
            'database/serotypefinder/serotypefinder_db/*',
            'database/serotypefinder/*',
        ],
    },
    # This ensures data files are installed with the package
    zip_safe=False,
)
