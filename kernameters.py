import subprocess
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# Function to run a command in the shell and return its output.
def run_command(command):
    # Create a subprocess to run the shell command.
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    (
        stdout,
        stderr,
    ) = process.communicate()  # Capture the output and error (if any) of the command.
    if process.returncode != 0:
        # If the command failed (return code not 0), return None.
        return None
    return stdout.decode("utf-8")  # Decode the output from bytes to string and return.


# Function to get module parameters from the 'modinfo' command.
def get_modinfo_params(module):
    output = run_command(
        f"modinfo -p {module}"
    )  # Run 'modinfo -p' for the given module.
    if output is None or output.strip() == "":
        # If there is no output or it's empty, return None.
        return None
    params = {}
    for line in output.strip().split("\n"):
        # Split each line by ':' to separate the parameter name and its description.
        parts = line.split(":")
        if len(parts) >= 2:
            # Add the parameter and its description to the dictionary.
            params[parts[0].strip()] = parts[1].strip()
    return params


# Function to get current module parameters from 'systool'.
def get_systool_params(module):
    output = run_command(
        f"systool -v -m {module}"
    )  # Run 'systool -v -m' for the given module.
    if output is None:
        # If there is no output, return an empty dictionary.
        return {}
    params = {}
    reading_params = False  # Flag to indicate if we are reading the parameters section.
    for line in output.strip().split("\n"):
        if reading_params:
            # Process the lines when we are in the parameters section.
            if line.strip() == "":
                # If we reach an empty line, end of parameters section.
                break
            parts = line.split("=")
            if len(parts) == 2:
                # Add the parameter and its current value to the dictionary.
                params[parts[0].strip()] = parts[1].strip()
        elif "Parameters:" in line:
            # Start reading parameters when we find the 'Parameters:' line.
            reading_params = True
    return params


# Function to create a formatted paragraph for long text.
def create_paragraph(text):
    styles = getSampleStyleSheet()  # Get default styles for paragraphs.
    return Paragraph(text, styles["Normal"])  # Create a paragraph with the given text.


# Function to create the PDF report.
def create_pdf_report(module_data, filename):
    doc = SimpleDocTemplate(
        filename, pagesize=landscape(letter)
    )  # Create a PDF document in landscape orientation.
    elements = []

    # Sorting modules into those with data and those without.
    modules_with_data = sorted([m for m, d in module_data.items() if d is not None])
    modules_no_data = sorted([m for m, d in module_data.items() if d is None])

    for module_list in [modules_with_data, modules_no_data]:
        for module in module_list:
            data = module_data[module]
            table_data = [["Module", "Loaded Parameters", "Available Parameters"]]
            if data is None:
                # For modules with no data, add a row indicating this.
                table_data.append([module, "No data available", ""])
            else:
                first = True  # Flag to handle the first parameter differently.
                for param, values in data.items():
                    # Create paragraphs for loaded and available parameter values.
                    loaded_para = create_paragraph(f'{param}: {values["current"]}')
                    available_para = create_paragraph(f'{param}: {values["available"]}')
                    if first:
                        # For the first parameter, include the module name in the first cell.
                        table_data.append([module, loaded_para, available_para])
                        first = False
                    else:
                        # For subsequent parameters, leave the first cell empty.
                        table_data.append(["", loaded_para, available_para])
            # Create a table with the data and set its style.
            t = Table(table_data, colWidths=[100, 300, 300], repeatRows=1)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            elements.append(t)  # Add the table to the document elements.

    doc.build(elements)  # Build the PDF document with the accumulated elements.


# Main function to run the script.
def main():
    modules = run_command(
        "lsmod | awk 'NR>1 {print $1}'"
    )  # Get the list of loaded kernel modules.
    if modules is None:
        print("Error: Unable to retrieve kernel modules.")
        return

    module_data = {}
    for module in set(modules.strip().split("\n")):
        modinfo_params = get_modinfo_params(module)  # Get available module parameters.
        systool_params = get_systool_params(module)  # Get current module parameters.
        if modinfo_params is None:
            # If no data available from modinfo, mark as None.
            module_data[module] = None
        else:
            # Compare current and available parameters.
            comparison = {
                param: {
                    "current": systool_params.get(param, "N/A"),
                    "available": modinfo_params.get(param, "N/A"),
                }
                for param in set(modinfo_params) | set(systool_params)
            }
            module_data[module] = comparison

    create_pdf_report(
        module_data, "module_parameters_report.pdf"
    )  # Create the PDF report.
    print("Report generated: module_parameters_report.pdf")


if __name__ == "__main__":
    main()
