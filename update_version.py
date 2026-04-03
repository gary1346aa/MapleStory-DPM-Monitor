import re
import os
from datetime import datetime

VERSION_FILE = "VERSION"
GUI_FILE = "maplestory_dps_gui.py"
SPEC_FILE = "MapleStory_DPM.spec"

def get_next_version():
    today = datetime.now().strftime("%Y%m%d")
    current_version = f"{today}.0"
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            current_version = f.read().strip()
    try:
        last_date, last_iter = current_version.split(".")
        new_iter = int(last_iter) + 1 if last_date == today else 1
    except:
        new_iter = 1
    return f"{today}.{new_iter}"

def update_files(version):
    # 1. Update VERSION file
    with open(VERSION_FILE, "w") as f:
        f.write(version)
    
    # 2. Update maplestory_dps_gui.py
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        gui_content = f.read()
    new_gui = re.sub(
        r'self\.root\.title\(v\["title"\] \+ f" v[^"]+"\)',
        f'self.root.title(v["title"] + f" v{version}")',
        gui_content
    )
    with open(GUI_FILE, "w", encoding="utf-8") as f:
        f.write(new_gui)
        
    # 3. Update Spec file
    if os.path.exists(SPEC_FILE):
        with open(SPEC_FILE, "r", encoding="utf-8") as f:
            spec_content = f.read()
        new_spec = re.sub(
            r"name='MapleStory_DPM_v[^']+'",
            f"name='MapleStory_DPM_v{version}'",
            spec_content
        )
        with open(SPEC_FILE, "w", encoding="utf-8") as f:
            f.write(new_spec)

if __name__ == "__main__":
    new_v = get_next_version()
    update_files(new_v)
    print(f"Updated all files to version: {new_v}")
