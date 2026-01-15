import os

base_dir = r"c:\Users\Windows Lite BR\Programação\Python\Portfolio"
files = [
    r"app\main.py",
    r"app\models.py",
    r"app\database.py",
    r"app\services\github_service.py",
    r"app\templates\base.html",
    r"app\templates\index.html",
    r"app\templates\partials\project_list.html",
    r"app\templates\partials\contact_success.html",
    r"requirements.txt",
    r"tests\run_tests.py"
]

output_file = os.path.join(base_dir, "project_context.md")

with open(output_file, "w", encoding="utf-8") as outfile:
    outfile.write("# Project Context: DevFolio Dinâmico\n\n")
    for f in files:
        full_path = os.path.join(base_dir, f)
        if os.path.exists(full_path):
            outfile.write(f"## File: {f}\n")
            # Determine language for syntax highlighting
            ext = f.split('.')[-1]
            lang = "python" if ext == "py" else "html" if ext == "html" else ""
            
            outfile.write(f"```{lang}\n")
            with open(full_path, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
            outfile.write("\n```\n\n")
        else:
            outfile.write(f"## File: {f} (NOT FOUND)\n\n")

print(f"Context written to {output_file}")
