"""Post-call analysis eval: the real analysis model over saved transcripts with known answers.

analysis_cases.json holds real calls from the scenario and campaign runs (transcript, outcome, collected
details, tool calls, the agent's success rule and analysis fields) and, written by hand, what
the analysis should say: whether the call succeeded and the value of chosen fields. The run
also checks that every analysis field comes back, which Retell users report going missing.

    backend\\studio-backend\\.venv\\Scripts\\python.exe evals\\run_analysis_eval.py [--repeat 3]

Needs the analysis model's key (OPENAI_API_KEY) in .env.local; no running stack.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from studio_backend.agents.schemas import AnalysisField
from studio_backend.calls.analysis import analyse, create_analysis_model, result_model
from studio_backend.config import export_provider_keys, get_settings

CASES_FILE = Path(__file__).with_name("analysis_cases.json")


async def run_case(case: dict, settings) -> list[str]:
    """The case's problems: wrong answers and missing fields (empty: it passed)."""
    specs = [AnalysisField.model_validate(field) for field in case["analysis_fields"]]
    call = SimpleNamespace(**{key: case[key] for key in ("transcript", "outcome", "fields")})
    call.tool_calls = case["tool_calls"]
    agent = SimpleNamespace(success_rule=case["success_rule"])
    model = create_analysis_model(settings, result_model(specs))
    answer, _ = await analyse(model, call, agent)
    problems = []
    missing = {spec.name for spec in specs} - set(answer["fields"])
    if missing:
        problems.append(f"missing fields {sorted(missing)}")
    expected = case["expected"]
    if answer["successful"] != expected["successful"]:
        problems.append(
            f"successful={answer['successful']}, expected {expected['successful']}"
            f" ({answer['success_reason']})"
        )
    for name, value in expected["fields"].items():
        if answer["fields"].get(name) != value:
            problems.append(f"{name}={answer['fields'].get(name)!r}, expected {value!r}")
    return problems


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=1, help="runs per case (LLMs vary)")
    args = parser.parse_args()
    export_provider_keys()
    settings = get_settings()
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    passed = total = 0
    for case in cases:
        for _ in range(args.repeat):
            problems = await run_case(case, settings)
            total += 1
            passed += not problems
            mark = "PASS" if not problems else "FAIL"
            print(f"{mark}  {case['name']:40} {'; '.join(problems)}")
    print(f"\n{passed}/{total} passed ({settings.analysis_llm_model})")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
