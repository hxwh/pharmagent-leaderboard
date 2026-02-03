#!/usr/bin/env python3
"""
Leaderboard Submission Generator for MedAgentBench.

Generates properly formatted leaderboard submissions from evaluation outputs.
Maps framework outputs to standard leaderboard subtasks:
- agentify-medagentbench → subtask1 (clinical decision making)
- fhiragentevaluator → subtask2 (multi-benchmark evaluation)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def load_evaluation_output(filepath: Path) -> Dict[str, Any]:
    """Load evaluation output from JSON file."""
    with open(filepath) as f:
        return json.load(f)


def extract_agentify_results(eval_output: Dict[str, Any]) -> Dict[str, Any]:
    """Extract results from Agentify-MedAgentBench overall.json output."""
    return {
        "subtask": "subtask1",
        "total_tasks": eval_output.get("total_tasks", 0),
        "correct_tasks": eval_output.get("correct_count", 0),
        "accuracy": eval_output.get("pass_rate", 0.0),
        "success_rate": eval_output.get("pass_rate", 0.0),
        "time_used": eval_output.get("time_used", 0),
    }


def extract_fhir_eval_results(eval_output: Dict[str, Any]) -> Dict[str, Any]:
    """Extract results from FHIR Agent Evaluator output."""
    return {
        "subtask": "subtask2",
        "total_tasks": eval_output.get("total_tasks", 0),
        "correct_tasks": eval_output.get("correct_answers", 0),
        "accuracy": eval_output.get("accuracy", 0.0),
        "precision": eval_output.get("avg_precision", 0.0),
        "recall": eval_output.get("avg_recall", 0.0),
        "f1_score": eval_output.get("f1_score", 0.0),
        "time_used": eval_output.get("time_used", 0),
    }


def generate_submission(eval_output_path: Path, participant_id: str, framework: str) -> Dict[str, Any]:
    """
    Generate a leaderboard submission from evaluation output.

    Args:
        eval_output_path: Path to the evaluation output file
        participant_id: AgentBeats participant ID
        framework: "agentify-medagentbench" or "fhiragentevaluator"
    """
    eval_output = load_evaluation_output(eval_output_path)

    if framework == "agentify-medagentbench":
        result = extract_agentify_results(eval_output)
    elif framework == "fhiragentevaluator":
        result = extract_fhir_eval_results(eval_output)
    else:
        raise ValueError(f"Unsupported framework: {framework}")

    # Add timestamp and participant info
    result["timestamp"] = datetime.now().isoformat()

    submission = {
        "participants": {"medical_agent": participant_id},
        "results": [result]
    }

    return submission


def main():
    """Generate leaderboard submission from evaluation output."""
    if len(sys.argv) != 4:
        print("Usage: python generate_leaderboard_submission.py <eval_output.json> <participant_id> <framework>")
        print("  framework: agentify-medagentbench or fhiragentevaluator")
        print("  Note: agentify-medagentbench maps to subtask1, fhiragentevaluator maps to subtask2")
        print("\nExample:")
        print("  python generate_leaderboard_submission.py outputs/overall.json abc123 agentify-medagentbench")
        sys.exit(1)

    eval_output_path = Path(sys.argv[1])
    participant_id = sys.argv[2]
    framework = sys.argv[3]

    if not eval_output_path.exists():
        print(f"Error: {eval_output_path} not found")
        sys.exit(1)

    try:
        submission = generate_submission(eval_output_path, participant_id, framework)

        # Write to stdout (can be redirected to file)
        print(json.dumps(submission, indent=2))

        print(f"\nSubmission generated for {framework} framework")
        print(f"Participant ID: {participant_id}")
        print(f"Results: {submission['results'][0]}")

    except Exception as e:
        print(f"Error generating submission: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()