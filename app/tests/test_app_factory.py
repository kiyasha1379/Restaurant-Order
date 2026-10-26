"""The application factory and the three configurations."""

import pytest

from restaurant import create_app
from restaurant.config import DemoConfig, DevConfig, TestConfig, resolve_config


def test_test_config_uses_in_memory_database():
    app = create_app("test")
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"
    assert app.config["DEMO_MODE"] is False


def test_demo_config_turns_demo_mode_on():
    assert create_app("demo").config["DEMO_MODE"] is True


def test_overrides_replace_single_settings():
    app = create_app("test", {"DEMO_MODE": True})
    assert app.config["DEMO_MODE"] is True


def test_resolve_config_reads_environment(monkeypatch):
    monkeypatch.setenv("APP_CONFIG", "demo")
    assert resolve_config() is DemoConfig


def test_resolve_config_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("APP_CONFIG", raising=False)
    assert resolve_config() is DevConfig


def test_resolve_config_by_name():
    assert resolve_config("TEST") is TestConfig


def test_unknown_config_name_is_rejected():
    with pytest.raises(ValueError, match="Unknown configuration"):
        resolve_config("production")


def test_seed_and_reset_commands_exist(app):
    runner = app.test_cli_runner()
    assert "added" in runner.invoke(args=["sync-ui-strings"]).output
    from restaurant.seed.demo_data import DEMO_BACKGROUNDS

    assert f"added {len(DEMO_BACKGROUNDS)} backgrounds" in runner.invoke(args=["seed-demo"]).output
    assert "added 0 backgrounds" in runner.invoke(args=["seed-demo"]).output
    assert "nothing to reset" in runner.invoke(args=["reset-demo"]).output
