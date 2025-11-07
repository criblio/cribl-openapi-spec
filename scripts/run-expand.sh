#!/bin/bash
# Script to generate fully resolved OpenAPI specs

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <input.yml> <output.yml>"
    echo ""
    echo "Examples:"
    echo "  $0 specs/control-plane.yml specs/control-plane-resolved.yml"
    echo "  $0 specs/mgmt-plane.yml specs/mgmt-plane-resolved.yml"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_FILE=$2

echo "Generating resolved OpenAPI specification..."
echo "Input:  $INPUT_FILE"
echo "Output: $OUTPUT_FILE"
echo ""

python3 "$SCRIPT_DIR/expand-refs.py" "$INPUT_FILE" "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Success!"
    ls -lh "$OUTPUT_FILE"
else
    echo "✗ Failed to process $INPUT_FILE"
    exit 1
fi
