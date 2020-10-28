import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

for dep in [
    os.path.join(SCRIPT_DIR, "deps", "six"),
    os.path.join(SCRIPT_DIR, "deps", "parsimonious"),
]:
    if not os.path.exists(dep):
        sys.exit("Error: dependency '{}' does not exist, check README.md for how to download it".format(dep))
    sys.path.insert(0, dep)
