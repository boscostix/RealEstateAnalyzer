"""FastAPI application entrypoint."""

import os

from fastapi import FastAPI

from app.api.agent_research_routes import router as agent_research_router
from app.api.analysis_routes import router as analysis_router
from app.api.investment_committee_routes import router as investment_committee_router
from app.api.persisted_analysis_routes import router as persisted_analysis_router
from app.api.property_routes import router as property_router
from app.api.research_routes import router as research_router
from app.api.routes import add_exception_handlers, router
from app.logging import add_middleware, configure_logging

configure_logging(os.getenv("LOG_LEVEL", "INFO"))
app = FastAPI(
    title="Real Estate Analyzer",
    version="0.1.0",
    description=(
        "Listing extraction, property verification, and deterministic underwriting service."
    ),
)
add_middleware(app)
add_exception_handlers(app)
app.include_router(router)
app.include_router(property_router)
app.include_router(persisted_analysis_router)
app.include_router(analysis_router)
app.include_router(research_router)
app.include_router(agent_research_router)
app.include_router(investment_committee_router)
