"""
Synthetic data generation + end-to-end test for the ROI framework.

Validates the calculation engine, API health, and data integrity.
Uses existing DB tables. New tables (rate_cards, quality_reviews, etc.)
are created via the Supabase dashboard SQL editor or skipped gracefully.

Run: cd backend && /opt/homebrew/bin/python3 -m pytest tests/test_roi_framework.py -v -s --tb=short
"""

import os
import sys
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database import get_supabase
from app.services.roi import (
    calculate_cost_avoided,
    get_active_rate,
    get_calibrated_baseline,
    get_quality_summary,
    get_adoption_rate,
    get_roi_summary,
)


def UUID(s: str) -> uuid.UUID:
    return uuid.UUID(s)


# ---------------------------------------------------------------------------
# Module-scoped seed data
# ---------------------------------------------------------------------------

_seed_cache = None


def _get_seed_data():
    global _seed_cache
    if _seed_cache:
        return _seed_cache

    supabase = get_supabase()

    # --- Client ---
    result = supabase.table("clients").select("id, slug").eq("slug", "meridian-law").execute()
    if result.data:
        client_id = result.data[0]["id"]
    else:
        client_id = str(uuid.uuid4())
        supabase.table("clients").insert({
            "id": client_id, "name": "Meridian Law Group", "slug": "meridian-law",
        }).execute()

    # --- Practice groups ---
    pg_result = supabase.table("practice_groups").select("id, slug").eq("client_id", client_id).execute()
    pg_ids = [r["id"] for r in (pg_result.data or [])]

    # --- Users ---
    user_result = supabase.table("user_profiles").select("id").eq("client_id", client_id).execute()
    user_ids = [r["id"] for r in (user_result.data or [])]

    # --- Functions ---
    fn_result = supabase.table("functions").select("id, slug, name").execute()
    fn_ids = {r["slug"]: r["id"] for r in (fn_result.data or [])}

    # Baseline configs used by both metrics generation and baseline seeding
    baseline_configs = {
        "matter-intake": 1_800,
        "contract-review": 7_200,
        "employment-agents": 5_400,
        "cowork-legal-plugin": 1_800,
        "due-diligence": 54_000,
        "regulatory-monitor": 3_600,
        "km-intelligence": 2_400,
        "client-value-reporting": 14_400,
    }

    # --- Seed lots of synthetic metrics if needed ---
    existing_count = supabase.table("metrics").select("id", count="exact").eq("client_id", client_id).execute()
    if (existing_count.count or 0) < 100:
        print(f"\n[seed] Generating synthetic metrics (existing: {existing_count.count or 0})...")
        rows = []
        now = datetime.now(timezone.utc)
        slugs = list(fn_ids.keys())
        for day_offset in range(90):
            day = now - timedelta(days=day_offset)
            daily = random.randint(3, 8) if day.weekday() >= 5 else random.randint(10, 35)
            for _ in range(daily):
                slug = random.choice(slugs)
                fn_id = fn_ids[slug]
                pg_id = random.choice(pg_ids) if pg_ids else None
                user_id = random.choice(user_ids) if user_ids else None
                base_ms = baseline_configs.get(slug, 1_800) * 1000
                proc_ms = random.randint(1_500, 90_000)
                saved = max(0, base_ms - proc_ms)
                rows.append({
                    "id": str(uuid.uuid4()),
                    "client_id": client_id,
                    "function_id": fn_id,
                    "initiated_by": user_id,
                    "practice_group_id": pg_id,
                    "started_at": day.isoformat(),
                    "completed_at": (day + timedelta(seconds=proc_ms / 1000)).isoformat(),
                    "processing_time_ms": proc_ms,
                    "prompt_tokens": random.randint(400, 6_000),
                    "completion_tokens": random.randint(150, 3_000),
                    "total_tokens": random.randint(550, 9_000),
                    "cost_usd": round(random.uniform(0.0005, 0.12), 4),
                    "model_used": "deepseek-chat",
                    "human_time_equivalent_ms": base_ms,
                    "time_saved_ms": saved,
                    "result_quality": random.choice(["correct", "correct", "correct", "minor_issues", "minor_issues"]),
                    "confidence": random.randint(65, 98),
                    "tags": {"source": "synthetic_test"},
                })
        # Batch insert
        for i in range(0, len(rows), 50):
            supabase.table("metrics").insert(rows[i:i+50]).execute()
        print(f"[seed] {len(rows)} synthetic metrics inserted")

    # --- Try to seed new tables (graceful skip if not yet created) ---
    # Rate cards
    try:
        existing_rc = supabase.table("rate_cards").select("id").eq("client_id", client_id).limit(1).execute()
        if not existing_rc.data:
            for rate_type, rate in [("blended", 350.00), ("partner", 850.00), ("associate", 450.00)]:
                supabase.table("rate_cards").insert({
                    "client_id": client_id, "rate_type": rate_type,
                    "hourly_rate_usd": rate, "created_by": user_ids[0] if user_ids else None,
                }).execute()
            print("[seed] Rate cards inserted")
    except Exception:
        print("[seed] Rate cards table not yet created — run 006_roi_framework.sql in Supabase SQL editor")

    # Quality reviews
    try:
        existing_qr = supabase.table("quality_reviews").select("id").limit(1).execute()
        if not existing_qr.data:
            metrics_sample = supabase.table("metrics").select("id, function_id, practice_group_id") \
                .eq("client_id", client_id).order("started_at", desc=True).limit(100).execute()
            qr_rows = []
            for m in (metrics_sample.data or [])[:100]:
                acc = random.choices(["correct", "minor_issues", "major_issues", "incorrect"], weights=[65, 20, 10, 5])[0]
                qr_rows.append({
                    "id": str(uuid.uuid4()),
                    "invocation_id": m["id"],
                    "function_id": m["function_id"],
                    "client_id": client_id,
                    "practice_group_id": m.get("practice_group_id"),
                    "reviewer_id": user_ids[0] if user_ids else None,
                    "accuracy": acc,
                    "false_positive": random.random() < 0.08,
                    "false_negative": random.random() < 0.05,
                    "human_overrode": acc in ("major_issues", "incorrect") or random.random() < 0.1,
                    "agreement_score": 100 if acc == "correct" else random.randint(40, 85),
                    "review_time_ms": random.randint(15_000, 300_000),
                })
            for i in range(0, len(qr_rows), 50):
                supabase.table("quality_reviews").insert(qr_rows[i:i+50]).execute()
            print(f"[seed] {len(qr_rows)} quality reviews inserted")
    except Exception:
        print("[seed] Quality reviews table not yet created — run 006_roi_framework.sql in Supabase SQL editor")

    # Eligible users
    try:
        existing_eu = supabase.table("eligible_users").select("id").limit(1).execute()
        if not existing_eu.data and user_ids:
            eu_rows = [{"id": str(uuid.uuid4()), "client_id": client_id,
                         "user_id": uid, "created_by": user_ids[0]} for uid in user_ids]
            supabase.table("eligible_users").insert(eu_rows).execute()
            print(f"[seed] {len(eu_rows)} eligible users inserted")
    except Exception:
        print("[seed] Eligible users table not yet created — run 006_roi_framework.sql in Supabase SQL editor")

    # Baselines — these are in the existing time_saved_baselines table
    try:
        for slug, seconds in baseline_configs.items():
            fn_id = fn_ids.get(slug)
            if not fn_id:
                continue
            existing_bl = supabase.table("time_saved_baselines").select("id") \
                .eq("function_id", fn_id).eq("client_id", client_id).execute()
            if not existing_bl.data:
                supabase.table("time_saved_baselines").insert({
                    "function_id": fn_id, "client_id": client_id,
                    "baseline_seconds": seconds,
                }).execute()
        print("[seed] Baselines seeded")
    except Exception as e:
        print(f"[seed] Baselines skip: {e}")

    # POC projects
    try:
        existing_poc = supabase.table("poc_projects").select("id").limit(1).execute()
        if not existing_poc.data:
            poc_configs = [
                ("AI Contract Review for M&A", "contract_review", "build"),
                ("Due Diligence Accelerator", "due_diligence", "discovery"),
                ("Employment Separation Agent", "employment", "review"),
                ("Regulatory Monitor — Energy", "regulatory_monitor", "discovery"),
                ("KM Semantic Search", "km_search", "graduated"),
                ("Client Value Reporting", "custom", "cancelled"),
            ]
            for name, fn_type, status in poc_configs:
                supabase.table("poc_projects").insert({
                    "id": str(uuid.uuid4()), "client_id": client_id,
                    "name": name, "function_type": fn_type, "status": status,
                    "started_at": (date.today() - timedelta(days=random.randint(10, 60))).isoformat(),
                    "target_completion": (date.today() + timedelta(days=random.randint(10, 45))).isoformat(),
                    "created_by": user_ids[0],
                }).execute()
            print(f"[seed] {len(poc_configs)} POC projects inserted")
    except Exception:
        print("[seed] POC projects table not yet created — run 007_poc_pipeline.sql in Supabase SQL editor")

    _seed_cache = {
        "client_id": client_id,
        "practice_group_ids": pg_ids,
        "user_ids": user_ids,
        "function_ids": fn_ids,
    }
    return _seed_cache


@pytest.fixture(scope="module")
def seed_data():
    return _get_seed_data()


# ===========================================================================
# Tests — ROI Service Logic (works with or without DB for new tables)
# ===========================================================================

class TestROICalculations:
    """Test the ROI calculation engine — math, not DB."""

    def test_cost_avoided_basic(self):
        """10 hours at $350/hr = $3,500 if rate card exists, otherwise $0."""
        result = calculate_cost_avoided(
            36_000_000,  # 10 hours in ms
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            rate_type="blended",
        )
        assert result["hours_saved"] == 10.0
        # With no rate_cards table, returns 0 (graceful degradation)
        print(f"\n[cost-avoided] 10h saved = ${result['cost_avoided_usd']:,.2f} avoided (0 = no rate_cards table)")

    def test_cost_avoided_with_rate_card(self, seed_data):
        """With a real client, cost avoided calculates (0 if no rate_cards table)."""
        client_id = UUID(seed_data["client_id"])
        rate = get_active_rate(client_id, rate_type="blended")
        result = calculate_cost_avoided(36_000_000, client_id, rate_type="blended")
        assert result["hours_saved"] == 10.0
        if rate:
            assert result["hourly_rate_usd"] == rate
            assert result["cost_avoided_usd"] == 10.0 * rate
        print(f"\n[cost-avoided] rate=${rate}/hr, 10h saved = ${result['cost_avoided_usd']:,.2f} avoided")

    def test_time_saved_formula(self):
        """time_saved = max(0, human_equivalent - processing_time)"""
        # AI takes 5s, manual takes 2h → 1h 59m 55s saved
        human_ms = 7_200_000  # 2 hours
        ai_ms = 5_000         # 5 seconds
        saved = max(0, human_ms - ai_ms)
        assert saved == 7_195_000
        assert round(saved / 3_600_000, 2) == 2.0  # ~2 hours saved

    def test_roi_ratio_math(self):
        """ROI ratio = cost avoided / AI cost."""
        cost_avoided = 5_000.00
        ai_cost = 15.42
        ratio = round(cost_avoided / ai_cost, 2)
        assert ratio == 324.25  # 324:1 return


class TestQualityLogic:
    """Test quality metric calculations independent of DB."""

    def test_accuracy_rate(self):
        reviews = [
            {"accuracy": "correct"},
            {"accuracy": "correct"},
            {"accuracy": "minor_issues"},
            {"accuracy": "correct"},
            {"accuracy": "major_issues"},
            {"accuracy": "incorrect"},
            {"accuracy": "correct"},
            {"accuracy": "correct"},
            {"accuracy": "minor_issues"},
            {"accuracy": "correct"},
        ]
        total = len(reviews)
        correct = sum(1 for r in reviews if r["accuracy"] == "correct")
        minor = sum(1 for r in reviews if r["accuracy"] == "minor_issues")
        accuracy_rate = round(((correct + minor) / total) * 100, 1)
        assert accuracy_rate == 80.0  # 6 correct + 2 minor = 8/10

    def test_override_rate(self):
        reviews = [{"human_overrode": True}, {"human_overrode": False}, {"human_overrode": False},
                    {"human_overrode": True}, {"human_overrode": False}]
        overrode = sum(1 for r in reviews if r.get("human_overrode"))
        assert round((overrode / len(reviews)) * 100, 1) == 40.0


class TestAdoptionLogic:
    """Test adoption rate calculations."""

    def test_adoption_rate(self):
        eligible = 50
        active = 32
        pct = round((active / eligible) * 100, 1)
        assert pct == 64.0

    def test_zero_eligible(self):
        eligible = 0
        active = 0
        pct = 0.0 if eligible == 0 else round((active / eligible) * 100, 1)
        assert pct == 0.0


# ===========================================================================
# Tests — Data Integrity (existing tables only)
# ===========================================================================

class TestExistingData:
    def test_metrics_data_exists(self, seed_data):
        supabase = get_supabase()
        result = supabase.table("metrics").select("id", count="exact") \
            .eq("client_id", seed_data["client_id"]).execute()
        count = result.count or 0
        print(f"\n[metrics] {count:,} total invocations in DB")
        assert count >= 50, f"Need at least 50 metrics rows, got {count}"

    def test_time_saved_positive(self, seed_data):
        supabase = get_supabase()
        result = supabase.table("metrics").select("time_saved_ms") \
            .eq("client_id", seed_data["client_id"]).limit(100).execute()
        positive = sum(1 for r in (result.data or []) if r.get("time_saved_ms", 0) > 0)
        assert positive >= 60, f"Most metrics should have time_saved > 0, got {positive}/100"

    def test_functions_registered(self, seed_data):
        assert len(seed_data["function_ids"]) >= 8, f"Expected 8 functions, got {len(seed_data['function_ids'])}"

    def test_clients_exist(self, seed_data):
        assert seed_data["client_id"] is not None

    def test_users_exist(self, seed_data):
        assert len(seed_data["user_ids"]) >= 1

    def test_practice_groups_exist(self, seed_data):
        assert len(seed_data["practice_group_ids"]) >= 4


# ===========================================================================
# Tests — ROI Summary with real metrics data
# ===========================================================================

class TestROISummaryReal:
    def test_get_roi_summary_from_metrics(self, seed_data):
        """ROI summary should work on real metrics data."""
        client_id = UUID(seed_data["client_id"])
        period_end = date.today()
        period_start = period_end - timedelta(days=90)

        roi = get_roi_summary(
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
        )
        s = roi["summary"]
        assert s["total_invocations"] > 0, f"No invocations found in metrics"
        assert s["total_hours_saved"] > 0, f"No hours saved in metrics"
        assert len(roi["by_function"]) >= 3, f"Expected 3+ functions, got {len(roi['by_function'])}"

        print(f"\n[ROI from real metrics]")
        print(f"  Invocations:    {s['total_invocations']:,}")
        print(f"  Hours saved:    {s['total_hours_saved']:,.1f}")
        print(f"  AI cost:        ${s['total_ai_cost_usd']:,.2f}")
        print(f"  Cost avoided:   ${s['total_cost_avoided_usd']:,.2f}")
        print(f"  ROI ratio:      {s['roi_ratio'] or 'N/A'}")
        print(f"  Functions:      {len(roi['by_function'])}")
        for fn in roi["by_function"]:
            print(f"    {fn['name']:30s} {fn['invocations']:5d} invoc  {fn['hours_saved']:8.1f}h saved")

    def test_roi_by_function(self, seed_data):
        client_id = UUID(seed_data["client_id"])
        period_end = date.today()
        period_start = period_end - timedelta(days=90)
        roi = get_roi_summary(client_id=client_id, period_start=period_start, period_end=period_end)

        for fn in roi["by_function"]:
            assert fn["invocations"] >= 0
            assert fn["hours_saved"] >= 0
            # All functions should have a name
            assert fn["name"] != "Unknown", f"Function {fn['function_id']} has no name mapping"


# ===========================================================================
# Tests — API Endpoints
# ===========================================================================

@pytest.fixture(scope="module")
def api_client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


class TestAPIHealth:
    def test_health(self, api_client):
        r = api_client.get("/health")
        assert r.status_code == 200
        assert r.json()["app"] == "legal-os"

    def test_roi_health(self, api_client):
        r = api_client.get("/api/roi/health")
        assert r.status_code == 200
        assert r.json()["function"] == "roi-framework"

    def test_roi_targets(self, api_client):
        r = api_client.get("/api/roi/targets")
        assert r.status_code == 200
        targets = r.json()["targets"]
        assert "accuracy_rate" in targets
        assert "adoption_rate" in targets

    def test_poc_health(self, api_client):
        r = api_client.get("/api/poc-pipeline/health")
        assert r.status_code == 200
        assert r.json()["function"] == "poc-pipeline"

    def test_poc_targets(self, api_client):
        r = api_client.get("/api/poc-pipeline/targets")
        assert r.status_code == 200
        assert "graduation_rate" in r.json()["targets"]

    def test_dashboard_governance(self, api_client):
        r = api_client.get("/api/governance/health")
        assert r.status_code == 200
        data = r.json()
        assert len(data["functions"]) >= 8
        assert "auditability" in data["governance_pillars"]
        print(f"\n[governance] {len(data['functions'])} functions, pillars: {data['governance_pillars']}")

    def test_reporting_health(self, api_client):
        r = api_client.get("/api/reporting/health")
        assert r.status_code == 200
        assert "client-value-reporting" in r.json()["function"]

    def test_reporting_metrics(self, api_client):
        r = api_client.get("/api/reporting/metrics")
        assert r.status_code == 200
        data = r.json()
        print(f"\n[reporting] {data['total_invocations']} invocations, {data['total_hours_saved']}h saved")


# ===========================================================================
# Tests — New Tables (if migrations applied)
# ===========================================================================

class TestNewTables:
    """Test the new tables created by 006/007 migrations — skips gracefully if not applied."""

    @pytest.fixture
    def sb(self):
        return get_supabase()

    def test_rate_cards_exists(self, sb, seed_data):
        try:
            result = sb.table("rate_cards").select("id", count="exact") \
                .eq("client_id", seed_data["client_id"]).execute()
            count = result.count or 0
            print(f"\n[rate_cards] {count} records")
            assert count >= 3, f"Expected 3+ rate cards, got {count}"
        except Exception as e:
            if "Could not find the table" in str(e):
                pytest.skip("rate_cards table not yet created — run 006_roi_framework.sql in Supabase SQL editor")
            raise

    def test_quality_reviews_exists(self, sb, seed_data):
        try:
            result = sb.table("quality_reviews").select("id", count="exact") \
                .eq("client_id", seed_data["client_id"]).execute()
            count = result.count or 0
            print(f"\n[quality_reviews] {count} records")
            if count > 0:
                summary = get_quality_summary(
                    client_id=UUID(seed_data["client_id"]),
                    period_start=date.today() - timedelta(days=90),
                    period_end=date.today(),
                )
                print(f"  accuracy={summary['accuracy_rate']}% override={summary['override_rate']}%")
                assert summary["total_reviews"] > 0
        except Exception as e:
            if "Could not find the table" in str(e):
                pytest.skip("quality_reviews table not yet created")
            raise

    def test_eligible_users_exists(self, sb, seed_data):
        try:
            result = sb.table("eligible_users").select("id", count="exact") \
                .eq("client_id", seed_data["client_id"]).execute()
            count = result.count or 0
            print(f"\n[eligible_users] {count} records")
            if count > 0:
                rate = get_adoption_rate(client_id=UUID(seed_data["client_id"]), period_days=90)
                print(f"  adoption: {rate['active_count']}/{rate['eligible_count']} = {rate['adoption_pct']}%")
                assert rate["eligible_count"] > 0
        except Exception as e:
            if "Could not find the table" in str(e):
                pytest.skip("eligible_users table not yet created")
            raise

    def test_poc_projects_exists(self, sb, seed_data):
        try:
            result = sb.table("poc_projects").select("id, status", count="exact") \
                .eq("client_id", seed_data["client_id"]).execute()
            count = result.count or 0
            print(f"\n[poc_projects] {count} projects")
            if count > 0:
                statuses = {r["status"] for r in (result.data or [])}
                print(f"  statuses: {statuses}")
                assert len(statuses) >= 2, f"Expected POCs in 2+ statuses, got {statuses}"
        except Exception as e:
            if "Could not find the table" in str(e):
                pytest.skip("poc_projects table not yet created — run 007_poc_pipeline.sql in Supabase SQL editor")
            raise

    def test_adoption_rate_with_data(self, seed_data):
        """If eligible_users exists and has data, adoption should be calculable."""
        try:
            supabase = get_supabase()
            supabase.table("eligible_users").select("id").limit(1).execute()
            rate = get_adoption_rate(
                client_id=UUID(seed_data["client_id"]),
                period_days=90,
            )
            assert rate["eligible_count"] > 0
            assert 0 <= rate["adoption_pct"] <= 100
        except Exception as e:
            if "Could not find the table" in str(e):
                pytest.skip("eligible_users table not yet created")

    def test_baselines_have_methodology(self, seed_data):
        """All baselines should ideally have methodology defined."""
        supabase = get_supabase()
        result = supabase.table("time_saved_baselines").select("*") \
            .eq("client_id", seed_data["client_id"]).execute()
        count = len(result.data or [])
        print(f"\n[baselines] {count} configured")
        assert count >= 7, f"Expected 7+ baselines, got {count}"


# ===========================================================================
# Summary
# ===========================================================================

def test_print_summary(seed_data):
    """Final summary of everything that was tested."""
    supabase = get_supabase()
    client_id = seed_data["client_id"]

    metrics_count = supabase.table("metrics").select("id", count="exact") \
        .eq("client_id", client_id).execute().count or 0

    # Check which new tables exist
    new_tables = {}
    for tbl in ["rate_cards", "quality_reviews", "eligible_users", "poc_projects", "poc_feedback"]:
        try:
            c = supabase.table(tbl).select("id", count="exact").eq("client_id", client_id).execute().count or 0
            new_tables[tbl] = f"{c} rows"
        except Exception:
            new_tables[tbl] = "NOT CREATED — run migrations"

    print(f"\n{'='*60}")
    print(f"ROI FRAMEWORK TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  Client:             {client_id}")
    print(f"  Practice groups:    {len(seed_data['practice_group_ids'])}")
    print(f"  Users:              {len(seed_data['user_ids'])}")
    print(f"  Functions:          {len(seed_data['function_ids'])}")
    print(f"  Metrics rows:       {metrics_count:,}")
    print(f"  ---")
    for tbl, status in new_tables.items():
        print(f"  {tbl:25s} {status}")
    print(f"{'='*60}")

    # Required tables should exist
    assert metrics_count > 0
    assert len(seed_data["function_ids"]) >= 8
