"""Minimal operator CLI over the persisted PRD workflow."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from prd_workflow.ai import CodexAIExecutor
from prd_workflow.canonical import final_canonical_path
from prd_workflow.models import (
    CustomAnswer,
    Decision,
    OptionSelection,
    OptionWithClarification,
    WorkflowRun,
    WorkflowState,
)
from prd_workflow.storage import FileStorage
from prd_workflow.workflow import WorkflowService


def main(argv: Sequence[str] | None = None) -> int:
    """Run one explicit operator command."""

    parser = _parser()
    arguments = parser.parse_args(argv)
    if (
        arguments.command == "answer"
        and arguments.clarification is not None
        and arguments.option is None
    ):
        parser.error("--clarification requires --option")

    storage = FileStorage()
    service = WorkflowService(storage, CodexAIExecutor())

    try:
        if arguments.command == "start":
            run = service.start(arguments.source_prd)
            _print_start(run)
        elif arguments.command == "advance":
            _print_advance(service.advance(arguments.run_id))
        elif arguments.command == "status":
            _print_status(service.status(arguments.run_id), storage)
        elif arguments.command == "answer":
            if arguments.custom is not None:
                answer = CustomAnswer(text=arguments.custom)
            elif arguments.clarification is not None:
                answer = OptionWithClarification(
                    option_id=arguments.option,
                    clarification=arguments.clarification,
                )
            else:
                answer = OptionSelection(option_id=arguments.option)
            _print_answer(
                service.answer(arguments.run_id, arguments.decision_id, answer)
            )
        elif arguments.command == "handoff":
            run = service.status(arguments.run_id)
            print(final_canonical_path(run, storage.run_directory(run.run_id)))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prd")
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="create a run from one Source PRD")
    start.add_argument("source_prd", type=Path)

    advance = commands.add_parser("advance", help="advance exactly one workflow step")
    advance.add_argument("run_id")

    status = commands.add_parser("status", help="show operator-relevant run status")
    status.add_argument("run_id")

    answer = commands.add_parser("answer", help="answer the pending Human Decision")
    answer.add_argument("run_id")
    answer.add_argument("decision_id")
    answer_form = answer.add_mutually_exclusive_group(required=True)
    answer_form.add_argument("--option", metavar="OPTION_ID")
    answer_form.add_argument("--custom", metavar="TEXT")
    answer.add_argument("--clarification", metavar="TEXT")

    handoff = commands.add_parser("handoff", help="expose the DONE Canonical PRD")
    handoff.add_argument("run_id")
    return parser


def _print_start(run: WorkflowRun) -> None:
    print(f"run_id: {run.run_id}")
    print(f"state: {run.state.value}")
    print(f"next: prd advance {run.run_id}")


def _print_advance(run: WorkflowRun) -> None:
    print(f"run_id: {run.run_id}")
    print(f"state: {run.state.value}")
    if run.state is WorkflowState.WAITING_HUMAN:
        print("outcome: Human Authority is required before the workflow can continue.")
    elif run.state is WorkflowState.DONE:
        print("outcome: Canonical PRD is ready.")
    elif run.state is WorkflowState.MODELING and run.convergence_result is not None:
        print("outcome: Modeling must be rebuilt from current Authority.")
    elif run.state is WorkflowState.MODELING:
        print("outcome: Intake is complete; modeling is ready.")
    elif run.state is WorkflowState.CANONICALIZATION and run.diagnostics:
        print("outcome: Canonical representation requires correction.")
    elif run.state is WorkflowState.CANONICALIZATION:
        print("outcome: Convergence passed; canonicalization is ready.")
    elif run.state is WorkflowState.BLOCKED:
        print("outcome: The workflow is blocked.")
    _print_findings(run)
    if run.state is WorkflowState.WAITING_HUMAN:
        _print_pending_decision(run)
    _print_next_action(run)


def _print_status(run: WorkflowRun, storage: FileStorage) -> None:
    pending = _pending_decision(run)
    print(f"run_id: {run.run_id}")
    print(f"state: {run.state.value}")
    print(f"human_decision_pending: {'yes' if pending is not None else 'no'}")
    _print_findings(run)
    if pending is not None:
        _print_decision(pending)
    if run.state is WorkflowState.DONE:
        try:
            final_canonical_path(run, storage.run_directory(run.run_id))
        except (OSError, ValueError):
            print("canonical_available: no")
        else:
            print("canonical_available: yes")
    _print_next_action(run)


def _print_answer(run: WorkflowRun) -> None:
    print(f"run_id: {run.run_id}")
    print(f"state: {run.state.value}")
    print("outcome: Human Decision accepted as Authority.")
    _print_next_action(run)


def _print_findings(run: WorkflowRun) -> None:
    findings = list(run.diagnostics)
    for result in (run.convergence_result, run.audit_result):
        if result is not None and result.status == "FAIL":
            findings.extend(result.findings)
    unique_findings = tuple(dict.fromkeys(findings))
    if unique_findings:
        print("findings:")
        for finding in unique_findings:
            print(f"  - {finding}")


def _print_pending_decision(run: WorkflowRun) -> None:
    decision = _pending_decision(run)
    if decision is None:
        raise ValueError("WAITING_HUMAN has no pending Human Decision")
    _print_decision(decision)


def _pending_decision(run: WorkflowRun) -> Decision | None:
    return next(
        (
            decision
            for decision in run.decisions
            if decision.classification == "MATERIAL" and decision.status == "PENDING"
        ),
        None,
    )


def _print_decision(decision: Decision) -> None:
    print("human_decision:")
    print(f"  decision_id: {decision.decision_id}")
    print(f"  origin_state: {decision.origin_state.value}")
    print(f"  question: {decision.question}")
    print(f"  context: {decision.context}")
    print("  options:")
    for option in decision.options:
        print(f"    {option.option_id}:")
        print(f"      text: {option.text}")
        print(f"      consequence: {option.consequence}")
    print("  RECOMMENDATION IS ADVISORY AND IS NOT THE HUMAN DECISION.")
    print(f"  advisory_recommended_option: {decision.recommended_option_id}")
    print(f"  recommendation_rationale: {decision.recommendation_rationale}")
    if decision.supersedes_decision_id is not None:
        print(f"  supersedes_decision_id: {decision.supersedes_decision_id}")


def _print_next_action(run: WorkflowRun) -> None:
    if run.state in {
        WorkflowState.INTAKE,
        WorkflowState.MODELING,
        WorkflowState.CANONICALIZATION,
    }:
        print(f"next: prd advance {run.run_id}")
    elif run.state is WorkflowState.WAITING_HUMAN:
        decision = _pending_decision(run)
        if decision is not None:
            print(f"next: prd answer {run.run_id} {decision.decision_id} ...")
    elif run.state is WorkflowState.DONE:
        print(f"next: prd handoff {run.run_id}")


if __name__ == "__main__":  # pragma: no cover - console entry point owns execution
    raise SystemExit(main())
