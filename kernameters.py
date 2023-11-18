import subprocess
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def run_command(command: str) -> str:
    """
    Run a shell command and return the output as a string.
    """
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    return None if process.returncode != 0 else stdout.decode("utf-8")

def get_modinfo_params(module: str):
    """
    Retrieve modinfo parameters for a given module.
    """
    if not isinstance(module, str) or not module:
        return None  # Handle non-string or empty module names
    output = run_command(f"modinfo -p {module}")
    if not output:
        return None  # Handle module not found in modinfo
    params = {}
    for line in output.strip().split("\n"):
        parts = line.split(":")
        if len(parts) >= 2:
            params[parts[0].strip()] = parts[1].strip()
    return params

def get_systool_params(module: str):
    """
    Retrieve systool parameters for a given module.
    """
    if not isinstance(module, str) or not module:
        return {}  # Handle non-string or empty module names
    output = run_command(f"systool -v -m {module}")
    if not output:
        return {}  # Handle module not found in systool
    params = {}
    reading_params = False
    for line in output.strip().split("\n"):
        if reading_params:
            if line.strip() == '':
                break
            parts = line.split('=')
            if len(parts) == 2:
                params[parts[0].strip()] = parts[1].strip()
        elif 'Parameters:' in line:
            reading_params = True
    return params

def create_paragraph(text: str, styles):
    """
    Create a formatted paragraph for long text.
    """
    if not text:
        return Paragraph("", styles["Normal"])  # Handle empty text input
    return Paragraph(text, styles["Normal"])

def create_table_data(module_data: dict):
    """
    Create table data for modules with loaded and available parameters.
    """
    if not module_data:
        return [["Module", "Loaded Parameters", "Available Parameters"]]  # Handle empty module_data input
    table_data = [["Module", "Loaded Parameters", "Available Parameters"]]
    for module, data in module_data.items():
        if data is None:
            table_data.append([module, "No data available", ""])
        else:
            first = True
            for param, values in data.items():
                loaded_para = create_paragraph(f'{param}: {values["current"]}', style)
                available_para = create_paragraph(f'{param}: {values["available"]}', style)
                if first:
                    table_data.append([module, loaded_para, available_para])
                    first = False
                else:
                    table_data.append(["", loaded_para, available_para])
    return table_data

def create_pdf_report(module_data: dict, filename: str):
    """
    Create a PDF report with module data.
    """
    if not filename:
        print("Error: Filename for PDF report is empty.")
        return
    try:
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))
        style = getSampleStyleSheet()
        table_data = create_table_data(module_data)
        elements = [Table(table_data, colWidths=[100, 300, 300], repeatRows=1).setStyle(
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
        )]
        doc.build(elements)
    except Exception as e:
        print(f"Error in creating PDF report: {e}")

def main():
    """
    Main function to run the script.
    """
    modules = run_command("lsmod | awk 'NR>1 {print $1}'")
    if not modules:
        print("Error: Unable to retrieve kernel modules or no modules loaded.")
        return

    module_data = {}
    for module in set(modules.strip().split("\n")):
        if not module:  # Skip empty module names
            continue
        modinfo_params = get_modinfo_params(module)
        systool_params = get_systool_params(module)
        if modinfo_params is None:
            module_data[module] = None
        else:
            comparison = {param: {"current": systool_params.get(param, "N/A"),
                                  "available": modinfo_params.get(param, "N/A")}
                          for param in set(modinfo_params) | set(systool_params)}
            module_data[module] = comparison

    create_pdf_report(module_data, "module_parameters_report.pdf")
    print("Report generated: module_parameters_report.pdf")

if __name__ == "__main__":
    main()
