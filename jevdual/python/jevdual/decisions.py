"""Optional, text-only Decisions shadow transport; never dispatches an action.

The native scores are retained without converting provider confidence to probability.
This module has no dependency on the Jev/TypeSafe contract or runtime factories.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

ENDPOINT = "https://api.openai.com/v1/decisions"
MODEL = "gpt-6-luna"
MAX_BODY_BYTES = 24_000
DISTRIBUTION_TOLERANCE = 0.02


@dataclass(frozen=True)
class PredicateQuestion:
    name: str
    instructions: str


@dataclass(frozen=True)
class ChoiceQuestion:
    name: str
    instructions: str
    choices: Mapping[str, str]


@dataclass(frozen=True)
class ScoreQuestion:
    name: str
    instructions: str
    levels: Mapping[str, str]


@dataclass(frozen=True)
class PredicateAnswer:
    name: str
    probability: float


@dataclass(frozen=True)
class ChoiceAnswer:
    """Discrete probability distribution and the provider's separate native confidence."""

    name: str
    choice: str
    probabilities: Mapping[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreAnswer:
    """Expected ordinal index; neither this score nor confidence is a predicate."""

    name: str
    score: float
    probabilities: Mapping[int, float]
    confidence: float


Question = PredicateQuestion | ChoiceQuestion | ScoreQuestion | Mapping[str, Any]
Answer = PredicateAnswer | ChoiceAnswer | ScoreAnswer


@dataclass(frozen=True)
class DecisionBatch:
    model: str
    answers: Mapping[str, Answer]
    input_tokens: int | None
    raw: Mapping[str, Any]
    latency_s: float


class DecisionsError(Exception):
    """Safe diagnostic code plus separately retained JSON receipt, when available.

    The receipt can contain evidence and must be redacted before publication. It is
    deliberately omitted from exception messages and reprs, as are HTTP error bodies.
    """

    def __init__(self, code: str, *, input_tokens: int | None = None, raw: Mapping | None = None):
        super().__init__(f"Decisions request failed: {code}")
        self.code = code
        self.input_tokens = input_tokens
        self.raw = raw


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise DecisionsError(code)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def serialize_questions(questions: Sequence[Question]) -> list[dict[str, Any]]:
    """Validate and serialize a nonempty question batch with distinct names."""
    _require(isinstance(questions, Sequence) and not isinstance(questions, (str, bytes)), "questions")
    _require(bool(questions), "questions")
    serialized = []
    names: set[str] = set()
    for question in questions:
        if isinstance(question, PredicateQuestion):
            item = {"type": "predicate", "name": question.name, "instructions": question.instructions}
        elif isinstance(question, ChoiceQuestion):
            _require(isinstance(question.choices, Mapping), "question_options")
            item = {
                "type": "choice", "name": question.name, "instructions": question.instructions,
                "choices": [{"value": value, "description": desc} for value, desc in question.choices.items()],
            }
        elif isinstance(question, ScoreQuestion):
            _require(isinstance(question.levels, Mapping), "question_options")
            item = {
                "type": "score", "name": question.name, "instructions": question.instructions,
                "levels": [{"label": label, "description": desc} for label, desc in question.levels.items()],
            }
        else:
            _require(isinstance(question, Mapping), "question_type")
            item = dict(question)
        kind = item.get("type")
        _require(kind in ("predicate", "choice", "score"), "question_type")
        allowed = {"type", "name", "instructions"}
        if kind != "predicate":
            allowed.add("choices" if kind == "choice" else "levels")
        _require(set(item) == allowed, "question_fields")
        _require(_text(item.get("name")) and _text(item.get("instructions")), "question_text")
        _require(item["name"] not in names, "duplicate_question_name")
        names.add(item["name"])
        if kind != "predicate":
            field, key = ("choices", "value") if kind == "choice" else ("levels", "label")
            options = item[field]
            _require(isinstance(options, list) and bool(options), "question_options")
            values: set[str] = set()
            copied = []
            for option in options:
                _require(isinstance(option, Mapping) and set(option) == {key, "description"}, "option_fields")
                _require(_text(option[key]) and _text(option["description"]), "option_text")
                _require(option[key] not in values, "duplicate_option")
                values.add(option[key])
                copied.append(dict(option))
            item[field] = copied
        serialized.append(item)
    return serialized


def request_body(input: str, questions: Sequence[Question], model: str = MODEL) -> bytes:
    """Canonical bounded UTF-8 request bytes, usable for preregistered hashes."""
    _require(isinstance(input, str), "text_input_required")
    _require(model == MODEL, "unsupported_model")
    serialized = serialize_questions(questions)
    try:
        body = json.dumps(
            {"model": model, "input": input, "questions": serialized},
            ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        ).encode("utf-8")
    except (ValueError, UnicodeError):
        raise DecisionsError("request_encoding") from None
    _require(len(body) <= MAX_BODY_BYTES, "request_too_large")
    return body


def _number(value: Any, low: float, high: float, code: str) -> float:
    _require(type(value) in (float, int), code)
    _require(low <= value <= high and math.isfinite(value), code)
    return float(value)


def _distribution(entries: Any, expected: Sequence[str | int], *, labels: list[str] | None = None) -> dict:
    _require(isinstance(entries, list) and len(entries) == len(expected), "distribution_options")
    values = {}
    for entry in entries:
        _require(isinstance(entry, dict), "distribution_entry")
        value = entry.get("value")
        _require(type(value) is type(expected[0]) and value in expected and value not in values,
                 "distribution_options")
        if labels is not None:
            _require(entry.get("label") == labels[value], "score_label")
        values[value] = _number(entry.get("probability"), 0, 1, "probability")
    _require(abs(sum(values.values()) - 1) <= DISTRIBUTION_TOLERANCE + 1e-12, "distribution_sum")
    return values


def _usage(raw: Mapping[str, Any]) -> int | None:
    usage = raw.get("usage")
    if usage is None:
        return None
    _require(isinstance(usage, dict), "usage")
    value = usage.get("input_tokens")
    if value is None:
        return None
    _require(type(value) is int and value >= 0, "usage")
    return value


def _parse(raw: Any, questions: list[dict], latency_s: float) -> DecisionBatch:
    _require(isinstance(raw, dict), "response_object")
    tokens = None
    try:
        tokens = _usage(raw)
        _require(_text(raw.get("model")), "response_model")
        answers = raw.get("answers")
        _require(isinstance(answers, list) and len(answers) == len(questions), "answer_set")
        expected = {item["name"]: item for item in questions}
        parsed = {}
        for answer in answers:
            _require(isinstance(answer, dict), "answer_object")
            name = answer.get("name")
            _require(isinstance(name, str) and name in expected and name not in parsed, "answer_set")
            question = expected[name]
            kind = answer.get("type")
            _require(kind != "refusal", "refusal")
            _require(kind == question["type"], "answer_type")
            if kind == "predicate":
                parsed[name] = PredicateAnswer(name, _number(answer.get("probability"), 0, 1, "probability"))
            elif kind == "choice":
                options = [item["value"] for item in question["choices"]]
                probabilities = _distribution(answer.get("probabilities"), options)
                choice = answer.get("choice")
                _require(isinstance(choice, str) and choice in probabilities, "choice")
                _require(probabilities[choice] >= max(probabilities.values()) - 1e-9, "choice_argmax")
                parsed[name] = ChoiceAnswer(
                    name, choice, probabilities, _number(answer.get("confidence"), 0, 1, "confidence")
                )
            else:
                labels = [item["label"] for item in question["levels"]]
                probabilities = _distribution(answer.get("probabilities"), list(range(len(labels))), labels=labels)
                score = _number(answer.get("score"), 0, len(labels) - 1, "score")
                expected_score = sum(index * probability for index, probability in probabilities.items())
                _require(abs(score - expected_score) <= 0.02 + 1e-12, "score_expectation")
                parsed[name] = ScoreAnswer(
                    name, score, probabilities, _number(answer.get("confidence"), 0, 1, "confidence")
                )
        return DecisionBatch(raw["model"], parsed, tokens, raw, latency_s)
    except DecisionsError as error:
        raise DecisionsError(error.code, input_tokens=tokens, raw=raw) from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    obj = {}
    for key, value in pairs:
        _require(key not in obj, "duplicate_json_key")
        obj[key] = value
    return obj


class DecisionsClient:
    """One request per call, standard endpoint only, with no retries or redirects."""

    def __init__(self, api_key: str, *, model: str = MODEL,
                 transport: httpx.AsyncBaseTransport | None = None, timeout: float = 60):
        _require(_text(api_key), "api_key_required")
        _require(model == MODEL, "unsupported_model")
        _require(type(timeout) in (int, float) and 0 < timeout <= 60 and math.isfinite(timeout), "timeout")
        self._api_key = api_key
        self.model = model
        self._transport = transport
        self._timeout = timeout

    async def decide(self, input: str, questions: Sequence[Question]) -> DecisionBatch:
        body = request_body(input, questions, self.model)
        serialized = json.loads(body)["questions"]
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self._timeout, follow_redirects=False, trust_env=False,
            ) as client:
                response = await client.post(ENDPOINT, content=body, headers={
                    "Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
                })
        except httpx.RequestError:
            raise DecisionsError("network") from None
        if not 200 <= response.status_code < 300:
            raise DecisionsError(f"http_{response.status_code}")
        try:
            raw = json.loads(response.content, object_pairs_hook=_unique_object)
        except (ValueError, UnicodeError):
            raise DecisionsError("invalid_json") from None
        return _parse(raw, serialized, time.perf_counter() - started)
