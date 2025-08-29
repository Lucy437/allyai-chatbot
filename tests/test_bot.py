import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import main


@pytest.fixture(autouse=True)
def stub_db(monkeypatch):
    # Make DB calls no-ops for CI
    monkeypatch.setattr(main, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(main, "create_or_update_user", lambda *a, **k: None)
    monkeypatch.setattr(main, "get_user_profile", lambda *a, **k: {})

@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    with main.app.test_client() as c:
        yield c

def test_bot_requires_from_number(client):
    resp = client.post("/bot", data={"Body": "hi"})
    assert resp.status_code == 200
    assert b"detect your phone number" in resp.data

def test_restart_without_profile_starts_over(client):
    resp = client.post("/bot", data={"From": "+10000000000", "Body": "restart"})
    assert resp.status_code == 200
    assert b"Let's start over" in resp.data or b"What\xe2\x80\x99s your name?" in resp.data

def test_new_user_intro_prompts_for_name(client):
    resp = client.post("/bot", data={"From": "+10000000001", "Body": "Hi"})
    assert resp.status_code == 200
    assert b"your name" in resp.data
