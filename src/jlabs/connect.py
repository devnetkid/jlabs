# src/jlabs/connect.py

import json
import logging
import time
import socket
from netmiko import ConnectHandler
from netmiko.exceptions import (
    AuthenticationException,
    NetmikoTimeoutException,
    ReadTimeout,
    SSHException
)

logger = logging.getLogger(__name__)


class DeviceConnection:
    """
    Connects to a devices in the lab to push configs or get settings
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
        # VPCS logic handling
        if self.device_type == "vpcs":
            try:
                # Create a raw socket for VPCS telnet
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.settimeout(10)
                self.connection.connect((self.device_ip, int(self.port)))
                
                # Send a carriage return to wake up the VPCS prompt
                self.connection.sendall(b"\r\n")
                time.sleep(1)
                return
            except Exception as err:
                print(f"Unable to connect to VPCS {self.device_ip} on port {self.port}")
                raise err

        # Cisco logic handling
        device = {
            "host": self.device_ip,
            "device_type": self.device_type,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "global_delay_factor": 2, 
        }
        
        try:
            self.connection = ConnectHandler(**device)
        except NetmikoTimeoutException as err:
            print(f"Unable to connect to {device['host']} on port {device['port']}")
            print("Make sure device is reachable and running ssh/telnet")
            raise err

    def disconnect(self):
        """Disconnects from a lab device"""
        if self.connection:
            if self.device_type == "vpcs":
                self.connection.close()
            else:
                self.connection.disconnect()

    def write_config(self, config):
        """Sends a list of commands to the device"""
        
        # VPCS logic for sending config
        if self.device_type == "vpcs":
            try:
                for cmd in config:
                    # Convert string to bytes and add carriage return
                    encoded_cmd = f"{cmd}\r\n".encode('ascii')
                    self.connection.sendall(encoded_cmd)
                    time.sleep(0.5) # Give VPCS a moment to process each command
                return "VPCS config applied successfully"
            except Exception as e:
                logger.error(f"Failed to write config to VPCS: {e}")
                return ""

        # Cisco logic for sending config
        try:
            return self.connection.send_config_set(config)
        except ReadTimeout:
            logger.info("A read timeout exception occurred")
            return ""
