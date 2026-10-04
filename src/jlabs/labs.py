# src/jlabs/labs.py

import logging
import os
import random
import sys
import time

from jlabs import connect, eveng, utils

logger = logging.getLogger(__name__)

client = eveng.EveNgClient()

def get_lab_settings(lab_folder: str, file_name: str = "lab.toml") -> dict:
    """Loads a TOML file and enforces the .unl extension on the lab name."""
    settings = utils.load_toml(f"{lab_folder}/{file_name}")
    
    # Enforce .unl suffix if the lab key exists
    if "lab" in settings and "name" in settings["lab"]:
        lab_name = settings["lab"]["name"]
        if not lab_name.endswith(".unl"):
            settings["lab"]["name"] = f"{lab_name}.unl"
            
    return settings


def inject_issue(lab_folder: str):
    """Injects a random issue for troubleshooting from the issues.toml file"""
    print("Injecting a random issue to troubleshoot")
    
    # Load and parse the TOML file
    lab_issues = utils.load_toml(f"{lab_folder}/issues.toml")
    
    # Extract the list using your top-level key
    issues_list = lab_issues["faults"]
    
    # Randomly select one
    selected_issue = random.choice(issues_list)
    
    # Get the lab name from the lab settings
    lab_settings = get_lab_settings(lab_folder)
    lab_name = lab_settings["lab"]["name"]

    # Create an answer key in case user get's lost or wants to verify
    answer_key = ["=== Random Issue Answer Key ===\n"]
    answer_key.append(f"Lab Name:        {lab_name}\n")
    answer_key.append(f"Target Device:   {selected_issue["device"]}\n")
    answer_key.append(f"Fault Type:      {selected_issue["scenario"]}\n")
    answer_key.append(f"Commands:        {selected_issue["commands"]}\n")
    utils.writelines_to_file("random_issue_answer_key.txt", answer_key)

    # Get the selected devices node id
    try:
        client.login()
        # Fetch all nodes in the lab dynamically
        nodes_endpoint = client.get_lab_endpoint(lab_name, "nodes")
        nodes_response = client.get(nodes_endpoint)
        nodes = nodes_response.get("data", {})

        # Iterate through the dictionary of nodes
        for node_id, node_data in nodes.items():
            if node_data.get('name') == selected_issue["device"]:
                url = node_data.get('url')
                logger.info(f"node {node_data["name"]} was selected for the issue")
             
    except Exception as err:
        logger.error(f"Error communicating with EVE-NG while stopping nodes: {err}")
        print(f"Warning: Could not verify or stop nodes due to a network error.")
    finally:
        client.logout()

    telnet_ip = telnet_port = eve_ip = None

    if ":" in url:
        telnet_ip = url.split(":")[-2]
        telnet_port = url.split(":")[-1]

    if telnet_ip and "//" in telnet_ip:
        eve_ip = telnet_ip.lstrip("//")
    
    device_settings = {
        "device_ip": eve_ip,
        "device_type": "cisco_ios_telnet",
        "port": telnet_port,
        "username": "admin",
        "password": "cisco",
    }
   
    device = connect.DeviceConnection(**device_settings)
   
    try:
        device.connect()
        device.write_config(selected_issue["commands"])
        if selected_issue["interactive"]:
            cmd = selected_issue["interactive"][0]
            exp = selected_issue["interactive"][1]
            ans = selected_issue["interactive"][2]
            result = device.send_interactive_command(cmd, exp, ans)
        device.disconnect()
    except Exception as e:
        logger.debug(f"Unable to SSH/Telnet: {e}")
    
    print(selected_issue["scenario"])
    

def find_node_id_by_name(nodes: dict, src_node: str, dst_node: str) -> tuple[str, str]:
    src_node_id = dst_node_id = ""
    for value in nodes.values():
        if value["name"] == src_node:
            src_node_id = value["id"]
        if value["name"] == dst_node:
            dst_node_id = value["id"]
    return src_node_id, dst_node_id


def get_node_status(lab: str, node: dict) -> dict:
    """Fetches node details and extracts status and telnet port."""
    logger.info("Getting node status...")

    endpoint = client.get_lab_endpoint(lab, f"nodes/{node['id']}")
    client.login()
    response = client.get(endpoint)

    node_data = response.get("data", {})
    status = node_data.get("status")
    url = node_data.get("url", "")

    telnet_ip = telnet_port = eve_ip = None

    if ":" in url:
        telnet_ip = url.split(":")[-2]
        telnet_port = url.split(":")[-1]

    if telnet_ip and "//" in telnet_ip:
        eve_ip = telnet_ip.lstrip("//")

    return {
        "name": node_data.get("name"),
        "type": node_data.get("type"),
        "status": status,
        "template": node_data.get("template"),
        "port": telnet_port,
        "eve_ip": eve_ip,
    }


def stop_nodes(lab_name: str):
    """Stops all running nodes in the specified lab."""
    logger.info(f"Checking for running nodes in lab '{lab_name}'...")
    print(f"Preparing to stop nodes in lab '{lab_name}' (this may take a moment)...")
   
    try:
        client.login()
        # Fetch all nodes in the lab dynamically
        nodes_endpoint = client.get_lab_endpoint(lab_name, "nodes")
        nodes_response = client.get(nodes_endpoint)
        nodes = nodes_response.get("data", {})
       
        if not nodes:
            logger.info("No nodes found in lab.")
            return

        # Iterate through the dictionary of nodes
        for node_id, node_data in nodes.items():
            # In EVE-NG, status 2 means running, 0 means stopped
            if node_data.get('status') == 2:
                node_name = node_data.get('name', f"Node_{node_id}")
                logger.info(f"Stopping node {node_name}")
                print(f"Stopping node {node_name}...")
               
                stop_endpoint = client.get_lab_endpoint(lab_name, f"nodes/{node_id}/stop/stopmode=3")
                client.get(stop_endpoint)
                time.sleep(1)  # Brief pause to avoid overwhelming the server API
               
    except Exception as err:
        logger.error(f"Error communicating with EVE-NG while stopping nodes: {err}")
        print(f"Warning: Could not verify or stop nodes due to a network error.")
    finally:
        client.logout()


def delete_lab(lab_name: str):
    """Delete a lab from eve-ng"""
   
    # Ensure all nodes are stopped before attempting deletion
    stop_nodes(lab_name)
   
    # Proceed with deleting the lab file
    url = client.get_lab_endpoint(lab_name)
    try:
        client.login()
        response = client.delete(url)
        logger.info(f"Successfully deleted lab {lab_name}")
       
        # Check if the API actually returned a success code (usually 200 or 201)
        if response in [200, 201, 204]:
            print(f"The eve-ng lab '{lab_name}' has been deleted.")
        else:
            print(f"Server responded, but lab may not have deleted: {response.get('message', 'Unknown error')}")
           
    except Exception as err:
        logger.info(f"Failed to delete lab {lab_name}")
        print(f"Failed to delete lab: \n{err}")
    finally:
        client.logout()


def get_interface_index(ports: list, label: str) -> str:
    for index, item in enumerate(ports):
        if label == item["name"]:
            return str(index)
    return ""


def create_lab(lab_data):
    """Creates a new lab in eve-ng based on the contents of a toml config file."""
    lab_data["name"] = lab_data.get("name").rstrip(".unl")
    logger.info(f"Attempting to create lab {lab_data.get("name")}")
    print(f"Creating the lab {lab_data.get("name")}")
    try:
        client.login()
        client.post("labs", lab_data)
        print(f"Successfully created lab {lab_data.get("name")}")
        logger.info("Successfully created a new lab.")
    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")
        sys.exit(1)
    finally:
        client.logout()


def add_nodes(lab_name, lab_nodes):
    """Adding nodes to the Eve-NG lab as described in the toml config file"""
    logger.info(f"Adding nodes to the lab {lab_name}")
    print(f"Adding the nodes to lab {lab_name}")
    try:
        for node in lab_nodes:
            client.login()
            nodes_endpoint = client.get_lab_endpoint(lab_name, "nodes")
            client.post(nodes_endpoint, node)
        logger.info("Successfully added nodes to the new lab.")
        print(f"Successfully added nodes for lab {lab_name}")
    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")
    finally:
        client.logout()


def connect_cables(lab_name, lab_cables):
    """Connecting the requested cables per lab.toml file"""
    logger.info(f"Connecting requested cables for the lab {lab_name}")
    logger.debug(f"cables for the lab {lab_cables}")
    print(f"Connecting cables for lab {lab_name}")
   
    try:
        client.login()
       
        # Fetch BOTH nodes and networks from the lab
        nodes_endpoint = client.get_lab_endpoint(lab_name, "nodes")
        networks_endpoint = client.get_lab_endpoint(lab_name, "networks")
       
        nodes = client.get(nodes_endpoint)["data"]
        networks = client.get(networks_endpoint)["data"]
       
        logger.debug(f"Nodes data: {nodes}")
        logger.debug(f"Networks data: {networks}")

        # Inline helper to safely find IDs by name from dict or list data types
        def find_id_by_name(data_store, name):
            if isinstance(data_store, dict):
                for item_id, item_info in data_store.items():
                    if item_info.get("name") == name:
                        return item_id
            elif isinstance(data_store, list):
                for item in data_store:
                    if item.get("name") == name:
                        return item.get("id")
            return None

        for cable in lab_cables:
            src_node = cable.get("source")
            dst_node = cable.get("destination")
            src_label = cable.get("source_label")
            dst_label = cable.get("destination_label")
            dst_type = str(cable.get("destination_type", "")).lower()

            # Get the Source Node ID (Cables always originate from a node)
            src_node_id = find_id_by_name(nodes, src_node)
            if not src_node_id:
                logger.error(f"Source node '{src_node}' not found. Skipping cable.")
                continue

            # Fetch source node ports
            src_interfaces_endpoint = client.get_lab_endpoint(lab_name, f"nodes/{src_node_id}/interfaces")
            src_node_ports = client.get(src_interfaces_endpoint)["data"]["ethernet"]
            src_idx = get_interface_index(src_node_ports, src_label)

            # Determine if the destination is an existing network
            dst_network_id = find_id_by_name(networks, dst_node)
            is_network_dst = (dst_type == "network") or (dst_network_id is not None)

            if is_network_dst:
                # --- NODE-TO-NETWORK CONNECTION ---
                if not dst_network_id:
                    logger.error(f"Destination network '{dst_node}' not found. Skipping.")
                    sys.exit(1)
               
                # Connect source node interface directly to the existing network ID
                client.put(src_interfaces_endpoint, {src_idx: dst_network_id})
                logger.info(f"Connected node '{src_node}' directly to network '{dst_node}'")

            else:
                # --- NODE-TO-NODE CONNECTION ---
                dst_node_id = find_id_by_name(nodes, dst_node)
                if not dst_node_id:
                    logger.error(f"Destination node '{dst_node}' not found. Skipping.")
                    sys.exit(1)

                dst_interfaces_endpoint = client.get_lab_endpoint(lab_name, f"nodes/{dst_node_id}/interfaces")
                dst_node_ports = client.get(dst_interfaces_endpoint)["data"]["ethernet"]
                dst_idx = get_interface_index(dst_node_ports, dst_label)

                # Create a new transit bridge network for this link
                bid_data = {
                    "name": f"Net-{src_node_id}-{dst_node_id}",
                    "type": "bridge",
                    "left": 940,
                    "top": 196,
                    "visibility": 1,
                }
                bid_result = client.post(networks_endpoint, bid_data)
                bid = bid_result["data"].get("id")

                # Connect both nodes to the transit bridge, then hide it
                client.put(src_interfaces_endpoint, {src_idx: bid})
                client.put(dst_interfaces_endpoint, {dst_idx: bid})
               
                network_visibility_endpoint = client.get_lab_endpoint(lab_name, f"networks/{bid}")
                client.put(network_visibility_endpoint, {"visibility": 0})
                logger.info(f"Connected node '{src_node}' to node '{dst_node}' via bridge {bid}")

        logger.info("The cables for the lab have been connected.")
        print(f"Successfully connected the cables for lab {lab_name}")

    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")

    finally:
        client.logout()


def start_nodes(lab: str, nodes: list):
    """Starts each node listed in the lab_settings."""
    logger.debug(f"Func: start_nodes, Var: lab {lab}")
    logger.debug(f"Func: start_nodes, Var: nodes {nodes}")

    logger.info("Starting lab nodes")
    for node in nodes:
        node_name = node.get("name", "Unknown")
        logger.info(f"Starting node {node_name} ...")
        print(f"Starting node {node_name} ...")

        endpoint = client.get_lab_endpoint(lab, f"nodes/{node['id']}/start")
        logger.debug(f"Func: start_nodes, Var: endpoint {endpoint}")
        
        try:
            client.login()
            client.get(endpoint)
            if node.get("type") == "qemu":
                time.sleep(2)
            if node.get("type") == "vpcs":
                time.sleep(1)
        except Exception as err:
            logger.error(f"Error starting node {node_name}: {err}")
        finally:
            client.logout()
    # Give nodes a couple minutes to boot up before trying to load configs
    print("All nodes have been started. Waiting a couple minutes for them to boot.")
    time.sleep(120)


def get_telnet_type(device_type: str) -> str:
    """ Based on device template type return an appropriate string for the cconnect library to use for the console connection """
    match device_type:
        case "vpcs":
            return ("vpcs", "", "")
        case "veos":
            return ("arista_eos_telnet", "admin", "")
        case "vios":
            return ("cisco_ios_telnet", "admin", "")
        case _:
            return ("linux_telnet", "", "")


def load_base_configs(lab: str, lab_name: str, nodes: list):
    logger.info("Loading base configs...")

    for node in nodes:
        delay = 10
        max_attempts = 3
        node_name = node["name"]
        logger.info(f"Current node {node_name}")
        node_info = get_node_status(lab_name, node)
        logger.debug(f"Node status for node {node_name}: {node_info}")
        node_type = node_info.get("type")
        logger.debug(f"Func - load_base_configs, Var node_type: {node_type}")
        node_template = node_info.get("template")
        logger.debug(f"Func - load_base_configs, Var node_template: {node_template}")
        telnet_template, username, password = get_telnet_type(node_template)
        config_path = f"{lab}/configs/{node_name}.cfg"
        config_lines = utils.load_config(config_path)
        logger.debug(f"Func - load_base_configs, Var config_lines: {config_lines}")
        if not config_lines:
            logger.info(f"No config file was found for {node_name}.")
            print("No config files were found for this lab")
            choice = input("Would you like to continue? [y/n]: ")
            if choice != "y":
                sys.exit(0)
            else:
                continue
        else:
            for attempt in range(1, max_attempts + 1):
                logger.info(f"Attempt {attempt}: loading config for node {node_name}")
                print(f"Waiting for node {node_info['name']} to complete booting ...")
   
                if node_info.get("eve_ip") and node_info.get("port"):
                
                    # Default to qemu / Cisco IOS
                    device_settings = {
                        "device_ip": node_info["eve_ip"],
                        "device_type": telnet_template,
                        "port": node_info["port"],
                        "username": username,
                        "password": password,
                    }
                    logger.debug(f"Func - load_base_configs, Var device_settings: {device_settings}")

                    device = connect.DeviceConnection(**device_settings)

                    try:
                        device.connect()
                        device.write_config(config_lines)
                        device.disconnect()
                        print(f"Successfully loaded config for {node_name}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        logger.debug(f"Telnet not ready yet for {node_name}: {e}")

                time.sleep(delay)


def check_if_lab_exists(lab_name):
    """Check if the selected lab already exists in Eve-NG"""
    logger.info(f"Checking if lab {lab_name} already exists.")
   
    try:
        client.login()
        endpoint = client.get_lab_endpoint(lab_name)
        response = client.get(endpoint)
       
        # If no exception was raised, the lab exists
        if response and response.get("code") == 200:
            logger.warning(f"The lab {lab_name} already exists.")
            print(f"The lab {lab_name} already exists.")
            logger.info(f"Prompting to delete the lab or not")
            choice = input("Would you like to continue? If so the current lab will be deleted. [y/n]: ")
            if choice.lower() != "y":
                logger.info(f"The request was made to not delete the lab {lab_name}")
                logger.info(f"Exiting jlabs")
                client.logout()
                sys.exit(0)
            else:
                logger.info(f"The request was made to delete the lab")
                logger.info(f"Deleting lab {lab_name}...")
                delete_lab(lab_name)
        else:
            # Fallback just in case it returns a non-200 dict without throwing an error
            logger.info("Confirmed lab does not exist, attempting to create lab.")
           
    except Exception as err:
        error_msg = str(err)
        # Check if the exception is a 404 Not Found
        if "404" in error_msg or "Not Found" in error_msg or "does not exist" in error_msg:
            logger.info("Confirmed lab does not exist, attempting to create lab.")
        else:
            # This is a real error (e.g., connection refused, 500 server error)
            print(f"Failed check for lab existence {lab_name}: {err}")
            logger.error(f"Failed check for lab existence {lab_name}: {err}")
           
    finally:
        # Ensure logout always happens, even if an unexpected exception occurs
        client.logout()


def shutdown_lab(lab: str):
    """
    Core logic for shutting down a lab.
    """
    logger.debug(f"Func - shutdown_lab, Var - lab: {lab}")
    filename = f"{lab}/lab.toml"
    logger.debug(f"Func - shutdown_lab, Var - filename: {filename}")
    lab_settings = get_lab_settings(lab)
    logger.debug(f"Func - shutdown_lab, Var - lab_settings: {lab_settings}")
    lab_data = lab_settings.get("lab", "")
    lab_name = lab_data.get("name", "")
    lab_path = lab_data.get("path", "")
    full_lab_path = normalize_lab_path(lab_name, lab_path)
    logger.debug(f"full_lab_path: {full_lab_path}")
    logger.info(f"Shutting down lab {lab_name}")
    delete_lab(full_lab_path)
    logger.info(f"Removing state file {lab}")
    utils.remove_state_file()


def normalize_lab_path(lab_name: str, lab_path: str = "") -> str:
    """Ensures consistent, single-slash pathing without leading/trailing slashes."""
    if not lab_name.endswith(".unl"):
        lab_name = f"{lab_name}.unl"
    
    clean_path = lab_path.strip("/")
    clean_name = lab_name.strip("/")
    
    if clean_path:
        return clean_path + "/" + clean_name
    return clean_name


def _setup_lab(lab_folder: str, is_restart: bool = False):
    """
    Core logic for loading or restarting a lab.
    """
    action_verb = "Restarting" if is_restart else "Loading"
    logger.info(f"{action_verb} lab.toml file from {lab_folder}")

    try:
        lab_settings = get_lab_settings(lab_folder)
        logger.debug(f"VAR: lab_settings -  {lab_settings}")
        lab_data = lab_settings.get("lab", [])
        lab_nodes = lab_settings.get("nodes", [])
        lab_cables = lab_settings.get("cables", [])
        lab_name = lab_data.get("name", "")
        lab_path = lab_data.get("path", "")
        full_lab_path = normalize_lab_path(lab_name, lab_path)
        logger.debug(f"full_lab_path: {full_lab_path}")

        # Separate the nodes out based on the 'type' key
        qemu_nodes = [node for node in lab_nodes if node['type'] == 'qemu']
        vpcs_nodes = [node for node in lab_nodes if node['type'] == 'vpcs']
        logger.info(f"QEMU Nodes: {qemu_nodes}")
        logger.info(f"VPCS Nodes: {vpcs_nodes}")
        
        # If the request is to restart, don't check for lab existance
        if is_restart:
            delete_lab(lab_name)
        else:
            check_if_lab_exists(lab_name)
           
        create_lab(lab_data)
        add_nodes(full_lab_path, lab_nodes)
        connect_cables(full_lab_path, lab_cables)

        # Boot up all qemu nodes first
        if qemu_nodes:
            start_nodes(full_lab_path, qemu_nodes)
            load_base_configs(lab_folder, full_lab_path, qemu_nodes)

        # Boot VPCS last in case DHCP comes from qemu node
        if vpcs_nodes:
            start_nodes(full_lab_path, vpcs_nodes)
            load_base_configs(lab_folder, full_lab_path, vpcs_nodes)
       
        # save_state only for loading a new lab
        if not is_restart:
            utils.save_state(lab_folder)
           
    except Exception as e:
        action_lower = "restart" if is_restart else "load"
        print(f"Failed to {action_lower} lab {lab_folder}: {e}")


def load_lab(lab: str):
    _setup_lab(lab, is_restart=False)


def restart_lab(lab: str):
    _setup_lab(lab, is_restart=True)
