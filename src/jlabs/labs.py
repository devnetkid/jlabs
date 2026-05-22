# src/jlabs/labs.py

import logging
import os
import sys
import time

from jlabs import connect, eveng, utils

logger = logging.getLogger(__name__)

EVENG_IP = os.getenv("EVENG_IP", None)
if EVENG_IP == None:
    print("You must define your Eve-NG IP address in an environment variable EVENG_IP.")
    sys.exit(0)
    
client = eveng.EveNgClient(EVENG_IP)

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

    endpoint = f"labs/{lab}/nodes/{node['id']}"
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
        # Fetch all nodes in the lab
        nodes_response = client.get(f"labs/{lab_name}/nodes")
        nodes = nodes_response.get("data", {})
        
        if not nodes:
            logger.info("No nodes found in lab.")
            return

        # Iterate through the dictionary of nodes
        for node_id, node_data in nodes.items():
            # In EVE-NG, status 2 means running, 0 means stopped
            if node_data.get('status') == 2:
                node_name = node_data.get('name', f"Node_{node_id}")
                print(f"Stopping node {node_name}...")
                client.get(f"labs/{lab_name}/nodes/{node_id}/stop")
                time.sleep(1)  # Brief pause to avoid overwhelming the server API
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with EVE-NG while stopping nodes: {e}")
        print(f"Warning: Could not verify or stop nodes due to a network error.")
    finally:
        client.logout()


def delete_lab(lab_name: str):
    """Delete a lab from eve-ng"""
    
    # Step 1: Ensure all nodes are stopped before attempting deletion
    stop_nodes(lab_name)
    
    # Step 2: Proceed with deleting the lab file
    url = f"labs/{lab_name}"
    try:
        client.login()
        response = client.delete(url)
        logger.debug(f"Deleted lab {lab_name}, response from server was {response}")
        
        # Check if the API actually returned a success code (usually 200 or 201)
        if response in [200, 201, 204]:
            print(f"The eve-ng lab '{lab_name}' has been deleted.")
        else:
            print(f"Server responded, but lab may not have deleted: {response.get('message', 'Unknown error')}")
            
    except requests.exceptions.RequestException as err:
        print(f"Failed to delete lab: \n{err}")
    finally:
        client.logout()
        
    input("Press [ENTER] to continue...")


def find_node_id_by_name(nodes: dict, src_node: str, dst_node: str) -> tuple[str, str]:
    src_node_id = dst_node_id = ""
    for value in nodes.values():
        if value["name"] == src_node:
            src_node_id = value["id"]
        if value["name"] == dst_node:
            dst_node_id = value["id"]
    return src_node_id, dst_node_id


def get_interface_index(ports: list, label: str) -> str:
    for index, item in enumerate(ports):
        if label == item["name"]:
            return str(index)
    return ""


def create_lab(lab_data):
    """Creates a new lab in eve-ng based on the contents of a toml config file."""
    lab_name = lab_data["name"] + ".unl"
    logger.info(f"Attempting to create lab {lab_name}")
    try:
        client.login()
        client.post("labs", lab_data)
    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")
    finally:
        client.logout()
        logger.info("Successfully created a new lab.")


def add_nodes(lab_name, lab_nodes):
    """Adding nodes to the Eve-NG lab as noted in the toml config file"""
    logger.info(f"Adding nodes to the lab {lab_name}")
    try:
        for node in lab_nodes:
            client.login()
            client.post(f"labs/{lab_name}/nodes", node)
    except Exception as err:
        print(f"An error occurred creating the lab: \n{err}")
    finally:
        client.logout()
        logger.info("Successfully added nodes to the new lab.")


def connect_cables(lab_name, lab_cables):
    """Connecting the requested cables per lab.toml file"""
    logger.info(f"Connecting requested cables for the lab {lab_name}")
    logger.info(f"cables for the lab {lab_cables}")
    
    try:
        client.login()
        # Get the ID assigned to each node so we know where to attach cable
        nodes = client.get(f"labs/{lab_name}/nodes")["data"]
        logger.info("The following is the node data pulled from the lab:")
        logger.info(nodes)
        for cable in lab_cables:
            src_node, dst_node = cable.get("source"), cable.get("destination")
            src_label, dst_label = cable.get("source_label"), cable.get(
                "destination_label"
            )

            src_node_id, dst_node_id = find_node_id_by_name(nodes, src_node, dst_node)
            logger.info(f"src_node_id is {src_node_id}")
            logger.info(f"dst_node_id is {dst_node_id}")

            src_node_ports = client.get(
                f"labs/{lab_name}/nodes/{src_node_id}/interfaces"
            )["data"]["ethernet"]
            dst_node_ports = client.get(
                f"labs/{lab_name}/nodes/{dst_node_id}/interfaces"
            )["data"]["ethernet"]

            bid_data = {
                "name": "Net-1",
                "type": "bridge",
                "left": 940,
                "top": 196,
                "visibility": 1,
            }
            bid_result = client.post(f"labs/{lab_name}/networks", bid_data)
            bid = bid_result["data"].get("id")

            src_idx = get_interface_index(src_node_ports, src_label)
            dst_idx = get_interface_index(dst_node_ports, dst_label)

            client.put(
                f"labs/{lab_name}/nodes/{src_node_id}/interfaces", {src_idx: bid}
            )
            client.put(
                f"labs/{lab_name}/nodes/{dst_node_id}/interfaces", {dst_idx: bid}
            )
            client.put(f"labs/{lab_name}/networks/{bid}", {"visibility": 0})

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

        endpoint = f"labs/{lab}/nodes/{node['id']}/start"
        try:
            client.login()
            client.get(endpoint)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error starting node {node_name}: {e}")
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
        logger.info(f"Node status for node {node_name}: {node_info}")

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
        response = client.get(f"labs/{lab_name}")
        
        # If no exception was raised, the lab exists
        if response and response.get("code") == 200:
            logger.warning(f"The lab {lab_name} already exists.")
            print(f"The lab {lab_name} already exists.")
            
            choice = input("Would you like to continue? If so the current lab will be deleted. [y/n]: ")
            if choice.lower() != "y":
                client.logout()
                sys.exit(0)
            else:
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


def load_lab(lab: str):
    logger.info(f"Loading lab.toml file from {lab}")
    filename = f"{lab}/lab.toml"

    try:
        lab_settings = utils.load_toml(str(filename))
        lab_name = lab_settings["lab"]["name"]
        if not lab_name.endswith(".unl"):
            lab_name = f"{lab_name}.unl"
        lab_data = lab_settings.get("lab", [])
        lab_nodes = lab_settings.get("nodes", [])
        lab_cables = lab_settings.get("cables", [])
        check_if_lab_exists(lab_name)
        create_lab(lab_data)
        add_nodes(lab_name, lab_nodes)
        connect_cables(lab_name, lab_cables)
        start_nodes(lab_name, lab_nodes)
        load_base_configs(lab, lab_name, lab_nodes)
        utils.save_state(lab)
    except Exception as e:
        print(f"Failed to load lab {lab}: {e}")
