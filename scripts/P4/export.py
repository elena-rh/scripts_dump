#!/usr/bin/env python3
from datetime import datetime
import subprocess
import csv
import re
import sys

import json
from pathlib import Path
from shared_utils import load_json

# need to login to p4 CLI in order to run this script
# p4 info <-- see current settings and write Client name in config.json
# p4 set <-- more settings

CONFIG_PATH = Path(__file__).parent / "config.json"
CONFIG_SCHEMA = {
        "type": "object",
        "required": ["client_name", "depot_path_prefix"],
        "properties": {
            "client_name": {"type": "string"},
            "depot_path_prefix": {"type": "string"},
            "depot_path_suffix": {"type": "string"},
            "outfile_path": {"type": "string"},
            "outfile_prefix": {"type": "string"},
        }
    }

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("Missing config.json. Copy config.example.json and fill in your values.")

    config_schema = json.dumps(CONFIG_SCHEMA)

    data = load_json(CONFIG_PATH, config_schema) # this raises errors, allow it
    if not isinstance(data, dict):
        raise TypeError("Expected top-level JSON to be an object")
    return data

#=============================================================================================

def main():
    if len(sys.argv) != 2:
        print("Usage: python export.py <depot_name>")
        sys.exit(1)

    config = _load_config()

    depot_name = sys.argv[1]
    depot_path = config.get("depot_path_prefix", "") + depot_name + config.get("depot_path_suffix", "") 
    
    client_name = config.get("client_name", "")
    outfile = config.get("outfile_path", "") + config.get("outfile_prefix", "") + depot_name + "_" + datetime.now().strftime("%Y%m%d_%H%M") + ".csv"

    try:
        changes_output = subprocess.check_output(["p4", "changes", "-c", client_name, "-s", "submitted", depot_path], text=True)
        changelist_ids = [line.split()[1] for line in changes_output.strip().split('\n') if line]
        
        with open(outfile, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Changelist ID", "Date", "Description", "Affected Files"])

            for cl_id in changelist_ids:
                cl_output = subprocess.check_output(["p4", "describe", "-s", "-a", cl_id], text=True)
                
                # Header
                header_match = re.search(r"^Change (\d+) by .* on (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})", cl_output, re.MULTILINE)
                cl_date = header_match.group(2) if header_match else ""

                # Description
                desc_match = re.search(r"\n\n([ \t].+?)\n\nAffected files", cl_output, re.DOTALL)
                description = desc_match.group(1).replace('\n', ' ').strip() if desc_match else ""

                # Affected files
                files_match = re.findall(r"\.\.\. (//.+?)#\d+", cl_output)
                affected_files = "; ".join(files_match)

                writer.writerow([cl_id, cl_date, description, affected_files])


        print("Export completed successfully to " + outfile)

    except subprocess.CalledProcessError as e:
        print(f"Error executing p4 command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()