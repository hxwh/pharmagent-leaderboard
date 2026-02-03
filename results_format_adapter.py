#!/usr/bin/env python3
"""
Results Format Adapter for MedAgentBench Leaderboard.

Transforms Green Agent A2A artifact output to leaderboard-compatible format.
Supports multiple evaluation frameworks:
- subtask1/subtask2: Original MedAgentBench
- agentify-medagentbench: Enhanced MedAgentBench with A2A and MCP
- fhiragentevaluator: Multi-benchmark evaluation
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def extract_result_from_artifact(artifact_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract result from A2A artifact DataPart for any supported evaluation framework.

    Supports:
    - subtask1/subtask2: Original MedAgentBench
    - agentify-medagentbench: Enhanced MedAgentBench with A2A and MCP
    - fhiragentevaluator: Multi-benchmark evaluation
    """
    # If already in correct format, return as-is
    if "subtask" in artifact_data:
        return artifact_data

    # Handle Agentify-MedAgentBench format (from overall.json)
    if "domain" in artifact_data and artifact_data.get("domain") == "medagentbench":
        return {
            "subtask": "subtask1",
            "total_tasks": artifact_data.get("total_tasks", 0),
            "correct_tasks": artifact_data.get("correct_count", 0),
            "accuracy": artifact_data.get("pass_rate", 0.0),
            "success_rate": artifact_data.get("pass_rate", 0.0),
            "time_used": artifact_data.get("time_used", 0),
        }

    # Handle FHIR Agent Evaluator format
    if any(key in artifact_data for key in ["answer_correctness", "action_correctness", "f1_score", "correct_answers", "avg_precision"]):
        return {
            "subtask": "subtask2",
            "total_tasks": artifact_data.get("total_tasks", 0),
            "correct_tasks": artifact_data.get("correct_answers", 0),
            "accuracy": artifact_data.get("accuracy", artifact_data.get("answer_correctness", 0.0)),
            "precision": artifact_data.get("avg_precision", 0.0),
            "recall": artifact_data.get("avg_recall", 0.0),
            "f1_score": artifact_data.get("f1_score", 0.0),
            "time_used": artifact_data.get("time_used", 0),
        }

    # Handle legacy format with nested result_data
    if "result_data" in artifact_data:
        result_data = artifact_data["result_data"]
        subtask = result_data.get("subtask", "subtask1")

        # Convert legacy fields to new format
        if subtask == "subtask1":
            # Legacy: score, success_rate, batch_info
            batch_info = result_data.get("batch_info", {})
            total = batch_info.get("total_tasks", 0) or result_data.get("total_tasks", 0)
            correct = batch_info.get("correct_tasks", 0) or result_data.get("correct_tasks", 0)
            accuracy = result_data.get("score", 0.0) or (correct / total if total > 0 else 0.0)

            return {
                "subtask": "subtask1",
                "total_tasks": total,
                "correct_tasks": correct,
                "accuracy": accuracy,
                "success_rate": accuracy,
                "time_used": result_data.get("time_used"),
            }

        elif subtask == "subtask2":
            # Legacy: accuracy, hallucination_rate, metrics
            metrics = result_data.get("metrics", {})
            total = metrics.get("total_cases", 0) or result_data.get("total_tasks", 0)
            accuracy = result_data.get("accuracy", 0.0)
            hallucination_rate = result_data.get("hallucination_rate", 0.0)
            correct = int(total * accuracy) if total > 0 else 0

            return {
                "subtask": "subtask2",
                "total_tasks": total,
                "correct_tasks": correct,
                "accuracy": accuracy,
                "hallucination_rate": hallucination_rate,
                "time_used": result_data.get("time_used"),
            }

    # Fallback: try to infer from available fields
    return artifact_data


def transform_agentbeats_output(client_output: dict[str, Any]) -> dict[str, Any]:
    """
    Transform AgentBeats client output to leaderboard format.

    Supports multiple evaluation frameworks:
    - Original MedAgentBench (subtask1/subtask2)
    - Agentify-MedAgentBench (enhanced with A2A and MCP)
    - FHIR Agent Evaluator (multi-benchmark)

    Input (from agentbeats-client):
    {
        "participants": {"medical_agent": "uuid"},
        "results": [<DataPart contents>]
    }

    Output:
    {
        "participants": {"medical_agent": "uuid"},
        "results": [<Framework-specific result>]
    }
    """
    participants = client_output.get("participants", {})
    results_list = client_output.get("results", [])
    
    transformed_results = []
    
    for result_item in results_list:
        transformed = extract_result_from_artifact(result_item)
        
        # Add timestamp if missing
        if "timestamp" not in transformed:
            transformed["timestamp"] = datetime.now().isoformat()
        
        # Remove None values
        transformed = {k: v for k, v in transformed.items() if v is not None}
        
        transformed_results.append(transformed)
    
    return {
        "participants": participants,
        "results": transformed_results,
    }


def get_participant_id_from_scenario() -> str:
    """Extract participant ID from scenario.toml."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return "unknown"
    
    scenario_path = Path("scenario.toml")
    if not scenario_path.exists():
        return "unknown"
    
    with open(scenario_path, "rb") as f:
        scenario = tomllib.load(f)
    
    participants = scenario.get("purple_agent", [])
    if participants:
        p = participants[0]
        return p.get("agentbeats_id") or p.get("name", "unknown")
    
    return "unknown"


def main():
    """Transform MedAgentBench results to leaderboard format."""
    if len(sys.argv) != 3:
        print("Usage: python results_format_adapter.py <input.json> <output.json>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)
    
    with open(input_path) as f:
        client_output = json.load(f)
    
    leaderboard_output = transform_agentbeats_output(client_output)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(leaderboard_output, f, indent=2)
    
    # Print summary
    for result in leaderboard_output.get("results", []):
        subtask = result.get("subtask", "unknown")
        accuracy = result.get("accuracy", 0)
        total = result.get("total_tasks", 0)
        print(f"[{subtask}] accuracy={accuracy:.2%} ({total} tasks)")
    
    print(f"Output written to {output_path}")


if __name__ == "__main__":
    main()
