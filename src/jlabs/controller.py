# src/jlabs/controller.py

import logging
import sys

from jlabs import labs, menu, tools, utils

logger = logging.getLogger(__name__)


def load_lab():
    """List the available labs"""
    labs_list = utils.list_dir()
    if not labs_list:
        print("No labs found.")
        input("Press [ENTER] to continue...")
        return

    for index, lab in enumerate(labs_list, start=1):
        print(f"{index} - {lab}")
        
    response = input("\nEnter the number next to the lab you would like to run: ")
    try:
        choice_idx = int(response) - 1
        if choice_idx < 0 or choice_idx >= len(labs_list):
            raise IndexError
        labs.load_lab(labs_list[choice_idx])
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a valid number from the list.")

    input("Press [ENTER] to continue...")


def create_toml():
    """Create a lab.toml file from a lab in eve-ng."""
    lab_name = input("Enter the name of the existing eve-ng lab: ").strip()
    logger.info(f"User requested to build lab.toml from eve-ng lab {lab_name}")
    tools.create_toml(lab_name)
    input("Press [ENTER] to continue...")


def jlabs_exit():
    """Clears the screen, logs an exit message, and terminates jlabs."""
    utils.clear_screen()
    logger.info("Exiting jlabs")
    sys.exit(0)


def labs_menu():
    """Displays the available lab exercises"""
    menu_title = utils.menu_title
    menu_subtitle = "Labs Menu"
    labs_menu = menu.Menu(
        menu_title,
        menu_subtitle,
        [
            ("Load a lab", load_lab),
            ("Return to the main menu", main_menu),
            ("Exit", jlabs_exit),
        ],
    )
    while True:
        labs_menu.get_input()


def tools_menu():
    """Displays a sub-menu for lab options"""
    menu_title = utils.menu_title
    menu_subtitle = "Tools"
    tools_menu = menu.Menu(
        menu_title,
        menu_subtitle,
        [
            ("Create a lab file from an existing lab", create_toml),
            ("Return to the main menu", main_menu),
            ("Exit", jlabs_exit),
        ],
    )
    while True:
        tools_menu.get_input()


def main_menu():
    """Displays the main menu and handles user input in an infinite loop."""
    menu_title = utils.menu_title
    menu_subtitle = "Main Menu"
    main_menu = menu.Menu(
        menu_title,
        menu_subtitle,
        [
            ("Labs", labs_menu),
            ("Tools", tools_menu),
            ("Exit", jlabs_exit),
        ],
    )
    while True:
        main_menu.get_input()
