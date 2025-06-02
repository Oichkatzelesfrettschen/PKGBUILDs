"""
Kernameters Text User Interface (TUI) (`kernameters_tui.py`)

This module implements an Urwid-based Text User Interface for interacting with
kernel module parameters. It uses `kernameters.py` as its backend for data
collection, sysfs interaction, and profile management.

Features:
-   Browsing loaded kernel modules and their parameters.
-   Displaying parameter descriptions, types (extracted by backend), and current values.
-   Editing parameter values with type-aware validation (for bool, int).
-   Saving current parameter configurations as named profiles.
-   Listing saved profiles.
-   Loading and applying profiles to the system.
-   Status bar for feedback and error messages.

Layout:
The TUI is divided into several panes:
-   Header: Displays the application title.
-   Module List: Shows loaded kernel modules. Selecting a module updates the
                 Parameter List.
-   Parameter List: Shows parameters for the selected module. Parameters can be
                    selected to trigger an edit overlay.
-   Profile List: Shows saved profiles. Profiles can be selected to be applied.
-   Status/Actions Pane: Displays status messages, error messages, and key hints.

Global Variables:
-   `loaded_module_data`: Stores the main data structure fetched from the backend.
-   `selected_module_name_global`: Tracks the currently selected module in the UI.
-   `param_list_walker`, `profile_list_walker`: Urwid ListWalkers for dynamic content.
-   `status_text`: Urwid Text widget for the status bar.
-   `main_layout_widget`, `urwid_loop`: Store the main Urwid layout and loop instance,
                                     primarily for managing overlays.
-   Widgets for overlays (e.g., `param_edit_widget`, `profile_name_edit`) are
  defined globally for easy access and state persistence across overlay invocations.

Note on Environment:
The TUI's ability to run may be affected by restrictive environments (e.g., some
sandboxes or containers) that limit Urwid's event loop capabilities. A
`PermissionError` has been observed in such cases during development.
"""
import urwid
# os import is not directly used here but kernameters.py uses it.
# from kernameters import PROFILES_DIR is used.

# Backend functions imported from kernameters.py
from kernameters import (
    collect_all_module_data,
    set_sysfs_param_value,
    get_sysfs_param_value,
    PROFILES_DIR, # Profile directory path, used as default in TUI calls
    save_profile,
    load_profile,
    apply_profile_parameters,
    list_profiles
)

# --- Global State Variables ---
# These variables hold the application's state and are accessed by various UI functions.

# Stores the comprehensive data about all modules and their parameters,
# fetched by `collect_all_module_data()`.
loaded_module_data = {}

# Name of the module currently selected in the module list pane.
selected_module_name_global = None

# Urwid ListWalkers for dynamic lists in the UI.
param_list_walker = urwid.SimpleFocusListWalker([])
profile_list_walker = urwid.SimpleFocusListWalker([])

# Urwid Text widget for displaying status messages, errors, and hints.
status_text = urwid.Text("Press 'S' to Save Profile | 'Q' to Quit")

# Stores the main layout widget of the TUI. Used to restore the view after an overlay is closed.
main_layout_widget = None
# Stores the Urwid MainLoop instance. Needed for changing the top-level widget (e.g., to show an overlay).
urwid_loop = None

# --- UI Widgets for Overlays (defined globally for state persistence) ---

# For Parameter Editing Overlay:
param_edit_widget = urwid.Edit(caption="New value: ", multiline=False, edit_text="")
param_original_value_text = urwid.Text("") # Displays details of the parameter being edited.
param_type_holder = None # Temporarily stores the type of the parameter being edited.

# For Save Profile Overlay:
profile_name_edit = urwid.Edit(caption="Profile Name: ")
profile_desc_edit = urwid.Edit(caption="Description: ")


# --- Overlay Construction and Handling Functions ---

def build_param_edit_overlay(module_name: str, param_name: str, current_value: str, param_type: str, description: str) -> urwid.Overlay:
    """
    Constructs and returns an Urwid Overlay for editing a kernel parameter.

    The overlay includes details of the parameter (name, type, description, current value),
    an Edit widget for the new value, and Save/Cancel buttons.

    Args:
        module_name (str): Name of the module.
        param_name (str): Name of the parameter.
        current_value (str): Current value of the parameter.
        param_type (str): Type of the parameter (e.g., "int", "bool", "string").
        description (str): Description of the parameter.

    Returns:
        urwid.Overlay: The configured overlay widget.
    """
    global param_edit_widget, param_original_value_text, param_type_holder

    param_type_holder = param_type # Store type for validation logic on save
    param_edit_widget.set_edit_text(str(current_value)) # Pre-fill with current value

    # Display comprehensive info in the overlay
    param_original_value_text.set_text(
        f"Editing: {module_name}/{param_name}\n"
        f"Type: {param_type or 'string (default)'}\n" # Show type, default if unknown
        f"Description: {description}\n"
        f"Current Value: {current_value}"
    )

    save_button = urwid.Button("Save Value")
    cancel_button = urwid.Button("Cancel Edit")

    # Connect signals for overlay buttons
    urwid.connect_signal(save_button, 'click', execute_param_save, user_args=[module_name, param_name, param_type])
    urwid.connect_signal(cancel_button, 'click', execute_cancel_overlay)

    # Layout for overlay content
    buttons = urwid.GridFlow([urwid.AttrMap(w, None, focus_map='reversed') for w in [save_button, cancel_button]],
                             cell_width=15, h_sep=2, v_sep=1, align='center')
    content_pile = urwid.Pile([param_original_value_text, urwid.Divider(), param_edit_widget, urwid.Divider(), buttons])
    overlay_content_box = urwid.LineBox(content_pile, title="Edit Parameter")

    # Create and return the overlay, centered on the main layout
    return urwid.Overlay(overlay_content_box, main_layout_widget,
                         align='center', width=('relative', 70),
                         valign='middle', height=('relative', 60))

def execute_param_save(_button, module_name: str, param_name: str, param_type: str) -> None:
    """
    Handles the 'Save' action for the parameter edit overlay.
    Validates the input based on parameter type, calls set_sysfs_param_value,
    updates status, and refreshes UI if successful.

    Args:
        _button: The button widget that triggered the event (unused).
        module_name (str): Name of the module.
        param_name (str): Name of the parameter.
        param_type (str): Type of the parameter for validation.
    """
    global loaded_module_data, status_text, urwid_loop, param_edit_widget

    user_input = param_edit_widget.edit_text
    validated_value = user_input # Default to original input, assuming string type initially

    # --- Input Validation Logic ---
    if param_type == "bool":
        # Normalize common boolean inputs to "1" or "0" for sysfs
        if user_input.lower() in ['1', 'y', 'yes', 'true', 'on']:
            validated_value = "1"
        elif user_input.lower() in ['0', 'n', 'no', 'false', 'off']:
            validated_value = "0"
        else:
            status_text.set_text("Validation Error: Invalid boolean. Use 0/1, y/n, true/false, on/off.")
            return # Keep overlay open for correction

    elif param_type == "int":
        try:
            int(user_input) # Check if input is a valid integer
            validated_value = user_input # Pass as string, kernel handles conversion
        except ValueError:
            status_text.set_text("Validation Error: Invalid integer value.")
            return # Keep overlay open

    # For other types like "string", "array of ...", no specific client-side validation for now.
    # The kernel will perform its own validation when the value is written to sysfs.

    success, message = set_sysfs_param_value(module_name, param_name, validated_value)
    status_text.set_text(f"Set param '{module_name}/{param_name}': {message}") # Update status bar

    if success:
        # If write was successful, refresh the data in our cache and the UI
        updated_value_from_sysfs = get_sysfs_param_value(module_name, param_name)

        # Update the 'loaded_module_data' cache
        if loaded_module_data.get(module_name) and \
           loaded_module_data[module_name].get(param_name) and \
           isinstance(loaded_module_data[module_name][param_name], dict):
            loaded_module_data[module_name][param_name]['current'] = updated_value_from_sysfs

        update_param_list_display(selected_module_name_global) # Refresh the parameter list view
        execute_cancel_overlay(None) # Close the overlay
    # If not successful (validation passed but sysfs write failed), overlay remains open for user.

def execute_cancel_overlay(_button) -> None:
    """
    Closes any active overlay and restores the main layout view.
    Called by "Cancel" buttons or 'Esc' key.

    Args:
        _button: The button widget that triggered (can be None if called directly).
    """
    global urwid_loop, main_layout_widget
    if urwid_loop and main_layout_widget:
        urwid_loop.widget = main_layout_widget # Restore the main TUI layout
        # Optionally, clear or update status_text upon cancellation
        # status_text.set_text("Operation cancelled.")

def prompt_edit_parameter(_button, module_name: str, param_name: str, current_value: str, param_type: str, description_text: str) -> None:
    """
    Builds and displays the parameter editing overlay.

    Args:
        _button: The parameter button widget that was clicked.
        module_name (str): Module name.
        param_name (str): Parameter name.
        current_value (str): Current value of the parameter.
        param_type (str): Type of the parameter.
        description_text (str): Description of the parameter.
    """
    global urwid_loop
    # Construct the overlay using the parameter's details
    edit_overlay = build_param_edit_overlay(module_name, param_name, current_value, param_type, description_text)
    if urwid_loop:
        urwid_loop.widget = edit_overlay # Set the main loop's widget to the overlay

# --- Save Profile Overlay Functions ---
def build_save_profile_overlay() -> urwid.Overlay:
    """
    Constructs and returns an Urwid Overlay for saving the current parameters as a profile.
    Includes Edit widgets for profile name and description, and Save/Cancel buttons.
    """
    global profile_name_edit, profile_desc_edit

    profile_name_edit.set_edit_text("") # Clear any previous input
    profile_desc_edit.set_edit_text("")

    save_button = urwid.Button("Save Profile")
    cancel_button = urwid.Button("Cancel Save")

    urwid.connect_signal(save_button, 'click', execute_save_profile)
    urwid.connect_signal(cancel_button, 'click', execute_cancel_overlay)

    buttons = urwid.GridFlow([urwid.AttrMap(w, None, focus_map='reversed') for w in [save_button, cancel_button]],
                             cell_width=18, h_sep=2, v_sep=1, align='center')
    content_pile = urwid.Pile([
        urwid.Text("Enter profile details:"),
        profile_name_edit,
        profile_desc_edit,
        urwid.Divider(),
        buttons
    ])
    overlay_content_box = urwid.LineBox(content_pile, title="Save Current Parameters as Profile")

    return urwid.Overlay(overlay_content_box, main_layout_widget,
                         align='center', width=('relative', 70),
                         valign='middle', height=('relative', 60))

def prompt_save_profile() -> None:
    """
    Validates if data is available and then displays the 'Save Profile' overlay.
    If no module data is loaded or it contains errors, a status message is shown instead.
    """
    global urwid_loop, status_text, loaded_module_data

    # Prevent saving if no valid data is loaded
    if loaded_module_data.get("error") or \
       (loaded_module_data.get("info") and len(loaded_module_data) == 1 and "info" in loaded_module_data) or \
       not loaded_module_data:
        status_text.set_text("Cannot save profile: No module data loaded or data contains errors.")
        return

    save_profile_overlay = build_save_profile_overlay()
    if urwid_loop:
        urwid_loop.widget = save_profile_overlay

def execute_save_profile(_button) -> None:
    """
    Handles the 'Save' action for the 'Save Profile' overlay.
    Collects current parameter values, calls backend `save_profile`, updates status,
    and refreshes the profile list.

    Args:
        _button: The button widget that triggered the event (unused).
    """
    global status_text, profile_name_edit, profile_desc_edit, loaded_module_data

    profile_new_name = profile_name_edit.edit_text
    profile_new_desc = profile_desc_edit.edit_text

    if not profile_new_name.strip(): # Ensure profile name is not empty
        status_text.set_text("Save Profile Error: Profile name cannot be empty.")
        # Keep overlay open for user to correct.
        return

    # Prepare parameters to save: iterate through loaded_module_data
    # and extract only the 'current' value for each parameter.
    params_to_save_in_profile = {}
    for mod_name, params_data_dict in loaded_module_data.items():
        # Skip special keys (like "error", "info") and modules with no parameter data (None)
        if mod_name in ["error", "info"] or params_data_dict is None:
            continue

        current_module_params = {}
        for param_name, values_dict in params_data_dict.items():
            # Ensure 'current' key exists; it might be missing if data is malformed
            if 'current' in values_dict:
                 current_module_params[param_name] = values_dict['current']

        if current_module_params: # Only add module to profile if it has parameters with current values
            params_to_save_in_profile[mod_name] = current_module_params

    if not params_to_save_in_profile:
        status_text.set_text("Save Profile Error: No parameters with current values found to save.")
        execute_cancel_overlay(None) # Close overlay
        return

    # Call backend function to save the profile
    success, message = save_profile(profile_new_name, profile_new_desc, params_to_save_in_profile, PROFILES_DIR)
    status_text.set_text(message) # Display success/error message from backend

    if success:
        update_profile_list_display() # Refresh the list of profiles in the UI

    execute_cancel_overlay(None) # Close the save profile overlay

# --- UI Display Update Functions ---

def update_param_list_display(current_selected_module_name: str | None) -> None:
    """
    Updates the parameter list pane based on the currently selected module.
    Populates the list with buttons for each parameter, allowing editing.

    Args:
        current_selected_module_name (str | None): The name of the module whose parameters
                                                  are to be displayed. If None, shows a placeholder.
    """
    global selected_module_name_global, param_list_walker, loaded_module_data

    selected_module_name_global = current_selected_module_name
    param_list_walker.clear() # Clear previous parameter list items

    if selected_module_name_global and selected_module_name_global in loaded_module_data:
        module_params_map = loaded_module_data[selected_module_name_global]

        if module_params_map: # Check if this module has parameter data (it could be None)
            for param_name, param_data in sorted(module_params_map.items()):
                current_value = param_data.get('current', 'N/A')
                available_info = param_data.get('available', {}) # This is a dict from get_modinfo_params

                description = available_info.get('description', 'No description available.')
                param_type = available_info.get('type', 'string') # Default to 'string' if type extraction failed

                # Create a button for each parameter; clicking it will trigger editing.
                param_button = urwid.Button(f"{param_name}: {current_value}")
                urwid.connect_signal(
                    param_button,
                    'click',
                    prompt_edit_parameter,
                    user_args=[selected_module_name_global, param_name, current_value, param_type, description]
                )
                param_list_walker.append(urwid.AttrMap(param_button, None, focus_map='reversed'))
        else:
            # Case where module exists in loaded_data but its parameter info is None
            # (e.g., modinfo failed for this specific module, or it has no parameters).
            param_list_walker.append(urwid.AttrMap(urwid.Text("No parameter data available for this module."), None, focus_map='reversed'))
    else:
        # No module selected, or selected module not found in data (should not happen if UI is consistent).
        param_list_walker.append(urwid.AttrMap(urwid.Text("Select a module to view its parameters."), None, focus_map='reversed'))

def on_profile_selected(_button, profile_name_sanitized: str) -> None:
    """
    Callback for when a profile is selected from the profile list.
    Loads the profile, applies its parameters, and updates UI status and data.

    Args:
        _button: The profile button widget that was clicked.
        profile_name_sanitized (str): The sanitized name of the selected profile.
    """
    global status_text, loaded_module_data, selected_module_name_global

    status_text.set_text(f"Loading profile '{profile_name_sanitized}'...")
    profile_data_dict, message = load_profile(profile_name_sanitized, PROFILES_DIR)

    if not profile_data_dict: # load_profile returns (None, error_message) on failure
        status_text.set_text(message) # Display error from load_profile
        return

    original_profile_name = profile_data_dict.get('profile_name', profile_name_sanitized)
    status_text.set_text(f"Applying profile '{original_profile_name}'...")

    # Apply parameters using the backend function
    application_results = apply_profile_parameters(profile_data_dict['parameters'])

    # Format and display the results of the apply operation
    success_c = application_results['success_count']
    failure_c = application_results['failure_count']
    summary_msg = f"Applied '{original_profile_name}': {success_c} succeeded, {failure_c} failed."

    if application_results['failures']:
        summary_msg += " (See details below - first few shown)"
        # Append details of a few failures to the status message for quick diagnostics
        for fail_info in application_results['failures'][:2]: # Limit to avoid overly long status
            summary_msg += f"\n  └─Fail: {fail_info['module']}/{fail_info['parameter']} - {fail_info['reason']}"
    status_text.set_text(summary_msg)

    # Crucially, refresh the 'loaded_module_data' for affected parameters
    # by re-reading their current values from sysfs. This ensures the UI
    # reflects the actual state after attempting to apply the profile.
    modules_affected_by_profile = profile_data_dict.get('parameters', {}).keys()
    for mod_name in modules_affected_by_profile:
        if mod_name not in loaded_module_data or loaded_module_data[mod_name] is None:
            # Module from profile might not be in current scan or has no params loaded.
            # A more advanced refresh might re-scan this module. For now, skip.
            continue

        params_in_module_profile = profile_data_dict['parameters'][mod_name]
        for param_name in params_in_module_profile.keys():
            if param_name in loaded_module_data[mod_name]: # Check if param is known
                # Fetch the actual current value from sysfs after apply attempt
                current_live_value = get_sysfs_param_value(mod_name, param_name)
                loaded_module_data[mod_name][param_name]['current'] = current_live_value

    # Refresh the parameter list display if the currently selected module was affected by the profile.
    if selected_module_name_global in modules_affected_by_profile:
        update_param_list_display(selected_module_name_global)

def update_profile_list_display() -> None:
    """
    Updates the profile list pane by fetching profiles from the backend.
    Handles cases like directory errors or no profiles found.
    """
    global profile_list_walker, status_text

    profile_list_walker.clear() # Clear existing profile list items
    profile_names_list, message = list_profiles(PROFILES_DIR) # Get profiles from backend

    if profile_names_list is None: # Indicates an error accessing the profile directory
        profile_list_walker.append(urwid.AttrMap(urwid.Text(message), None, focus_map='reversed'))
        status_text.set_text(message) # Display the error in the status bar as well
    elif not profile_names_list: # Directory exists but no profiles found
        profile_list_walker.append(urwid.AttrMap(urwid.Text(message), None, focus_map='reversed'))
        # Optionally update status_text, but 'message' might be "No profiles found..."
        # which is already clear in the list itself.
    else: # Profiles found
        for name_sanitized in sorted(profile_names_list): # Ensure sorted display
            # Create a button for each profile; clicking it triggers loading/applying.
            profile_button = urwid.Button(name_sanitized)
            urwid.connect_signal(profile_button, 'click', on_profile_selected, user_args=[name_sanitized])
            profile_list_walker.append(urwid.AttrMap(profile_button, None, focus_map='reversed'))
        # status_text.set_text(message) # "Found X profiles" message can be a bit verbose for status bar.

def on_module_selected(_button, new_selected_module_name: str) -> None:
    """
    Callback for when a module is selected from the module list.
    Updates the parameter list display for the newly selected module.

    Args:
        _button: The module button widget that was clicked.
        new_selected_module_name (str): Name of the newly selected module.
    """
    update_param_list_display(new_selected_module_name)

# --- Main TUI Setup and Execution ---
def run_tui() -> None:
    """
    Initializes and runs the main Text User Interface.
    Sets up the layout, loads initial data, and starts the Urwid event loop.
    """
    global loaded_module_data, module_list_walker, status_text, profile_list_walker
    global main_layout_widget, urwid_loop # Store main layout and loop globally

    # 1. Load Initial Data from the backend
    # This fetches all module and parameter data at startup.
    loaded_module_data = collect_all_module_data()

    # 2. Header Widget
    header = urwid.AttrMap(urwid.Text("Kernameters TUI - Kernel Module Parameters", align='center'), 'header')

    # 3. Module List Pane
    module_buttons = []
    # Handle cases where initial data loading might have failed or returned specific info.
    if "error" in loaded_module_data:
        module_buttons.append(urwid.Text(f"Error loading modules: {loaded_module_data['error']}"))
    elif "info" in loaded_module_data and len(loaded_module_data) == 1 and "info" in loaded_module_data : # Only info key
         module_buttons.append(urwid.Text(loaded_module_data['info']))
    elif not loaded_module_data: # Empty dictionary means no modules or data
        module_buttons.append(urwid.Text("No kernel modules found or data is empty."))
    else: # Populate with actual module names
        for module_name_key in sorted(loaded_module_data.keys()):
            # Skip special keys like "error" or "info" if they are part of the dict
            if module_name_key in ["error", "info"]:
                continue
            module_button = urwid.Button(module_name_key)
            urwid.connect_signal(module_button, 'click', on_module_selected, user_args=[module_name_key])
            module_buttons.append(urwid.AttrMap(module_button, None, focus_map='reversed'))

    module_list_walker.contents = module_buttons # Set contents after creating all buttons
    module_list_box = urwid.ListBox(module_list_walker)
    module_list_ui = urwid.LineBox(module_list_box, title="Modules")

    # 4. Parameter List Pane (uses global param_list_walker)
    param_list_box = urwid.ListBox(param_list_walker)
    param_list_ui = urwid.LineBox(param_list_box, title="Parameters")

    # 5. Profile List Pane (uses global profile_list_walker)
    profile_list_box = urwid.ListBox(profile_list_walker)
    profiles_pane = urwid.LineBox(profile_list_box, title="Profiles")

    # Status Pane (uses global status_text)
    actions_pane = urwid.LineBox(urwid.Filler(status_text, valign='top',min_height=2), title="Status / Actions") # Ensure min height for status

    # 6. Assemble Main Layout using Columns and Pile
    # Top section: Module List and Parameter List side-by-side
    top_columns = urwid.Columns([
        ('weight', 1, module_list_ui),    # Module list takes 1/3 of width
        ('weight', 2, param_list_ui),     # Parameter list takes 2/3 of width
    ], dividechars=1) # Adds a vertical divider line

    # Bottom section: Profile List and Status/Actions Pane side-by-side
    bottom_columns = urwid.Columns([
        ('weight', 1, profiles_pane),     # Profile list
        ('weight', 2, actions_pane),      # Status/Actions
    ], dividechars=1)

    # Overall layout: Header, then top columns, then bottom columns
    main_layout_widget = urwid.Pile([ # Store the main layout for overlay restoration
        (1, header), # Header has fixed height of 1 row
        ('weight', 2, top_columns),  # Top section takes 2/3 of remaining vertical space
        ('weight', 1, bottom_columns) # Bottom section takes 1/3 of remaining vertical space
    ])

    # 7. Initial UI State Setup
    # If modules were loaded, select the first one and display its parameters.
    if module_buttons and hasattr(module_list_walker[0], 'original_widget') and \
       isinstance(module_list_walker[0].original_widget, urwid.Button):
        initial_module_name_label = module_list_walker[0].original_widget.label
        update_param_list_display(initial_module_name_label)
        if module_list_walker: # Ensure walker is not empty
             module_list_walker.set_focus(0) # Set focus to the first module
    else: # No modules loaded or error state
        update_param_list_display(None) # Show placeholder in parameter list

    update_profile_list_display() # Populate the profile list at startup

    # 8. Urwid MainLoop Setup
    # Define color palette for UI elements
    palette = [
        ('header', 'white', 'dark blue', 'bold'), # Header style
        ('reversed', 'standout', ''),             # Style for focused items
        # Add more styles here as needed (e.g., for errors, status messages)
    ]

    def global_input_handler(key: str) -> bool | None:
        """Handles global key presses (like 'q' to quit, 's' to save profile, 'Esc' for overlays)."""
        nonlocal urwid_loop # Allow modification of urwid_loop if needed (though already global)

        # If an overlay is active, 'esc' should close it.
        if key == 'esc' and isinstance(urwid_loop.widget, urwid.Overlay):
            execute_cancel_overlay(None) # Call the generic overlay cancel function
            return True # Key was handled

        # If not in an overlay:
        if not isinstance(urwid_loop.widget, urwid.Overlay):
            if key in ('q', 'Q'): # Quit application
                raise urwid.ExitMainLoop()
            if key in ('s', 'S'): # Save profile
                prompt_save_profile()
                return True # Key was handled

        return None # Key not handled by this global handler, pass to focused widget

    # Create and run the main event loop
    urwid_loop = urwid.MainLoop(main_layout_widget, palette=palette, unhandled_input=global_input_handler)
    urwid_loop.run()

if __name__ == "__main__":
    # This block allows the TUI to be run directly using `python kernameters_tui.py`.
    # It assumes that `kernameters.py` (the backend) is in the same directory
    # or is otherwise findable via Python's import mechanisms (e.g., PYTHONPATH).
    run_tui()
