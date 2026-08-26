import argparse
import json
import sys
from pathlib import Path

import yaml

from .context import ContextProvider
from .config import Settings
from .generator import GenerationError, Generator
from .llm_client import LLMClient
from .models import PipelineResult
from .policy import validate_context
from .safety import write_audit
from .safety import state_hash
from .salt_client import SaltClient, SaltClientError
from .validator import validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="salt-assistant", description="Safe, context-aware SaltStack assistance")
    parser.add_argument("prompt", nargs="?", help="Natural-language infrastructure request")
    parser.add_argument("-t", "--target", default="*", help="Salt target expression")
    parser.add_argument("-o", "--output", type=Path, help="Write generated SLS to this path")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Preview without executing (default behavior)")
    parser.add_argument("-e", "--execute", action="store_true", help="Apply after test mode and hash confirmation")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON")
    parser.add_argument("-V", "--verbose", action="store_true")
    parser.add_argument("--audit-log", type=Path, help="Audit log path; defaults to logs/salt-assistant.log")
    return parser


def run(args: argparse.Namespace) -> int:
    if not args.prompt:
        print("A natural-language prompt is required.", file=sys.stderr)
        return 2
    try:
        settings = Settings.from_environment()
        salt_client = SaltClient(settings.salt_command, settings.salt_timeout, settings.salt_file_root, settings.salt_config_dir)
        context = ContextProvider(salt_client=salt_client).collect(args.target)
        generator = Generator(LLMClient(settings.llm_base_url, settings.llm_api_key, settings.llm_model, settings.llm_timeout))
    except (SaltClientError, ValueError) as error:
        print(f"Context collection failed: {error}", file=sys.stderr)
        return 1
    context_policy = validate_context(context, settings.max_minions_affected)
    if not context_policy.passed:
        print("Target blocked by policy:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in context_policy.errors), file=sys.stderr)
        return 1
    try:
        state, assumptions = generator.generate(args.prompt, context)
    except GenerationError as error:
        print(f"Generation blocked: {error}", file=sys.stderr)
        return 1
    validation = validate(state, args.prompt)
    status = "success" if validation.passed else "blocked"
    dry_run = {"passed": validation.passed, "minions_affected": len(context.minions), "simulated": False}
    if validation.passed:
        try:
            preview = salt_client.test_state(args.target, state)
            dry_run = {"passed": preview.passed, "minions_affected": preview.minions_affected, "simulated": False, "output": preview.output}
        except SaltClientError as error:
            validation.errors.append(f"Salt test mode failed: {error}")
            validation.passed = False
            status = "blocked"
    if validation.passed and args.execute:
        print("\nApproval required")
        print(f"Target: {args.target}")
        print(f"Resolved minions: {', '.join(context.minions)}")
        print(f"State hash: {state_hash(state)}")
        try:
            approval = input("Type the full state hash to execute: ").strip()
        except EOFError:
            approval = ""
        if approval != state_hash(state):
            dry_run["approval"] = "rejected"
            validation.errors.append("Execution approval did not match the generated state hash.")
            validation.passed = False
            status = "blocked"
        else:
            try:
                dry_run["execution"] = {"passed": True, "output": salt_client.apply_state(args.target, state)}
            except SaltClientError as error:
                dry_run["execution"] = {"passed": False, "error": str(error)}
                validation.errors.append(f"Salt execution failed: {error}")
                validation.passed = False
                status = "blocked"
    result = PipelineResult(
        status=status,
        prompt=args.prompt,
        target=args.target,
        context=context,
        state=state,
        validation=validation,
        dry_run=dry_run,
        assumptions=assumptions,
    )
    audit_log = args.audit_log or Path(settings.audit_log)
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    write_audit(result, audit_log)
    if args.output:
        output_path = args.output if args.output.is_absolute() else Path(settings.state_output_dir) / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(state, encoding="utf-8")
    if args.as_json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print_human(result)
    return 0 if validation.passed else 1


def print_human(result: PipelineResult) -> None:
    print("Salt Assistant")
    print(f"\nContext: {len(result.context.minions)} minions resolved ({result.context.source})")
    print(f"Generation: complete\nValidation: {'passed' if result.validation.passed else 'blocked'}")
    print(f"Dry-run: {'passed' if result.validation.passed else 'blocked'}; {len(result.context.minions)} minions affected")
    print(f"Risk: {result.validation.risk_level}")
    if result.validation.errors:
        print("\nErrors:")
        print("\n".join(f"- {error}" for error in result.validation.errors))
    if result.assumptions:
        print("\nAssumptions:")
        print("\n".join(f"- {assumption}" for assumption in result.assumptions))
    print("\nGenerated state:\n" + yaml.safe_dump(yaml.safe_load(result.state), sort_keys=False).rstrip())
    if "execution" in result.dry_run and result.dry_run["execution"].get("passed"):
        print("\nExecution completed after hash-bound approval.")
    else:
        print("\nNo changes were executed.")


def main() -> None:
    raise SystemExit(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
