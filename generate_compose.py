#!/usr/bin/env python3
"""
Generate Docker Compose configuration for MedAgentBench Leaderboard

Used by GitHub Actions workflow for AgentBeats platform assessment runs.
Not intended for local development - use AgentBeats platform instead.
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

def generate_compose_config(scenario: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Generate Docker Compose configuration from scenario."""

    services = {}

    # Green agent (evaluator) service
    green_agent = scenario.get('green_agent', {})
    if 'image' in green_agent and green_agent['image']:
        services['green_agent'] = {
            'image': green_agent['image'],
            'environment': green_agent.get('env', {}),
            'ports': ['8000:8000'],
            'volumes': ['./output:/app/output']
        }
    elif 'agentbeats_id' in green_agent and green_agent.get('agentbeats_id'):
        # For registered AgentBeats agents, use the platform-resolved image
        # In production, AgentBeats resolves agentbeats_id to actual container images
        agent_id = green_agent['agentbeats_id']
        services['green_agent'] = {
            'image': f'agentbeats/{agent_id}:latest',  # Platform-resolved naming
            'environment': green_agent.get('env', {}),
            'ports': ['8000:8000'],
            'volumes': ['./output:/app/output']
        }
    else:
        print("Error: Green agent must have either 'image' or valid 'agentbeats_id'")
        sys.exit(1)

    # Purple agent services
    participants = scenario.get('participants', [])
    for i, participant in enumerate(participants):
        service_name = f"purple_agent_{i}"
        if 'image' in participant and participant['image']:
            services[service_name] = {
                'image': participant['image'],
                'environment': participant.get('env', {}),
                'depends_on': ['green_agent'],
                'volumes': ['./output:/app/output']
            }
        elif 'agentbeats_id' in participant and participant.get('agentbeats_id'):
            # For registered AgentBeats agents, use the platform-resolved image
            agent_id = participant['agentbeats_id']
            services[service_name] = {
                'image': f'agentbeats/{agent_id}:latest',  # Platform-resolved naming
                'environment': participant.get('env', {}),
                'depends_on': ['green_agent'],
                'volumes': ['./output:/app/output']
            }
        else:
            print(f"Warning: Participant {i} has no valid image or agentbeats_id, skipping")
            continue

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
                        if 'agentbeats/' in str(service.get('image', ''))]

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