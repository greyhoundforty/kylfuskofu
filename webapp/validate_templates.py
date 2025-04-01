import os
import jinja2

# Setup Jinja environment
env = jinja2.Environment(loader=jinja2.FileSystemLoader(["templates"]))

# Try to load each template
for root, dirs, files in os.walk("templates"):
    for file in files:
        if file.endswith(".html"):
            try:
                template_path = os.path.join(root, file).replace("templates/", "")
                template = env.get_template(template_path)
                print(f"✅ {template_path} - Valid")
            except Exception as e:
                print(f"❌ {template_path} - ERROR: {str(e)}")
