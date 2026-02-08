"""
Alexa ↔ Gemini Bridge
=====================
A Modal endpoint that receives Alexa skill requests, extracts the user's
spoken query, forwards it to Google Gemini (gemini-1.5-flash), and returns
a well-formed Alexa JSON response.

NOTE – Alexa enforces a hard 10-second timeout on skill responses.
We use gemini-1.5-flash specifically because it is the lowest-latency
Gemini model, which keeps round-trip time well within that window.
"""

from __future__ import annotations

import os
import sys

from google import genai
import modal
from fastapi import Request, Response
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response as AlexaResponse
from ask_sdk_model.ui import SimpleCard

# Ensure the repo root is on sys.path so `shared` is importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from shared.alexa_utils import build_skill, invoke_skill  # noqa: E402

# ---------------------------------------------------------------------------
# Modal app & image
# ---------------------------------------------------------------------------
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "ask-sdk-core",
    "google-genai",
    "fastapi",
)

app = modal.App(name="alexa-gemini-skill", image=image)

# ---------------------------------------------------------------------------
# Gemini helper
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-1.5-flash"


def _ask_gemini(question: str) -> str:
    """Send *question* to Gemini and return the text response."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=question,
    )
    return response.text


# ---------------------------------------------------------------------------
# Skill-specific Alexa request handlers
# ---------------------------------------------------------------------------
class LaunchRequestHandler(AbstractRequestHandler):
    """Handles the LaunchRequest (when the user says 'Alexa, open gemini')."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> AlexaResponse:
        speech = (
            "Welcome to Gemini. You can ask me anything. "
            "For example, say: ask, what is the speed of light?"
        )
        return (
            handler_input.response_builder
            .speak(speech)
            .set_card(SimpleCard("Gemini", speech))
            .set_should_end_session(False)
            .response
        )


class GeminiQueryIntentHandler(AbstractRequestHandler):
    """Handles the GeminiQueryIntent – forwards the question to Gemini."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("GeminiQueryIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> AlexaResponse:
        slots = handler_input.request_envelope.request.intent.slots
        question: str = slots["question"].value if slots.get("question") else ""

        if not question:
            speech = "I didn't catch a question. Please try again."
        else:
            try:
                speech = _ask_gemini(question)
            except Exception as exc:
                speech = f"Sorry, I couldn't reach Gemini right now. Error: {exc}"

        return (
            handler_input.response_builder
            .speak(speech)
            .set_card(SimpleCard("Gemini", speech))
            .set_should_end_session(True)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handles AMAZON.HelpIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> AlexaResponse:
        speech = "You can ask me any question. For example: ask, what is quantum computing?"
        return (
            handler_input.response_builder
            .speak(speech)
            .set_card(SimpleCard("Gemini Help", speech))
            .set_should_end_session(False)
            .response
        )


# ---------------------------------------------------------------------------
# Build skill (common handlers are added automatically by build_skill)
# ---------------------------------------------------------------------------
skill = build_skill(
    request_handlers=[
        LaunchRequestHandler(),
        GeminiQueryIntentHandler(),
        HelpIntentHandler(),
    ],
)


# ---------------------------------------------------------------------------
# Modal ↔ FastAPI endpoint
# ---------------------------------------------------------------------------
@app.function(secrets=[modal.Secret.from_name("gemini-api-key")])
@modal.fastapi_endpoint(method="POST")
async def alexa_handler(request: Request) -> Response:
    """Receive an Alexa request, process it through the skill, and return
    the raw JSON envelope that Alexa expects."""
    return await invoke_skill(skill, request)
