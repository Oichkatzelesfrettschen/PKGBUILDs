import subprocess
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Function to run a command and return its output
def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error running command '{command}': {stderr.decode('utf-8')}")
        return None
    return stdout.decode('utf-8')

# Function to get module parameters from modinfo
def get_modinfo_params(module):
    if not module or not isinstance(module, str):
        return None
    output = run_command(f'modinfo -p {module}')
    if output is None or output.strip() == '':
        return None
    params = {}
    for line in output.strip().split('\n'):
        parts = line.split(':')
        if len(parts) >= 2:
            params[parts[0].strip()] = parts[1].strip()
    return params

# Function to get current module parameters from systool
def get_systool_params(module):
    if not module or not isinstance(module, str):
        return {}
    output = run_command(f'systool -v -m {module}')
    if output is None:
        return {}
    params = {}
    reading_params = False
    for line in output.strip().split('\n'):
        if reading_params:
            if line.strip() == '':
                break
            parts = line.split('=')
            if len(parts) == 2:
                params[parts[0].strip()] = parts[1].strip()
        elif 'Parameters:' in line:
            reading_params = True
    return params

# Function to create the PDF report
def create_pdf_report(module_data, filename):
    styles = getSampleStyleSheet()
    try:
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))
        elements = []

        modules_with_data = sorted([m for m, d in module_data.items() if d is not None])
        modules_no_data = sorted([m for m, d in module_data.items() if d is None])

        for module_list in [modules_with_data, modules_no_data]:
            for module in module_list:
                data = module_data[module]
                table_data = [['Module', 'Loaded Parameters', 'Available Parameters']]
                if data is None:
                    table_data.append([module, 'No data available', ''])
                else:
                    first = True
                    for param, values in data.items():
                        loaded_para = Paragraph(f'{param}: {values["current"]}', styles['Normal'])
                        available_para = Paragraph(f'{param}: {values["available"]}', styles['Normal'])
                        if first:
                            table_data.append([module, loaded_para, available_para])
                            first = False
                        else:
                            table_data.append(['', loaded_para, available_para])
                t = Table(table_data, colWidths=[100, 300, 300], repeatRows=1)
                t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                       ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                                       ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                       ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                       ('FONTSIZE', (0, 0), (-1, -1), 8),
                                       ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
                elements.append(t)

        doc.build(elements)
    except Exception as e:
        print(f"Error in creating PDF report: {e}")

# Main function
def main():
    modules = run_command("lsmod | awk 'NR>1 {print $1}'")
    if modules is None:
        print("Error: Unable to retrieve kernel modules.")
        return

    module_data = {}
    for module in set(modules.strip().split('\n')):
        modinfo_params = get_modinfo_params(module)
        systool_params = get_systool_params(module)
        if modinfo_params is None:
            module_data[module] = None
        else:
            comparison = {param: {'current': systool_params.get(param, 'N/A'), 'available': modinfo_params.get(param, 'N/A')}
                          for param in set(modinfo_params) | set(systool_params)}
            module_data[module] = comparison

    create_pdf_report(module_data, 'module_parameters_report.pdf')
    print("Report generated: module_parameters_report.pdf")

if __name__ == "__main__":
    main()
