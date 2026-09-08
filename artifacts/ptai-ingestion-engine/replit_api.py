"""Replit-only path mount for the portable PT-AI operator API."""

from starlette.applications import Starlette
from starlette.routing import Mount

from ptai_ingestion.api.app import app as portable_app


app = Starlette(routes=[Mount("/ptai-api", app=portable_app)])