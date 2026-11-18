"""Load the synthetic catalog into an already provisioned BigQuery dataset."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from google.cloud import bigquery

from geoops_api.config import Settings

SCHEMAS_PATH = Path(__file__).resolve().parents[4] / "infrastructure/terraform/tables.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Load GeoOps synthetic seed data into BigQuery")
    parser.add_argument(
        "--replace",
        action="store_true",
        required=True,
        help="Acknowledge replacing the synthetic catalog tables",
    )
    parser.parse_args()
    settings = Settings()
    if not settings.google_cloud_project:
        raise ValueError("GOOGLE_CLOUD_PROJECT is required")
    client = bigquery.Client(project=settings.google_cloud_project)
    payload = json.loads(settings.seed_data_path.read_text())
    schemas = json.loads(SCHEMAS_PATH.read_text())
    updated_at = datetime.now(UTC).isoformat()
    for table in (
        "customers",
        "sites",
        "technicians",
        "certifications",
        "technician_certifications",
        "service_tickets",
        "assignments",
        "sla_events",
    ):
        rows = payload[table]
        for row in rows:
            if table != "sla_events":
                row["updated_at"] = updated_at
            for column in ("location", "current_location"):
                if row.get(column):
                    point = row[column]
                    row[column] = f"POINT({point['longitude']} {point['latitude']})"
        definition = schemas[table]
        partition = definition["partition"]
        fields = [bigquery.SchemaField.from_api_repr(field) for field in definition["fields"]]
        job = client.load_table_from_json(
            rows,
            f"{settings.google_cloud_project}.{settings.bigquery_dataset}.{table}",
            job_config=bigquery.LoadJobConfig(
                autodetect=False,
                create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                schema=fields,
                time_partitioning=bigquery.TimePartitioning(field=partition) if partition else None,
                clustering_fields=definition["clustering"] or None,
            ),
        )
        job.result(timeout=120)
        print(f"Loaded {len(rows)} synthetic {table}")


if __name__ == "__main__":
    main()
