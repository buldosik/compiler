#!/bin/bash

# Iterate over example files
for file in examples2025/example*.imp; do
    # Extract file name without path and extension
    filename=$(basename -- "$file")
    filename_noext="${filename%.*}"

    echo "Running test for $filename..."
    
    # Run the Python script with the current input file
    ./run_test.sh "$file" "examples2025/$filename_noext.my.mr"

    # Wait for user input before proceeding to the next test
    read -p "Press Enter to continue to the next test..."
done
