import re
import yaml
import os
import argparse

# Define regex patterns
variable_pattern = re.compile(r'\* - (\w+): \[(\w+|object|array)\] (.*)')
object_pattern = re.compile(r'\*   - (\w+): \[(\w+)\] (.*)')
enum_patterns = {
  'theme': ['light', 'dark'],
  'kind': {
      'button': ['submit', 'reset', 'button', 'link'],
      'chip': ['default', 'input']
  },
  'type': {
      'button': ['primary', 'secondary', 'tertiary']
  },
  'size': {
      'chip': ['large', 'regular', 'small']
  },
  'icon_placement': ['left', 'right'],
  'image_position': ['left', 'right'],
  'vertical_spacing': ['top', 'bottom', 'both']
}

def parse_variables(twig_content, component_name):
  variables = {}
  slots = {}
  
  # Find all variable matches
  for match in variable_pattern.finditer(twig_content):
      var_name, var_type, var_desc = match.groups()
      
      # Detect slots
      if 'slot' in var_desc.lower():
          slots[var_name] = {
              'title': var_name.replace('_', ' ').capitalize(),
              'description': var_desc
          }
          continue
      
      # Determine type and construct variable entry
      variable_entry = {
          'type': var_type if var_type != 'object' else 'object',
          'title': var_name.replace('_', ' ').capitalize(),
          'description': var_desc
      }
      
      # Add enums for specific variables
      enums = enum_patterns.get(var_name, None)
      if isinstance(enums, dict):
          enums = enums.get(component_name, None)
      if enums:
          variable_entry['default'] = enums[0]
          variable_entry['enum'] = enums
      
      # Handle objects
      if var_type == 'object':
          variable_entry['properties'] = {}
          object_properties = object_pattern.findall(twig_content)
          for obj_name, obj_type, obj_desc in object_properties:
              variable_entry['properties'][obj_name] = {
                  'type': obj_type,
                  'title': obj_name.replace('_', ' ').capitalize(),
                  'description': obj_desc
              }
      variables[var_name] = variable_entry
  
  return variables, slots

def generate_yaml(component_name, variables, slots):
  required_fields = [key for key in variables if 'optional' not in variables[key].get('description', '')]
  yaml_data = {
      'name': component_name,
      'props': {
          'type': 'object',
          'required': required_fields,
          'properties': variables
      },
      'slots': slots
  }
  return yaml.dump(yaml_data, sort_keys=False)

def process_directory(directory):
  for root, dirs, files in os.walk(directory):
    for file in files:
      if file.endswith('.twig') and not file.endswith('.stories.twig'):
        component_name = file.replace('.twig', '').replace('-', ' ').title().replace(' ', '')
        file_path = os.path.join(root, file)
        with open(file_path, 'r') as twig_file:
            twig_content = twig_file.read()
        
        variables, slots = parse_variables(twig_content, component_name)
        yaml_output = generate_yaml(component_name, variables, slots)
        
        # Write YAML to a new file with the same name, overwriting if it exists
        yaml_file_path = os.path.join(root, file.replace('.twig', '.component.yml'))
        with open(yaml_file_path, 'w') as yaml_file:
            yaml_file.write(yaml_output)
        
        print(f'Processed {file_path}, output saved to {yaml_file_path}')

def main():
  parser = argparse.ArgumentParser(description='Process Twig files and generate YAML files for SDC components.')
  parser.add_argument('directory', type=str, help='The directory path to process.')
  args = parser.parse_args()
  
  process_directory(args.directory)

if __name__ == "__main__":
  main()
