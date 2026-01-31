# Engine Module Documentation

## Overview

The engine module is responsible for managing core simulation logic and database interactions. It provides foundational services such as system initialization, order processing, and account state management, serving as the execution backbone of the simulation framework.

---

## Configuration

### `config.py`

This file stores database connection parameters and SQL statements for initializing database tables.

- Database connection parameters **must be configured with valid, environment-specific values** before running the system.
- Initial table creation statements are defined to ensure the required database schema is available at startup.

---

## Database Management

### `dbmanager.py`

#### `DatabaseManager` Class

The `DatabaseManager` class provides a unified interface for basic database operations, including:

- Creating and initializing database tables
- Inserting records
- Querying records
- Updating records
- Deleting records

This class abstracts low-level database interactions and is used by higher-level components to ensure consistent and reliable data access.

---

## Engine Core

### `engine.py`

#### `Engine` Class

The `Engine` class implements the core simulation logic and acts as the central coordinator between agents and the database layer.

Key responsibilities include:

- System initialization and state setup
- Order submission and matching
- Trade execution and settlement
- Account information retrieval and updates
- Margin checks and risk-related validations
- Maintaining and updating global simulation states

The engine interacts with the database exclusively through the `DatabaseManager` interface, ensuring separation between business logic and data persistence.
