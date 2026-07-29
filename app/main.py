"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes import add_exception_handlers, router

app = FastAPI(
    title="Real Estate Analyzer",
    version="0.1.0",
    description="Milestone 1 listing ingestion and extraction service.",
)
add_exception_handlers(app)
app.include_router(router)
