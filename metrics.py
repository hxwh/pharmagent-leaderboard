"""
Simple Metrics Calculator for MedAgentBench Leaderboard

Clear rules for calculating metrics from evaluation results.
No complex JSON configs or SQL queries - just straightforward Python functions.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime


@dataclass
class Subtask1Metrics:
    """Metrics for Subtask 1: Clinical Decision Making"""
    total_tasks: int
    correct_tasks: int
    accuracy: float
    timestamp: str

    @classmethod
    def calculate(cls, results: Dict[str, Any]) -> 'Subtask1Metrics':
        """
        Calculate Subtask 1 metrics.

        Rules:
        - total_tasks: Number of tasks evaluated
        - correct_tasks: Number of tasks with correct answers
        - accuracy: correct_tasks / total_tasks (0.0 to 1.0)
        """
        total_tasks = results.get('total_tasks', 0)
        correct_tasks = results.get('correct_count', results.get('correct_tasks', 0))

        # Accuracy calculation rule: correct / total, handle division by zero
        accuracy = correct_tasks / total_tasks if total_tasks > 0 else 0.0

        return cls(
            total_tasks=total_tasks,
            correct_tasks=correct_tasks,
            accuracy=accuracy,
            timestamp=datetime.now().isoformat()
        )


@dataclass
class Subtask2Metrics:
    """Metrics for Subtask 2: Confabulation Detection"""
    total_cases: int
    correct_cases: int
    accuracy: float
    hallucination_rate: float
    timestamp: str

    @classmethod
    def calculate(cls, results: Dict[str, Any]) -> 'Subtask2Metrics':
        """
        Calculate Subtask 2 metrics.

        Rules:
        - total_cases: Number of hallucination detection cases
        - correct_cases: Number of correctly identified hallucinations/non-hallucinations
        - accuracy: correct_cases / total_cases (0.0 to 1.0)
        - hallucination_rate: proportion of false positives (lower is better)
        """
        total_cases = results.get('total_cases', results.get('total_tasks', 0))
        correct_cases = results.get('correct_answers', results.get('correct_cases', 0))

        # Accuracy calculation rule: correct / total
        accuracy = correct_cases / total_cases if total_cases > 0 else 0.0

        # Hallucination rate calculation rule: from metrics or calculate from accuracy
        hallucination_rate = results.get('hallucination_rate', 1.0 - accuracy)

        return cls(
            total_cases=total_cases,
            correct_cases=correct_cases,
            accuracy=accuracy,
            hallucination_rate=hallucination_rate,
            timestamp=datetime.now().isoformat()
        )


def calculate_metrics(results: Dict[str, Any], subtask: str) -> Dict[str, Any]:
    """
    Calculate metrics for a specific subtask.

    Simple rules:
    - subtask1: Clinical Decision Making (accuracy from correct/total)
    - subtask2: Confabulation Detection (accuracy + hallucination rate)
    """
    if subtask == "subtask1":
        metrics = Subtask1Metrics.calculate(results)
        return {
            "subtask": "subtask1",
            "total_tasks": metrics.total_tasks,
            "correct_tasks": metrics.correct_tasks,
            "accuracy": metrics.accuracy,
            "timestamp": metrics.timestamp
        }

    elif subtask == "subtask2":
        metrics = Subtask2Metrics.calculate(results)
        return {
            "subtask": "subtask2",
            "total_tasks": metrics.total_cases,
            "correct_tasks": metrics.correct_cases,
            "accuracy": metrics.accuracy,
            "hallucination_rate": metrics.hallucination_rate,
            "timestamp": metrics.timestamp
        }

    else:
        raise ValueError(f"Unknown subtask: {subtask}")


def create_leaderboard_submission(
    participant_id: str,
    subtask1_results: Dict[str, Any] = None,
    subtask2_results: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a leaderboard submission from evaluation results.

    Simple rule: Include results for subtasks that have data.
    """
    results = []

    if subtask1_results:
        results.append(calculate_metrics(subtask1_results, "subtask1"))

    if subtask2_results:
        results.append(calculate_metrics(subtask2_results, "subtask2"))

    return {
        "participants": {"medical_agent": participant_id},
        "results": results
    }


# Simple ranking functions (replace complex SQL queries)

def rank_subtask1(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank submissions by Subtask 1 accuracy (highest first).

    Rule: Sort by accuracy descending, then by timestamp descending.
    """
    subtask1_results = []

    for submission in submissions:
        participant_id = submission["participants"]["medical_agent"]

        for result in submission["results"]:
            if result["subtask"] == "subtask1":
                subtask1_results.append({
                    "participant_id": participant_id,
                    "accuracy": result["accuracy"],
                    "correct_tasks": result["correct_tasks"],
                    "total_tasks": result["total_tasks"],
                    "timestamp": result["timestamp"]
                })

    # Sort by accuracy (desc), then timestamp (desc)
    return sorted(
        subtask1_results,
        key=lambda x: (x["accuracy"], x["timestamp"]),
        reverse=True
    )


def rank_subtask2(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank submissions by Subtask 2 accuracy (highest first).

    Rule: Sort by accuracy descending, then hallucination_rate ascending, then timestamp descending.
    """
    subtask2_results = []

    for submission in submissions:
        participant_id = submission["participants"]["medical_agent"]

        for result in submission["results"]:
            if result["subtask"] == "subtask2":
                subtask2_results.append({
                    "participant_id": participant_id,
                    "accuracy": result["accuracy"],
                    "hallucination_rate": result["hallucination_rate"],
                    "total_tasks": result["total_tasks"],
                    "timestamp": result["timestamp"]
                })

    # Sort by accuracy (desc), then hallucination_rate (asc), then timestamp (desc)
    return sorted(
        subtask2_results,
        key=lambda x: (x["accuracy"], -x["hallucination_rate"], x["timestamp"]),
        reverse=True
    )


def get_overall_ranking(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate overall ranking across both subtasks.

    Rule: Average accuracy across all subtasks, sort by average descending.
    """
    participant_stats = {}

    for submission in submissions:
        participant_id = submission["participants"]["medical_agent"]

        if participant_id not in participant_stats:
            participant_stats[participant_id] = {
                "accuracies": [],
                "submissions": 0,
                "latest_timestamp": ""
            }

        participant_stats[participant_id]["submissions"] += 1

        for result in submission["results"]:
            accuracy = result["accuracy"]
            timestamp = result["timestamp"]

            participant_stats[participant_id]["accuracies"].append(accuracy)

            # Track latest timestamp
            if timestamp > participant_stats[participant_id]["latest_timestamp"]:
                participant_stats[participant_id]["latest_timestamp"] = timestamp

    # Calculate averages and create ranking
    ranking = []
    for participant_id, stats in participant_stats.items():
        accuracies = stats["accuracies"]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0

        ranking.append({
            "participant_id": participant_id,
            "avg_accuracy": avg_accuracy,
            "submissions": stats["submissions"],
            "latest_timestamp": stats["latest_timestamp"]
        })

    # Sort by average accuracy descending
    return sorted(ranking, key=lambda x: x["avg_accuracy"], reverse=True)