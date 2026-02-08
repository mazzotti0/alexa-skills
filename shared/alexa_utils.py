"""
Shared Alexa Utilities
======================
Reusable request/exception handlers, skill builder, and endpoint helpers
that any Alexa skill in this repo can import.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request, Response
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
)
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response as AlexaResponse


# ---------------------------------------------------------------------------
# Generic request handlers (identical across skills)
# ---------------------------------------------------------------------------
class CancelAndStopIntentHandler(AbstractRequestHandler):
    """Handles AMAZON.CancelIntent and AMAZON.StopIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input)
            or is_intent_name("AMAZON.StopIntent")(handler_input)
        )

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
# Skill builder helper
# ---------------------------------------------------------------------------
def build_skill(
    request_handlers: List[AbstractRequestHandler],
    exception_handlers: Optional[List[AbstractExceptionHandler]] = None,
) -> Any:
    """Build an Alexa skill from a list of *skill-specific* request handlers.

    The common handlers (CancelAndStop, SessionEnded) are appended
    automatically.  A global ``CatchAllExceptionHandler`` is added unless
    *exception_handlers* is provided.

    Returns
    -------
    The compiled skill object (result of ``SkillBuilder.create()``).
    """
    sb = SkillBuilder()

    for handler in request_handlers:
        sb.add_request_handler(handler)

    # Always append the generic handlers last so skill-specific ones
    # are matched first.
    sb.add_request_handler(CancelAndStopIntentHandler())
    sb.add_request_handler(SessionEndedRequestHandler())

    for exc_handler in (exception_handlers or [CatchAllExceptionHandler()]):
        sb.add_exception_handler(exc_handler)

    return sb.create()


# ---------------------------------------------------------------------------
# Endpoint helper
# ---------------------------------------------------------------------------
async def invoke_skill(skill: Any, request: Request) -> Response:
    """Deserialize an Alexa request, run it through *skill*, and return
    the raw JSON envelope that Alexa expects."""
    body: Dict[str, Any] = await request.json()
    alexa_response = skill.invoke(body, None)
    return Response(
        content=json.dumps(alexa_response),
        media_type="application/json",
    )
