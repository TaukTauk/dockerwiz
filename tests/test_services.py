"""Tests for services.py."""

from dockerwiz.services import SERVICES, get_mutex_conflicts, get_service


def test_all_services_present():
    names = {s.name for s in SERVICES}
    assert names == {"postgres", "mysql", "redis", "nginx", "mongo"}


def test_get_service():
    svc = get_service("postgres")
    assert svc is not None
    assert svc.label == "PostgreSQL"
    assert svc.default_port == 5432


def test_get_service_missing():
    assert get_service("nonexistent") is None


def test_mutex_conflict_postgres_mysql():
    conflicts = get_mutex_conflicts(["postgres", "mysql"])
    assert len(conflicts) == 1
    assert set(conflicts[0]) == {"postgres", "mysql"}


def test_no_mutex_conflict():
    assert get_mutex_conflicts(["postgres", "redis", "nginx"]) == []


def test_single_db_no_conflict():
    assert get_mutex_conflicts(["postgres"]) == []
    assert get_mutex_conflicts(["mysql"]) == []
