from datasheet_agent.config import Settings


def test_admin_and_agent_use_different_roles():
    s = Settings()
    assert s.database_url != s.agent_database_url
    assert "agent_ro" in s.agent_database_url


def test_spend_cap_defaults_to_one_dollar(monkeypatch):
    monkeypatch.delenv("DAILY_SPEND_CAP_USD", raising=False)
    assert Settings(_env_file=None).daily_spend_cap_usd == 1.00
