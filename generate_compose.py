#!/usr/bin/env python3
"""
Generate Docker Compose configuration for MedAgentBench Leaderboard

Based on AgentBeats template for local testing and assessment running.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict
import tomllib

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("Error: tomli or tomllib required. Install with: pip install tomli")
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

def generate_compose_config(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Docker Compose configuration from scenario."""

    services = {}

    # Green agent (evaluator) service
    green_agent = scenario.get('green_agent', {})
    if 'image' in green_agent:
        services['green_agent'] = {
            'image': green_agent['image'],
            'environment': green_agent.get('env', {}),
            'ports': ['8000:8000'],
            'volumes': ['./output:/app/output']
        }
    elif 'agentbeats_id' in green_agent:
        # For registered agents, we'd use the AgentBeats registry
        # For now, use placeholder
        services['green_agent'] = {
            'image': 'placeholder/green:latest',
            'environment': green_agent.get('env', {}),
            'ports': ['8000:8000'],
            'volumes': ['./output:/app/output']
        }

    # Purple agent services
    participants = scenario.get('participants', [])
    for i, participant in enumerate(participants):
        service_name = f"purple_agent_{i}"
        if 'image' in participant:
            services[service_name] = {
                'image': participant['image'],
                'environment': participant.get('env', {}),
                'depends_on': ['green_agent'],
                'volumes': ['./output:/app/output']
            }
        elif 'agentbeats_id' in participant:
            # For registered agents, use placeholder
            services[service_name] = {
                'image': 'placeholder/purple:latest',
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
        'version': '3.8',
        'services': services,
        'volumes': {
            'output': {
                'driver': 'local'
            }
        }
    }

    return compose_config

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
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate Docker Compose for MedAgentBench assessment')
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
    compose_config = generate_compose_config(scenario)
    print("✓ Generated Docker Compose configuration")

    # Save compose file
    save_compose_file(compose_config, args.output)

    print("\nNext steps:")
    print("1. Copy .env.example to .env and fill in your API keys")
    print("2. Run: docker compose up --abort-on-container-exit")
    print("3. Check output/ directory for results")

if __name__ == '__main__':
    main()