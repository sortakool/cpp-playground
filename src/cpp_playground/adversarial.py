from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from .common import print_json


@dataclass(frozen=True, slots=True)
class Perspective:
    name: str
    priority: str
    rationale: str


SELECTIONS: dict[str, list[Perspective]] = {
    "technical": [
        Perspective(
            "devils-advocate",
            "high",
            "Challenge architecture and technology choices.",
        ),
        Perspective(
            "assumption-buster",
            "high",
            "Stress hidden scalability and dependency assumptions.",
        ),
        Perspective("red-team", "medium", "Assess exposed attack surface and unsafe defaults."),
        Perspective("trust-but-verify", "medium", "Validate benchmark and capability claims."),
        Perspective("white-hat", "context", "Add defensive guidance when security is material."),
    ],
    "product": [
        Perspective(
            "devils-advocate",
            "high",
            "Challenge market-fit and prioritization claims.",
        ),
        Perspective("assumption-buster", "high", "Pressure-test user-behavior assumptions."),
        Perspective("trust-but-verify", "medium", "Validate customer or market evidence."),
        Perspective("red-team", "medium", "Assess competitive or abuse risks."),
        Perspective("white-hat", "context", "Harden sensitive user journeys."),
    ],
    "security": [
        Perspective("red-team", "high", "Model attacks and identify exploit paths."),
        Perspective("white-hat", "high", "Design defenses and compensating controls."),
        Perspective("assumption-buster", "medium", "Break optimistic security assumptions."),
        Perspective(
            "trust-but-verify",
            "medium",
            "Verify control effectiveness with evidence.",
        ),
        Perspective("devils-advocate", "context", "Challenge architecture tradeoffs."),
    ],
    "process": [
        Perspective("devils-advocate", "high", "Challenge efficiency and coordination claims."),
        Perspective("assumption-buster", "high", "Probe brittle operational assumptions."),
        Perspective("trust-but-verify", "medium", "Verify claimed process outcomes."),
        Perspective("red-team", "medium", "Assess misuse and failure modes."),
        Perspective("white-hat", "context", "Add resilience and guardrails."),
    ],
    "risk": [
        Perspective("assumption-buster", "high", "Identify hidden failure conditions."),
        Perspective("trust-but-verify", "high", "Verify the evidence behind risk claims."),
        Perspective("devils-advocate", "medium", "Challenge ranking and mitigation choices."),
        Perspective("red-team", "medium", "Model adversarial escalation paths."),
        Perspective("white-hat", "context", "Design prevention or containment controls."),
    ],
}


STAKE_HINTS = {
    "low": "Use the two primary perspectives first.",
    "medium": "Use primary plus one secondary perspective.",
    "high": "Use primary and secondary perspectives, then add the context-dependent lens.",
}


def normalize_context(value: str) -> str:
    key = value.strip().lower().replace("_", "-")
    aliases = {
        "technical-decision": "technical",
        "architecture": "technical",
        "product-decision": "product",
        "feature": "product",
        "security-assessment": "security",
        "pentest": "security",
        "process-design": "process",
        "operational": "process",
        "risk-assessment": "risk",
        "general": "technical",
    }
    return aliases.get(key, key)


def select_perspectives(context: str, specifics: str, stakes: str) -> dict[str, Any]:
    normalized = normalize_context(context)
    if normalized not in SELECTIONS:
        choices = ", ".join(sorted(SELECTIONS))
        raise SystemExit(f"unsupported context {context!r}; expected one of: {choices}")
    stakes_key = stakes.strip().lower()
    if stakes_key not in STAKE_HINTS:
        raise SystemExit("unsupported stakes value; expected: low, medium, high")
    perspectives = SELECTIONS[normalized]
    return {
        "context": normalized,
        "requested_context": context,
        "specifics": specifics,
        "stakes": stakes_key,
        "guidance": STAKE_HINTS[stakes_key],
        "perspectives": [
            {
                "name": item.name,
                "priority": item.priority,
                "rationale": item.rationale,
            }
            for item in perspectives
        ],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Adversarial helper commands.")
    subparsers = root.add_subparsers(dest="command", required=True)

    select_parser = subparsers.add_parser(
        "select-perspectives",
        help="Recommend adversarial perspectives for a decision context.",
    )
    select_parser.add_argument("context")
    select_parser.add_argument("specifics", nargs="?", default="")
    select_parser.add_argument("--stakes", default="medium", choices=["low", "medium", "high"])
    select_parser.add_argument("--json", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = select_perspectives(args.context, args.specifics, args.stakes)
    if args.json:
        print_json(result)
    else:
        print("Adversarial Thinking Perspective Selection")
        print("------------------------------------------")
        print(f"Context: {result['context']}")
        if result["specifics"]:
            print(f"Specifics: {result['specifics']}")
        print(f"Stakes: {result['stakes']}")
        print(f"Guidance: {result['guidance']}")
        print()
        for item in result["perspectives"]:
            print(f"- {item['name']} [{item['priority']}]")
            print(f"  {item['rationale']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
