# Gemini Skill

An Alexa skill that bridges voice queries to [Google Gemini](https://ai.google.dev/) (`gemini-1.5-flash`), deployed as a serverless endpoint on [Modal](https://modal.com).

## How It Works

```
User → "Alexa, open gemini" → Alexa → Modal endpoint → Gemini API → spoken response
```

1. **You speak** a question to your Echo device (or the Alexa test simulator).
2. **Alexa** matches your utterance to the `GeminiQueryIntent` and extracts your question via the `AMAZON.SearchQuery` slot.
3. **Modal** receives the Alexa JSON request, dispatches it through `ask-sdk-core` handlers, and calls the Gemini API.
4. **Gemini** returns a text response, which is wrapped in an Alexa response envelope and spoken back to you.

The skill uses `gemini-1.5-flash` specifically for its low latency — Alexa enforces a hard **10-second timeout** on skill responses.

## Setup

### 1. Create the Modal secret

The skill expects a Modal secret named `gemini-api-key` containing your Google AI API key:

```bash
modal secret create gemini-api-key GEMINI_API_KEY=<your-key>
```

You can get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 2. Deploy

From the repo root:

```bash
uv run modal deploy gemini-skill/backend/main.py
```

### 3. Configure Alexa

See the [main README](../README.md#3-alexa-developer-console) for Alexa Developer Console setup. Use the interaction model at:

```
gemini-skill/skill-package/interactionModels/custom/en-US.json
```

The invocation name is **"gemini"**.

## Usage Examples

| You say | What happens |
|---|---|
| *"Alexa, open gemini"* | Launches the skill with a welcome greeting. |
| *"Ask, what is the speed of light?"* | Sends "what is the speed of light?" to Gemini and speaks the answer. |
| *"Tell me, how does photosynthesis work?"* | Sends "how does photosynthesis work?" to Gemini. |
| *"Search for, the capital of France"* | Sends "the capital of France" to Gemini. |
| *"Help"* | Returns a help message with example usage. |
| *"Stop"* / *"Cancel"* | Ends the session. |

> **Note:** Because the `question` slot uses `AMAZON.SearchQuery`, utterances require a carrier phrase (e.g. "ask", "tell me", "search for") before the freeform question. You cannot say just the question by itself.

## Supported Intents

- **`LaunchRequest`** — greeting when the skill is opened
- **`GeminiQueryIntent`** — forwards a freeform question to Gemini
- **`AMAZON.HelpIntent`** — usage help
- **`AMAZON.CancelIntent` / `AMAZON.StopIntent`** — exit (handled by `shared/alexa_utils.py`)
- **`SessionEndedRequest`** — cleanup (handled by `shared/alexa_utils.py`)

## File Structure

```
gemini-skill/
├── backend/
│   ├── main.py              # Modal + FastAPI endpoint, Gemini integration
│   └── requirements.txt     # Pinned deps (also in root pyproject.toml)
└── skill-package/
    └── interactionModels/
        └── custom/
            └── en-US.json   # Alexa interaction model
```
