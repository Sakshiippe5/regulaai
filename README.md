# RegulaAI

A multi-agent regulatory compliance assistant that reads regulatory
circulars, checks them against a bank's internal policies, and produces
cited gap reports with human-approved remediation tasks.

**Status:** 🚧 In active development

## Planned architecture
- LangGraph multi-agent workflow (Extraction, Applicability, RAG, Gap Analysis, Report)
- MCP tools for policies, controls, tasks, and audit history
- FastAPI backend, PostgreSQL, FAISS
- Docker, GitHub Actions, AWS

## Roadmap
- [ ] Phase 1: Document ingestion and extraction agent
- [ ] Phase 2: Policy knowledge base (RAG)
- [ ] Phase 3: LangGraph workflow
- [ ] Phase 4: Applicability and gap analysis
- [ ] Phase 5: MCP tools
- [ ] Phase 6: API, database, human approval
- [ ] Phase 7: Docker and deployment