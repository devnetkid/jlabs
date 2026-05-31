# src/jlabs/connect.py

import json
import logging
from netmiko import ConnectHandler
from netmiko.exceptions import AuthenticationException
from netmiko.exceptions import NetmikoTimeoutException
from netmiko.exceptions import ReadTimeout
from netmiko.exceptions import SSHException


logger = logging.getLogger(__name__)


class DeviceConnection:
    """
    Connects to a device in the lab to push config or get settings
    """

    def __init__(self, device_ip, device_type, username, password, port=22):
        self.device_ip = device_ip
        self.device_type = device_type
        self.port = port
        self.username = username
        self.password = password
        self.connection = None

    def connect(self):
        """
        Connects to a device in the lab
        """
        device = {
            "host": self.device_ip,
            "device_type": self.device_type,
            "port": self.port,
            "username": self.username,
            "password": self.password,
        }
        try:
            self.connection = ConnectHandler(**device)
        except NetmikoTimeoutException as err:
            print(f"Unable to connect to {device["host"]} on port {device["port"]}")
            print("Make sure device is reachable and running ssh")

    def disconnect(self):
        """Disconnects from a lab device"""
        self.connection.disconnect()

    def write_config(self, config):
        """Sends a list of commands to the device"""
        try:
            output = self.connection.send_config_set(config)
        except ReadTimeout:
            logger.info("A read timeout exception occured")
