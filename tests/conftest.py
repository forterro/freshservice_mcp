"""Shared test fixtures and configuration."""
import os
import pytest

# Set test environment variables before any imports
os.environ.setdefault("FRESHSERVICE_DOMAIN", "test.freshservice.com")
os.environ.setdefault("FRESHSERVICE_APIKEY", "test-api-key")
