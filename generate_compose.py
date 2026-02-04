#!/usr/bin/env python3
"""
Generate Docker Compose configuration for MedAgentBench Leaderboard

Used by GitHub Actions workflow for AgentBeats platform assessment runs.
Not intended for local development - use AgentBeats platform instead.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("Error: tomli or tomllib required. Install with: pip install tomli")
        sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests required. Install with: pip install requests")
    sys.exit(1)

AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"


def fetch_agent_info(agentbeats_id: str) -> dict:
    """Fetch agent info from agentbeats.dev API."""
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Error: Failed to fetch agent {agentbeats_id}: {e}")
        sys.exit(1)
    except requests.exceptions.JSONDecodeError:
        print(f"Error: Invalid JSON response for agent {agentbeats_id}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed for agent {agentbeats_id}: {e}")
        sys.exit(1)


def resolve_image(agent: dict, name: str) -> None:
    """Resolve docker image for an agent, either from 'image' field or agentbeats API."""
    has_image = "image" in agent
    has_id = "agentbeats_id" in agent and agent.get("agentbeats_id", "").strip()

    if has_image and has_id:
        print(f"Error: {name} has both 'image' and 'agentbeats_id' - use one or the other")
        sys.exit(1)
    elif has_image:
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"Error: {name} requires 'agentbeats_id' for GitHub Actions (use 'image' for local testing only)")
            sys.exit(1)
        print(f"Using {name} image: {agent['image']}")
    elif has_id:
        info = fetch_agent_info(agent["agentbeats_id"])
        agent["image"] = info["docker_image"]
        print(f"Resolved {name} image: {agent['image']}")
    else:
        print(f"Error: {name} must have either 'image' or 'agentbeats_id' field")
        sys.exit(1)


def load_scenario(scenario_path: Path) -> Dict[str, Any]:
    """Load and parse scenario.toml file."""
    try:
        with open(scenario_path, 'rb') as f:
            return tomli.load(f)
    except FileNotFoundError:
        print(f"Error: Scenario file not found: {scenario_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to parse scenario file: {e}")
        sys.exit(1)

def generate_compose_config(scenario: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Generate Docker Compose configuration from scenario."""

    # Resolve images for all agents
    green_agent = scenario.get('green_agent', {})
    resolve_image(green_agent, "green_agent")

    participants = scenario.get('participants', [])
    valid_participants = []
    for i, participant in enumerate(participants):
        name = participant.get('name', f'participant_{i}')
        try:
            resolve_image(participant, f"participant '{name}'")
            valid_participants.append(participant)
        except SystemExit:
            print(f"Skipping participant '{name}' - no valid image or agentbeats_id")
            continue

    services = {}

    # Green agent (evaluator) service
    services['green_agent'] = {
        'image': green_agent['image'],
        'environment': green_agent.get('env', {}),
        'ports': ['8000:8000'],
        'volumes': ['./output:/app/output']
    }

    # Purple agent services
    for i, participant in enumerate(valid_participants):
        service_name = f"purple_agent_{i}"
        services[service_name] = {
            'image': participant['image'],
            'environment': participant.get('env', {}),
            'depends_on': ['green_agent'],
            'volumes': ['./output:/app/output']
        }

    # FHIR server for medical data (if needed)
    if scenario.get('config', {}).get('domain') == 'medagentbench':
        services['fhir_server'] = {
            'image': 'jyxsu6/medagentbench:latest',
            'ports': ['8080:8080'],
            'environment': {
                'FHIR_PORT': '8080'
            }
        }

    compose_config = {
        'services': services,
        'volumes': {
            'output': {
                'driver': 'local'
            }
        }
    }

    return compose_config, services

def save_compose_file(compose_config: Dict[str, Any], output_path: Path):
    """Save Docker Compose configuration to file."""
    import yaml

    try:
        with open(output_path, 'w') as f:
            yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False)
        print(f"✓ Docker Compose configuration saved to {output_path}")
    except Exception as e:
        print(f"Error: Failed to save compose file: {e}")
        sys.exit(1)

def main():
    """Main entry point for GitHub Actions workflow. Not for local use."""
    parser = argparse.ArgumentParser(description='Generate Docker Compose for AgentBeats platform assessment')
    parser.add_argument('--scenario', type=Path, default=Path('scenario.toml'),
                       help='Path to scenario.toml file')
    parser.add_argument('--output', type=Path, default=Path('docker-compose.yml'),
                       help='Output path for docker-compose.yml')

    args = parser.parse_args()

    if not args.scenario.exists():
        print(f"Error: Scenario file not found: {args.scenario}")
        sys.exit(1)

    # Load scenario
    scenario = load_scenario(args.scenario)
    print(f"✓ Loaded scenario from {args.scenario}")

    # Generate compose config
    compose_config, services = generate_compose_config(scenario)
    print("✓ Generated Docker Compose configuration")

    # Save compose file
    save_compose_file(compose_config, args.output)

    # Validate that we have at least one service
    if not services:
        print("Error: No valid services configured. Check your scenario.toml for agentbeats_id fields.")
        print("This script is for AgentBeats platform use only - local testing requires real Docker images.")
        sys.exit(1)

    print(f"✓ Generated {len(services)} services: {', '.join(services.keys())}")

    # Check for platform usage
    agentbeats_images = [service.get('image', '') for service in services.values()
                        if 'ghcr.io/agentbeats/' in str(service.get('image', ''))]

    if agentbeats_images:
        print("\n✅ AgentBeats Platform Configuration Confirmed")
        print(f"   Ready for automated assessment with {len(agentbeats_images)} registered agent(s)")
        print("   GitHub Actions will resolve agentbeats_id to container images")
    else:
        print("\n❌ Local Development Configuration Detected")
        print("   This script is for AgentBeats platform use only")
        print("   For local testing, use direct Docker image references")
        print("   Example: image = 'your-registry/your-image:latest'")
        sys.exit(1)

    print("\n🚀 Ready for GitHub Actions workflow execution")

if __name__ == '__main__':
    main()
