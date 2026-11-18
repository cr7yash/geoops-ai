"""Load the synthetic catalog into an already provisioned BigQuery dataset."""

import argparse
import json
from datetime import UTC, datetime

from google.cloud import bigquery

from geoops_api.config import Settings


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
                row["updated_at"] = datetime.now(UTC).isoformat()
            for column in ("location", "current_location"):
                if row.get(column):
                    point = row[column]
                    row[column] = f"POINT({point['longitude']} {point['latitude']})"
            if "metadata" in row:
                row["metadata"] = json.dumps(row["metadata"])
        job = client.load_table_from_json(
            rows,
            f"{settings.google_cloud_project}.{settings.bigquery_dataset}.{table}",
            job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
        )
        job.result(timeout=120)
        print(f"Loaded {len(rows)} synthetic {table}")


if __name__ == "__main__":
    main()
