#!/usr/bin/env python3
"""Generate Docker Compose configuration from scenario.toml

AgentBeats-compatible compose generator for MedAgentBench leaderboard.
Based on: https://github.com/RDI-Foundation/agentbeats-leaderboard-template
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("Error: tomli required. Install with: pip install tomli", file=sys.stderr)
        sys.exit(1)
try:
    import tomli_w
except ImportError:
    print("Error: tomli-w required. Install with: pip install tomli-w", file=sys.stderr)
    sys.exit(1)
try:
    import requests
except ImportError:
    print("Error: requests required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"

# Determine root relative to script location
SCRIPT_DIR = Path(__file__).parent
COMPOSE_PATH = SCRIPT_DIR / "docker-compose.yml"
A2A_SCENARIO_PATH = SCRIPT_DIR / "a2a-scenario.toml"
ENV_PATH = SCRIPT_DIR / ".env.example"

DEFAULT_PORT = 9009
PARTICIPANT_START_PORT = 9010
DEFAULT_ENV_VARS = {"PYTHONUNBUFFERED": "1"}


def fetch_agent_info(agentbeats_id: str) -> dict:
    """Fetch agent info from agentbeats.dev API."""
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Error: Failed to fetch agent {agentbeats_id}: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.JSONDecodeError:
        print(f"Error: Invalid JSON response for agent {agentbeats_id}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed for agent {agentbeats_id}: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_image(agent: dict, name: str) -> None:
    """Resolve docker image for an agent, either from 'image' field or agentbeats API."""
    has_image = "image" in agent and agent["image"]
    has_id = "agentbeats_id" in agent and agent["agentbeats_id"]

    if has_image and has_id:
        print(f"Error: {name} has both 'image' and 'agentbeats_id' - use one or the other", file=sys.stderr)
        sys.exit(1)
    elif has_image:
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"Error: {name} requires 'agentbeats_id' for GitHub Actions (use 'image' for local testing only)", file=sys.stderr)
            sys.exit(1)
        print(f"Using {name} image: {agent['image']}")
    elif has_id:
        try:
            info = fetch_agent_info(agent["agentbeats_id"])
            agent["image"] = info["docker_image"]
            print(f"Resolved {name} image: {agent['image']}")
        except SystemExit:
            # If agentbeats_id resolution fails, check for fallback image
            if "image" in agent:
                print(f"Using fallback {name} image: {agent['image']}")
            else:
                print(f"Error: {name} agentbeats_id '{agent['agentbeats_id']}' not found and no fallback image provided", file=sys.stderr)
                print(f"For local testing, add an 'image' field to the {name} configuration", file=sys.stderr)
                sys.exit(1)
    else:
        print(f"Error: {name} must have either 'image' or 'agentbeats_id' field", file=sys.stderr)
        sys.exit(1)


def parse_scenario(scenario_path: Path) -> dict[str, Any]:
    """Parse scenario.toml and resolve all agent images."""
    toml_data = scenario_path.read_text()
    data = tomli.loads(toml_data)

    green = data.get("green_agent", {})
    resolve_image(green, "green_agent")

    participants = data.get("purple_agent", [])

    # Check for duplicate participant names
    names = [p.get("name") for p in participants]
    duplicates = [name for name in set(names) if names.count(name) > 1]
    if duplicates:
        print(f"Error: Duplicate participant names found: {', '.join(duplicates)}", file=sys.stderr)
        print("Each participant must have a unique name.", file=sys.stderr)
        sys.exit(1)

    for participant in participants:
        name = participant.get("name", "unknown")
        resolve_image(participant, f"participant '{name}'")

    return data


def format_env_vars(env_dict: dict[str, Any]) -> str:
    """Format environment variables for docker-compose."""
    env_vars = {**DEFAULT_ENV_VARS, **env_dict}
    lines = [f"      - {key}={value}" for key, value in env_vars.items()]
    return "\n" + "\n".join(lines)


def format_depends_on(services: list) -> str:
    """Format depends_on section with health checks."""
    lines = []
    for service in services:
        lines.append(f"      {service}:")
        lines.append(f"        condition: service_healthy")
    return "\n" + "\n".join(lines)


COMPOSE_TEMPLATE = """# Auto-generated from scenario.toml
# MedAgentBench AgentBeats Leaderboard

services:
  green-agent:
    image: {green_image}
    platform: linux/amd64
    container_name: green-agent
    command: ["--host", "0.0.0.0", "--port", "{green_port}", "--card-url", "http://green-agent:{green_port}"]
    environment:{green_env}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{green_port}/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    depends_on:{green_depends}
    networks:
      - agent-network

{participant_services}  fhir-server:
    image: jyxsu6/medagentbench:latest
    platform: linux/amd64
    container_name: medagentbench-fhir
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/fhir/metadata"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 60s
    networks:
      - agent-network

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    platform: linux/amd64
    container_name: agentbeats-client
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./results:/app/output
    working_dir: /app
    command: ["scenario.toml", "output/results.json"]
    depends_on:{client_depends}
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
"""

PARTICIPANT_TEMPLATE = """  {name}:
    image: {image}
    platform: linux/amd64
    container_name: {name}
    command: ["--host", "0.0.0.0", "--port", "{port}", "--card-url", "http://{name}:{port}"]
    environment:{env}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{port}/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    networks:
      - agent-network

"""

A2A_SCENARIO_TEMPLATE = """# Auto-generated A2A scenario configuration
# MedAgentBench Assessment

[green_agent]
endpoint = "http://green-agent:{green_port}"

{participants}
{config}"""


def generate_docker_compose(scenario: dict[str, Any]) -> str:
    """Generate docker-compose.yml content."""
    green = scenario["green_agent"]
    participants = scenario.get("purple_agent", [])

    participant_names = [p["name"] for p in participants]

    participant_services = "".join([
        PARTICIPANT_TEMPLATE.format(
            name=p["name"],
            image=p["image"],
            port=PARTICIPANT_START_PORT + i,
            env=format_env_vars({**p.get("env", {}), "MCP_FHIR_API_BASE": "http://medagentbench-fhir:8080/fhir/"})
        )
        for i, p in enumerate(participants)
    ])

    all_services = ["green-agent", "fhir-server"] + participant_names

    # Handle case with no participants
    green_depends = format_depends_on(participant_names + ["fhir-server"]) if participant_names else format_depends_on(["fhir-server"])

    return COMPOSE_TEMPLATE.format(
        green_image=green["image"],
        green_port=DEFAULT_PORT,
        green_env=format_env_vars(green.get("env", {})),
        green_depends=green_depends,
        participant_services=participant_services,
        client_depends=format_depends_on(all_services)
    )


def generate_a2a_scenario(scenario: dict[str, Any]) -> str:
    """Generate a2a-scenario.toml content."""
    participants = scenario.get("purple_agent", [])

    participant_lines = []
    for i, p in enumerate(participants):
        lines = [
            f"[[participants]]",
            f'role = "{p["name"]}"',
            f'endpoint = "http://{p["name"]}:{PARTICIPANT_START_PORT + i}"',
        ]
        if p.get("agentbeats_id"):
            lines.append(f'agentbeats_id = "{p["agentbeats_id"]}"')
        participant_lines.append("\n".join(lines) + "\n")

    config_section = scenario.get("config", {})
    config_lines = [tomli_w.dumps({"config": config_section})]

    return A2A_SCENARIO_TEMPLATE.format(
        green_port=DEFAULT_PORT,
        participants="\n".join(participant_lines),
        config="\n".join(config_lines)
    )


def generate_env_file(scenario: dict[str, Any]) -> str:
    """Generate .env.example file with required secrets."""
    green = scenario["green_agent"]
    participants = scenario.get("purple_agent", [])

    secrets = set()

    # Extract secrets from ${VAR} patterns in env values
    env_var_pattern = re.compile(r'\$\{([^}]+)\}')

    for value in green.get("env", {}).values():
        for match in env_var_pattern.findall(str(value)):
            secrets.add(match)

    for p in participants:
        for value in p.get("env", {}).values():
            for match in env_var_pattern.findall(str(value)):
                secrets.add(match)

    if not secrets:
        return ""

    lines = []
    for secret in sorted(secrets):
        lines.append(f"{secret}=")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate Docker Compose from scenario.toml")
    parser.add_argument("--scenario", type=Path, default=Path("scenario.toml"))
    args = parser.parse_args()

    if not args.scenario.exists():
        print(f"Error: {args.scenario} not found", file=sys.stderr)
        sys.exit(1)

    scenario = parse_scenario(args.scenario)

    with open(COMPOSE_PATH, "w") as f:
        f.write(generate_docker_compose(scenario))

    with open(A2A_SCENARIO_PATH, "w") as f:
        f.write(generate_a2a_scenario(scenario))

    env_content = generate_env_file(scenario)
    if env_content:
        with open(ENV_PATH, "w") as f:
            f.write(env_content)
        print(f"Generated {ENV_PATH}")

    print(f"Generated {COMPOSE_PATH} and {A2A_SCENARIO_PATH}")


if __name__ == "__main__":
    main()