#!/bin/bash

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 infile [outfile]"
    exit 1
fi

infile="$1"
outfile="${2:-output.txt}"

# Run the Python compiler
python3 compiler/compiler.py "$infile" "$outfile"

# Check if the compilation was successful
if [ $? -eq 0 ]; then
    # Run the virtual machine with the output file
    ./virtual_machine/maszyna-wirtualna-cln "$outfile"
else
    echo ""
    echo "Compilation failed. Exiting."
    exit 1
fi
