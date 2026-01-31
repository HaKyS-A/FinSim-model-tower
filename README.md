# Model Tower: Advanced Simulation Driven by Hierarchical Model Integration for Complex Financial Systemic Projection

## Project Overview

The simulation framework is composed of three core components:

- **Simulator**: Coordinates agents and the engine to execute the full simulation process.
- **Engine**: Handles system logic, order processing, and database interactions.
- **Agents**: Represent market participants with configurable behaviors and decision-making strategies.

### `simulator.py`

#### `Simulator` Class

The `Simulator` class orchestrates the simulation workflow by coordinating interactions between the engine and multiple agents. It is responsible for:

- Initializing the simulation environment
- Invoking agent actions at each simulation stage
- Calling engine functions to process orders and update system states
- Managing the overall simulation loop

### `main.py`

The `main.py` file provides multiple entry points for running different types of experiments.  
Users can select the appropriate `main` function based on experimental requirements, including:

- Standard market simulation
- Heterogeneous agent experiments
- Futures price prediction experiments

---

## Prerequisites

Before running the simulation, the following configurations must be completed.

### Database Configuration

Update the database connection parameters in: `Engine/config.py`. Ensure that all connection fields are set to valid values for your local or remote database instance.

### Expert Model Configuration

The expert model used in the simulation is CFGPT, an open-source model.
1. Download and configure CFGPT according to its official instructions.
2. Set the correct model path in the corresponding configuration file.
3. You may freely modify, replace, or extend the expert model, provided that the associated invocation functions are updated accordingly.

### Base LLM Configuration

Base large language models are accessed via Volcengine APIs.
1. Set your API keys as required by Volcengine.
2. For custom base models, implement a new dialogue class by following the structure in `Agent/chat_volc.py` and register the new class in the agent interface.

### Running the Simulation

Once all configurations are complete, run the simulation by executing `main.py`.
You must specify:
- The output folder for dialogue logs (`folder`)
- The database name (`db_name`)
Select the appropriate main function or execution mode based on your experimental setup.