#!/bin/bash

# File Organizer launcher script
# Launches the FileOrganizer GUI application

# Script directory (for relative paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to virtual environment Python
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Python virtual environment not found at $VENV_PYTHON"
    echo "Please set up the virtual environment with:"
    echo "  python -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "Using Python: $(realpath $VENV_PYTHON)"

# Check if custom modules path is provided as argument
if [ -n "$1" ] && [ -d "$1" ]; then
    export PYTHONPATH="$1:$PYTHONPATH"
    echo "Added custom modules path: $1"
fi

# Check if Pillow is installed in the virtual environment
if ! $VENV_PYTHON -c "import PIL" &> /dev/null; then
    echo "Warning: Pillow (PIL) is not installed in the virtual environment."
    echo "Consider installing it with: .venv/bin/pip install pillow"
fi

# Check if the script exists
if [ ! -f "$SCRIPT_DIR/file_organizer.py" ]; then
    echo "Error: Could not find file_organizer.py in $SCRIPT_DIR"
    exit 1
fi

# Make the script executable if it isn't already
if [ ! -x "$SCRIPT_DIR/file_organizer.py" ]; then
    chmod +x "$SCRIPT_DIR/file_organizer.py"
fi

echo "Starting File Organizer..."
# Run the application using the virtual environment Python
"$VENV_PYTHON" "$SCRIPT_DIR/file_organizer.py"
exit $?