"""
Kernameters Backend (`kernameters.py`)

This module provides the core backend functionalities for the Kernameters TUI.
It is responsible for:
1.  **Interacting with System Commands**: Executing `lsmod` to list loaded kernel
    modules and `modinfo` to retrieve parameter details (description, type hints).
2.  **Sysfs Interaction**: Reading current parameter values from the `/sys/module/`
    filesystem and writing new values to these parameters.
3.  **Data Aggregation**: Collecting and structuring data about modules and their
    parameters, including type information extracted from `modinfo` descriptions.
4.  **Profile Management**:
    *   Saving the current state of module parameters to JSON-based profile files.
    *   Loading parameter values from these profiles.
    *   Applying loaded profiles back to the system via sysfs.
    *   Listing available profiles.
5.  **Output Generation**: Optionally generating a JSON report of all collected
    module and parameter data (used by the CLI mode).

The functions in this module are designed to be called by the TUI (`kernameters_tui.py`)
or by the `main()` function in this file for CLI operations.
Error handling is typically done by returning status tuples (e.g., (bool, message))
or specific data structures indicating errors (e.g., a dictionary with an "error" key).
"""
import subprocess
import json
import os
import errno
import re # For filename sanitization and type extraction
from datetime import datetime # For profile creation timestamp

# Global constant for the directory where profiles are stored.
PROFILES_DIR = "kernameters_profiles"

# --- Helper Functions ---
def _sanitize_filename(name: str) -> str:
    """
    Sanitizes a string to be a valid filename.

    Replaces spaces with underscores and removes characters that are not
    alphanumeric, underscore, or hyphen. Limits filename length.

    Args:
        name (str): The input string to sanitize.

    Returns:
        str: The sanitized string, suitable for use as a filename.
             Returns an empty string if the input `name` is empty or None.
    """
    if not name:
        return ""
    # Replace spaces with underscores first
    name = name.replace(' ', '_')
    # Remove characters that are not alphanumeric, underscore, or hyphen
    name = re.sub(r'[^\w\-]', '', name)
    # Limit length to prevent overly long filenames (common filesystem limit is 255)
    return name[:200]

# --- Core System Interaction Functions ---

def run_command(command: str) -> str | None:
    """
    Runs a shell command and returns its standard output.

    Args:
        command (str): The command string to execute.

    Returns:
        str | None: The standard output of the command as a string if successful,
                    None if an error occurs or the command fails.
                    Error details are printed to stderr for CLI context.
    """
    try:
        # Using shell=True can be a security risk if the command string is derived from
        # untrusted input. Here, command strings are hardcoded, so it's acceptable.
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            # Log error for CLI context; TUI might need more structured error reporting
            # or might rely on this function returning None.
            print(f"Error running command '{command}': {stderr.decode('utf-8', 'replace')}")
            return None
        return stdout.decode('utf-8', 'replace')
    except Exception as e:
        # Catching a broad exception here to ensure the program doesn't crash
        # if Popen itself fails for some reason (e.g., OS error).
        print(f"Exception running command '{command}': {e}")
        return None

def get_modinfo_params(module: str) -> dict | None:
    """
    Retrieves module parameters, descriptions, and attempts to extract type hints using `modinfo`.

    Parses the output of `modinfo -F parameters <module>`. The output for each parameter
    is typically "param_name:description (type_hint)". This function tries to isolate
    the parameter name, its textual description, and a type string (e.g., "int", "bool",
    "array of string").

    Args:
        module (str): The name of the kernel module.

    Returns:
        dict | None: A dictionary where keys are parameter names. Each value is another
                     dictionary: `{'description': str, 'type': str, 'raw_modinfo_line': str}`.
                     'type' defaults to "string" if not determinable. 'charp' is treated as "string".
                     Returns None if `modinfo` fails, the module has no parameters, or input is invalid.
    """
    if not module or not isinstance(module, str):
        return None # Invalid input

    # Example modinfo -F parameters output lines:
    # "debug:Enable debug messages (bool)"
    # "wq_power_efficient:Enable power efficient workqueues by default (bool)"
    # "alignment_ok:Use unaligned access if benefitial (bool)"
    # "disable_ertm:Disable ERTM (Enhanced ReTransmission Mode) (bool)"

    output = run_command(f'modinfo -F parameters {module}')
    if output is None or not output.strip(): # Check if output is empty or command failed
        return None

    params_info = {}
    for line in output.strip().split('\n'):
        if not line.strip(): # Skip empty lines
            continue

        parts = line.split(':', 1) # Split on the first colon only
        param_name = parts[0].strip()
        if not param_name: # Should not happen with valid modinfo output
            continue

        description_full = parts[1].strip() if len(parts) > 1 else ""
        description_text_only = description_full
        # Default type; 'charp' (char pointer) is treated as string for sysfs R/W.
        extracted_type = "string"

        # Regex patterns to find type hints, typically at the end of the description.
        # Order matters: check for "array of <type>" before simple "<type>".
        # These patterns try to match "(type)" or "(array of type)" at the end of the line.
        type_patterns = [
            (r'\s*\(array of (int|bool|short|long|charp|string)\)$', lambda m: f"array of {m.group(1).replace('charp', 'string')}"),
            (r'\s*\((int|bool|short|long|charp|string)\)$', lambda m: m.group(1).replace('charp', 'string'))
        ]

        type_found_at_end = False
        for pattern, type_extractor_func in type_patterns:
            match = re.search(pattern, description_text_only, re.IGNORECASE)
            if match:
                extracted_type = type_extractor_func(match)
                # Remove the matched type hint from the description string for a cleaner description.
                description_text_only = re.sub(pattern, '', description_text_only, flags=re.IGNORECASE).strip()
                type_found_at_end = True
                break

        # Fallback: if no type hint was found enclosed in parentheses at the end,
        # try a more general search for type keywords within the description.
        # This is less reliable as it might pick up words like "integer" that aren't formal type hints.
        if not type_found_at_end:
            m_array = re.search(r'array of (int|bool|short|long|charp|string)', description_text_only, re.IGNORECASE)
            if m_array:
                extracted_type = f"array of {m_array.group(1).replace('charp', 'string')}"
            else:
                m_simple = re.search(r'\b(int|bool|short|long|charp|string)\b', description_text_only, re.IGNORECASE)
                if m_simple:
                     # This fallback is tricky. Avoid misinterpreting descriptive words.
                     # Example: "enable string debug" should not make type "string" if not intended.
                     # Only apply if it seems like a plausible type hint (e.g., not just "string" unless "(string)" was present).
                     potential_type = m_simple.group(1).replace('charp', 'string')
                     # Heuristic: if 'string' is found, but not as '(string)', it might be part of description.
                     # For other types like 'int' or 'bool', it's more likely a type hint.
                     if potential_type != "string" or "(string)" in description_full:
                         extracted_type = potential_type

        params_info[param_name] = {
            'description': description_text_only, # Cleaned description text
            'type': extracted_type,               # Extracted type string ("int", "bool", "array of string", etc.)
            'raw_modinfo_line': line.strip()      # Original full line from modinfo, for reference or debugging
        }
    return params_info if params_info else None # Return None if dictionary is empty (no params parsed)

def get_sysfs_param_value(module_name: str, param_name: str) -> str:
    """
    Reads the current value of a kernel module parameter from its sysfs entry.

    Args:
        module_name (str): The name of the kernel module.
        param_name (str): The name of the parameter.

    Returns:
        str: The current value of the parameter as a string (parameters are text in sysfs).
             Returns a specific string like 'N/A (sysfs access error)' if reading fails
             (e.g., file not found, permission denied), to distinguish from parameters
             that might genuinely have "N/A" as a value.
    """
    sysfs_path = f"/sys/module/{module_name}/parameters/{param_name}"
    try:
        with open(sysfs_path, 'r') as f:
            return f.read().strip() # Values usually have a trailing newline
    except IOError:
        # Common errors: FileNotFoundError if param doesn't exist or not readable, PermissionError.
        return 'N/A (sysfs access error)'
    except Exception: # Catch any other unexpected errors during read
        return 'N/A (unexpected read error)'


def set_sysfs_param_value(module_name: str, param_name: str, value: str) -> tuple[bool, str]:
    """
    Attempts to set a kernel module parameter value via its sysfs entry.

    Args:
        module_name (str): The name of the kernel module.
        param_name (str): The name of the parameter to set.
        value (str): The value (as a string) to write to the parameter. Kernel modules
                     expect string inputs for their sysfs parameter files; type conversion
                     (e.g., for booleans like "Y"/"N" or "1"/"0") should be handled
                     by the caller or the kernel module itself.

    Returns:
        tuple[bool, str]: (success_status, message).
                          `success_status` is True if the write was successful, False otherwise.
                          The `message` provides details on success or the type of error encountered.
    """
    sysfs_path = f"/sys/module/{module_name}/parameters/{param_name}"

    # Pre-check existence and writability using os.access for clearer error messages.
    if not os.path.exists(sysfs_path):
        return (False, f"Error: Parameter file not found at '{sysfs_path}'.")
    if not os.access(sysfs_path, os.W_OK): # Check if the process has write permissions
        return (False, "Error: Permission denied (parameter file not writable).")

    try:
        with open(sysfs_path, 'w') as f:
            f.write(str(value)) # Kernel parameters expect string values.
        return (True, f"Successfully wrote '{value}' to {param_name}.")
    except IOError as e:
        # Handle specific OS errors for more informative feedback.
        if e.errno == errno.EACCES or e.errno == errno.EPERM: # Permission denied by kernel
            return (False, "Error: Permission denied by kernel during write operation.")
        elif e.errno == errno.EINVAL: # Invalid argument (kernel rejected the value)
            return (False, f"Error: Kernel rejected value '{value}' as invalid for {param_name}.")
        elif e.errno == errno.ENOENT: # File not found - should have been caught by os.path.exists
            return (False, "Error: Parameter file disappeared before write could occur.")
        else: # Other I/O errors
            return (False, f"Error writing to sysfs parameter {param_name}: {os.strerror(e.errno)} (errno {e.errno}).")
    except Exception as e: # Catch any other unexpected errors during the write operation
        return (False, f"An unexpected error occurred while writing to {param_name}: {str(e)}")

# --- Profile Management Functions ---

def save_profile(profile_name: str, description: str, modules_parameters_to_save: dict, base_dir: str = PROFILES_DIR) -> tuple[bool, str]:
    """
    Saves the given module parameters to a profile JSON file.

    The profile includes the original name, a sanitized version for the filename,
    a user-provided description, a creation timestamp, and the parameter data.

    Args:
        profile_name (str): The user-defined name for the profile. This name will be
                            sanitized to create a valid filename.
        description (str): A user-provided description for the profile.
        modules_parameters_to_save (dict): A dictionary structured as
                                           `{"module_name": {"param_name": "value", ...}}`.
                                           Only current parameter values are saved.
        base_dir (str): The directory where profiles are stored. Defaults to `PROFILES_DIR`.

    Returns:
        tuple[bool, str]: (True, "Success message") or (False, "Error message") indicating
                          the outcome of the save operation.
    """
    sanitized_name = _sanitize_filename(profile_name)
    if not sanitized_name: # Check if sanitization resulted in an empty string
        return (False, "Error: Profile name is invalid or results in an empty filename after sanitization.")

    try:
        os.makedirs(base_dir, exist_ok=True) # Ensure the profile directory exists
    except OSError as e: # Handle errors during directory creation (e.g., permission issues)
        return (False, f"Error creating profile directory '{base_dir}': {os.strerror(e.errno)}")

    file_path = os.path.join(base_dir, f"{sanitized_name}.json")

    profile_data = {
        "profile_name": profile_name,           # Store the original user-provided name for display purposes
        "sanitized_name": sanitized_name,       # Store the filename-safe version, used for loading
        "description": description,
        "date_created": datetime.now().isoformat(), # Store creation date in ISO 8601 format
        "parameters": modules_parameters_to_save # The actual module:param:value data
    }

    try:
        with open(file_path, 'w') as f:
            json.dump(profile_data, f, indent=4) # Save JSON with pretty-printing
        return (True, f"Profile '{profile_name}' saved successfully as '{sanitized_name}.json'.")
    except IOError as e: # Handle file writing errors
        return (False, f"Error writing profile to file '{file_path}': {os.strerror(e.errno)}")
    except Exception as e: # Catch other potential errors (e.g., JSON serialization issues)
        return (False, f"An unexpected error occurred while saving profile '{profile_name}': {str(e)}")

def load_profile(profile_name_sanitized: str, base_dir: str = PROFILES_DIR) -> tuple[dict | None, str]:
    """
    Loads a profile from a JSON file using its sanitized name (filename without extension).

    Args:
        profile_name_sanitized (str): The sanitized name of the profile to load.
        base_dir (str): The directory where profiles are stored. Defaults to `PROFILES_DIR`.

    Returns:
        tuple[dict | None, str]: (`profile_data`, `message`).
                                 `profile_data` is the loaded dictionary on success, `None` on failure.
                                 The `message` indicates success or describes the error encountered.
    """
    file_path = os.path.join(base_dir, f"{profile_name_sanitized}.json")

    if not os.path.exists(file_path): # Check if the profile file exists
        return (None, f"Error: Profile file '{profile_name_sanitized}.json' not found in '{base_dir}'.")

    try:
        with open(file_path, 'r') as f:
            profile_data = json.load(f) # Load and parse the JSON data
        # Basic validation to ensure essential keys are present in the loaded profile
        required_keys = ["profile_name", "parameters", "sanitized_name", "date_created", "description"]
        if not all(k in profile_data for k in required_keys):
             # This indicates a potentially corrupted or incomplete profile file.
             return (None, f"Error: Profile '{profile_name_sanitized}.json' is missing one or more required fields.")
        return (profile_data, f"Profile '{profile_data.get('profile_name', profile_name_sanitized)}' loaded successfully.")
    except json.JSONDecodeError: # Handle errors if the file is not valid JSON
        return (None, f"Error: Invalid JSON format in profile file '{profile_name_sanitized}.json'.")
    except IOError as e: # Handle file reading errors
        return (None, f"Error reading profile file '{profile_name_sanitized}.json': {os.strerror(e.errno)}")
    except Exception as e: # Catch any other unexpected errors during loading
        return (None, f"An unexpected error occurred while loading profile '{profile_name_sanitized}': {str(e)}")


def apply_profile_parameters(profile_parameters: dict) -> dict:
    """
    Applies parameter values from a loaded profile dictionary to the system via sysfs.

    Args:
        profile_parameters (dict): The "parameters" section of a loaded profile,
                                   structured as `{"module_name": {"param_name": "value", ...}}`.
    Returns:
        dict: A summary of the application attempt, structured as:
              `{"success_count": int, "failure_count": int, "failures": list_of_failure_details}`.
              Each entry in `failures` is a dictionary:
              `{"module": str, "parameter": str, "value": str, "reason": str_error_message}`.
    """
    applied_successfully_count = 0
    failed_to_apply_details = [] # Store details of each failure

    if not isinstance(profile_parameters, dict):
        # This case should ideally be caught by validation before calling.
        return {
            "success_count": 0,
            "failure_count": 1, # Consider this one overall failure
            "failures": [{"module": "N/A", "parameter": "N/A", "value": "N/A",
                          "reason": "Invalid profile_parameters format (must be a dictionary)."}]
        }

    for module_name, params in profile_parameters.items():
        if not isinstance(params, dict): # Validate structure for each module
            failed_to_apply_details.append({
                "module": module_name, "parameter": "N/A", "value": "N/A",
                "reason": f"Invalid parameters format for module '{module_name}' (must be a dictionary)."
            })
            continue # Skip to the next module if this one has malformed data

        for param_name, value in params.items():
            # Attempt to set the parameter value using the backend function.
            # Value must be converted to string as sysfs expects text.
            success, message = set_sysfs_param_value(module_name, param_name, str(value))
            if success:
                applied_successfully_count += 1
            else:
                failed_to_apply_details.append({
                    "module": module_name,
                    "parameter": param_name,
                    "value": str(value), # Record the value that was attempted
                    "reason": message    # Store the error message from set_sysfs_param_value
                })

    return {
        "success_count": applied_successfully_count,
        "failure_count": len(failed_to_apply_details),
        "failures": failed_to_apply_details # List of detailed failure information
    }

def list_profiles(base_dir: str = PROFILES_DIR) -> tuple[list[str] | None, str]:
    """
    Lists available profiles by scanning the specified directory for `.json` files.

    Args:
        base_dir (str): The directory where profiles are stored. Defaults to `PROFILES_DIR`.

    Returns:
        tuple[list[str] | None, str]: (`list_of_profile_names`, `message`).
                                      `list_of_profile_names` contains sanitized profile names
                                      (filenames without the `.json` extension), sorted alphabetically.
                                      The list is `None` if `base_dir` is not a directory or is unreadable.
                                      If `base_dir` is empty or contains no `.json` files,
                                      returns an empty list and an appropriate message.
    """
    if not os.path.isdir(base_dir): # Ensure the base_dir exists and is a directory
        return (None, f"Profile directory '{base_dir}' not found or is not a directory.")

    try:
        # List files, filter for .json extension, and ensure they are actual files (not subdirectories).
        profile_files = [
            f for f in os.listdir(base_dir)
            if f.endswith(".json") and os.path.isfile(os.path.join(base_dir, f))
        ]
    except OSError as e: # Handle potential errors like permission denied when listing directory
        return (None, f"Error reading profile directory '{base_dir}': {os.strerror(e.errno)}")

    if not profile_files: # Check if any .json files were found
        return ([], f"No profiles found in '{base_dir}'.")

    # Return filenames without .json extension (these are the sanitized names used for loading)
    # Sort the list for consistent display.
    profile_names = sorted([os.path.splitext(f)[0] for f in profile_files])
    return (profile_names, f"Found {len(profile_names)} profile(s).")

# --- Data Aggregation & JSON Output ---

def generate_json_output(module_data: dict, filename: str) -> bool:
    """
    Generates a JSON report of the collected module parameter data.

    Args:
        module_data (dict): The module data, typically from `collect_all_module_data()`.
        filename (str): The name of the file to save the JSON report to.

    Returns:
        bool: True if JSON generation was successful, False otherwise.
              Prints an error message to the console on failure.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(module_data, f, indent=4) # Use indent=4 for readable JSON output
    except Exception as e: # Catch potential errors like IOErrors or JSON encoding issues
        print(f"Error creating JSON report '{filename}': {e}")
        return False
    return True

def collect_all_module_data() -> dict:
    """
    Collects comprehensive data for all currently loaded kernel modules.

    This involves:
    1. Listing all modules using `lsmod` (via `run_command`).
    2. For each module:
        a. Fetching its parameters, descriptions, and type hints using `get_modinfo_params`.
        b. For each parameter identified by `modinfo`, reading its current value from
           sysfs using `get_sysfs_param_value`.

    The data structure returned is suitable for direct use by the TUI or for
    serialization to JSON.

    Returns:
        dict: A nested dictionary structured as:
              `{module_name: {param_name: {"current": value, "available": modinfo_dict}, ...}, ...}`
              where `modinfo_dict` is `{'description': ..., 'type': ..., 'raw_modinfo_line': ...}`.

              Special top-level keys like "error" or "info" may be present if issues occur
              at the `lsmod` stage (e.g., command failure) or if no modules are found.

              Individual modules within the main dictionary might map to `None` if `get_modinfo_params`
              fails for them (e.g., the module has no parameters, or `modinfo` encounters an issue
              like permission denied for that specific module).
    """
    modules_output = run_command("lsmod | awk 'NR>1 {print $1}'") # Get list of loaded module names
    if modules_output is None:
        # This indicates a failure in run_command for lsmod (e.g., lsmod not found or errored)
        return {"error": "Failed to list kernel modules (lsmod command failed)."}

    module_data = {}
    # Process each line of lsmod output; filter out empty lines if any.
    module_list = [m for m in modules_output.strip().split('\n') if m]

    if not module_list: # No modules currently loaded
        return {"info": "No kernel modules found."}

    # Use set to process unique module names, in case lsmod output has duplicates, then sort for consistent processing order.
    for module_name in sorted(list(set(module_list))):
        # For each module, get its parameters' descriptions and types from modinfo
        parameter_details_map = get_modinfo_params(module_name)

        if parameter_details_map is None:
            # Module might have no parameters, or modinfo failed (e.g., permission denied for modinfo on this module).
            # Store None to indicate data retrieval issues for this specific module.
            module_data[module_name] = None
        else:
            current_module_params_state = {}
            for param_name, param_info_dict in parameter_details_map.items():
                # param_info_dict is {'description': ..., 'type': ..., 'raw_modinfo_line': ...}
                current_sysfs_value = get_sysfs_param_value(module_name, param_name)
                current_module_params_state[param_name] = {
                    'current': current_sysfs_value,  # Current value from /sys/module/.../parameters/
                    'available': param_info_dict     # Rich dict with desc, type, raw_line from modinfo
                }
            module_data[module_name] = current_module_params_state # Store all parameters for this module
    return module_data

# --- Main CLI Entry Point ---
def main():
    """
    Command-line interface (CLI) entry point for `kernameters.py`.

    When this script is run directly from the command line, this function is executed.
    It collects all kernel module parameter data by calling `collect_all_module_data()`
    and then saves this data to a JSON file named 'module_parameters.json' in the
    current working directory. It also prints status messages to the console.
    This serves as a simple CLI utility for data export.
    """
    print("Collecting kernel module parameter data for JSON report...")
    module_data = collect_all_module_data()

    # Handle cases where data collection might have issues (e.g., lsmod error, no modules)
    if "error" in module_data: # Check for critical error from lsmod stage
        print(f"Error during data collection: {module_data['error']}")
        return # Exit if lsmod failed
    if "info" in module_data and len(module_data) == 1: # Only "info" key exists, meaning no modules found
        print(module_data["info"])
        # Still attempt to generate an (empty or info-containing) JSON file.
        # If you prefer not to generate a file in this case, uncomment the 'return' below.
        # return

    print("Generating JSON report...")
    if generate_json_output(module_data, 'module_parameters.json'):
        print("JSON report 'module_parameters.json' generated successfully.")
    else:
        # generate_json_output already prints an error, so this is a general failure message.
        print("Failed to generate JSON report.")

if __name__ == "__main__":
    # This standard Python construct ensures that main() is called only when the script
    # is executed directly (e.g., `python kernameters.py`), not when it's imported as a module.
    main()
