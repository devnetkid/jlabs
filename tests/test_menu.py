import pytest
from unittest.mock import patch, call, MagicMock
from jlabs.menu import Menu

@pytest.fixture
def sample_menu():
    """A fixture to provide a standard Menu instance for tests."""
    mock_callback_1 = MagicMock(return_value="Action 1 Executed")
    mock_callback_2 = MagicMock(return_value="Action 2 Executed")
    options = [
        ("Option 1", mock_callback_1),
        ("Option 2", mock_callback_2)
    ]
    return Menu("Main Menu", "Choose wisely", options)

def test_menu_initialization(sample_menu):
    """Test that the Menu initializes attributes correctly."""
    assert sample_menu._title == "Main Menu"
    assert sample_menu._subtitle == "Choose wisely"
    assert len(sample_menu._options) == 2
    
    # Check that namedtuples were created correctly
    assert sample_menu._options[0].label == "Option 1"
    assert callable(sample_menu._options[0].callback)

@patch("jlabs.menu.utils.clear_screen")
@patch("jlabs.menu.utils.colorme")
@patch("builtins.print")
def test_menu_display(mock_print, mock_colorme, mock_clear_screen, sample_menu):
    """Test that display() clears the screen and prints the correct layout."""
    # Make colorme just return the text it was given to simplify testing
    mock_colorme.side_effect = lambda text, color: text
    
    sample_menu.display()

    # Verify utils.clear_screen was called
    mock_clear_screen.assert_called_once()

    # Verify the correct sequence of prints occurred
    expected_calls = [
        call("Main Menu"),
        call("  Choose wisely\n"),
        call("    1 - Option 1\n    2 - Option 2\n")
    ]
    mock_print.assert_has_calls(expected_calls)

@patch("builtins.input", return_value="1")
@patch.object(Menu, "display")
def test_get_input_valid_selection(mock_display, mock_input, sample_menu):
    """Test that a valid selection executes the callback and returns its value."""
    result = sample_menu.get_input()

    # Verify it returns the result of the first callback
    assert result == "Action 1 Executed"
    
    # Verify the callback was actually triggered
    sample_menu._options[0].callback.assert_called_once()
    
    # Verify display was called twice (once at start, once before execution)
    assert mock_display.call_count == 2

@patch("builtins.print")
@patch("builtins.input")
@patch.object(Menu, "display")
def test_get_input_out_of_range(mock_display, mock_input, mock_print, sample_menu):
    """Test how the menu handles an integer that is not in the options list."""
    # Sequence of inputs: "9" (out of bounds), "" (press enter), "1" (valid selection to exit loop)
    mock_input.side_effect = ["9", "", "1"]
    
    sample_menu.get_input()

    # Check if the correct error message was printed
    mock_print.assert_any_call("\n  Entry not in range, please try again.")

@patch("builtins.print")
@patch("builtins.input")
@patch.object(Menu, "display")
def test_get_input_value_error(mock_display, mock_input, mock_print, sample_menu):
    """Test how the menu handles non-integer input."""
    # Sequence of inputs: "abc" (value error), "" (press enter), "2" (valid selection to exit loop)
    mock_input.side_effect = ["abc", "", "2"]
    
    sample_menu.get_input()

    # Check if the correct error message was printed
    mock_print.assert_any_call("\n  Entry must be a number, please try again.")
