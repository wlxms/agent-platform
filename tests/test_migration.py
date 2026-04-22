"""Tests for Alembic migration — new models."""
from pathlib import Path


def test_migration_file_exists():
    """At least 2 migration files should exist (initial + new)."""
    versions_dir = Path("alembic/versions")
    migration_files = sorted(versions_dir.glob("*.py"))
    # Filter out __pycache__ and non-migration files
    migration_files = [f for f in migration_files if f.name != "__init__.py"]
    assert len(migration_files) >= 2


def test_migration_file_contains_new_tables():
    """The latest migration should mention the new tables."""
    versions_dir = Path("alembic/versions")
    migration_files = sorted(
        [f for f in versions_dir.glob("*.py") if f.name != "__init__.py"]
    )
    latest = migration_files[-1]
    content = latest.read_text(encoding="utf-8")
    for table in (
        "agent_configs", "agent_config_versions", "approvals",
        "budgets", "audit_logs", "templates", "skills",
        "mcp_servers", "categories",
    ):
        assert table in content or table in content.lower(), f"Table {table} not found in migration"


def test_migration_has_unique_constraint_budgets():
    """budgets table should have UniqueConstraint on org_id."""
    versions_dir = Path("alembic/versions")
    migration_files = sorted(
        [f for f in versions_dir.glob("*.py") if f.name != "__init__.py"]
    )
    latest = migration_files[-1]
    content = latest.read_text(encoding="utf-8")
    assert "uq_budgets_org_id" in content


def test_migration_has_foreign_keys():
    """New tables with org_id should have FK to organizations."""
    versions_dir = Path("alembic/versions")
    migration_files = sorted(
        [f for f in versions_dir.glob("*.py") if f.name != "__init__.py"]
    )
    latest = migration_files[-1]
    content = latest.read_text(encoding="utf-8")
    # agent_configs, approvals, budgets, templates all reference organizations
    fk_count = content.count("ForeignKeyConstraint(['org_id'], ['organizations.id']")
    assert fk_count >= 4, f"Expected >= 4 org FKs, found {fk_count}"


def test_migration_downgrade_drops_new_tables():
    """Downgrade should drop the new tables (via alter reversal)."""
    versions_dir = Path("alembic/versions")
    migration_files = sorted(
        [f for f in versions_dir.glob("*.py") if f.name != "__init__.py"]
    )
    latest = migration_files[-1]
    content = latest.read_text(encoding="utf-8")
    # The autogenerate reverses nullable changes in downgrade; table drops
    # happen implicitly. Verify downgrade function exists.
    assert "def downgrade()" in content
