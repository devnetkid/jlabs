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
                self.current_prompt = "#" # Set manually, skip enable()
            else:
                # Only use enable() on supported network devices (like Cisco/Arista)
                self.connection.enable()
                self.current_prompt = self.connection.find_prompt()
                
        except NetmikoTimeoutException:
            raise ValueError(f"Unable to connect to {device_config['host']} on port {device_config['port']}")
        except NetmikoAuthenticationException:
            raise ValueError("CONNECTION FAILED: Authentication error. Verify credentials.")

    def _handle_fortigate_console(self):
        """Handles manual login override for FortiGate via EVE-NG terminal server."""
        
        # 1. Clear any lingering garbage characters from the buffer, then wake it up
        self.connection.clear_buffer()
        self.connection.write_channel("\n")
        
        # 2. Enter a State Machine loop to handle prompts in ANY order
        max_loops = 10
        for attempt in range(max_loops):
            try:
                # Read the stream until we see ANY known FortiGate prompt
                output = self.connection.read_until_pattern(
                    pattern=r"(?i)(login:|username:|new password:|confirm password:|password:|accept|\(a/d\)|[#$])",
                    read_timeout=10
                )
                
                output_lower = output.lower()
                
                # Evaluate from most specific to least specific
                if "new password:" in output_lower:
                    self.connection.write_channel("jlabs\n")
                    
                elif "confirm password:" in output_lower:
                    self.connection.write_channel("jlabs\n")
                    
                elif "password:" in output_lower:
                    self.connection.write_channel(f"{self.password}\n")
                    
                elif "login:" in output_lower or "username:" in output_lower:
                    self.connection.write_channel(f"{self.username}\n")
                    
                elif "accept" in output_lower or "(a/d)" in output_lower:
                    self.connection.write_channel("a\n")
                    
                elif "#" in output_lower or "$" in output_lower:
                    # We reached the final CLI prompt, setup is complete
                    self.connection.clear_buffer()
                    return 
                    
            except Exception as e:
                # If we time out waiting for a prompt, the console might have gone to sleep.
                # Send a carriage return to refresh the prompt and loop again.
                self.connection.write_channel("\n")
                
        # If we exceed max_loops without hitting the return statement, something is fundamentally broken
        raise ValueError("Failed to reach FortiGate CLI prompt. Stuck in a console loop or unresponsive.")

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
                logger.debug("Sending configuration via terminal server channel...")
                
                # Disable paging safely using the raw write channel
                self.connection.write_channel("config system console\nset output standard\nend\n")
                time.sleep(1)
                self.connection.read_channel() # Clear the buffer
                
                output = ""
                for cmd in config:
                    logger.debug(f"Sending line: {cmd}")
                    # Write command directly to the stream
                    self.connection.write_channel(f"{cmd}\n")
                    
                    # Give the virtual FortiGate time to process the line (adjust if needed)
                    time.sleep(0.5) 
                    
                    # Drain the text buffer continuously so it doesn't fill up and hang
                    output += self.connection.read_channel()
                    
                return output
                
            # HANDLE NATIVE CISCO / OTHER SUPPORTED DEVICES
            logger.debug("Sending configuration via native Netmiko engine...")
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
