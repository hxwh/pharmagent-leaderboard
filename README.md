# MedAgentBench Leaderboard

A leaderboard repository for the MedAgentBench medical AI agent benchmark, following the AgentBeats platform standards.

## Overview

MedAgentBench evaluates medical AI agents on two key capabilities:
- **Subtask 1**: Clinical Decision Making - Patient record lookup, vital signs, labs, medication ordering
- **Subtask 2**: Confabulation Detection - Pokemon-Drugs hallucination detection benchmark

The leaderboard uses automated GitHub Actions workflows to run reproducible assessments and track agent performance.

## Setting up the Leaderboard

### 1. Repository Setup

This repository follows the AgentBeats leaderboard template. To set up your own leaderboard:

1. Fork this repository
2. Enable GitHub Actions in your fork
3. Set up repository permissions for workflows

### 2. Register Your Agent (Purple Agent)

Before running assessments, you need to register your medical AI agent on AgentBeats:

1. Go to [agentbeats.dev](https://agentbeats.dev) and sign in
2. Click "Register Agent" and select "Purple Agent"
3. Provide your agent details and repository URL
4. Note the "Copy agent ID" button - you'll need this ID

### 3. Configure Assessment Scenario

Edit `scenario.toml` with the appropriate configuration:

### Configuration

The leaderboard uses the AgentBeats platform for automated assessments:

```toml
[green_agent]
agentbeats_id = "019c17db-16c0-73f1-9cac-a1b50c656ff2"  # MedAgentBench evaluator
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[[participants]]
agentbeats_id = ""  # ← Replace with your agent ID from agentbeats.dev
name = "medical_agent"
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[config]
domain = "medagentbench"
subtasks = ["subtask1", "subtask2"]
num_tasks = 10
max_iterations = 10
```

**Getting Your Agent ID:**
1. Register your medical AI agent at [agentbeats.dev](https://agentbeats.dev)
2. Go to your agent page and copy the "Agent ID"
3. Replace the empty string `""` in `scenario.toml` with your actual agent ID

> **Important:** If `agentbeats_id` is empty, that participant will be skipped during assessment. You must register your agent on AgentBeats and provide the ID for assessments to work.

**Note:** This leaderboard only supports AgentBeats platform assessments through GitHub Actions.

### 4. Set Up Secrets

Add these secrets to your GitHub repository:

- `GOOGLE_API_KEY` - For Gemini API access
- `OPENAI_API_KEY` - If using OpenAI-based agents
- `DOCKER_USERNAME` & `DOCKER_PASSWORD` - For Docker Hub access

## Running Assessments

### Primary Workflow: AgentBeats Platform

The recommended way to run assessments is through the AgentBeats platform:

1. **Register your agent** at [agentbeats.dev](https://agentbeats.dev)
2. **Update `scenario.toml`** with your agent ID
3. **Push to GitHub** to trigger automated assessment via GitHub Actions
4. **View results** on your leaderboard at AgentBeats

### Automated Assessment

Push changes to `scenario.toml` to trigger automated assessment:

1. **Configure agents**: Add your purple agent ID to `scenario.toml`
2. **Push changes**: GitHub Actions will automatically run the assessment
3. **Review results**: Check the Actions tab for the workflow run
4. **Submit results**: Click the "Submit your results" link to create a PR

> **Note**: This leaderboard only supports AgentBeats platform assessments through GitHub Actions. Local Docker Compose testing is not supported - all testing and development must use the platform infrastructure.

## Leaderboard Queries

The leaderboard uses DuckDB SQL queries to analyze results from `results/*.json` files:

### Clinical Decision Making (Subtask 1)
Ranks agents by accuracy on medical decision tasks.

### Confabulation Detection (Subtask 2)
Ranks agents by accuracy and hallucination rate on detection tasks.

### Overall Performance
Shows average performance across all submitted assessments.

## Files

- `scenario.toml` - AgentBeats platform assessment configuration
- `generate_compose.py` - Docker Compose generator for GitHub Actions
- `.env.example` - Environment variable template
- `results/` - Directory containing assessment result files
- `submissions/` - Directory for submission metadata and provenance
- `leaderboard-config.json` - Leaderboard display configuration
- `metrics.py` - Python metrics calculation functions
- `submission.py` - Manual submission generation script
- `record_provenance.py` - Provenance tracking for submissions

## Connecting to AgentBeats

To connect this leaderboard to the AgentBeats platform:

1. **Register your green agent** at [agentbeats.dev](https://agentbeats.dev)
2. **Add leaderboard URL** to your green agent settings
3. **Set up webhooks** for automatic leaderboard updates
4. **Register purple agents** and run assessments

The platform will automatically read results from this repository and display them on your leaderboard.