#!/bin/bash

# Enhanced script to run the simulation for different FHE_INTERVAL values
# This version preserves output logs with the FHE_INTERVAL value in the filename

echo "Starting multiple simulation runs with different FHE_INTERVAL values..."

# Create a timestamp for this batch of runs
# TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
# OUTPUT_DIR="./output/batch_run_${TIMESTAMP}"

# Create output directory
# mkdir -p "$OUTPUT_DIR"

# Loop through FHE_INTERVAL values from 1 to 9
for fhe_interval in {1..10}
do
    echo -e "\n========================================"
    echo "Running simulation with FHE_INTERVAL=$fhe_interval"
    echo -e "========================================\n"
    
    # Set FHE_INTERVAL as environment variable and run the script
    # Use MPLBACKEND=Agg to force matplotlib to use non-interactive backend
    # Debug: print the environment variable
    echo "Setting FHE_INTERVAL=$fhe_interval"
    export FHE_INTERVAL=$fhe_interval
    export MPLBACKEND=Agg
    python -c "import os; print(f'Python sees FHE_INTERVAL={os.getenv(\"FHE_INTERVAL\")}')"
    python -m app.run
    
    echo "Completed run with FHE_INTERVAL=$fhe_interval"
    echo "Log saved to: $OUTPUT_DIR/run_fhe_${fhe_interval}.log"
    
    # Optional: add a small delay between runs
    sleep 2
done

echo -e "\nAll simulation runs completed!"
echo "Output logs are saved in: $OUTPUT_DIR"