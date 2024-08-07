import re
import yaml
import os
import argparse

# Define regex patterns for matching variables, object properties, default values, and conditionals
variable_pattern = re.compile(r"\* - (\w+): \[(\w+|object|array)\] (.*)")
object_property_pattern = re.compile(r"\*   - (\w+): \[(\w+)\] (.*)")
default_pattern = re.compile(r"{% set (\w+) = [^%]+ \? [^:]+ : (.+?) %}")
conditional_pattern = re.compile(r"{% if (\w+) %}")
default_pipe_pattern = re.compile(r"(\w+)\|default\(\'(.+?)\'\)")
null_coalescing_pattern = re.compile(r"\b(\w+)\s*\?\?\s*null\b")


# Define patterns for enum values associated with specific variables and components
enum_patterns = {
    "theme": ["light", "dark"],
    "direction": ["horizontal", "vertical"],
    "size": {
        "button": ["large", "regular", "small"],
        "chip": ["large", "regular", "small"],
        "field-description": ["large", "regular"],
        "paragraph": ["extra-large", "large", "regular", "small"],
        "label": ["extra-large", "large", "regular", "small", "extra-small"],
        "icon": ["small", "regular", "large"],
        "link-list": ["small", "regular", "large"],
    },
    "kind": {
        "button": ["submit", "reset", "button", "link"],
        "chip": ["default", "input"],
    },
    "type": {
        "button": ["primary", "secondary", "tertiary"],
        "field-message": ["error", "information", "warning", "success"],
        "tag": ["primary", "secondary", "tertiary"],
        "alert": ["info", "error", "warning", "success"],
        "message": ["info", "error", "warning", "success"],
        "navigation": ["none", "inline", "dropdown", "drawer"],
        "logo": ["default", "stacked", "inline", "inline-stacked"],
    },
    "icon_placement": {
        "button": ["left", "right"],
        "link": ["before", "after"],
        "tag": ["before", "after"],
    },
    "vertical_spacing": ["top", "bottom", "both"],
    "description_display": ["before", "after", "invisible"],
    "caption_position": ["before", "after"],
    "title_display": ["visible", "invisible", "hidden"],
    "orientation": ["vertical", "horizontal"],
}


def format_with_quotes(name):
    """
    Format the given name by replacing underscores with spaces, capitalizing it,
    and wrapping it in double quotes. If the name contains double quotes, they will be removed.

    Args:
        name (str): The name to format.

    Returns:
        str: The formatted name.
    """
    name = name.replace("_", " ").capitalize()
    if '"' in name:
        name = name.replace('"', "")
    if not name.startswith('"') or not name.endswith('"'):
        name = '"' + name + '"'
    return name


def find_include_file(directory, var_name):
    """
    Find the include file with the same name as the variable in the specified directory.

    Args:
        directory (str): The path to the directory to search.
        var_name (str): The name of the variable to search for.


    Returns:
        str: The path to the include file if found, None otherwise.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == f"{var_name}":
                include_file_path = os.path.join(root, file)
                return include_file_path
    return None


def check_variable_in_includes(twig_content, target_var_name):
    """
    Check if a variable name or its properties are present in the values of include statements
    and return the Twig file name if the variable or its properties are found in the values.
    Also return the variables and their properties inside the include block.

    Args:
        twig_content (str): The content of the Twig file.
        var_name (str): The variable name to search for.

    Returns:
        tuple: A tuple containing the Twig file name and a dictionary of variables found inside the include block.
               Returns (None, None) if the variable or its properties are not found.
    """
    # Regex pattern to capture include statements and variable definitions
    include_pattern = re.compile(
        r"{%\s*include\s*['\"]@[^/]+/[^/]+/([^'\"]+\.twig)['\"]\s*with\s*\{([^}]*)\}\s*only\s*%}"
    )

    # Dictionary to hold variables found inside include block
    include_variables_name = {}

    # Check for direct variable usage
    for include_match in include_pattern.finditer(twig_content):
        file_name = include_match.group(1)  # Extract the Twig file name
        variables_content = include_match.group(
            2
        )  # Extract the content inside the with clause

        # Extract variables from the with content
        variables_dict = {}
        for var_match in re.finditer(
            r"(\w+):\s*(\w+|\'[^\']*\'|\"[^\"]*\")", variables_content
        ):
            var_name_extracted = var_match.group(1).strip()
            var_value = var_match.group(2).strip()
            variables_dict[var_name_extracted] = var_value

        # Search for the target variable name or its properties in the with content
        if re.search(r"\b{}\b".format(re.escape(target_var_name)), variables_content):
            include_variables_name = variables_dict
            return file_name, include_variables_name

    # Check for indirect usage
    # Example: Detect variables used in loops
    for loop_match in re.finditer(r"{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}", twig_content):
        loop_var = loop_match.group(1)  # The loop variable (e.g., 'tag')
        loop_source = loop_match.group(2)  # The source variable (e.g., 'tags')

        if loop_source == target_var_name:
            # Extract the content where the loop variable is used
            loop_content_start = loop_match.end()
            loop_content_end = twig_content.find("{% endfor %}", loop_content_start)
            loop_content = twig_content[loop_content_start:loop_content_end]

            if re.search(r"\b{}\b".format(re.escape(loop_var)), loop_content):
                # If the loop variable is used in an include, consider indirect match
                for include_match in include_pattern.finditer(loop_content):
                    file_name = include_match.group(1)  # Extract the Twig file name
                    variables_content = include_match.group(
                        2
                    )  # Extract the content inside the with clause

                    # Extract variables from the with content
                    variables_dict = {}
                    for var_match in re.finditer(
                        r"(\w+):\s*(\w+|\'[^\']*\'|\"[^\"]*\")", variables_content
                    ):
                        var_name_extracted = var_match.group(1).strip()
                        var_value = var_match.group(2).strip()
                        variables_dict[var_name_extracted] = var_value

                    if re.search(
                        r"\b{}\b".format(re.escape(loop_var)), variables_content
                    ):
                        include_variables_name = variables_dict
                        return file_name, include_variables_name
    return None, None


def get_common_properties(include_variables_name, include_variables):
    """
    Get the common properties between two dictionaries.

    Args:
        include_variables_name (dict): The dictionary of variables from the include block.
        include_variables (dict): The dictionary of variables from the parsed include file.

    Returns:
        dict: A dictionary containing common properties.
    """
    common_properties = {
        key: include_variables[key]
        for key in include_variables
        if key in include_variables_name
    }
    return common_properties


def filter_properties(properties, all_variable_names_twig_filtered, var_name):
    filtered_properties = {}
    for key, value in properties.items():
        if key not in all_variable_names_twig_filtered and key != var_name:
            if "properties" in value and isinstance(value["properties"], dict):
                nested_filtered = filter_properties(
                    value["properties"], all_variable_names_twig_filtered, var_name
                )
                if nested_filtered:
                    value["properties"] = nested_filtered
                else:
                    value.pop("properties", None)
            filtered_properties[key] = value
        elif key == var_name:
            nested_type = get_last_child_type(value)
            if nested_type:
                filtered_properties["type"] = nested_type
                filtered_properties["array_type"] = True
    return filtered_properties


def get_last_child_type(properties):
    last_child_type = None
    for key, value in properties.items():
        if "properties" in value:
            last_child_type = get_last_child_type(value["properties"])
        elif "type" in value:
            last_child_type = value["type"]
    return last_child_type


def parse_variables(twig_content, component_name, file_directory, include_directory):
    """
    Parse variables from Twig content, extract slots and conditional variables.

    Args:
      twig_content (str): The content of the Twig file.
      component_name (str): The name of the component.
      file_directory (str): The directory where the Twig file is located.

    Returns:
      tuple: A tuple containing variables dictionary, slots dictionary, and conditional variables set.
    """
    variables = {}
    slots = {}
    conditional_variables = set()

    all_variable_names_twig = []

    all_variable_names_twig = []
    for match in variable_pattern.finditer(twig_content):
        var_name, var_type, var_desc = match.groups()
        all_variable_names_twig.append(var_name)

    # Find all variable matches in the Twig content
    for match in variable_pattern.finditer(twig_content):
        var_name, var_type, var_desc = match.groups()

        # Detect and handle slots
        if "slot" in var_desc.lower():
            slots[var_name] = {
                "title": var_name.replace("_", " ").capitalize(),
                "description": var_desc,
            }
            continue

        # Create an entry for the variable
        variable_entry = {
            "type": var_type if var_type != "object" else "object",
            "title": var_name.replace("_", " ").capitalize(),
            "description": var_desc,
        }

        # Add enum values if applicable
        enums = enum_patterns.get(var_name, None)
        if isinstance(enums, dict):
            enums = enums.get(component_name, None)
        if enums:
            variable_entry["default"] = enums[0]
            variable_entry["enum"] = enums

        # Handle object properties
        if var_type == "object":
            variable_entry["properties"] = {}
            object_scope_pattern = re.compile(
                rf"\* - {var_name}: \[object\](.*?)(\* - |\Z)", re.DOTALL
            )
            object_scope_match = object_scope_pattern.search(twig_content)
            if object_scope_match:
                object_scope_content = object_scope_match.group(1)
                for obj_match in object_property_pattern.finditer(object_scope_content):
                    obj_name, obj_type, obj_desc = obj_match.groups()
                    variable_entry["properties"][obj_name] = {
                        "type": obj_type,
                        "title": obj_name.replace("_", " ").capitalize(),
                        "description": obj_desc,
                    }

        # Handle array properties
        if var_type == "array":
            # Check if the array type is defined in an include file
            file_name, include_variables_name = check_variable_in_includes(
                twig_content, var_name
            )
            include_file_path = find_include_file(include_directory, file_name)

            if include_file_path:
                with open(include_file_path, "r") as include_file:
                    include_content = include_file.read()
                    include_variables, _, _ = parse_variables(
                        include_content,
                        component_name,
                        file_directory,
                        include_directory,
                    )
                    common_properties = get_common_properties(
                        include_variables_name, include_variables
                    )
                    all_variable_names_twig_filtered = [
                        item for item in all_variable_names_twig if item != var_name
                    ]
                    filtered_properties = filter_properties(
                        common_properties, all_variable_names_twig_filtered, var_name
                    )
                    if (
                        "array_type" in filtered_properties
                        and filtered_properties["array_type"]
                    ):
                        filtered_properties.pop("array_type")
                        variable_entry["items"] = filtered_properties
                    else:
                        variable_entry["items"] = {
                            "type": "object",
                            "properties": filtered_properties,
                        }

            else:
                # Process array items inline
                array_scope_pattern = re.compile(
                    rf"\* - {var_name}: \[array\](.*?)(\* - |\Z)", re.DOTALL
                )
                array_scope_match = array_scope_pattern.search(twig_content)
                if array_scope_match:
                    array_scope_content = array_scope_match.group(1)
                    array_items = {}

                    for arr_match in object_property_pattern.finditer(
                        array_scope_content
                    ):
                        arr_name, arr_type, arr_desc = arr_match.groups()
                        array_items[arr_name] = {
                            "type": arr_type,
                            "title": arr_name.replace("_", " ").capitalize(),
                            "description": arr_desc,
                        }

                        if array_items:
                            variable_entry["items"] = {
                                "type": "object",
                                "properties": array_items,
                            }
                        else:
                            del variable_entry[
                                "items"
                            ]  # Remove items if no properties found

        variables[var_name] = variable_entry

    # Extract default values from Twig set statements
    matches = default_pattern.findall(twig_content)
    for variable_name, default_value in matches:
        default_value = default_value.strip().replace("'", "").replace('"', "")
        if variable_name in variables:
            if default_value == "null":
                default_value = None
            variables[variable_name]["default"] = default_value

    # Extract default values from patterns like variable|default('value')
    pipe_matches = default_pipe_pattern.findall(twig_content)
    for variable_name, default_value in pipe_matches:
        default_value = default_value.strip().replace("'", "").replace('"', "")
        if variable_name in variables:
            if default_value == "null":
                default_value = None
            variables[variable_name]["default"] = default_value

    # Extract variables used in conditional statements
    for match in conditional_pattern.finditer(twig_content):
        conditional_variables.add(match.group(1))

    for match in null_coalescing_pattern.finditer(twig_content):
        conditional_variables.add(match.group(1))

    return variables, slots, conditional_variables


def generate_yaml(component_name, variables, slots, has_js_file, conditional_variables):
    """
    Generate YAML data for the component based on parsed variables and slots.

    Args:
      component_name (str): The name of the component.
      variables (dict): The variables dictionary.
      slots (dict): The slots dictionary.
      has_js_file (bool): Whether a JavaScript file exists for the component.
      conditional_variables (set): Set of conditional variables.

    Returns:
      str: The generated YAML as a string.
    """
    # Determine required fields based on descriptions, default values, and conditionals
    required_fields = []
    for key, var in variables.items():
        if key in ["attributes", "modifier_class"]:
            continue
        if (
            "optional" not in var.get("description", "")
            and var.get("type") != "boolean"
        ):
            if "default" not in var and key not in conditional_variables:
                required_fields.append(key)

    yaml_data = {
        "name": component_name,
        "status": "experimental",
        "group": "default",
        "props": {"type": "object"},
    }

    # Add required fields inside props before properties if not empty
    if required_fields:
        yaml_data["props"]["required"] = required_fields

    # Include properties
    yaml_data["props"]["properties"] = variables  # Include all variables

    # Add slots if not empty
    if slots:
        yaml_data["slots"] = slots

    # Include JavaScript library override if applicable
    if has_js_file:
        yaml_data["libraryOverrides"] = {"js": {f"{component_name.lower()}.js": {}}}

    return yaml.dump(yaml_data, sort_keys=False, default_flow_style=False, indent=2)


def process_directory(directory, include_directory):
    """
    Process all Twig files in a directory, generate YAML configurations for each component.

    Args:
      directory (str): The path to the directory containing Twig files.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".twig"):
                component_name = file.split(".")[0]
                file_path = os.path.join(root, file)
                # Check for the existence of a JS file
                js_file_path = os.path.join(root, f"{component_name.lower()}.js")
                has_js_file = os.path.exists(js_file_path)

                # Read and parse the Twig file content
                with open(file_path, "r") as twig_file:
                    twig_content = twig_file.read()
                    variables, slots, conditional_variables = parse_variables(
                        twig_content, component_name, root, include_directory
                    )

                # Generate YAML content and write to .component.yml file
                yaml_output = generate_yaml(
                    component_name, variables, slots, has_js_file, conditional_variables
                )
                yaml_file_path = os.path.join(
                    root, f"{component_name.lower()}.component.yml"
                )
                with open(yaml_file_path, "w") as yaml_file:
                    yaml_file.write(yaml_output)

                folder_component_type_mapping = {
                    "00-base": "a base",
                    "01-atoms": "an atom",
                    "02-molecules": "a molecule",
                    "03-organisms": "a organism",
                    "04-templates": "a template",
                }
                component_type = ""
                for key in folder_component_type_mapping:
                    if key in file_path:
                        component_type = folder_component_type_mapping[key]
                        break
                # Create a string with the desired content
                readme_content = f"""
Starshot Demo Design System {component_name.replace('-', ' ').capitalize()}

## Usage
This component is {component_type} which can be used on its own or within other components.
"""
                # Open a file in write mode and write the content to it
                readme_file_path = os.path.join(root, "README.md")
                with open(readme_file_path, "w") as file:
                    file.write(readme_content)
                # Print relative path of processed files
                relative_file_path = os.path.relpath(file_path, directory)
                relative_yaml_path = os.path.relpath(yaml_file_path, directory)
                print(
                    f"Processed {relative_file_path}, output saved to {relative_yaml_path}"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Process Twig files and generate YAML output."
    )
    parser.add_argument(
        "directory", help="Path to the directory containing Twig files."
    )
    parser.add_argument(
        "include_directory", help="Path to the directory containing include files."
    )

    args = parser.parse_args()

    process_directory(args.directory, args.include_directory)


if __name__ == "__main__":
    main()
