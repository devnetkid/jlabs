# src/jlabs/labs.py

import logging
import os
import sys
import time

from jlabs import connect, eveng, utils

logger = logging.getLogger(__name__)

client = eveng.EveNgClient()

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
               
                stop_endpoint = client.get_lab_endpoint(lab_name, f"nodes/{node_id}/stop")
                client.get(stop_endpoint)
                time.sleep(1)  # Brief pause to avoid overwhelming the server API
               
    except Exception as err:
        logger.error(f"Error communicating with EVE-NG while stopping nodes: {err}")
        print(f"Warning: Could not verify or stop nodes due to a network error.")
    finally:
        client.logout()


def delete_lab(lab_name: str):
    """Delete a lab from eve-ng"""
   
    # Step 1: Ensure all nodes are stopped before attempting deletion
    stop_nodes(lab_name)
   
    # Step 2: Proceed with deleting the lab file
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
    lab_name = lab_data["name"] + ".unl"
    logger.info(f"Attempting to create lab {lab_name}")
    print(f"Creating the lab {lab_name}")
    try:
        client.login()
        # Creating a lab always POSTs to the base 'labs' endpoint with lab path payload
        client.post("labs", lab_data)
    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")
    finally:
        client.logout()
        logger.info("Successfully created a new lab.")
        print(f"Successfully created lab {lab_name}")


def add_nodes(lab_name, lab_nodes):
    """Adding nodes to the Eve-NG lab as noted in the toml config file"""
    logger.info(f"Adding nodes to the lab {lab_name}")
    print(f"Adding the nodes to lab {lab_name}")
    try:
        for node in lab_nodes:
            client.login()
            nodes_endpoint = client.get_lab_endpoint(lab_name, "nodes")
            client.post(nodes_endpoint, node)
    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")
    finally:
        client.logout()
        logger.info("Successfully added nodes to the new lab.")
        print(f"Successfully added nodes for lab {lab_name}")


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
                    continue
               
                # Connect source node interface directly to the existing network ID
                client.put(src_interfaces_endpoint, {src_idx: dst_network_id})
                logger.info(f"Connected node '{src_node}' directly to network '{dst_node}'")

            else:
                # --- NODE-TO-NODE CONNECTION ---
                dst_node_id = find_id_by_name(nodes, dst_node)
                if not dst_node_id:
                    logger.error(f"Destination node '{dst_node}' not found. Skipping.")
                    continue

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
    logger.info("Starting lab nodes")
    for node in nodes:
        node_name = node.get("name", "Unknown")
        logger.info(f"Starting node {node_name} ...")
        print(f"Starting node {node_name} ...")

        endpoint = client.get_lab_endpoint(lab, f"nodes/{node['id']}/start")
        try:
            client.login()
            client.get(endpoint)
        except Exception as err:
            logger.error(f"Error starting node {node_name}: {err}")
        finally:
            client.logout()
        time.sleep(3)


def load_base_configs(lab: str, lab_name: str, nodes: list):
    logger.info("Loading base configs...")

    for node in nodes:
        delay = 10
        max_attempts = 30
        node_name = node["name"]
        logger.info(f"Current node {node_name}")
        node_info = get_node_status(lab_name, node)
        logger.debug(f"Node status for node {node_name}: {node_info}")

        # If type is other, like vpcs, then go to next iteration
        if node_info["type"] != "qemu":
            logger.info("Node is not a qemu node, getting next iteration.")
            continue

        config_path = f"{lab}/configs/{node_name}.cfg"
        config_lines = utils.load_config(config_path)
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
   
                if (node_info["eve_ip"] and node_info["port"]):
                    device_settings = {
                        "device_ip": node_info["eve_ip"],
                        "device_type": "cisco_ios_telnet",
                        "port": node_info["port"],
                        "username": "admin",
                        "password": "cisco",
                    }
   
                    device = connect.DeviceConnection(**device_settings)
   
                    try:
                        device.connect()
                        device.write_config(config_lines)
                        device.disconnect()
                        print(f"Successfully loaded config for {node_name}")
                        break  # Success, exit retry loop
                    except Exception as e:
                        logger.debug(f"SSH/Telnet not ready yet: {e}")
               
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
   
    filename = f"{lab}/lab.toml"

    lab_settings = utils.load_toml(str(filename))
    lab_name = lab_settings["lab"]["name"]
   
    if not lab_name.endswith(".unl"):
        lab_name = f"{lab_name}.unl"
       
    logger.info(f"Shutting down lab {lab_name}")
    delete_lab(lab_name)
    logger.info(f"Removing state file {lab}")
    utils.remove_state_file()


def _setup_lab(lab: str, is_restart: bool = False):
    """
    Core logic for loading or restarting a lab.
    """
    action_verb = "Restarting" if is_restart else "Loading"
    logger.info(f"{action_verb} lab.toml file from {lab}")
   
    filename = f"{lab}/lab.toml"

    try:
        lab_settings = utils.load_toml(str(filename))
        lab_name = lab_settings["lab"]["name"]
       
        if not lab_name.endswith(".unl"):
            lab_name = f"{lab_name}.unl"
           
        lab_data = lab_settings.get("lab", [])
        lab_nodes = lab_settings.get("nodes", [])
        lab_cables = lab_settings.get("cables", [])
       
        # If the request is to restart don't check for lab existance
        if is_restart:
            delete_lab(lab_name)
        else:
            check_if_lab_exists(lab_name)
           
        create_lab(lab_data)
        add_nodes(lab_name, lab_nodes)
        connect_cables(lab_name, lab_cables)
        start_nodes(lab_name, lab_nodes)
        load_base_configs(lab, lab_name, lab_nodes)
       
        # save_state only for loading a new lab
        if not is_restart:
            utils.save_state(lab)
           
    except Exception as e:
        action_lower = "restart" if is_restart else "load"
        print(f"Failed to {action_lower} lab {lab}: {e}")


def load_lab(lab: str):
    _setup_lab(lab, is_restart=False)


def restart_lab(lab: str):
    _setup_lab(lab, is_restart=True)
