import { test, expect } from "@playwright/test";

const API_BASE = process.env.PLAYWRIGHT_API_URL || "http://localhost:8080";

test.describe("Backend API Health", () => {
  test("health endpoint returns ok", async ({ request }) => {
    const r = await request.get(`${API_BASE}/health`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.app).toBe("legal-os");
    expect(data.status).toBe("healthy");
  });

  test("ROI summary returns data in demo mode", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/roi/summary?period_days=90`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.summary.total_invocations).toBeGreaterThan(0);
  });

  test("ROI health returns capabilities", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/roi/health`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.capabilities).toContain("cost_impact_calculation");
  });

  test("POC pipeline health returns ok", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/poc-pipeline/health`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.function).toBe("poc-pipeline");
  });

  test("POC pipeline metrics returns project counts", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/poc-pipeline/metrics`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.total_projects).toBeGreaterThanOrEqual(6);
  });

  test("governance health returns pillars", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/governance/health`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.governance_pillars).toContain("auditability");
    expect(data.functions.length).toBeGreaterThanOrEqual(8);
  });

  test("reporting health returns ok", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/reporting/health`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.function).toBe("client-value-reporting");
  });

  test("quality summary returns metrics", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/roi/quality/summary?period_days=90`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.total_reviews).toBeGreaterThan(0);
  });

  test("adoption rate returns data", async ({ request }) => {
    const r = await request.get(`${API_BASE}/api/roi/adoption?period_days=90`);
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data.eligible_count).toBeGreaterThan(0);
    expect(data.adoption_pct).toBeGreaterThanOrEqual(0);
  });
});
