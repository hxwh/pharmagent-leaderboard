#!/usr/bin/env python3
"""
Generate Docker Compose for MedAgentBench Leaderboard on AgentBeats platform.

REQUIRES AgentBeats registration - no local images supported.
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
        raise Exception(f"Failed to fetch agent {agentbeats_id}: {e}")
    except requests.exceptions.JSONDecodeError:
        raise Exception(f"Invalid JSON response for agent {agentbeats_id}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed for agent {agentbeats_id}: {e}")


def resolve_image(agent: dict, name: str) -> bool:
    """Resolve docker image for an agent via AgentBeats API."""
    agentbeats_id = agent.get("agentbeats_id", "").strip()

    if not agentbeats_id:
        print(f"Skipping {name} - no agentbeats_id provided")
        return False

    info = fetch_agent_info(agentbeats_id)
    agent["image"] = info["docker_image"]
    print(f"Resolved {name} image: {agent['image']}")
    return True


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

    services = {}

    # Resolve green agent image (required)
    green_agent = scenario.get('green_agent', {})
    if not resolve_image(green_agent, "green_agent"):
        print("Error: Green agent must have a valid agentbeats_id")
        sys.exit(1)

    services['green_agent'] = {
        'image': green_agent['image'],
        'command': ['--host', '0.0.0.0', '--port', '8000', '--card-url', 'http://green_agent:8000'],
        'environment': green_agent.get('env', {}),
        'ports': ['8000:8000'],
        'volumes': ['./output:/app/output'],
        'healthcheck': {
            'test': ['CMD', 'curl', '-f', 'http://localhost:8000/.well-known/agent-card.json'],
            'interval': '5s',
            'timeout': '3s',
            'retries': 10,
            'start_period': '30s'
        },
        'platform': 'linux/amd64'
    }

    # Resolve participant images (optional - skip if no agentbeats_id)
    participants = scenario.get('participants', [])
    valid_participants = []
    for i, participant in enumerate(participants):
        name = participant.get('name', f'participant_{i}')
        if resolve_image(participant, f"participant '{name}'"):
            valid_participants.append(participant)

    # Purple agent services
    for i, participant in enumerate(valid_participants):
        service_name = f"purple_agent_{i}"
        services[service_name] = {
            'image': participant['image'],
            'command': ['--host', '0.0.0.0', '--port', '8000', '--card-url', f'http://{service_name}:8000'],
            'environment': participant.get('env', {}),
            'depends_on': {
                'green_agent': {'condition': 'service_healthy'}
            },
            'volumes': ['./output:/app/output'],
            'healthcheck': {
                'test': ['CMD', 'curl', '-f', 'http://localhost:8000/.well-known/agent-card.json'],
                'interval': '5s',
                'timeout': '3s',
                'retries': 10,
                'start_period': '30s'
            },
            'platform': 'linux/amd64'
        }

    # FHIR server for medical data (if needed)
    # Service name must be 'fhir-server' to match FHIR_SERVER_URL in scenario.toml
    if scenario.get('config', {}).get('domain') == 'medagentbench':
        services['fhir-server'] = {
            'image': 'jyxsu6/medagentbench:latest',
            'ports': ['8080:8080'],
            'environment': {
                'FHIR_PORT': '8080'
            },
            'platform': 'linux/amd64'
        }
        # Note: No health check for FHIR server - it starts reliably
        # Green agent will connect to it via environment variable

    # AgentBeats client service to orchestrate the evaluation
    # This service runs the client that coordinates between green and purple agents
    all_agent_services = ['green_agent'] + [f'purple_agent_{i}' for i in range(len(valid_participants))]

    # Create depends_on dict for agentbeats-client
    client_depends_on = {}
    for service in all_agent_services:
        client_depends_on[service] = {'condition': 'service_healthy'}

    services['agentbeats-client'] = {
        'image': 'ghcr.io/agentbeats/agentbeats-client:v1.0.0',
        'volumes': [
            './scenario.toml:/app/scenario.toml',
            './output:/app/output'
        ],
        'command': ['scenario.toml', 'output/results.json'],
        'depends_on': client_depends_on,
        'platform': 'linux/amd64'
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

    # Check for platform usage - all agents must have agentbeats_id
    green_agent = scenario.get('green_agent', {})
    participants = scenario.get('participants', [])

    has_green_agentbeats_id = bool(green_agent.get('agentbeats_id', '').strip())

    agentbeats_participants = 0
    empty_participants = 0

    for participant in participants:
        agentbeats_id = participant.get('agentbeats_id', '').strip()
        if agentbeats_id:
            agentbeats_participants += 1
        else:
            empty_participants += 1

    total_registered_agents = (1 if has_green_agentbeats_id else 0) + agentbeats_participants

    if total_registered_agents == 0:
        print("\n❌ No Registered Agents Found")
        print("   All agents must be registered with AgentBeats platform")
        print("   Visit https://agentbeats.dev to register your agents")
        print("   Then update scenario.toml with your agentbeats_id values")
        sys.exit(1)

    if not has_green_agentbeats_id:
        print("\n❌ Green Agent Not Registered")
        print("   The green agent (evaluator) must have a valid agentbeats_id")
        sys.exit(1)

    print("\n✅ AgentBeats Platform Configuration Confirmed")
    print(f"   Using {total_registered_agents} registered agent(s) from AgentBeats platform")
    print("   Images resolved via agentbeats.dev API")

    if empty_participants > 0:
        print(f"   Note: {empty_participants} participant(s) skipped (no agentbeats_id provided)")

    print("\n🚀 Ready for GitHub Actions workflow execution")

if __name__ == '__main__':
    main()
