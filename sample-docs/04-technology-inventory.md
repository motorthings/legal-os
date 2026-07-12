# Meridian Law Group — Technology Systems Inventory

**Last Updated:** December 2025
**Maintained By:** IT Manager (1 person, reports to Office Administrator)

## Core Systems

| System | Purpose | Adoption | Integration |
|--------|---------|----------|-------------|
| Clio Manage | Practice management, billing, calendar | 100% attorneys | Partial — Clio billing syncs to QuickBooks; no CRM integration |
| NetDocuments | Document management | 60% (Corporate, IP migrated; Litigation, Employment pending) | Clio integration available but not configured |
| Microsoft 365 | Email, calendar, Teams, SharePoint | 100% | Standard — no custom integrations |
| QuickBooks Enterprise | Accounting, trust accounting | Finance team only | One-way sync from Clio billing |
| Westlaw | Legal research | All attorneys | None — standalone |
| LexisNexis | Secondary legal research | ~40% of attorneys | None — standalone |
| Adobe Acrobat Pro | PDF creation, redaction | All attorneys | None |
| DocuSign | E-signatures | All practice groups | Clio integration configured |
| Zoom | Video conferencing | All personnel | Calendar integration with Outlook |

## Infrastructure

- **Network:** On-premises file server (Windows Server 2019) — being phased out for NetDocuments
- **Cloud:** Microsoft 365 tenant (Exchange Online, SharePoint, Teams); Clio cloud; NetDocuments cloud
- **Backup:** M365 native backup + CrashPlan for on-prem server
- **Security:** MFA enforced on M365 and Clio; VPN for remote access to legacy file server
- **WiFi:** Cisco Meraki across both offices
- **Endpoints:** Dell laptops (Windows 11) for attorneys; Lenovo desktops for staff
- **Mobile:** iPhones for partners (firm-provided); BYOD for associates and staff

## Systems Not Currently In Use
- **CRM:** Evaluated Lawmatics and HubSpot in 2024; no decision made
- **KM Platform:** SharePoint exists but not configured for KM; no dedicated KM software
- **AI/ML Tools:** CoCounsel pilot (1 license, 1 partner); no firm-wide AI platform
- **Data Analytics:** None — all reporting is manual Excel from Clio exports
- **Contract Analysis:** Desire to evaluate; no tool selected
- **E-discovery Platform:** Relativity used ad-hoc through a vendor; no in-house e-discovery capability

## Integration Status
- Clio ↔ QuickBooks: Working (billing export only)
- Clio ↔ NetDocuments: Not configured (license purchased, not implemented)
- Clio ↔ DocuSign: Working
- SharePoint ↔ Anything: Not integrated — used as a static file share
- No API-based integrations exist. All cross-system data movement is CSV export/import or manual re-entry.

## IT Staffing
- 1 IT Manager (generalist — networking, help desk, vendor management)
- 1 part-time IT support contractor (10 hrs/week)
- No dedicated: security officer, data analyst, KM specialist, integration engineer, AI/innovation role

## Budget
- 2025 IT budget: $340,000 (1.9% of gross revenue)
- 2026 proposed: $415,000 (includes NetDocuments completion + CRM evaluation)
- No line item for AI tools or KM staffing in 2026 budget
