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

import json
import os
from typing import Any, Dict

import google.generativeai as genai
import modal
from fastapi import Request, Response
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import Response as AlexaResponse
from ask_sdk_model.ui import SimpleCard

# ---------------------------------------------------------------------------
# Modal app & image
# ---------------------------------------------------------------------------
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "ask-sdk-core",
    "google-generativeai",
    "fastapi",
)

app = modal.App(name="alexa-gemini-skill", image=image)

# ---------------------------------------------------------------------------
# Gemini helper
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-1.5-flash"


def _ask_gemini(question: str) -> str:
    """Send *question* to Gemini and return the text response."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(question)
    return response.text


# ---------------------------------------------------------------------------
# Alexa request handlers
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


class CancelAndStopIntentHandler(AbstractRequestHandler):
    """Handles AMAZON.CancelIntent and AMAZON.StopIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or \
               is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> AlexaResponse:
        return (
            handler_input.response_builder
            .speak("Goodbye!")
            .set_should_end_session(True)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handles SessionEndedRequest."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> AlexaResponse:
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Global exception handler – returns a friendly error to Alexa."""

    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> AlexaResponse:
        speech = "Sorry, something went wrong. Please try again later."
        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(True)
            .response
        )


# ---------------------------------------------------------------------------
# Skill builder
# ---------------------------------------------------------------------------
sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GeminiQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

skill = sb.create()


# ---------------------------------------------------------------------------
# Modal ↔ FastAPI endpoint
# ---------------------------------------------------------------------------
@app.function(secrets=[modal.Secret.from_name("gemini-api-key")])
@modal.fastapi_endpoint(method="POST")
async def alexa_handler(request: Request) -> Response:
    """Receive an Alexa request, process it through the skill, and return
    the raw JSON envelope that Alexa expects."""
    body: Dict[str, Any] = await request.json()
    alexa_response = skill.invoke(body, None)
    return Response(
        content=json.dumps(alexa_response),
        media_type="application/json",
    )
