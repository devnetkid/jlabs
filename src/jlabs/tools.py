# src/jlabs/tools.py

import logging

from jlabs import eveng, utils

logger = logging.getLogger(__name__)

client = eveng.EveNgClient()


def define_lab_details(lab_data: dict) -> dict:
    """Define the parameters needed to create a new lab."""
    for key in ["id", "lock", "filename"]:
        lab_data.pop(key, None)

    lab_data["path"] = "/"
    lab_data["name"] = f"{lab_data.get('name', 'unnamed')}_temp"
    return lab_data


def build_nodes_list(lab_nodes: dict) -> tuple[list, list]:
    """Builds a list of nodes removing items that aren't needed to re-create the lab."""
    nodes = []
    node_map = []
    for node in lab_nodes.values():
        for key in ["url", "uuid", "config", "config_list"]:
            node.pop(key, None)
        nodes.append(node)
        node_map.append({f"node{node['id']}": node["name"]})
    return nodes, node_map


def build_cable_list(lab_cables: list, node_map: list) -> list:
    """Builds a list of cable connections from an existing eve-ng lab."""
    node_lookup = {}
    for node in node_map:
        node_lookup.update(node)

    cables = []
    for cable in lab_cables:
        new_cable = {k: v for k, v in cable.items() if k != "network_id"}
        new_cable["source"] = node_lookup.get(new_cable["source"], new_cable["source"])
        new_cable["destination"] = node_lookup.get(
            new_cable["destination"], new_cable["destination"]
        )
        cables.append(new_cable)

    return cables


def create_toml(lab_name):
    """Returns a toml formatted file representing the specified eve-ng lab."""
    toml_data = {}
    logger.info(f"Attempting to create lab.toml from Eve-NG lab name {lab_name}")

    try:
        client.login()
        lab_data = client.get(f"labs/{lab_name}.unl").get("data")
        lab_nodes = client.get(f"labs/{lab_name}.unl/nodes").get("data", {})
        lab_cables = client.get(f"labs/{lab_name}.unl/topology").get("data", [])
    except Exception as err:
        print(f"A network error occurred communicating with EVE-NG: \n{err}")
        return
    finally:
        client.logout()

    if not lab_data:
        print("No lab data found.")
        return

    toml_data["lab"] = define_lab_details(lab_data)
    nodes, node_map = build_nodes_list(lab_nodes)
    toml_data["nodes"] = nodes
    toml_data["cables"] = build_cable_list(lab_cables, node_map)

    file_name = "lab.toml"
    utils.write_toml(file_name, toml_data)
    logger.info(f"Successfully saved lab name '{lab_name}' to file '{file_name}'")
