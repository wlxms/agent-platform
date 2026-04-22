"""Tests for required dependencies."""
import importlib

import pytest


def test_import_celery():
    assert importlib.import_module("celery") is not None


def test_import_multipart():
    assert importlib.import_module("python_multipart") is not None


def test_import_yaml():
    assert importlib.import_module("yaml") is not None


def test_import_httpx():
    assert importlib.import_module("httpx") is not None


def test_existing_imports_still_work():
    modules = ["sqlalchemy", "pydantic", "fastapi", "redis", "jwt"]
    for m in modules:
        importlib.import_module(m)
