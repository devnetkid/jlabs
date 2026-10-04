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
        self.current_prompt = None

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
            "session_log": "netmiko.log"
        }
        
        try:
            self.connection = ConnectHandler(**device)
            self.connection.enable()
            self.current_prompt = self.connection.find_prompt()
            print(f"Current prompt: {self.current_prompt}")
        except NetmikoTimeoutException as err:
            print(f"Unable to connect to {device['host']} on port {device['port']}")
        except NetmikoAuthenticationException:
            print("\nCONNECTION FAILED: Authentication error.")
            print("Please verify your username, password, or privilege levels.")
        except Exception as error:
            print(f"\nCONNECTION FAILED: An unexpected error occurred:")
            print(str(error))

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


    def send_interactive_command(self, command, expect_prompt, response):
        """
        Handles interactive prompts via low-level channel control to bypass Telnet buffering traps.
        """
        if self.device_type == "vpcs":
            logger.info("Interactive commands not applicable for VPCS.")
            return ""

        try:
            # 1. Clear the input buffer to flush any lingering carriage returns (\r or \n)
            self.connection.clear_buffer()
            
            # 2. Write the exact command to the channel with a single clean newline
            self.connection.write_channel(f"{command}\n")
            
            # 3. Read the raw stream until the question prompt shows up
            output = self.connection.read_until_pattern(pattern=expect_prompt, read_timeout=5)
            
            # 4. Send the confirmation ('y') followed by a newline
            self.connection.write_channel(f"{response}\n")
            
            # 5. Read until we are safely back at the standard router prompt (#)
            output += self.connection.read_until_pattern(pattern=r"#", read_timeout=5)
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to execute interactive command '{command}': {e}")
            # Safety fallback: keep the buffer clean for subsequent operations
            try:
                self.connection.clear_buffer()
            except:
                pass
            return ""
