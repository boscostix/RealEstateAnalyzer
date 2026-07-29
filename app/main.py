"""FastAPI application entrypoint."""

import os

from fastapi import FastAPI

from app.api.routes import add_exception_handlers, router
from app.logging import add_middleware, configure_logging

configure_logging(os.getenv("LOG_LEVEL", "INFO"))
app = FastAPI(
    title="Real Estate Analyzer",
    version="0.1.0",
    description="Milestone 1 listing ingestion and extraction service.",
)
add_middleware(app)
add_exception_handlers(app)
app.include_router(router)
