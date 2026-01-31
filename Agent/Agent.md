## Agent Description

### Agent Action Workflow

#### Simulation Initialization Phase

- Load and verify simulation settings from configuration files
- Confirm game rules
- Initialize the simulation state based on parameters defined in the configuration files

#### Trading Phase

##### Initial Information Gathering

- The system broadcasts the latest market information (e.g., news)
  - Agents may consult specialized expert models for professional analysis
- Retrieve current futures market information
- Retrieve the current account status

The latter two components are updated on a per-round basis and are cleared after each trading round.

##### i-th Bidding Round (i = 1–5)

- Determine the trading strategy
- Refine the strategy with the assistance of expert models
- Submit trading orders
- Execute order matching
- Confirm execution results
- Update account balances
- Decide whether to cancel remaining orders

##### End-of-Round Phase

- Aggregate all executed trades
- Compute the daily settlement price
- Perform margin checks
- Update account-related states

---

## Class Inheritance Structure

- `chat_volc.ChatBasicVolc`  
  Dialogue interface class responsible for interactions between agents and large language models.

- `agent.AgentBasic`  
  Base class providing fundamental agent functionalities, including dialogue handling, logging, and configuration management.
  - `players.Player`  
    Abstract player class implementing shared behaviors such as action extraction, context truncation, and interaction with the simulation engine.
    - `players.QingShanPlayer` — Tsingshan
    - `players.GlencorePlayer` — Glencore
    - `players.OrdinaryPlayer` — Ordinary market participants

---

## File Organization

### Configuration Files

- `./configs/*.json`
  These files define global simulation parameters, including large language model configurations, logging paths, and initial capital allocations.
  Subdirectories named HET({i}) correspond to heterogeneous experimental settings. Each HET({i}) folder contains information for heterogeneous agents, excluding Tsingshan and Glencore, whose configurations remain fixed across experiments.
- `./profiles/*.txt` (Agent Persona Files)
  This directory contains the system personas (system prompts) for each agent, which specify their behavioral characteristics, decision-making styles, and role-specific constraints during the simulation.
- `./templates/*.txt` (Prompt Templates)
  This directory stores unified prompt templates shared across agents.Subdirectories contain specialized prompts designed for specific roles or tasks.
