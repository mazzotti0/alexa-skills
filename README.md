# alexa-skills

A collection of Alexa skills backed by [Modal](https://modal.com) serverless endpoints.

Each skill lives in its own directory and shares common Alexa request-handling utilities from `shared/`.

## Repository Structure

```
alexa-skills/
├── shared/                  # Reusable Alexa handlers & helpers
│   ├── __init__.py
│   └── alexa_utils.py
├── gemini-skill/            # Alexa ↔ Google Gemini bridge
│   ├── backend/
│   ├── skill-package/
│   └── README.md
├── pyproject.toml
└── README.md
```

## Prerequisites

### 1. Python & uv

This project requires **Python 3.11+**. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 2. Modal

[Modal](https://modal.com) is used to deploy each skill as a serverless HTTPS endpoint.

1. **Create an account** at [modal.com](https://modal.com) (free tier available).
2. **Install & authenticate:**
   ```bash
   uv run modal setup
   ```
3. **Create secrets** for any API keys your skills need. Each skill's README will specify the required secret name and keys. Secrets are created in the [Modal dashboard](https://modal.com/secrets) or via the CLI:
   ```bash
   modal secret create <secret-name> KEY=value
   ```

### 3. Alexa Developer Console

Each skill requires a corresponding configuration in the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).

For every skill in this repo:

1. **Create a new skill** — choose "Custom" model and "Provision your own" for the backend.
2. **Set the endpoint** — under *Endpoint*, select **HTTPS** and paste the Modal endpoint URL (printed when you run `modal deploy`). Set the SSL certificate type to **"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"**.
3. **Upload the interaction model** — go to *JSON Editor* under the *Build* tab, and paste the contents of the skill's `skill-package/interactionModels/custom/en-US.json`.
4. **Build & test** — click *Build Skill*, then switch to the *Test* tab and enable testing in "Development" mode.

### 4. Deploying a Skill

From the repo root:

```bash
# Deploy (example: gemini-skill)
uv run modal deploy gemini-skill/backend/main.py
```

Modal will print the live endpoint URL — use this in the Alexa Developer Console.

## Adding a New Skill

1. Create a new directory (e.g. `my-new-skill/`) with `backend/` and `skill-package/` subdirectories.
2. In `backend/main.py`, import `build_skill` and `invoke_skill` from `shared.alexa_utils`.
3. Define only your skill-specific handlers — common handlers (Cancel, Stop, SessionEnded, exception handling) are provided automatically.
4. Create an interaction model JSON under `skill-package/interactionModels/custom/`.
5. Register the skill in the Alexa Developer Console and deploy via Modal.
