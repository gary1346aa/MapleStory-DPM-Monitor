import re
import os
from datetime import datetime

VERSION_FILE = "VERSION"
GUI_FILE = "maplestory_dps_gui.py"
SPEC_FILE = "MapleStory_DPM_v20260329.2.spec" # Current spec file name

def get_next_version():
    today = datetime.now().strftime("%Y%m%d")
    
    # Default if no version file exists
    current_version = f"{today}.0"
    
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            current_version = f.read().strip()
    
    try:
        last_date, last_iter = current_version.split(".")
        if last_date == today:
            new_iter = int(last_iter) + 1
        else:
            new_iter = 1
    except ValueError:
        new_iter = 1
        
    return f"{today}.{new_iter}"

def update_files(version):
    # 1. Update VERSION file
    with open(VERSION_FILE, "w") as f:
        f.write(version)
    
    # 2. Update maplestory_dps_gui.py title
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = re.sub(
        r'self\.root\.title\("MapleStory Boss DPM Monitor v[^"]+"\)',
        f'self.root.title("MapleStory Boss DPM Monitor v{version}")',
        content
    )
    
    with open(GUI_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    # 3. Update/Rename Spec file
    # We'll rename the spec file to a generic name to make automation easier
    GENERIC_SPEC = "MapleStory_DPM.spec"
    
    with open(SPEC_FILE if os.path.exists(SPEC_FILE) else GENERIC_SPEC, "r", encoding="utf-8") as f:
        spec_content = f.read()
        
    # Update name in spec (EXE and COLLECT)
    spec_content = re.sub(
        r"name='MapleStory_DPM_v[^']+'",
        f"name='MapleStory_DPM_v{version}'",
        spec_content
    )
    
    with open(GENERIC_SPEC, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # Remove the old versioned spec file if it exists and isn't the generic one
    if os.path.exists(SPEC_FILE) and SPEC_FILE != GENERIC_SPEC:
        os.remove(SPEC_FILE)
        
    return GENERIC_SPEC

if __name__ == "__main__":
    new_v = get_next_version()
    spec_path = update_files(new_v)
    print(f"Version updated to: {new_v}")
    print(f"Spec file ready: {spec_path}")
