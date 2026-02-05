#!/usr/bin/env python3
"""
Results Format Adapter for MedAgentBench Leaderboard.

Transforms assessment results to be compatible with the AgentBeats leaderboard format.
This is a pass-through adapter that ensures results are in the expected format.
"""

import json
import sys
from pathlib import Path


def transform_results(input_path: Path, output_path: Path) -> None:
    """
    Transform results to leaderboard-compatible format.
    
    Args:
        input_path: Path to input results JSON file
        output_path: Path to write transformed results
    """
    try:
        with open(input_path, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"Error: Results file not found: {input_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in results file: {e}")
        sys.exit(1)
    
    # Ensure results have expected structure
    # The AgentBeats client produces results in a specific format
    # This adapter ensures compatibility with the leaderboard
    
    transformed = results  # Pass-through for now
    
    # Write transformed results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(transformed, f, indent=2)
    
    print(f"✓ Results transformed and saved to {output_path}")


def main():
    """Command-line interface."""
    if len(sys.argv) != 3:
        print("Usage: python results_format_adapter.py <input.json> <output.json>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    transform_results(input_path, output_path)


if __name__ == '__main__':
    main()
