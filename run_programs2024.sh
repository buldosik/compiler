#!/bin/bash

# Iterate over example files
for file in tests2024/program*.imp; do
    # Extract file name without path and extension
    filename=$(basename -- "$file")
    filename_noext="${filename%.*}"
    echo "Running test for $filename..."
    
    # Run the Python script with the current input file
    ./run_test.sh "$file" "tests2024/$filename_noext.my.mr"

    # Wait for user input before proceeding to the next test
    read -p "Press Enter to continue to the next test..."
done
