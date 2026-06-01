import pytest
from src.jlabs.eveng import EveNgClient

@pytest.mark.parametrize("input_ip, expected_base_url, expected_is_pro", [
    # 1. Raw IP provided
    ("192.168.1.50", "http://192.168.1.50/api", False),
    
    # 2. HTTP URL provided
    ("http://192.168.1.50", "http://192.168.1.50/api", False),
    
    # 3. HTTPS URL provided (Pro)
    ("https://192.168.1.50", "https://192.168.1.50/api", True),
    
    # 4. Edge Case: User accidentally leaves a trailing slash
    ("https://192.168.1.50/", "https://192.168.1.50/api", True),
])
def test_target_parsing(monkeypatch, input_ip, expected_base_url, expected_is_pro):
    # Setup: Mock the environment variables so the class doesn't crash on init
    monkeypatch.setenv("JLABS_EVENG_IP", input_ip)
    monkeypatch.setenv("JLABS_EVENG_USER", "admin")
    monkeypatch.setenv("JLABS_EVENG_PASS", "eve")

    # Execution: Instantiate the client
    client = EveNgClient()

    # Assertion: Verify the parsing logic holds up
    assert client.base_url == expected_base_url
    assert client.is_pro is expected_is_pro
