# Help Documentation

This directory contains the source markdown files for Legal AI OS's RAG-based help system. Files are indexed into vector embeddings and served to users through the in-app help panel.

## Structure

```
help_docs/
  README.md                        # This file (not indexed)
  user/                            # Accessible to all authenticated users
    getting-started.md             # First-time user walkthrough
    app-navigation.md              # Sidebar, pages, and navigation
    dashboard-guide.md             # Portfolio dashboard and ROI metrics
    poc-pipeline-guide.md          # POC Pipeline Kanban board
    harvey-monitor-guide.md        # Harvey agent evaluation and drift detection
    enablement-kit-guide.md        # Training and enablement materials
    understanding-scores.md        # Scoring formula, tiers, veto, certification
    roi-framework-guide.md         # Cost impact, quality metrics, adoption tracking
    faq.md                         # Common questions
  system/                          # Accessible to all authenticated users
    platform-overview.md           # Full platform architecture
    governance-architecture.md     # Audit trail, RLS, HITL, compliance
```

## Indexing

After modifying any help docs, reindex them:

```bash
cd backend
python3 scripts/index_help_docs.py --force
```

This requires the following environment variables:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `VOYAGE_API_KEY` (for generating embeddings)

## Writing Guidelines

- Use exact UI element names (bold for buttons and links)
- Include numbered step-by-step instructions for workflows
- Keep sections focused and scannable
- Use markdown headings (H1 for title, H2/H3 for sections)
- No emojis
- Link to other help docs using their filename without extension: "See [Understanding Scores](understanding-scores) for details"
