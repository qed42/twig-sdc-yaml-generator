import re
import yaml
import os
import argparse

# Define regex patterns for matching variables, object properties, default values, and conditionals
variable_pattern = re.compile(r'\* - (\w+): \[(\w+|object|array)\] (.*)')
object_property_pattern = re.compile(r'\*   - (\w+): \[(\w+)\] (.*)')
default_pattern = re.compile(r'{% set (\w+) = [^%]+ \? [^:]+ : (.+?) %}')
conditional_pattern = re.compile(r'{% if (\w+) %}')

# Define patterns for enum values associated with specific variables and components
enum_patterns = {
  'theme': ['light', 'dark'],
  'direction': ['horizontal', 'vertical'],
  'size': {
    'button': ['large', 'regular', 'small'],
    'chip': ['large', 'regular', 'small'],
    'field-description': ['large', 'regular'],
    'paragraph': ['extra-large', 'large', 'regular', 'small'],
    'label': ['extra-large', 'large', 'regular', 'small', 'extra-small'],
    'icon': ['small', 'regular', 'large'],
    'link-list': ['small', 'regular', 'large'],
  },
  'kind': {
    'button': ['submit', 'reset', 'button', 'link'],
    'chip': ['default', 'input']
  },
  'type': {
    'button': ['primary', 'secondary', 'tertiary'],
    'field-message': ['error', 'information', 'warning', 'success'],
    'tag': ['primary', 'secondary', 'tertiary'],
    'alert': ['info', 'error', 'warning', 'success'],
    'message': ['info', 'error', 'warning', 'success'],
    'navigation': ['none', 'inline', 'dropdown', 'drawer'],
    'logo': ['default', 'stacked', 'inline', 'inline-stacked']
  },
  'icon_placement': {
    'button': ['left', 'right'],
    'link': ['before', 'after'],
    'tag': ['before', 'after']
  },
  'vertical_spacing': ['top', 'bottom', 'both'],
  'description_display': ['before', 'after', 'invisible'],
  'caption_position': ['before', 'after'],
  'title_display': ['visible', 'invisible', 'hidden'],
  'orientation': ['vertical', 'horizontal']
}

def parse_variables(twig_content, component_name):
  """
  Parse variables from Twig content, extract slots and conditional variables.

  Args:
    twig_content (str): The content of the Twig file.
    component_name (str): The name of the component.

  Returns:
    tuple: A tuple containing variables dictionary, slots dictionary, and conditional variables set.
  """
  variables = {}
  slots = {}
  conditional_variables = set()

  # Find all variable matches in the Twig content
  for match in variable_pattern.finditer(twig_content):
    var_name, var_type, var_desc = match.groups()

    # Detect and handle slots
    if 'slot' in var_desc.lower():
      slots[var_name] = {
        'title': var_name.replace('_', ' ').capitalize(),
        'description': var_desc
      }
      continue

    # Create an entry for the variable
    variable_entry = {
      'type': var_type if var_type != 'object' else 'object',
      'title': var_name.replace('_', ' ').capitalize(),
      'description': var_desc
    }

    # Add enum values if applicable
    enums = enum_patterns.get(var_name, None)
    if isinstance(enums, dict):
      enums = enums.get(component_name, None)
    if enums:
      variable_entry['default'] = enums[0]
      variable_entry['enum'] = enums

    # Handle object properties
    if var_type == 'object':
      variable_entry['properties'] = {}
      object_scope_pattern = re.compile(rf'\* - {var_name}: \[object\](.*?)(\* - |\Z)', re.DOTALL)
      object_scope_match = object_scope_pattern.search(twig_content)
      if object_scope_match:
        object_scope_content = object_scope_match.group(1)
        for obj_match in object_property_pattern.finditer(object_scope_content):
          obj_name, obj_type, obj_desc = obj_match.groups()
          variable_entry['properties'][obj_name] = {
            'type': obj_type,
            'title': obj_name.replace('_', ' ').capitalize(),
            'description': obj_desc
          }
    variables[var_name] = variable_entry

  # Extract default values from Twig set statements
  matches = default_pattern.findall(twig_content)
  for variable_name, default_value in matches:
    default_value = default_value.strip().replace('\'', '').replace('"', '')
    if variable_name in variables:
      if default_value == 'null':
        default_value = None
      variables[variable_name]['default'] = default_value

  # Extract variables used in conditional statements
  for match in conditional_pattern.finditer(twig_content):
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
    if key in ['attributes', 'modifier_class']:
      continue
    if 'optional' not in var.get('description', '') and var.get('type') != 'boolean':
      if 'default' not in var and key not in conditional_variables:
        required_fields.append(key)

  yaml_data = {
    'name': component_name,
    'props': {
      'type': 'object',
      'required': required_fields,
      'properties': variables  # Include all variables
    },
    'slots': slots
  }

  # Include JavaScript library override if applicable
  if has_js_file:
    yaml_data['libraryOverrides'] = {
      'js': {
        f'{component_name.lower()}.js': {}
      }
    }

  return yaml.dump(yaml_data, sort_keys=False)

def process_directory(directory):
  """
  Process all Twig files in a directory, generating corresponding YAML files.

  Args:
    directory (str): The path to the directory containing Twig files.
  """
  for root, dirs, files in os.walk(directory):
    for file in files:
      if file.endswith('.twig') and not file.endswith('.stories.twig'):
        # Derive component name and paths
        component_name = file.replace('.twig', '').replace('-', ' ').title().replace(' ', '')
        file_path = os.path.join(root, file)

        # Check for the existence of a corresponding .js file
        js_file_path = os.path.join(root, file.replace('.twig', '.js'))
        has_js_file = os.path.exists(js_file_path)

        # Read Twig file content
        with open(file_path, 'r') as twig_file:
          twig_content = twig_file.read()

        # Parse variables and generate YAML
        variables, slots, conditional_variables = parse_variables(twig_content, component_name)
        yaml_output = generate_yaml(component_name, variables, slots, has_js_file, conditional_variables)

        # Write YAML to a new file with the same name, overwriting if it exists
        yaml_file_path = os.path.join(root, file.replace('.twig', '.component.yml'))
        with open(yaml_file_path, 'w') as yaml_file:
          yaml_file.write(yaml_output)

        # Print relative path of processed files
        relative_file_path = os.path.relpath(file_path, directory)
        relative_yaml_path = os.path.relpath(yaml_file_path, directory)
        print(f'Processed {relative_file_path}, output saved to {relative_yaml_path}')

def main():
  """
  Main entry point of the script. Parses command-line arguments and processes the specified directory.
  """
  parser = argparse.ArgumentParser(description='Process Twig files and generate YAML files for SDC components.')
  parser.add_argument('directory', type=str, help='The directory path to process.')
  args = parser.parse_args()

  process_directory(args.directory)

if __name__ == "__main__":
  main()
