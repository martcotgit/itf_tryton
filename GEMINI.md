# GEMINI.md

## Project Overview

This project is a multi-component system for "Ilnu Transforme", a company specializing in pallets. It consists of a Tryton ERP backend, a Django client portal, and a static informational website. The entire stack is containerized using Docker and managed with `docker-compose`.

### Components

*   **Tryton ERP (`/tryton`)**: The core backend for business logic and data management. It uses a PostgreSQL database. Custom modules can be found in `tryton/modules`, and various operational scripts are located in `tryton/scripts`.
*   **Client Portal (`/portal`)**: A Django-based web application that serves as the client-facing interface. It communicates with the Tryton backend via JSON-RPC calls (see `portal/apps/core/services/tryton_client.py`). It uses Redis for caching.
*   **Static Website (`/siteweb-itf`)**: A simple, responsive informational website built with HTML, CSS, and JavaScript. It is served by a dedicated Nginx container.
*   **Traefik (`/`)**: A reverse proxy that routes traffic to the appropriate service based on the requested hostname (e.g., `portal.localhost`, `tryton.localhost`).

## Building and Running

The project is managed via a combination of `make` and `docker-compose`.

### Prerequisites

*   Docker and Docker Compose

### Development Setup

The main development stack (Portal and Tryton) can be managed from the root directory.

1.  **Initial Setup**: Copy the example environment file for the portal:
    ```bash
    cp portal/.env.example portal/.env
    ```

2.  **Start the services**:
    ```bash
    make up
    ```
    *   The Django Portal will be available at `http://portal.localhost`.
    *   The Tryton ERP will be available at `http://tryton.localhost`.

3.  **Apply database migrations** for the portal:
    ```bash
    docker compose exec portal python manage.py migrate
    ```

4.  **Stop the services**:
    ```bash
    make down
    ```

### Running the Static Website

The static website is managed separately.

1.  Navigate to the website's directory:
    ```bash
    cd siteweb-itf
    ```

2.  Start the service:
    ```bash
    docker-compose up -d
    ```
    *   The site will be available at `http://localhost:8080`.

3.  Stop the service:
    ```bash
    docker-compose down
    ```

### Useful Commands

*   `make build`: Rebuild the Docker images for the main application.
*   `make portal-shell`: Open a Bash shell inside the Django portal container.
*   `make tryton-shell`: Open a Bash shell inside the Tryton container.

## Gemini Instructions

- NEVER commit any changes to the codebase.

## Development Conventions

### Testing

The Django portal uses `pytest` for testing.

*   **Run all tests**:
    ```bash
    docker compose run --rm \
      -e DJANGO_SETTINGS_MODULE=itf_portal.settings.base \
      -e DATABASE_URL=sqlite:////tmp/test-db.sqlite3 \
      portal pytest
    ```
*   The test suite is automatically run on push/pull-request to `main` or `master` branches, as defined in `.github/workflows/tests.yml`.

### Tryton Scripts

The `tryton/scripts` directory contains Python scripts that interact with Tryton using the `proteus` library. These scripts are designed to be run within the `tryton` container.

*   **Example**: To create an invoice from a sale order:
    ```bash
    docker compose run --rm tryton python3 tryton/scripts/create_invoice_from_order.py --email <customer_email>
    ```
