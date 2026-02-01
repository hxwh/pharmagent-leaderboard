#!/usr/bin/env python3
"""
Results Format Adapter for AgentBeats Leaderboard Compatibility

Transforms PharmAgent's detailed evaluation results into AgentBeats-compatible format.
Based on leaderboard-config.json scoring requirements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def extract_leaderboard_metrics(result_data: Dict[str, Any], subtask: str) -> Dict[str, Any]:
    """
    Extract metrics that match leaderboard-config.json scoring requirements.

    Args:
        result_data: The detailed result data from PharmAgent evaluation
        subtask: Either "subtask1" or "subtask2"

    Returns:
        Simplified metrics dict compatible with AgentBeats leaderboard
    """
    # First try to get metrics directly (for simple format)
    if subtask == "subtask1":
        # Subtask 1: Medical Record Tasks
        # Expected metrics: score, success_rate
        score = result_data.get("score", 0.0)
        report = result_data.get("report") or {}
        success_rate = report.get("success_rate", 0.0) if isinstance(report, dict) else 0.0

        # If we have direct metrics, use them
        if score > 0.0 or success_rate > 0.0:
            return {
                "score": float(score),
                "success_rate": float(success_rate)
            }

        # Otherwise, calculate from batch_info if available
        batch_info = result_data.get("batch_info", {})
        if batch_info:
            total_tasks = batch_info.get("total_tasks", 0)
            correct_tasks = batch_info.get("correct_tasks", 0)

            if total_tasks > 0:
                score = correct_tasks / total_tasks
                success_rate = score  # For subtask1, score and success_rate are the same
                return {
                    "score": float(score),
                    "success_rate": float(success_rate)
                }

        # Fallback: calculate from task_results
        task_results = batch_info.get("task_results", {}) if batch_info else {}
        if task_results:
            total_tasks = len(task_results)
            correct_tasks = sum(1 for task_result in task_results.values()
                              if not task_result.get("failure_type"))

            if total_tasks > 0:
                score = correct_tasks / total_tasks
                success_rate = score
                return {
                    "score": float(score),
                    "success_rate": float(success_rate)
                }

        # Default fallback
        return {
            "score": 0.0,
            "success_rate": 0.0
        }

    elif subtask == "subtask2":
        # Subtask 2: Confabulation Detection
        # Expected metrics: accuracy, hallucination_rate
        accuracy = result_data.get("accuracy", 0.0)
        hallucination_rate = result_data.get("hallucination_rate", 0.0)

        # If we have direct metrics, use them
        if accuracy > 0.0 or hallucination_rate > 0.0:
            return {
                "accuracy": float(accuracy),
                "hallucination_rate": float(hallucination_rate)
            }

        # For subtask2, we would need similar batch processing logic
        # For now, return defaults
        return {
            "accuracy": 0.0,
            "hallucination_rate": 0.0
        }

    else:
        raise ValueError(f"Unknown subtask: {subtask}")


def transform_agentbeats_results(agentbeats_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform AgentBeats client results into AgentBeats leaderboard-compatible format.

    Args:
        agentbeats_results: Results from AgentBeats client (may be A2A artifacts or direct results)

    Returns:
        AgentBeats leaderboard-compatible results format with participants and results array
    """
    # Extract participant_id from participants field if available
    participant_id = None
    participants = {}
    if "participants" in agentbeats_results:
        participants = agentbeats_results["participants"]
        # Get the first participant's ID (usually medical_agent)
        if isinstance(participants, dict):
            # Extract the UUID from the first participant
            participant_id = list(participants.values())[0] if participants else None

    # Handle different possible input formats from AgentBeats client

    # Case 1: Direct results format (if client outputs structured JSON)
    if "subtask" in agentbeats_results and "participant_id" in agentbeats_results:
        result = agentbeats_results.copy()
        if participant_id and not result.get("participant_id"):
            result["participant_id"] = participant_id
        # Wrap in AgentBeats format
        return {
            "participants": participants,
            "results": [result]
        }

    # Case 2: Results array format (AgentBeats client output)
    if "results" in agentbeats_results and isinstance(agentbeats_results["results"], list):
        # Process first result in the array
        if agentbeats_results["results"]:
            result_item = agentbeats_results["results"][0]
            # Check if result_item has result_data directly
            if "result_data" in result_item:
                if participant_id:
                    result_item["participant_id"] = participant_id
                transformed = transform_pharmagent_results(result_item)
            # Or if it's nested differently
            elif isinstance(result_item, dict):
                if participant_id:
                    result_item["participant_id"] = participant_id
                transformed = transform_pharmagent_results(result_item)
            else:
                transformed = result_item
            # Return in AgentBeats format
            return {
                "participants": participants,
                "results": [transformed]
            }

    # Case 3: A2A artifacts format (extract from artifacts)
    if "artifacts" in agentbeats_results:
        for artifact in agentbeats_results["artifacts"]:
            if artifact.get("name") == "Evaluation Result":
                parts = artifact.get("parts", [])
                for part in parts:
                    if part.get("kind") == "data":
                        data = part.get("data", {})
                        if data:
                            # Add participant_id if extracted
                            if participant_id:
                                data["participant_id"] = participant_id
                            # This should contain the detailed PharmAgent results
                            transformed = transform_pharmagent_results(data)
                            # Return in AgentBeats format
                            return {
                                "participants": participants,
                                "results": [transformed]
                            }

    # Case 4: Raw PharmAgent format (fallback for testing)
    if "result_data" in agentbeats_results:
        if participant_id:
            agentbeats_results["participant_id"] = participant_id
        transformed = transform_pharmagent_results(agentbeats_results)
        # Return in AgentBeats format
        return {
            "participants": participants,
            "results": [transformed]
        }

    # Default: assume it's already in the right format, wrap it
    if participant_id and "participant_id" not in agentbeats_results:
        agentbeats_results["participant_id"] = participant_id
    return {
        "participants": participants,
        "results": [agentbeats_results]
    }


def get_participant_id_from_scenario() -> str:
    """
    Extract participant ID from scenario.toml for leaderboard results.
    """
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    scenario_file = Path("scenario.toml")
    if scenario_file.exists():
        with open(scenario_file, 'rb') as f:
            scenario = tomllib.load(f)

        participants = scenario.get("participants", [])
        if participants:
            # Use the first participant's agentbeats_id, or name if no ID
            participant = participants[0]
            return participant.get("agentbeats_id") or participant.get("name", "unknown")

    return "unknown"


def transform_pharmagent_results(pharmagent_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform PharmAgent evaluation results into AgentBeats leaderboard format.

    Args:
        pharmagent_results: Raw results from PharmAgent evaluation

    Returns:
        AgentBeats-compatible results format
    """
    # Extract subtask from config, result_data, or infer from task_id
    config = pharmagent_results.get("config", {})
    result_data = pharmagent_results.get("result_data", {})
    
    # Try to get subtask from multiple sources (priority: result_data > config > infer from task_id > default)
    subtask = result_data.get("subtask") or config.get("subtask")
    
    # If still missing, infer from task_id (old image compatibility)
    if not subtask:
        task_id = result_data.get("task_id") or ""
        task_id_str = str(task_id).lower() if task_id else ""
        if task_id_str.startswith("subtask2") or "pokemon" in task_id_str:
            subtask = "subtask2"
        elif task_id_str.startswith("task") or "batch" in task_id_str:
            subtask = "subtask1"
        else:
            subtask = "subtask1"  # Default fallback

    # Extract leaderboard-compatible metrics
    metrics = extract_leaderboard_metrics(result_data, subtask)

    # Get participant ID from results or scenario
    participant_id = pharmagent_results.get("participant_id")
    if not participant_id or participant_id == "unknown":
        participant_id = get_participant_id_from_scenario()

    # Extract timestamp (prefer ISO format from result_data or top level)
    timestamp = (
        result_data.get("timestamp") or 
        pharmagent_results.get("timestamp") or 
        ""
    )
    
    # Ensure timestamp is in ISO format (DuckDB expects consistent format)
    if timestamp and not timestamp.endswith("Z") and "T" in timestamp:
        # Already ISO format, keep as is
        pass
    elif not timestamp:
        # Fallback: use current time if missing
        from datetime import datetime
        timestamp = datetime.now().isoformat()

    # Build AgentBeats-compatible results
    leaderboard_results = {
        "subtask": subtask,
        "participant_id": participant_id,
        "timestamp": timestamp,
        "config": config,
        **metrics  # Add the scoring metrics at top level
    }

    return leaderboard_results


def main():
    """Convert PharmAgent results to AgentBeats format."""
    if len(sys.argv) != 3:
        print("Usage: python results_format_adapter.py <input_file> <output_file>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist")
        sys.exit(1)

    # Load AgentBeats client results
    with open(input_file, 'r') as f:
        client_results = json.load(f)

    # Transform to leaderboard format
    leaderboard_results = transform_agentbeats_results(client_results)

    # Save transformed results
    with open(output_file, 'w') as f:
        json.dump(leaderboard_results, f, indent=2)

    print(f"Transformed results saved to {output_file}")
    print(f"Metrics: {leaderboard_results}")


if __name__ == "__main__":
    main()