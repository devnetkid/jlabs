import pytest
import logging
from unittest.mock import patch, MagicMock
from netmiko.exceptions import NetmikoTimeoutException, ReadTimeout

from src.jlabs.connect import DeviceConnection

@pytest.fixture
def base_device():
    """Fixture to provide a standard DeviceConnection object for testing."""
    return DeviceConnection(
        device_ip="192.168.1.10",
        device_type="cisco_ios",
        username="admin",
        password="password123",
        port=22
    )

def test_initialization(base_device):
    """Test that the class initializes attributes correctly."""
    assert base_device.device_ip == "192.168.1.10"
    assert base_device.device_type == "cisco_ios"
    assert base_device.username == "admin"
    assert base_device.password == "password123"
    assert base_device.port == 22
    assert base_device.connection is None

@patch("src.jlabs.connect.ConnectHandler")
def test_connect_success(mock_connect_handler, base_device):
    """Test a successful connection to a device."""
    base_device.connect()
    
    # Ensure ConnectHandler was called with the exact dictionary we expect
    mock_connect_handler.assert_called_once_with(
        host="192.168.1.10",
        device_type="cisco_ios",
        port=22,
        username="admin",
        password="password123"
    )
    # Ensure the connection object was saved to the instance
    assert base_device.connection == mock_connect_handler.return_value

@patch("src.jlabs.connect.ConnectHandler")
def test_connect_timeout_exception(mock_connect_handler, base_device, capsys):
    """Test that NetmikoTimeoutException is caught and prints the correct output."""
    # Force the mocked ConnectHandler to raise a timeout exception
    mock_connect_handler.side_effect = NetmikoTimeoutException("Connection timed out")
    
    base_device.connect()
    
    # Capture standard output printed by the exception handler
    captured = capsys.readouterr()
    
    assert "Unable to connect to 192.168.1.10 on port 22" in captured.out
    assert "Make sure device is reachable and running ssh" in captured.out

def test_disconnect(base_device):
    """Test the disconnect method calls the underlying connection disconnect."""
    # Mock the internal connection object since we aren't really connecting
    base_device.connection = MagicMock()
    
    base_device.disconnect()
    
    # Ensure the internal disconnect method was called
    base_device.connection.disconnect.assert_called_once()

def test_write_config_success(base_device):
    """Test sending a configuration command successfully."""
    base_device.connection = MagicMock()
    commands = ["interface loopback0", "description Test"]
    
    base_device.write_config(commands)
    
    # Ensure the mock's send_config_set was called with our commands
    base_device.connection.send_config_set.assert_called_once_with(commands)

def test_write_config_read_timeout(base_device, caplog):
    """Test that ReadTimeout is caught and logged properly."""
    base_device.connection = MagicMock()
    
    # Force send_config_set to raise a ReadTimeout
    base_device.connection.send_config_set.side_effect = ReadTimeout("Read timeout")
    
    # Run the function while capturing logging at the INFO level
    with caplog.at_level(logging.INFO):
        base_device.write_config(["show run"])
        
    assert "A read timeout exception occured" in caplog.text
