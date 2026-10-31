# src/jlabs/connect.py

import json
import logging
import time
import socket
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
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
        Connects to a device in the lab (VPCS, Cisco, FortiGate, etc.).
        """
        # 1. Route to the appropriate connection handler
        if self.device_type == "vpcs":
            return self._connect_vpcs()
            
        return self._connect_netmiko()
    
    def _connect_vpcs(self):
        """Establishes a raw socket connection for VPCS devices."""
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(10)
            self.connection.connect((self.device_ip, int(self.port)))
            
            # Send a carriage return to wake up the VPCS prompt
            self.connection.sendall(b"\r\n")
            time.sleep(1)
        except Exception as err:
            print(f"Unable to connect to VPCS {self.device_ip} on port {self.port}")
            raise err
    
    def _connect_netmiko(self):
        """Establishes a Netmiko connection for network devices."""
        device_config = {
            "host": self.device_ip,
            "device_type": self.device_type,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "global_delay_factor": 2, 
        }
        
        try:
            self.connection = ConnectHandler(**device_config)
            
            if self.device_type == "generic_termserver_telnet":
                self._handle_fortigate_console()
                
            self.connection.enable()
            self.current_prompt = self.connection.find_prompt()
            print(f"Current prompt: {self.current_prompt}")
            
        except NetmikoTimeoutException:
            print(f"Unable to connect to {device_config['host']} on port {device_config['port']}")
        except NetmikoAuthenticationException:
            print("\nCONNECTION FAILED: Authentication error.\nPlease verify credentials.")
        except Exception as error:
            print(f"\nCONNECTION FAILED: An unexpected error occurred:\n{error}")
    
    def _handle_fortigate_console(self):
        """Handles manual login override for FortiGate via EVE-NG terminal server."""
        print("Connecting to FortiGate console via EVE-NG Telnet...")
        
        # 1. Wake up the console line
        self.connection.write_channel("\n")
        time.sleep(1)
        output = self.connection.read_channel()
        print(f"Sent an newline char, here is output:\n{output}")
        
        # 2. Handle manual login prompt using instance credentials instead of hardcoded strings
        if "login:" in output or "Username:" in output:
            print("Sending login credentials...{self.username} - {self.password}")
            self.connection.write_channel(f"{self.username}\n")
            time.sleep(1)
            self.connection.write_channel(f"{self.password}\n")
            time.sleep(1)
            output = self.connection.read_channel()
            print(f"Sent username and password, here is output:\n{output}")
            print("Entering new password then confirming it")
            self.connection.write_channel("jlabs\n")
            time.sleep(1)
            self.connection.write_channel("jlabs\n")
            time.sleep(3)
            self.connection.write_channel("\n")
            output = self.connection.read_channel()
            print(f"All done here is output:\n{output}")
            self.connection.clear_buffer()
    
        # 3. Verify and verify session state
        if "#" in output or "$" in output:
            print("Successfully logged in!")
        else:
            print(f"Could not reach the command prompt. Current output:\n{output}")


    def disconnect(self):
        """Disconnects from a lab device"""
        if self.connection:
            if self.device_type == "vpcs":
                self.connection.close()
            else:
                self.connection.disconnect()


    def write_config(self, config):
        """
        Sends a list or string of configuration commands to the device.
        """
        if self.device_type == "vpcs":
            return self._write_config_vpcs(config)
            
        return self._write_config_netmiko(config)
    
    def _write_config_vpcs(self, config):
        """Sends configuration to a VPCS device via raw socket."""
        try:
            for cmd in config:
                encoded_cmd = f"{cmd}\r\n".encode('ascii')
                self.connection.sendall(encoded_cmd)
                time.sleep(0.5)  # Give VPCS a moment to process each command
            return "VPCS config applied successfully"
        except Exception as e:
            logger.error(f"Failed to write config to VPCS: {e}")
            return ""
    
    def _write_config_netmiko(self, config):
        """Sends configuration to a network device via Netmiko."""
        try:
            # HANDLE FORTIGATE VIA EVE-NG TELNET
            if self.device_type == "generic_termserver_telnet":
                print("Sending configuration via terminal server channel...")
                
                # Disable paging safely using the raw write channel
                self.connection.write_channel("config system console\nset output standard\nend\n")
                time.sleep(1)
                self.connection.read_channel() # Clear the buffer
                
                output = ""
                for cmd in config:
                    print(f"Sending line: {cmd}")
                    # Write command directly to the stream
                    self.connection.write_channel(f"{cmd}\n")
                    
                    # Give the virtual FortiGate time to process the line (adjust if needed)
                    time.sleep(0.5) 
                    
                    # Drain the text buffer continuously so it doesn't fill up and hang
                    output += self.connection.read_channel()
                    
                return output
                
            # HANDLE NATIVE CISCO / OTHER SUPPORTED DEVICES
            print("Sending configuration via native Netmiko engine...")
            return self.connection.send_config_set(config)
            
        except ReadTimeout:
            logger.info("A read timeout exception occurred while applying configuration.")
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
