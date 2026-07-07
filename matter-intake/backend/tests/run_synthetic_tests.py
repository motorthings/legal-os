"""Run synthetic matter intake fixtures against the evaluate endpoint.

Usage:
    python tests/run_synthetic_tests.py                    # all 15 fixtures
    python tests/run_synthetic_tests.py --ids synth-001    # single fixture
    python tests/run_synthetic_tests.py --ids synth-001 synth-006 synth-015  # specific fixtures
    python tests/run_synthetic_tests.py --save-output      # save full responses to disk
    python tests/run_synthetic_tests.py --base-url http://localhost:8000  # custom server
"""

import json
import sys
import time
from pathlib import Path

import requests

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "synthetic_matters.json"
OUTPUT_DIR = Path(__file__).parent / "output"


def load_fixtures() -> list[dict]:
    with open(FIXTURES_PATH) as f:
        return json.load(f)


def run_evaluation(
    matter: dict, base_url: str
) -> tuple[dict | None, float, str | None]:
    """POST a matter summary to the evaluate endpoint. Returns (response, elapsed, error)."""
    start = time.monotonic()
    try:
        resp = requests.post(
            f"{base_url}/api/evaluate",
            json={"matter_summary": matter["matter_summary"]},
            timeout=120,
        )
        elapsed = time.monotonic() - start
        if resp.status_code == 200:
            return resp.json(), elapsed, None
        else:
            return None, elapsed, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.ConnectionError:
        elapsed = time.monotonic() - start
        return None, elapsed, "Connection refused — is the server running?"
    except Exception as e:
        elapsed = time.monotonic() - start
        return None, elapsed, str(e)


def print_result(matter: dict, result: dict | None, elapsed: float, error: str | None):
    """Print a compact summary of one evaluation result."""
    id_ = matter["id"]
    desc = matter["description"]

    print(f"\n{'='*80}")
    print(f"  {id_} — {desc}")
    print(f"{'='*80}")

    if error:
        print(f"  ERROR: {error}")
        return

    r = result
    print(f"  Overall:    {r['overall_score']}/100  |  Risk: {r['overall_risk_level']}")
    print(
        f"  Practice:   {r['practice_area']['practice_area']} "
        f"(confidence: {r['practice_area']['confidence']}%)"
    )
    print(
        f"  Urgency:    {r['urgency_risk']['urgency_level']}  |  "
        f"Risk score: {r['urgency_risk']['risk_score']}/100  |  "
        f"Level: {r['urgency_risk']['risk_level']}"
    )
    print(
        f"  Conflict:   {r['conflict_check']['conflict_type']}"
        + (
            f" — {r['conflict_check']['entity_name']}"
            if r['conflict_check'].get('entity_name')
            else ""
        )
    )
    print(
        f"  Staffing:   {r['staffing']['recommended_role']}  |  "
        f"~{r['staffing']['estimated_hours']} hrs"
    )
    di = r["data_integrity"]
    print(
        f"  Integrity:  completeness={di['completeness']}/100  |  "
        f"clarity={di['clarity']}/100"
    )
    if di["issues"]:
        for issue in di["issues"]:
            print(f"              issue: {issue}")

    # Dimension breakdown
    print(f"  Dimensions:")
    for d in r["dimension_scores"]:
        bar = "█" * (d["score"] // 5) + "░" * (20 - d["score"] // 5)
        print(
            f"    {d['dimension_name']:<40} {bar} {d['score']}/100 (×{d['weight']})"
        )

    print(f"  Processing: {r['processing_time_ms']}ms  |  Model: {r['model_used']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run synthetic matter intake tests")
    parser.add_argument(
        "--ids", nargs="*", default=None, help="Run only specific fixture IDs"
    )
    parser.add_argument(
        "--save-output", action="store_true", help="Save full JSON responses to disk"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    fixtures = load_fixtures()
    if args.ids:
        fixtures = [m for m in fixtures if m["id"] in args.ids]
        if not fixtures:
            print(f"No fixtures matched IDs: {args.ids}")
            sys.exit(1)

    print(f"Running {len(fixtures)} synthetic matter intake evaluations...")
    print(f"Server: {args.base_url}")
    print(f"Fixtures: {FIXTURES_PATH}")

    passed = 0
    failed = 0
    scores = []

    for i, matter in enumerate(fixtures):
        result, elapsed, error = run_evaluation(matter, args.base_url)
        print_result(matter, result, elapsed, error)

        if result:
            passed += 1
            scores.append(result["overall_score"])
        else:
            failed += 1

        if args.save_output and result:
            OUTPUT_DIR.mkdir(exist_ok=True)
            out_path = OUTPUT_DIR / f"{matter['id']}.json"
            with open(out_path, "w") as f:
                json.dump(
                    {
                        "fixture": matter,
                        "result": result,
                        "elapsed_seconds": round(elapsed, 2),
                    },
                    f,
                    indent=2,
                )

    # Summary
    print(f"\n{'='*80}")
    print(f"  SUMMARY")
    print(f"{'='*80}")
    print(f"  Total:    {len(fixtures)}")
    print(f"  Passed:   {passed}")
    print(f"  Failed:   {failed}")
    if scores:
        print(f"  Scores:   min={min(scores)}  max={max(scores)}  avg={sum(scores)//len(scores)}")
    print(f"  Server:   {args.base_url}")
    if args.save_output:
        print(f"  Output:   {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
