#!/bin/bash

# Set variables
KING_URL="./tools/Linux-king.tar.gz"
PLINK_URL="./tools/plink_linux_x86_64_20241022.zip"
BIN_DIR="./bin"
SRC_DIR="./src"

# Create bin directory
mkdir -p $BIN_DIR

# Extract KING
echo "Extracting KING..."
tar -zxvf $KING_URL -C $BIN_DIR

# Extract Plink
echo "Extracting Plink..."
unzip $PLINK_URL -d $BIN_DIR

# Ensure Plink and KING are executable
chmod +x $BIN_DIR/king
chmod +x $BIN_DIR/plink

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installation complete! You can now start using duckPI!"
