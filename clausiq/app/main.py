import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import SAMPLE_CONTRACTS_DIR, SEED_DEMO, STATIC_DIR
from .db import init_db
from .routes import auth, contracts, governance, meta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="ClausIQ", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(governance.router)
app.include_router(meta.router)


@app.on_event("startup")
async def _startup() -> None:
    init_db()
    if SEED_DEMO:
        asyncio.create_task(_bootstrap_demo())


async def _bootstrap_demo() -> None:
    """On a completely fresh database, ingest the CloudBase sample and run the
    full review + negotiation pipeline so the first screen is already alive."""
    try:
        from .agents.negotiation import run_negotiation
        from .db import execute, query_one, utcnow
        from .jobs import create_job
        from .pipeline import run_review_job

        existing = query_one("SELECT COUNT(*) AS n FROM contracts")
        if existing and existing["n"] > 0:
            return
        path = SAMPLE_CONTRACTS_DIR / "cloudbase-vendor-agreement.txt"
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        contract_id = execute(
            "INSERT INTO contracts (name, counterparty, filename, format, status,"
            " company_playbook, counterparty_playbook, full_text, created_at)"
            " VALUES (?, ?, ?, 'txt', 'uploaded', 'startup-friendly', 'vendor-friendly', ?, ?)",
            ("CloudBase Vendor Agreement (demo)", "CloudBase Inc.", "cloudbase-vendor-agreement.txt", text, utcnow()),
        )
        job_id = create_job()
        await run_review_job(job_id, contract_id, "startup-friendly")
        contract = query_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
        await run_negotiation(contract, "startup-friendly", "vendor-friendly")
        logging.getLogger("clausiq").info("Demo bootstrap complete for contract %s", contract_id)
    except Exception:  # noqa: BLE001
        logging.getLogger("clausiq").exception("Demo bootstrap failed")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
