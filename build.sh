#!/bin/bash
set -e

echo "Installing dependencies..."
pip install --upgrade pip

echo "Installing Pillow with no cache..."
pip install Pillow==9.5.0 --no-cache-dir

echo "Installing remaining requirements..."
pip install -r requirements.txt

echo "Build completed successfully!"
