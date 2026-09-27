from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import pytest

from prd_workflow.ai import (
    canonical_schema_json,
    generated_strict_schema,
    load_committed_schema,
    load_prompt,
    schema_resource,
)
from prd_workflow.canonical import load_canonical_template


OPERATIONS_AND_ASSETS = {
    "intake": ("intake.md", "intake.schema.json"),
    "derive_domain": ("domain.md", "domain.schema.json"),
    "derive_capabilities": ("capabilities.md", "capabilities.schema.json"),
    "derive_architecture": ("architecture.md", "architecture.schema.json"),
    "review_convergence": ("convergence.md", "convergence.schema.json"),
    "compose_canonical": ("canonical-compose.md", "canonical-prd.schema.json"),
    "audit_canonical": ("canonical-audit.md", "canonical-audit.schema.json"),
}


def test_prompt_assets_are_package_readable_and_preserve_operation_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts = {operation: load_prompt(operation) for operation in OPERATIONS_AND_ASSETS}
    package = resources.files("prd_workflow")

    for operation, prompt in prompts.items():
        prompt_resource = package.joinpath(
            "prompts", OPERATIONS_AND_ASSETS[operation][0]
        )
        assert prompt_resource.is_file()
        assert prompt_resource.read_text(encoding="utf-8") == prompt
        assert prompt
        assert "Source PRD" in prompt
        assert "Human Decision" in prompt
        assert "Authority" in prompt
        assert "AI recommendation" in prompt
        assert "Use only the supplied payload as input." in prompt
        assert "Do not use external information or unstated assumptions." in prompt
        assert "Authority status within the payload is defined below." in prompt
        assert "return one json value matching the output schema" in prompt.lower()
        assert "docs/" not in prompt

    assert "material ambiguity" in prompts["intake"]
    assert "AI recommendations are never Authority" in prompts["intake"]
    assert "workflow interprets the draft as a pending INTAKE-origin" in prompts["intake"]
    assert "exactly one concrete non-compound question" in prompts["intake"]
    assert "2-4 plausible materially distinct options" in prompts["intake"]
    assert "no Human Answer or deferral fields" in prompts["intake"]
    assert "Use business language" in prompts["derive_domain"]
    assert "Do not invent technical entities" in prompts["derive_domain"]
    assert "what the product must do" in prompts["derive_capabilities"]
    assert "Every returned Capability requires" in prompts["derive_capabilities"]
    assert "release_status = IN | PARTIAL | OUT | FUTURE" in prompts["derive_capabilities"]
    assert "Never guess release scope" in prompts["derive_capabilities"]
    assert "downstream Feature decomposition" in prompts["derive_capabilities"]
    assert "displaying, using, or transmitting" in prompts["derive_architecture"]
    assert "workflow classifies every such draft as DEFERRED" in prompts[
        "derive_architecture"
    ]
    assert "The subsequent Convergence Review is responsible" in prompts[
        "derive_architecture"
    ]
    assert "Return outcome REMODEL" in prompts["review_convergence"]
    assert "Return outcome HUMAN_DECISION" in prompts["review_convergence"]
    assert "recommendation is advisory" in prompts["review_convergence"]
    assert "earliest consequential blocking question" in prompts["review_convergence"]
    assert "Prohibited composition" in prompts["compose_canonical"]
    assert "answer a Material Unknown" in prompts["compose_canonical"]
    assert "accepted Human Decision takes precedence" in prompts["compose_canonical"]
    assert "fresh independent Canonical Audit" in prompts["audit_canonical"]
    assert "With ONLY this exact Canonical Markdown" in prompts["audit_canonical"]
    assert "If NO, Audit cannot PASS" in prompts["audit_canonical"]
    assert "explicitly superseded, narrowed, or qualified" in prompts[
        "audit_canonical"
    ]
    assert "Audit CURRENT Active Authority" in prompts["audit_canonical"]


def test_committed_schemas_match_current_pydantic_strict_types() -> None:
    for operation, (_, expected_filename) in OPERATIONS_AND_ASSETS.items():
        resource = schema_resource(operation)
        committed_text = resource.read_text(encoding="utf-8")

        assert resource.name == expected_filename
        assert load_committed_schema(operation) == generated_strict_schema(operation)
        assert committed_text == canonical_schema_json(generated_strict_schema(operation))


def test_operation_schemas_expose_only_exact_provider_output_shapes() -> None:
    intake = load_committed_schema("intake")
    intake_draft = intake["$defs"]["MaterialDecisionDraft"]
    assert intake["anyOf"] == [
        {"$ref": "#/$defs/MaterialDecisionDraft"},
        {"type": "null"},
    ]
    assert set(intake_draft["properties"]) == {
        "decision_id",
        "question",
        "context",
        "options",
        "recommended_option_id",
        "recommendation_rationale",
        "supersedes_decision_id",
    }
    assert intake_draft["properties"]["options"]["minItems"] == 2
    assert intake_draft["properties"]["options"]["maxItems"] == 4
    assert "Decision" not in intake["$defs"]
    assert "HumanAnswer" not in intake["$defs"]

    domain = load_committed_schema("derive_domain")
    capabilities = load_committed_schema("derive_capabilities")
    architecture = load_committed_schema("derive_architecture")
    assert set(domain["properties"]) == {"product_context", "domain"}
    assert set(capabilities["properties"]) == {"capabilities"}
    assert set(architecture["properties"]) == {
        "architecture",
        "deferred_decisions",
    }
    deferred_draft = architecture["$defs"]["DeferredDecisionDraft"]
    assert set(deferred_draft["properties"]) == {
        "decision_id",
        "question",
        "context",
        "safe_to_defer_rationale",
        "downstream_constraints",
    }
    assert deferred_draft["properties"]["downstream_constraints"]["minItems"] == 1
    assert "Decision" not in architecture["$defs"]


@pytest.mark.parametrize(
    ("operation", "outcomes"),
    (
        ("review_convergence", {"PASS", "REMODEL", "HUMAN_DECISION"}),
        (
            "audit_canonical",
            {"PASS", "EDITORIAL", "REMODEL", "HUMAN_DECISION"},
        ),
    ),
)
def test_conditional_schemas_use_exact_outcome_discriminated_unions(
    operation: str,
    outcomes: set[str],
) -> None:
    schema = load_committed_schema(operation)

    assert schema["discriminator"]["propertyName"] == "outcome"
    assert set(schema["discriminator"]["mapping"]) == outcomes
    assert len(schema["oneOf"]) == len(outcomes)
    assert {branch["$ref"] for branch in schema["oneOf"]} == set(
        schema["discriminator"]["mapping"].values()
    )


def test_runtime_assets_remain_readable_without_repository_docs_or_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert not (tmp_path / "docs").exists()
    assert all(load_prompt(operation) for operation in OPERATIONS_AND_ASSETS)
    assert all(load_committed_schema(operation) for operation in OPERATIONS_AND_ASSETS)
    template = load_canonical_template()
    template_resource = resources.files("prd_workflow").joinpath(
        "templates", "canonical-prd.md"
    )
    assert template_resource.is_file()
    assert template_resource.read_text(encoding="utf-8") == template
    assert template.startswith("# Canonical PRD\n")
    placeholders = re.findall(r"\{\{[^{}\n]+\}\}", template)
    assert len(placeholders) == 40
    assert len(placeholders) == len(set(placeholders))
    for label in (
        "**Problem:**",
        "**Target actors:**",
        "**Target release:**",
        "**Material concepts:**",
        "**Inside the system:**",
        "**Architectural invariants:**",
        "**Fixed upstream constraints that must not be reopened:**",
    ):
        assert label in template
