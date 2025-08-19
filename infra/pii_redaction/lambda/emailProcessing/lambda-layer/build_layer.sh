#!/bin/bash
set -eo pipefail

# Clean up any previous builds
rm -rf python
rm -f layer_content.zip

# Create directory structure
mkdir -p python

# Install packages
pip install -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: -t python/  

# Remove unnecessary files to reduce size
find python -type d -name "tests" -exec rm -rf {} +
find python -type d -name "__pycache__" -exec rm -rf {} +
find python -type f -name "*.pyc" -delete
find python -type f -name "*.pyo" -delete
find python -type f -name "*.dist-info" -exec rm -rf {} +

# Create zip file
zip -r layer_content.zip python/
