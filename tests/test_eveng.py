import pytest
import requests
from src.jlabs.eveng import EveNgClient
from unittest.mock import call, patch, MagicMock

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

def test_init_raises_system_exit_when_ip_missing(monkeypatch):
    # Ensure the environment variable is completely blank
    monkeypatch.delenv("JLABS_EVENG_IP", raising=False)
    
    # Verify that instantiating the class triggers a sys.exit(1)
    with pytest.raises(SystemExit) as sample_exception:
        EveNgClient()
        
    assert sample_exception.value.code == 1

# Patch the base 'request' method of the Session class
@patch('requests.Session.request')
def test_login_success(mock_request, monkeypatch):
    # 1. Setup the environment variables
    monkeypatch.setenv("JLABS_EVENG_IP", "10.0.0.1")
    monkeypatch.setenv("JLABS_EVENG_USER", "admin")
    monkeypatch.setenv("JLABS_EVENG_PASS", "eve")
    
    # 2. Setup the mock response that the session will return
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "message": "Authenticated."}
    
    # Tell our patched request method to return our fake response
    mock_request.return_value = mock_response

    # 3. Instantiate the client and execute the login
    client = EveNgClient()
    result = client.login("test_user", "test_pass")

    # 4. Assertions
    # Note: Because we patched Session.request, requests translates .post() into a "POST" argument
    mock_request.assert_called_once_with(
        "POST",
        "http://10.0.0.1/api/auth/login",
        json={"username": "test_user", "password": "test_pass", "html5": "-1"}
    )
    
    expected_entries = [
        call("POST", "http://10.0.0.1/api/auth/login", json={"username": "test_user", "password": "test_pass", "html5": "-1"}),
        call("GET", "http://10.0.0.1/api/auth", allow_redirects=True)
    ]

    mock_request.assert_has_calls(expected_entries, any_order=True)
    # Verify that your method successfully returned the mock data
    assert result == {"status": "success", "message": "Authenticated."}

def test_login_failure_raises_error(monkeypatch):
    # Setup
    monkeypatch.setenv("JLABS_EVENG_IP", "10.0.0.1")
    client = EveNgClient()
    
    # Force raise_for_status() to bubble up an HTTPError (simulating bad credentials)
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
    client.session.post = MagicMock(return_value=mock_response)

    # Assert that the client doesn't swallow the exception
    with pytest.raises(requests.exceptions.HTTPError):
        client.login("wrong_user", "wrong_pass")

def test_get_wrapper_appends_endpoint(monkeypatch):
    monkeypatch.setenv("JLABS_EVENG_IP", "10.0.0.1")
    client = EveNgClient()
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"labs": ["Lab1", "Lab2"]}
    client.session.get = MagicMock(return_value=mock_response)

    # Call the wrapper with a specific endpoint
    result = client.get("labs/list")

    # Ensure it targeted the right URL
    client.session.get.assert_called_once_with("http://10.0.0.1/api/labs/list")
    assert result == {"labs": ["Lab1", "Lab2"]}
    
    
def test_delete_wrapper_returns_status_code(monkeypatch):
    monkeypatch.setenv("JLABS_EVENG_IP", "10.0.0.1")
    client = EveNgClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    client.session.delete = MagicMock(return_value=mock_response)

    # The delete wrapper uniquely returns status_code instead of json()
    result = client.delete("labs/Lab1")

    client.session.delete.assert_called_once_with("http://10.0.0.1/api/labs/Lab1")
    assert result == 200

def test_logout_clears_cookies(monkeypatch):
    monkeypatch.setenv("JLABS_EVENG_IP", "10.0.0.1")
    client = EveNgClient()
    
    # Fake an active cookie session
    client.session.cookies.set("username", "admin")
    
    mock_response = MagicMock()
    client.session.get = MagicMock(return_value=mock_response)

    # Execute logout
    client.logout()

    # Assert API was hit and cookies are empty string/cleared
    client.session.get.assert_called_once_with("http://10.0.0.1/api/auth/logout")
    assert len(client.session.cookies) == 0
