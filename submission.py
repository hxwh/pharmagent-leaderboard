"""
Simple Submission Generator for MedAgentBench Leaderboard

Replaces complex format adapters with straightforward result processing.
No complex framework detection - just clear rules for each input format.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

from metrics import create_leaderboard_submission, calculate_metrics


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def process_agentify_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Agentify-MedAgentBench results.

    Simple rule: Maps to subtask1 with direct field mapping.
    """
    return {
        "total_tasks": results.get("total_tasks", 0),
        "correct_count": results.get("correct_count", 0),
        "pass_rate": results.get("pass_rate", 0.0)
    }


def process_fhir_eval_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process FHIR Agent Evaluator results.

    Simple rule: Maps to subtask2 with direct field mapping.
    """
    return {
        "total_cases": results.get("total_tasks", 0),
        "correct_answers": results.get("correct_answers", 0),
        "accuracy": results.get("accuracy", 0.0),
        "hallucination_rate": results.get("hallucination_rate", 0.0)
    }


def process_agentbeats_output(output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process AgentBeats client output.

    Simple rule: Extract the first (and typically only) result.
    """
    results = output.get("results", [])
    if not results:
        print("Error: No results found in AgentBeats output")
        sys.exit(1)

    # Take the first result (simplified assumption)
    return results[0]


def generate_submission(
    input_file: Path,
    participant_id: str,
    input_type: str = "auto"
) -> Dict[str, Any]:
    """
    Generate leaderboard submission from evaluation results.

    Simple rules:
    - agentify: Maps to subtask1
    - fhir_eval: Maps to subtask2
    - agentbeats: Extract result and determine subtask from content
    """
    data = load_json_file(input_file)

    if input_type == "auto":
        # Simple auto-detection: check for unique identifying fields
        if "participants" in data and "results" in data:
            input_type = "agentbeats"
        elif "hallucination_rate" in data:
            input_type = "fhir_eval"
        elif "correct_count" in data or "pass_rate" in data:
            input_type = "agentify"
        else:
            print("Error: Could not auto-detect input type")
            print("Available fields:", list(data.keys()))
            sys.exit(1)

    # Process based on detected type
    if input_type == "agentify":
        subtask1_results = process_agentify_results(data)
        return create_leaderboard_submission(participant_id, subtask1_results=subtask1_results)

    elif input_type == "fhir_eval":
        subtask2_results = process_fhir_eval_results(data)
        return create_leaderboard_submission(participant_id, subtask2_results=subtask2_results)

    elif input_type == "agentbeats":
        # Extract result and determine which subtask
        result = process_agentbeats_output(data)
        subtask = result.get("subtask", "subtask1")

        if subtask == "subtask1":
            return create_leaderboard_submission(participant_id, subtask1_results=result)
        elif subtask == "subtask2":
            return create_leaderboard_submission(participant_id, subtask2_results=result)
        else:
            print(f"Error: Unknown subtask in AgentBeats output: {subtask}")
            sys.exit(1)

    else:
        print(f"Error: Unsupported input type: {input_type}")
        sys.exit(1)


def main():
    """Generate leaderboard submission from command line."""
    args = sys.argv[1:]

    # Parse --save option
    save_path = None
    if "--save" in args:
        try:
            save_idx = args.index("--save")
            if save_idx + 1 < len(args):
                save_path = Path(args[save_idx + 1])
                # Remove --save and its argument from args
                args = args[:save_idx] + args[save_idx + 2:]
            else:
                print("Error: --save requires a filename")
                sys.exit(1)
        except ValueError:
            pass  # --save not found

    # Check minimum required arguments
    if len(args) < 2:
        print("Usage: python submission.py <input.json> <participant_id> [input_type] [--save output.json]")
        print("")
        print("Input types:")
        print("  auto       - Auto-detect from file content (default)")
        print("  agentify   - Agentify-MedAgentBench format (maps to subtask1)")
        print("  fhir_eval  - FHIR Agent Evaluator format (maps to subtask2)")
        print("  agentbeats - AgentBeats client output")
        print("")
        print("Options:")
        print("  --save FILE    Save submission to specified file instead of stdout")
        print("")
        print("Examples:")
        print("  python submission.py results/overall.json abc123")
        print("  python submission.py results/eval.json xyz789 agentify")
        print("  python submission.py results/output.json participant_789 --save results/manual_assessment.json")
        sys.exit(1)

    input_file = Path(args[0])
    participant_id = args[1]
    input_type = args[2] if len(args) > 2 else "auto"

    submission = generate_submission(input_file, participant_id, input_type)

    # Output handling: save to file or stdout
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w') as f:
            json.dump(submission, f, indent=2)
        print(f"✓ Submission saved to {save_path}")
    else:
        # Output JSON to stdout (can be redirected to file)
        print(json.dumps(submission, indent=2))

    # Print summary
    results = submission.get("results", [])
    for result in results:
        subtask = result.get("subtask")
        accuracy = result.get("accuracy", 0)
        total = result.get("total_tasks", 0)
        print(f"✓ {subtask}: {accuracy:.1%} accuracy ({total} tasks)")


if __name__ == "__main__":
    main()