# Contract Review System - Documentation

Documentation for the AI-powered contract analysis and review system.

---

## Overview

This folder contains documentation for deploying and operating the contract review system built for the Contentful AI Solutions Partner interview assignment.

The system provides automated contract analysis with:
- Multi-format contract parsing (PDF, DOCX, TXT)
- AI-powered risk assessment (5 specialized contract types)
- Human-in-the-loop review workflow
- RAG-powered chat for contract Q&A
- Dashboard triage and reporting

---

## Documentation Structure

### 📁 `/deployments`
Infrastructure setup and deployment guides:
- `ENVIRONMENT_VARIABLES.md` - Environment configuration reference
- `RAILWAY_ENV_VARS.md` - Railway-specific environment variables
- `RAILWAY_VOLUME_SETUP.md` - Railway persistent volume configuration
- `RAILWAY_UPGRADE_PERFORMANCE.md` - Railway performance optimization
- `SUPABASE_AUTH_CONFIGURATION.md` - Supabase authentication setup
- `SUPABASE_STORAGE_SETUP.md` - Supabase storage configuration for contract files
- `SENTRY_SETUP.md` - Error tracking with Sentry
- `PRE_COMMIT_HOOKS_SETUP.md` - Pre-commit hooks for code quality

**Key deployment steps:**
1. Configure Supabase (database + storage + auth)
2. Set up Railway (backend deployment)
3. Configure Vercel (frontend deployment)
4. Set environment variables
5. Run database migrations
6. Configure storage buckets for contracts

### 📁 `/operations`
Operational procedures and troubleshooting:
- `PRODUCTION_DEV_WORKFLOW.md` - Development and deployment workflow
- `ENV_VARIABLES_MAP.md` - Comprehensive environment variables dependency map
- `TROUBLESHOOTING_KB_SEARCH.md` - Knowledge base and RAG troubleshooting

**Common operational tasks:**
- Contract upload and processing pipeline
- Database maintenance and backups
- Log monitoring and debugging
- Performance optimization
- API rate limit management

---

## Tech Stack

**Frontend:**
- Next.js 16.0.1 + React 19.2.0
- TypeScript 5
- Tailwind CSS 4
- Deployed on Vercel

**Backend:**
- FastAPI 0.115.0 (Python)
- Anthropic Claude API (contract analysis)
- Voyage AI (embeddings for RAG)
- Deployed on Railway

**Database:**
- Supabase PostgreSQL 15+
- pgvector extension (semantic search)
- Row Level Security (RLS) policies

**AI Services:**
- Claude API: Contract parsing and analysis
- Voyage AI: 1024-dimensional embeddings for RAG
- Specialized XML system instructions per contract type

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account
- Railway account
- Vercel account
- Anthropic API key
- Voyage AI API key

### Local Development Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/contentful-contract-review.git
   cd contentful-contract-review
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   uvicorn backend.main:app --reload --port 8000
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your backend URL and Supabase credentials
   npm run dev
   ```

4. **Database migrations**
   ```bash
   # Run from project root
   python -m backend.database.run_migrations
   ```

5. **Visit application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs

---

## Deployment

### Production Deployment Checklist

- [ ] Supabase project created
- [ ] pgvector extension enabled in Supabase
- [ ] Database migrations run
- [ ] Storage buckets created (contracts, documents)
- [ ] RLS policies configured
- [ ] Railway project created and linked
- [ ] Railway environment variables set
- [ ] Backend deployed to Railway
- [ ] Vercel project created
- [ ] Frontend deployed to Vercel
- [ ] Vercel environment variables set
- [ ] API endpoints tested
- [ ] Contract upload and analysis tested
- [ ] RAG search tested
- [ ] Sentry error tracking configured (optional)

### Environment Variables Required

**Backend (Railway):**
```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://...

# AI Services
ANTHROPIC_API_KEY=your-anthropic-api-key
VOYAGE_API_KEY=pa-...

# Auth
JWT_SECRET=your-secret-key

# CORS
FRONTEND_URL=https://your-app.vercel.app
```

**Frontend (Vercel):**
```bash
NEXT_PUBLIC_API_URL=https://your-api.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

## Contract Analysis Pipeline

```
1. UPLOAD → User uploads PDF/DOCX/TXT contract
2. STORE → Save to Supabase Storage
3. EXTRACT → PyPDF2/python-docx text extraction
4. CLASSIFY → Router agent identifies contract type
   ├─ Vendor
   ├─ Customer
   ├─ Employment
   ├─ DPA (Data Processing Agreement)
   └─ General
5. RAG → Retrieve relevant best practices from knowledge base
6. ANALYZE → Claude API with specialized XML instructions
   ├─ Extract parties, dates, terms, obligations
   ├─ Identify red flags (critical issues)
   ├─ Identify yellow flags (moderate concerns)
   └─ Calculate risk score (0-100)
7. SCORE → Weighted risk algorithm
   ├─ Financial Exposure (25%)
   ├─ Compliance & Legal (25%)
   ├─ Operational Risk (20%)
   ├─ Ambiguity & Clarity (15%)
   └─ Term Favorability (15%)
8. FLAG → Human review if needed
   ├─ Ambiguous language
   ├─ Conflicting terms
   ├─ Novel clauses
   └─ Low confidence
9. SAVE → Store analysis in contract_analysis table
10. NOTIFY → Update dashboard with results
```

---

## API Endpoints

### Contract Management
- `POST /api/contracts/upload` - Upload contract
- `GET /api/contracts` - List contracts (with filters)
- `GET /api/contracts/{id}` - Get contract details
- `PATCH /api/contracts/{id}/review` - Save review decision
- `GET /api/contracts/dashboard/stats` - Dashboard statistics
- `POST /api/contracts/compare` - Compare contracts

### Chat & Documents
- `POST /api/chat` - Send message with RAG
- `GET /api/documents` - List knowledge base documents
- `POST /api/documents/upload` - Upload document to KB

### Admin
- `GET /api/admin/stats` - System statistics
- `GET /api/admin/users` - List users

---

## Database Schema

### Key Tables

**contracts**
- Stores uploaded contract files
- Status: pending → analyzed → reviewed

**contract_analysis**
- AI-generated analysis results
- Risk scores and flags
- Extracted terms and parties
- Review decisions

**document_chunks**
- RAG knowledge base
- 800-char chunks with 200 overlap
- Voyage AI embeddings (1024-dim)
- pgvector HNSW index

**conversations / messages**
- Chat history
- Contract-specific Q&A

---

## Monitoring & Troubleshooting

### Health Checks
- Backend: `/health` endpoint
- Database: Connection pooling status
- Storage: Bucket access test
- AI Services: API key validation

### Common Issues

**Contract analysis fails:**
- Check Anthropic API key
- Verify contract text extraction
- Review error logs in Railway

**RAG search returns no results:**
- Verify Voyage AI API key
- Check document chunks table
- Ensure embeddings generated
- See `TROUBLESHOOTING_KB_SEARCH.md`

**Upload errors:**
- Check Supabase storage bucket permissions
- Verify file size limits
- Check file format support

### Logs
- Backend logs: Railway dashboard
- Frontend logs: Vercel dashboard
- Database logs: Supabase dashboard
- Error tracking: Sentry (if configured)

---

## Security Considerations

- Row Level Security (RLS) policies enforce data isolation
- JWT-based authentication via Supabase Auth
- API rate limiting on sensitive endpoints
- Secure storage of API keys via environment variables
- File upload validation and virus scanning (recommended)
- HTTPS enforced on all deployments

---

## Performance Optimization

- pgvector HNSW indexing for fast semantic search
- Connection pooling for database
- Railway volume persistence for logs
- Frontend code splitting and lazy loading
- CDN caching via Vercel
- Batch document processing

---

## Contributing

This is a technical demonstration project for the Contentful AI Solutions Partner interview.

**Contact:**
- Charlie Fuller
- Email: charlie@sickofancy.ai
- Assignment Context: Contentful AI Solutions Partner role

---

## License

Proprietary - Interview Assignment Project
