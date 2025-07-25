#!/bin/bash

# This script controls the Vercel build process.
# It will exit immediately if any command fails.
set -e

echo "--- Starting custom build process ---"

# Step 1: Install all Python dependencies from requirements.txt.
echo "[1/2] Installing dependencies..."
pip install -r requirements.txt

# Step 2: Run our Python script to patch the broken library.
echo "[2/2] Applying patch to pollinations.ai library..."
python patch_pollinations.py

echo "--- Custom build process finished successfully. ---"
