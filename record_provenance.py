#!/usr/bin/env python3
"""
Record Provenance for MedAgentBench Leaderboard

Tracks assessment provenance and metadata for AgentBeats leaderboard.
Based on AgentBeats leaderboard template requirements.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

def record_assessment_provenance(
    assessment_id: str,
    scenario_config: Dict[str, Any],
    results_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    Record provenance information for an assessment run.

    Args:
        assessment_id: Unique identifier for the assessment
        scenario_config: The scenario.toml configuration used
        results_path: Path to the assessment results file
        output_path: Path to write the provenance record

    Returns:
        Dict containing provenance information
    """
    # Load results to get basic metadata
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading results from {results_path}: {e}")
        sys.exit(1)

    # Extract participant information
    participants = results.get('participants', {})
    agent_ids = []
    if isinstance(participants, dict):
        agent_ids = list(participants.values())
    elif isinstance(participants, list):
        agent_ids = [p.get('agentbeats_id', p.get('id', 'unknown')) for p in participants]

    # Create provenance record
    provenance = {
        "assessment_id": assessment_id,
        "timestamp": datetime.now().isoformat(),
        "agentbeats_ids": agent_ids,
        "scenario_config": scenario_config,
        "results_summary": {
            "total_participants": len(agent_ids),
            "results_file": str(results_path.name),
            "has_results": bool(results.get('results'))
        },
        "metadata": {
            "generator": "MedAgentBench Leaderboard",
            "version": "1.0.0",
            "benchmark": "MedAgentBench",
            "subtasks": ["subtask1", "subtask2"]
        }
    }

    # Write provenance record
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(provenance, f, indent=2, default=str)

    print(f"✓ Provenance recorded to {output_path}")
    return provenance

def main():
    """Command-line interface for recording provenance."""
    parser = argparse.ArgumentParser(description='Record provenance information for an assessment run.')
    parser.add_argument('--compose', type=Path, help='Path to docker-compose.yml file (for workflow compatibility)')
    parser.add_argument('--output', type=Path, required=True, help='Path to write provenance record')
    parser.add_argument('assessment_id', nargs='?', help='Unique identifier for the assessment')
    parser.add_argument('scenario_path', nargs='?', type=Path, help='Path to scenario configuration file')
    parser.add_argument('results_path', nargs='?', type=Path, help='Path to assessment results file')

    args = parser.parse_args()

    # Handle workflow-style arguments
    if args.compose and not args.assessment_id:
        # Workflow mode: extract info from compose file location
        assessment_id = "agentbeats-workflow"
        scenario_path = args.compose.parent / "scenario.toml"
        results_path = args.output.parent / "results.json"
        output_path = args.output
    else:
        # Direct mode: use positional arguments
        if not all([args.assessment_id, args.scenario_path, args.results_path]):
            print("Usage: python record_provenance.py [--compose docker-compose.yml --output output/provenance.json]")
            print("   or: python record_provenance.py <assessment_id> <scenario.toml> <results.json> <output.json>")
            print("")
            print("Record provenance information for an assessment run.")
            sys.exit(1)
        assessment_id = args.assessment_id
        scenario_path = args.scenario_path
        results_path = args.results_path
        output_path = args.output

    # Load scenario config
    try:
        import tomllib
        with open(scenario_path, 'rb') as f:
            scenario_config = tomllib.load(f)
    except ImportError:
        try:
            import tomli as tomllib
            with open(scenario_path, 'rb') as f:
                scenario_config = tomllib.load(f)
        except ImportError:
            print("Error: tomli or tomllib required. Install with: pip install tomli")
            sys.exit(1)
    except Exception as e:
        print(f"Error loading scenario config: {e}")
        sys.exit(1)

    # Record provenance
    provenance = record_assessment_provenance(
        assessment_id=assessment_id,
        scenario_config=scenario_config,
        results_path=results_path,
        output_path=output_path
    )

    print(f"✓ Assessment {assessment_id} provenance recorded successfully")

if __name__ == '__main__':
    main()