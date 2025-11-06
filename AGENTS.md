# Repository Guidelines

## Project Structure & Module Organization
- `docker-compose.yml` orchestrates local services (`db`, `tryton`). Use it during development; staging uses `docker-compose-staging.yml`.
- `docker/Dockerfile` extends `tryton/tryton:7.6` and copies local modules plus `config/trytond.conf`. Update it when adding Python dependencies.
- Place custom Tryton modules under `tryton/modules/<module_name>`. Each module should contain `__init__.py`, `__manifest__.py`, models, views, and an optional `tests/` package.
- Shared configuration lives in `config/`, currently only `trytond.conf`. Keep secrets out of version control and inject them through environment variables.

## Build, Test, and Development Commands
- Start the stack: `docker compose up --build` (rebuilds the image, provisions Postgres, and exposes Tryton on `http://localhost:8000`).
- Update modules or run admin tasks: `docker compose run --rm tryton trytond-admin -c /etc/tryton/trytond.conf --update=<module>`.
- Open an interactive shell for debugging: `docker compose exec tryton bash`.
- Reset the database for a clean slate: `docker compose down -v` (drops volumes; use with care).

## Coding Style & Naming Conventions
- Write Python with 4-space indents, descriptive snake_case names, and docstrings where business rules are non-obvious.
- Follow Tryton module conventions: model classes end with `*Mixin` or `*Model`, XML identifiers use `module.record_name`.
- Prefer domain-specific comments over generic ones; keep translation strings in English.
- Apply SOLID principles (single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion) when structuring Python and Tryton code.

## Testing Guidelines
- Create tests in `tryton/modules/<module>/tests/test_*.py` using `trytond.tests.test_tryton` helpers.
- Run the suite with `docker compose run --rm tryton python -m unittest discover -s /opt/trytond/modules/<module>/tests`.
- Include regression tests for every bug fix and keep fixtures minimal; favor Tryton's `with_transaction()` context for database setup.
- Target meaningful coverage (no hard percentage target yet); document gaps in the PR if coverage is limited.

### Automated Testing Strategy
- Extend each module test package with focused unit scenarios that cover core business validations, computed fields, and model behaviors; isolate cases with `with_transaction()`.
- Add integration coverage via `trytond.tests.test_tryton.ModuleTestCase` to ensure module activation, dependency glue, and registered records (menus, actions, groups) work together.
- Capture every bug fix with a regression test that reproduces the original failure and asserts the intended outcome.
- Verify access controls when updating `ir.model.access` or security-critical workflows by asserting expected read/write permissions.
- Keep a smoke-test entry point (`docker compose run --rm tryton python -m unittest discover …`) in CI to run the full module suites on every PR.

## Commit & Pull Request Guidelines
- Use short, imperative commit subjects (`add port 8000`, `install ssl`) with optional body explaining context or rollback steps.
- Rebase before opening a PR, ensure the branch passes `docker compose` smoke checks, and link to the associated issue or ticket.
- PR descriptions should summarize the business goal, list key changes, note schema or migration impacts, and include screenshots for UI-facing updates.
- Request at least one reviewer familiar with the affected module; capture follow-up tasks as checklist items in the PR.

## Security & Configuration Tips
- Rotate credentials set in `docker-compose-staging.yml` (e.g., `TRYTON_ADMIN_PASSWORD`) through your deployment secrets manager; never rely on committed defaults in production.
- Keep production overrides in environment files managed outside the repository, and audit mounted volumes (`tryton_filestore`, `db_data`) when handling customer data.

## Documentation Workflow
- Se referer a `docs/documentation-plan.md` avant chaque tache pour identifier les sections cibles (developpement, guides utilisateurs, runbooks, qualite).
- Initialiser ou completer les journaux de tache dans `docs/taches/<ID>/` a l'aide des gabarits du dossier `docs/templates/`.
- Noter dans le journal d'implementation et la note finale de tache quelles pieces de documentation ont ete mises a jour ou restent a produire.
