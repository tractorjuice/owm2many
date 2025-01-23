import os, re, json, toml, base64
import streamlit as st
import streamlit.components.v1 as components
from streamlit_option_menu import option_menu
from pyvis.network import Network
import yaml
import networkx as nx
from github import Github
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import rc
from IPython.display import HTML
from wardley_map import (
    create_wardley_map_plot,
    get_owm_map,
    convert_owm2json,
    convert_owm2toml,
    convert_owm2cypher,
    convert_owm2graph,
    convert_owm2yaml,
    parse_wardley_map
)

import matplotlib
matplotlib.use("Agg")  # Safe for Streamlit
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from io import BytesIO
import numpy as np
import time

API_ENDPOINT = "https://api.onlinewardleymaps.com/v1/maps/fetch?id="
GITHUB = st.secrets["GITHUB"]
GITHUBREPO = "swardley/MAP-REPOSITORY"
DEBUG = False  # True to overwrite files that already exist
MAP_ID = None

# Dictionary of map IDs with user-friendly names
map_dict = {
    "Tea Shop": "QRXryFJ8Q1NxhbHKQL",
    "Agriculture 2023 Research": "gQuu7Kby3yYveDngy2",
    "AI & Entertainment": "1LSW3jTlx4u16T06di",
    "Prompt Engineering": "mUJtoSmOfqlfXhNMJP",
    "Microsoft Fabric": "K4DjW1RdsbUWV8JzoP",
    "Fixed Penalty Notices": "gTTfD4r2mORudVFKge",
}


# Reset the map on page reload
def reset_map():
    st.session_state["messages"] = []
    st.session_state["total_tokens_used"] = 0
    st.session_state["tokens_used"] = 0
    st.session_state["past"] = []
    st.session_state["generated"] = []
    st.session_state["disabled_buttons"] = []


st.set_page_config(page_title="Convert Wardley Map", layout="wide")

if "map_text" not in st.session_state:
    st.session_state["map_text"] = []

if "current_map_id" not in st.session_state:
    st.session_state["current_map_id"] = []

with st.sidebar:
    selected = option_menu(
        "Choose conversion",
        [
            "WM to JSON",
            "WM to TOML",
            "WM to YAML",
            "WM to GRAPH",
            "WM to CYPHER",
            "WM to GML",
            "JSON to TOML",
            "Animate Map"  # New option for animation
        ],
        icons=["gear"] * 7,
        menu_icon="robot",
        default_index=0,
    )

try:
    g = Github(GITHUB)
    REPO = g.get_repo(GITHUBREPO)
except GithubException as e:
    st.error(f"An error occurred contacting GitHub: {e}")
    REPO = None

map_selection = st.sidebar.radio(
    "Map Selection",
    ("Select from GitHub", "Select from List", "Enter Map ID"),
    help="Select GitHub to get a list of Simon 's latest research.\n\nSelect from list to get predefined maps.\n\nSelect Enter Map ID to provide your own Onlinewardleymaps id",
    key="map_selection",
)

if map_selection == "Select from List":
    selected_name = st.sidebar.selectbox("Select Map", list(map_dict.keys()))
    MAP_ID = map_dict[selected_name]

elif map_selection == "Select from GitHub":
    with st.spinner("Fetching latest maps from GitHub"):
        if "file_list" not in st.session_state:
            st.session_state.file_list = []
            contents = REPO.get_contents("")
            while contents:
                file_item = contents.pop(0)
                if file_item.type == "dir":
                    contents.extend(REPO.get_contents(file_item.path))
                else:
                    file_name = file_item.name
                    # Check if the file name starts with a '.', has no extension, or is named 'LICENSE'
                    if (
                        not file_name.startswith(".")
                        and os.path.splitext(file_name)[1] == ""
                        and file_name.lower() != "license"
                    ):
                        st.session_state.file_list.append(file_item.path)

    if "file_list" in st.session_state:
        selected_file = st.sidebar.selectbox("Select a Map", st.session_state.file_list)
        file_item = REPO.get_contents(selected_file)
        file_content = base64.b64decode(file_item.content).decode("utf-8")
        MAP_ID = selected_file
        st.session_state["file_content"] = file_content
else:
    MAP_ID = st.sidebar.text_input("Enter Map ID:", key="map_id_input")
    selected_name = MAP_ID

if map_selection != "Select from GitHub":
    if st.session_state.get("current_map_id") != MAP_ID:
        reset_map()
        del st.session_state["messages"]
        st.session_state["current_map_id"] = MAP_ID
        st.session_state["map_text"] = get_owm_map(MAP_ID)

if map_selection == "Select from GitHub":
    if st.session_state.get("current_map_id") != MAP_ID:
        reset_map()
        st.session_state["current_map_id"] = MAP_ID
        st.session_state["map_text"] = st.session_state["file_content"]

# Display the map in the sidebar
if "map_text" in st.session_state:
    with st.sidebar:
        TITLE = "No Title"
        map_text = st.session_state["map_text"]
        for line in map_text.split("\n"):
            if line.startswith("title"):
                TITLE = line.split("title ")[1]
        if TITLE:
            st.markdown(f"### {TITLE}")

        # Get the Wardley Map
        map, map_plot = create_wardley_map_plot(map_text)

        # Display any warnings drawing the map
        if map.warnings:
            st.write("Warnings parsing and the drawing map")
            for map_message in map.warnings:
                st.warning(map_message)

if selected == "JSON to TOML":
    st.title("JSON to TOML file converter")
    st.write("			")
    st.write("Let's convert your Wardley Map in JSON to TOML")
    st.write("			")

    json_file = st.file_uploader("UPLOAD JSON FILE")
    st.info("👆 Upload your json file.")

    if json_file is not None:
        json_text = json_file.read()
        st.sidebar.write("JSON CONTENT")
        toml_content = toml.dumps(json.loads(json_text))
        st.write("TOML FILE CONTENT")
        st.code(toml_content, language="toml")
        toml_file_name = json_file.name.replace(".json", ".toml")
        st.download_button(
            "DOWNLOAD TOML FILE", data=toml_content, file_name=toml_file_name
        )
        st.code(json.loads(json_text))

elif selected == "WM to TOML":
    st.title("WM to TOML Converter")
    st.write("			")
    st.write("Let's convert your Wardley Map in WM to TOML			")
    st.write("			")

    wardley_map_toml = convert_owm2toml(st.session_state.map_text)
    st.write("TOML FILE CONTENT")

    toml_file_name = MAP_ID + ".toml"
    st.download_button(
        "DOWNLOAD TOML FILE", data=wardley_map_toml, file_name=toml_file_name
    )

    st.code(wardley_map_toml, language="toml")

elif selected == "WM to JSON":
    st.title("WM to JSON File Converter")
    st.write("			")
    st.write("Let's convert your Wardley Map in WM to JSON")
    st.write("			")

    wardley_map_json = convert_owm2json(st.session_state.map_text)
    st.write("JSON FILE CONTENT")

    json_file_name = MAP_ID + ".json"
    st.download_button(
        "DOWNLOAD JSON FILE", data=wardley_map_json, file_name=json_file_name
    )

    st.code(wardley_map_json, language="json")

elif selected == "WM to CYPHER":
    st.title("WM to CYPHER Converter")
    st.write("Let's convert your Wardley Map in WM to Cypher queries for Neo4j")

    NODE_SIZE = 5  # Adjust this value as needed to make the nodes smaller or larger
    FONT_SIZE = 6

    # Convert the Wardley map text to JSON (using your existing conversion logic)
    parsed_map = parse_wardley_map(st.session_state.map_text)

    # Initialize Cypher query list
    cypher_queries = []

    # Initialize the graph
    G = nx.DiGraph()

    # Define a color mapping for evolution stages
    evolution_colors = {
        "genesis": "#FF5733",
        "custom": "#33FF57",
        "product": "#3357FF",
        "commodity": "#F333FF",
    }

    # Add nodes with stage (evolution) and visibility
    for component in parsed_map["components"]:
        pos_str = component.get("pos", "[0, 0]")
        x, y = json.loads(pos_str)
        stage = component.get(
            "evolution", "unknown"
        )  # Default to 'unknown' if not specified
        node_color = evolution_colors.get(
            stage, "#f68b24"
        )  # Use a default color if the stage is not found
        G.add_node(
            component["name"],
            stage=stage,
            visibility=component["visibility"],
            pos=(x, y),
            color=node_color,
        )

    # Add edges with a check for existence of nodes
    for link in parsed_map["links"]:
        src, tgt = link["src"], link["tgt"]
        if src in G and tgt in G:
            G.add_edge(src, tgt)

    # Process pipelines
    for pipeline in parsed_map["pipelines"]:
        # Extract pipeline details
        pipeline_name = pipeline["name"]
        pipeline_x = pipeline["x"]  # Left side of the bounding box
        pipeline_right_side = pipeline["y"]  # Right side of the bounding box

        # Determine the pipeline's vertical position and height
        matching_component = next(
            (
                comp
                for comp in parsed_map["components"]
                if comp["name"] == pipeline["name"]
            ),
            None,
        )
        if matching_component:
            _, pipeline_y = json.loads(
                matching_component["pos"]
            )  # Use the y position of the matching component for the pipeline
            pipeline_bottom = (
                pipeline_y - 0.01
            )  # Assuming the bounding box is 10 units high

        # Ensure the pipeline node exists in the graph
        try:
            if pipeline_name not in G.nodes:
                G.add_node(pipeline_name, type="pipeline", pos=(pipeline_x, pipeline_y))
        except:
            st.sidebar.warning("Could not process pipeline")

        # Iterate over components in the pipeline and link them to the pipeline
        for component_name in pipeline["components"]:
            # Skip adding an edge to itself if the pipeline is named after a component
            if component_name == pipeline_name:
                continue

            if component_name in G.nodes:  # Check if the component node exists
                component_pos = G.nodes[component_name]["pos"]
                component_x, component_y = component_pos

                # Check if the component is within the pipeline's bounding box
                if (
                    pipeline_x <= component_x <= pipeline_right_side
                    and pipeline_bottom <= component_y <= pipeline_y
                ):
                    # Link the pipeline to the component
                    G.add_edge(pipeline_name, component_name)

    # Visualization with PyVis
    net = Network(height="1200px", width="100%", font_color="black")
    net.toggle_physics(False)

    # Add nodes to the PyVis network with colors based on their stage
    for node, node_attrs in G.nodes(data=True):
        pos = node_attrs.get("pos", (0, 0))
        x, y = pos
        node_color = node_attrs.get(
            "color", "#f68b24"
        )  # Use the color assigned based on the stage
        net.add_node(
            node, label=node, x=x * 1700, y=-y * 1000, color=node_color, size=NODE_SIZE
        )

    # Add edges to the PyVis network
    for src, tgt in G.edges():
        net.add_edge(src, tgt)

    # Save and display the network
    OUTPUT_PATH = "graph.html"
    net.save_graph(OUTPUT_PATH)
    with open(OUTPUT_PATH, "r", encoding="utf-8") as file:
        html_content = file.read()
    components.html(html_content, height=1200)

    # Generate Cypher queries for nodes
    cypher_script = convert_owm2cypher(st.session_state.map_text)

    # Display Cypher script
    st.write("CYPHER FILE CONTENT")

    # Add a download button for the Cypher script
    st.download_button(
        label="Download Cypher Script",
        data=cypher_script,
        file_name="wardley_map_to_cypher.cql",
        mime="text/plain",
    )

    st.code(cypher_script, language="cypher")

elif selected == "WM to GRAPH":

    st.title("WM to GRAPH Converter")
    st.write("Let's convert your Wardley Map in WM to GRAPH and visualize it.")

    NODE_SIZE = 5  # Adjust this value as needed to make the nodes smaller or larger
    FONT_SIZE = 6

    # Convert the Wardley map text to GRAPH
    parsed_map = parse_wardley_map(st.session_state.map_text)

    # Initialize the graph
    G = nx.DiGraph()

    # Define a color mapping for evolution stages
    evolution_colors = {
        "genesis": "#FF5733",
        "custom": "#33FF57",
        "product": "#3357FF",
        "commodity": "#F333FF",
    }

    # Add nodes with stage (evolution) and visibility
    for component in parsed_map["components"]:
        pos_str = component.get("pos", "[0, 0]")
        x, y = json.loads(pos_str)
        stage = component.get(
            "evolution", "unknown"
        )  # Default to 'unknown' if not specified
        node_color = evolution_colors.get(
            stage, "#f68b24"
        )  # Use a default color if the stage is not found
        G.add_node(
            component["name"],
            stage=stage,
            visibility=component["visibility"],
            pos=(x, y),
            color=node_color,
        )

    # Add edges with a check for existence of nodes
    for link in parsed_map["links"]:
        src, tgt = link["src"], link["tgt"]
        if src in G and tgt in G:
            G.add_edge(src, tgt)

    # Process pipelines
    for pipeline in parsed_map["pipelines"]:
        # Extract pipeline details
        pipeline_name = pipeline["name"]
        pipeline_x = pipeline["x"]  # Left side of the bounding box
        pipeline_right_side = pipeline["y"]  # Right side of the bounding box

        # Determine the pipeline's vertical position and height
        matching_component = next(
            (
                comp
                for comp in parsed_map["components"]
                if comp["name"] == pipeline["name"]
            ),
            None,
        )
        if matching_component:
            _, pipeline_y = json.loads(
                matching_component["pos"]
            )  # Use the y position of the matching component for the pipeline
            pipeline_bottom = (
                pipeline_y - 0.01
            )  # Assuming the bounding box is 10 units high

        # Ensure the pipeline node exists in the graph
        try:
            if pipeline_name not in G.nodes:
                G.add_node(pipeline_name, type="pipeline", pos=(pipeline_x, pipeline_y))
        except:
            st.sidebar.warning("Could not process pipeline")

        # Iterate over components in the pipeline and link them to the pipeline
        for component_name in pipeline["components"]:
            # Skip adding an edge to itself if the pipeline is named after a component
            if component_name == pipeline_name:
                continue

            if component_name in G.nodes:  # Check if the component node exists
                component_pos = G.nodes[component_name]["pos"]
                component_x, component_y = component_pos

                # Check if the component is within the pipeline's bounding box
                if (
                    pipeline_x <= component_x <= pipeline_right_side
                    and pipeline_bottom <= component_y <= pipeline_y
                ):
                    # Link the pipeline to the component
                    G.add_edge(pipeline_name, component_name)

    # Visualization with PyVis
    net = Network(height="1200px", width="100%", font_color="black")
    net.toggle_physics(False)

    # Add nodes to the PyVis network with colors based on their stage
    for node, node_attrs in G.nodes(data=True):
        pos = node_attrs.get("pos", (0, 0))
        x, y = pos
        node_color = node_attrs.get(
            "color", "#f68b24"
        )  # Use the color assigned based on the stage
        net.add_node(
            node, label=node, x=x * 1700, y=-y * 1000, color=node_color, size=NODE_SIZE
        )

    # Add edges to the PyVis network
    for src, tgt in G.edges():
        net.add_edge(src, tgt)

    # Save and display the network
    OUTPUT_PATH = "graph.html"
    net.save_graph(OUTPUT_PATH)
    with open(OUTPUT_PATH, "r", encoding="utf-8") as file:
        html_content = file.read()
    components.html(html_content, height=1200)

    # Convert the graph to a JSON format for download
    graph_json_str = convert_owm2graph(st.session_state.map_text)

    st.write("JSON FILE CONTENT")

    # Add a download button for the JSON file
    st.download_button(
        label="Download Graph JSON",
        data=graph_json_str,
        file_name="graph.json",
        mime="application/json",
    )

    st.code(graph_json_str, language="json")

# Handle "WM to GML" option
elif selected == "WM to GML":

    st.title("WM to GML Converter")  # Update the title to reflect the new functionality
    st.write("Let's convert your Wardley Map in WM to GML format and visualize it.")

    NODE_SIZE = 5  # Adjust this value as needed to make the nodes smaller or larger
    FONT_SIZE = 6

    # Convert the Wardley map text to JSON
    parsed_map = parse_wardley_map(st.session_state.map_text)

    # Initialize the graph
    G = nx.DiGraph()

    # Define a color mapping for evolution stages
    evolution_colors = {
        "genesis": "#FF5733",
        "custom": "#33FF57",
        "product": "#3357FF",
        "commodity": "#F333FF",
    }

    # Add nodes with stage (evolution) and visibility
    for component in parsed_map["components"]:
        pos_str = component.get("pos", "[0, 0]")
        x, y = json.loads(pos_str)
        stage = component.get(
            "evolution", "unknown"
        )  # Default to 'unknown' if not specified
        node_color = evolution_colors.get(
            stage, "#f68b24"
        )  # Use a default color if the stage is not found
        G.add_node(
            component["name"],
            stage=stage,
            visibility=component["visibility"],
            pos=(x, y),
            color=node_color,
        )

    # Add edges with a check for existence of nodes
    for link in parsed_map["links"]:
        src, tgt = link["src"], link["tgt"]
        if src in G and tgt in G:
            G.add_edge(src, tgt)

    # Process pipelines
    for pipeline in parsed_map["pipelines"]:
        # Extract pipeline details
        pipeline_name = pipeline["name"]
        pipeline_x = pipeline["x"]  # Left side of the bounding box
        pipeline_right_side = pipeline["y"]  # Right side of the bounding box

        # Determine the pipeline's vertical position and height
        matching_component = next(
            (
                comp
                for comp in parsed_map["components"]
                if comp["name"] == pipeline["name"]
            ),
            None,
        )
        if matching_component:
            _, pipeline_y = json.loads(
                matching_component["pos"]
            )  # Use the y position of the matching component for the pipeline
            pipeline_bottom = (
                pipeline_y - 0.01
            )  # Assuming the bounding box is 10 units high

        # Ensure the pipeline node exists in the graph
        try:
            if pipeline_name not in G.nodes:
                G.add_node(pipeline_name, type="pipeline", pos=(pipeline_x, pipeline_y))
        except:
            st.sidebar.warning("Could not process pipeline")

        # Iterate over components in the pipeline and link them to the pipeline
        for component_name in pipeline["components"]:
            # Skip adding an edge to itself if the pipeline is named after a component
            if component_name == pipeline_name:
                continue

            if component_name in G.nodes:  # Check if the component node exists
                component_pos = G.nodes[component_name]["pos"]
                component_x, component_y = component_pos

                # Check if the component is within the pipeline's bounding box
                if (
                    pipeline_x <= component_x <= pipeline_right_side
                    and pipeline_bottom <= component_y <= pipeline_y
                ):
                    # Link the pipeline to the component
                    G.add_edge(pipeline_name, component_name)

    # Visualization with PyVis
    net = Network(height="1200px", width="100%", font_color="black")
    net.toggle_physics(False)

    # Add nodes to the PyVis network with colors based on their stage
    for node, node_attrs in G.nodes(data=True):
        pos = node_attrs.get("pos", (0, 0))
        x, y = pos
        node_color = node_attrs.get(
            "color", "#f68b24"
        )  # Use the color assigned based on the stage
        net.add_node(
            node, label=node, x=x * 1700, y=-y * 1000, color=node_color, size=NODE_SIZE
        )

    # Add edges to the PyVis network
    for src, tgt in G.edges():
        net.add_edge(src, tgt)

    # Save and display the network
    OUTPUT_PATH = "graph.html"
    net.save_graph(OUTPUT_PATH)
    with open(OUTPUT_PATH, "r", encoding="utf-8") as file:
        html_content = file.read()
    components.html(html_content, height=1200)

    # Save the graph to a GML file
    GML_FILE_PATH = "graph.gml"
    nx.write_gml(G, GML_FILE_PATH)

    # Read the GML file content
    with open(GML_FILE_PATH, "r") as gml_file:
        gml_data = gml_file.read()

    # Display GML file content (optional, for verification)
    st.write("GML FILE CONTENT")

    # Add a download button for the GML file
    st.download_button(
        label="Download GML File", data=gml_data, file_name="graph.gml", mime="text/gml"
    )

    st.code(gml_data, language="gml")

# Handle WM to YAML option
elif selected == "WM to YAML":
    st.title("WM to YAML Converter")
    st.write("Let's convert your Wardley Map in WM to YAML format.")

    # Convert the parsed map to YAML
    wardley_map_yaml = convert_owm2yaml(st.session_state.map_text)

    # Display YAML file content
    st.write("YAML FILE CONTENT")

    # Add a download button for the YAML file
    st.download_button(
        label="Download YAML File",
        data=wardley_map_yaml,
        file_name="wardley_map.yaml",
        mime="text/yaml",
    )

    st.code(wardley_map_yaml, language="yaml")

elif selected == "Animate Map":
    st.title("Wardley Map Animation")

    # Make sure we have the parsed map
    parsed_map = parse_wardley_map(st.session_state.map_text)

    # Let the user pick an animation type
    animation_type = st.selectbox(
        "Animation Type",
        ["Components"]
    )

    # Let the user pick animation speed (milliseconds per frame)
    animation_speed = st.slider("Animation speed (ms per frame)", 100, 1000, 500, step=100)

    # Build the graph (similar to your other code)
    G = nx.DiGraph()
    evolution_colors = {
        "genesis": "#FF5733",
        "custom": "#33FF57",
        "product": "#3357FF",
        "commodity": "#F333FF"
    }

    # Identify anchors (nodes with no incoming edges) and normal components
    def identify_node_types(graph, components):
        anchors = []
        normal_components = []

        for component in components:
            name = component["name"]
            # Check if node has any incoming edges
            if name in graph and not any(v == name for u, v in graph.edges()):
                anchors.append(name)
            else:
                normal_components.append(name)

        return anchors, normal_components

    # Add nodes
    for component in parsed_map["components"]:
        pos_str = component.get("pos", "[0, 0]")
        x, y = json.loads(pos_str)
        stage = component.get("evolution", "unknown")
        node_color = evolution_colors.get(stage, "#f68b24")
        G.add_node(
            component["name"],
            stage=stage,
            visibility=component["visibility"],
            pos=(x, y),
            color=node_color
        )

    # Add edges
    for link in parsed_map["links"]:
        src, tgt = link["src"], link["tgt"]
        if src in G and tgt in G:
            G.add_edge(src, tgt)

    # Process pipelines
    for pipeline in parsed_map["pipelines"]:
        pipeline_name = pipeline["name"]
        pipeline_x = pipeline["x"]
        pipeline_right_side = pipeline["y"]

        matching_component = next(
            (comp for comp in parsed_map["components"] if comp["name"] == pipeline_name),
            None
        )

        if not matching_component:
            st.sidebar.warning(f"Skipping pipeline '{pipeline_name}' - no matching component found.")
            continue

        _, pipeline_y = json.loads(matching_component["pos"])
        pipeline_bottom = pipeline_y - 0.01

        if pipeline_name not in G.nodes:
            G.add_node(pipeline_name, type="pipeline", pos=(pipeline_x, pipeline_y))

        for component_name in pipeline["components"]:
            if component_name == pipeline_name:
                continue

            if component_name in G.nodes:
                cx, cy = G.nodes[component_name]["pos"]
                if (pipeline_x <= cx <= pipeline_right_side and
                    pipeline_bottom <= cy <= pipeline_y):
                    G.add_edge(pipeline_name, component_name)

    # Get node positions and colors
    pos = nx.get_node_attributes(G, 'pos')
    colors = [G.nodes[node]['color'] for node in G]

    # Identify anchors and normal components
    anchors, normal_components = identify_node_types(G, parsed_map["components"])

    # --- Create the animation ---
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_xlabel("Evolution")
    ax.set_ylabel("Value Chain")

    def init():
        ax.clear()
        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.set_xlabel("Evolution")
        ax.set_ylabel("Value Chain")
        nx.draw(G, pos, node_color=colors, with_labels=True, ax=ax)
        return []

    def update(frame):
        ax.clear()
        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.set_xlabel("Evolution")
        ax.set_ylabel("Value Chain")

        if animation_type == "Components":
            # Draw anchors
            nx.draw_networkx_nodes(G, pos, nodelist=anchors, node_color="red", ax=ax)
            anchor_edges = [(u, v) for (u, v) in G.edges() if u in anchors and v in anchors]
            nx.draw_networkx_edges(G, pos, edgelist=anchor_edges, ax=ax)

            # Reveal components progressively
            shown_count = min(frame, len(normal_components))
            shown_nodes = normal_components[:shown_count]
            nx.draw_networkx_nodes(G, pos, nodelist=shown_nodes, node_color="blue", ax=ax)

            # Draw edges for visible nodes
            partial_edges = [(u, v) for (u, v) in G.edges()
                           if (u in anchors or u in shown_nodes) and
                              (v in anchors or v in shown_nodes)]
            nx.draw_networkx_edges(G, pos, edgelist=partial_edges, ax=ax)

            # Labels for visible nodes
            label_dict = {n: n for n in anchors + shown_nodes}
            nx.draw_networkx_labels(G, pos, labels=label_dict, ax=ax)

        return []

    # Create and display animation
    ani = animation.FuncAnimation(
        fig, update, frames=50, init_func=init, interval=animation_speed, blit=False
    )

    # Convert to HTML and display
    html_ani = ani.to_jshtml()
    st.components.v1.html(html_ani, height=700)
    plt.close(fig)