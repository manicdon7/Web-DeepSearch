#!/bin/bash

# This script controls the build process.
# It ensures dependencies are installed BEFORE we try to patch them.

# Exit immediately if any command fails.
set -e

echo "--- Starting custom Vercel build process ---"

# Step 1: Install all Python dependencies as usual.
echo "Step 1: Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Step 2: Run our Python script to patch the broken pollinations library.
echo "Step 2: Applying patch to pollinations.ai library..."
python patch_pollinations.py

echo "--- Custom build process finished successfully. ---"
