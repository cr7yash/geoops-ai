"""Generate Terraform BigQuery table schemas from the canonical SQL DDL."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tables = {}
for path in sorted((ROOT / "data/schema").glob("*.sql")):
    for match in re.finditer(
        r"CREATE TABLE IF NOT EXISTS `[^`]+\.([^`.]+)` \((.*?)\)\s*(.*?);", path.read_text(), re.S
    ):
        name, columns, options = match.groups()
        fields = []
        for line in columns.splitlines():
            column = re.fullmatch(r"\s*(\w+)\s+(ARRAY<\w+>|\w+)(\s+NOT NULL)?\s*,?", line)
            if column is None:
                if line.strip():
                    raise ValueError(f"Unrecognized column: {line}")
                continue
            field, type_name, required = column.groups()
            repeated = type_name.startswith("ARRAY<")
            fields.append(
                {
                    "name": field,
                    "type": type_name[6:-1] if repeated else type_name,
                    "mode": "REPEATED" if repeated else "REQUIRED" if required else "NULLABLE",
                }
            )
        partition = re.search(r"PARTITION BY DATE\((\w+)\)", options)
        clustering = re.search(r"CLUSTER BY ([\w, ]+)", options)
        tables[name] = {
            "fields": fields,
            "partition": partition.group(1) if partition else None,
            "clustering": [item.strip() for item in clustering.group(1).split(",")]
            if clustering
            else [],
        }
(ROOT / "infrastructure/terraform/tables.json").write_text(json.dumps(tables, indent=2) + "\n")
print(f"Generated {len(tables)} BigQuery table definitions")
