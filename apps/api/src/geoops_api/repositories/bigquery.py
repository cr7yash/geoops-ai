"""Bounded analytical snapshots loaded through BigQuery, with operational overlays."""

import asyncio
import json
from time import monotonic
from typing import Any

from google.cloud import bigquery

from geoops_api.domain.models import SeedDataset
from geoops_api.repositories.local import JsonCatalogRepository


class BigQueryCatalogRepository(JsonCatalogRepository):
    def configure(self, project: str, dataset: str) -> None:
        self._client = bigquery.Client(project=project)
        self._dataset_id = f"{project}.{dataset}"
        self._loaded_at = 0.0
        self._load_lock = asyncio.Lock()

    async def refresh(self) -> None:
        async with self._load_lock:
            if monotonic() - self._loaded_at > 30:

                def load() -> SeedDataset:
                    payload = self._seed.model_dump(mode="json")
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
                        projection = "* EXCEPT(updated_at)" if table != "sla_events" else "*"
                        if table == "sites":
                            projection = (
                                "* EXCEPT(updated_at, location), IF(location IS NULL, NULL, "
                                "STRUCT(ST_Y(location) AS latitude, "
                                "ST_X(location) AS longitude)) AS location"
                            )
                        if table == "technicians":
                            projection = (
                                "* EXCEPT(updated_at, current_location), "
                                "STRUCT(ST_Y(current_location) AS latitude, "
                                "ST_X(current_location) AS longitude) AS current_location"
                            )
                        query = f"SELECT {projection} FROM `{self._dataset_id}.{table}` LIMIT 10000"
                        config = bigquery.QueryJobConfig(maximum_bytes_billed=100_000_000)
                        rows = self._client.query(query, job_config=config).result(timeout=60)
                        records: list[dict[str, Any]] = [dict(row) for row in rows]
                        for record in records:
                            if isinstance(record.get("metadata"), str):
                                record["metadata"] = json.loads(record["metadata"])
                        payload[table] = records
                    return SeedDataset.model_validate(payload)

                self._seed = await asyncio.to_thread(load)
                self._customers = {item.customer_id: item for item in self._seed.customers}
                self._sites = {item.site_id: item for item in self._seed.sites}
                self._technicians = {item.technician_id: item for item in self._seed.technicians}
                self._loaded_at = monotonic()
        await super().refresh()
