# Script Overview:
This script scans a directory for Twig files, extracts variable definitions and options from comments, and generates the corresponding .component.yml files required for SDC components. 

# Try it as Drush command (Coming soon)
Drupal module: [Twig to SDC](https://www.drupal.org/project/twig_to_sdc)\
Demo: https://www.linkedin.com/posts/anand-toshniwal_drupal-twig-sdc-activity-7253234417312165888-Whve?utm_source=share&utm_medium=member_desktop

## How It Works:

### Setup:
 - **Ensure Python is Installed:**
   Make sure you have Python installed on your system.

 - **Install Required Libraries:**
   Check that the required libraries (pyyaml and re) are available in your Python environment.

### Running the Script

- **Execute the Script:**  
  Run the script from the command line, providing the directory containing your Twig files as an argument.

  ```bash
  python script.py /path/to/your/twig/files

## What the Script Does

### Traverse the Directory

- **Searches through the specified directory and its subdirectories for `.twig` files.**

### Read and Parse Twig Files

- **Variables:**  
  Extracts key-value pairs defined in the Twig file.

- **Slots:**  
  Identifies special variables used to slot content into predefined places within the component.

- **Conditionals:**  
  Detects variables used in conditional statements to assess their necessity.

### Extract Default Values

- **Detects and extracts default values defined within Twig `set` statements or patterns.**

### Handle Array Variables

- **Identify Array Variables:**  
  Detects variables that are arrays and looks for related include files.

- **Include Files:**  
  Checks if there are include files that define the structure of the array items.

- **Incorporate Information:**  
  Integrates information from these include files into the YAML output to accurately represent the array’s structure.

### Determine Required Fields

- **Required Fields Detection:**  
  Identifies required variables based on their descriptions, default values, and usage in conditional statements.

- **Required Fields Inclusion:**  
  Includes these required fields in the YAML output under the `required` key to ensure they are properly defined.

### Generate YAML Configuration

- **Component Name:**  
  Derives the component name from the Twig file name.

- **Props:**  
  Lists all variables, their types, default values, and whether they are required.

- **Slots:**  
  Defines any slots found in the Twig file.

- **JavaScript File:**  
  Indicates if there is an associated JavaScript file for the component.

### Save YAML Files

- **Save Configuration:**  
  Saves the YAML configuration files in the same directory as the Twig files, with the `.component.yml` extension.
