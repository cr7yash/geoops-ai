resource "google_project_iam_member" "datastore" {
  project  = var.project_id
  for_each = toset(["api", "worker", "ingestion"])
  role     = "roles/datastore.user"
  member   = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_project_iam_member" "query" {
  project  = var.project_id
  for_each = toset(["api", "worker", "ingestion"])
  role     = "roles/bigquery.jobUser"
  member   = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_bigquery_dataset_iam_member" "data" {
  for_each   = toset(["api", "worker", "ingestion"])
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_project_iam_member" "vertex" {
  project  = var.project_id
  for_each = toset(["api", "ingestion"])
  role     = "roles/aiplatform.user"
  member   = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_storage_bucket_iam_member" "documents" {
  for_each = toset(["api", "ingestion"])
  bucket   = google_storage_bucket.documents.name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_secret_manager_secret_iam_member" "token" {
  for_each  = toset(["api", "web", "worker", "ingestion"])
  secret_id = google_secret_manager_secret.secret["geoops-api-token"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_secret_manager_secret_iam_member" "model" {
  for_each  = var.model_provider == "gemini_api" ? toset(["api", "ingestion"]) : toset([])
  secret_id = google_secret_manager_secret.secret["gemini-api-key"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_secret_manager_secret_iam_member" "maps" {
  for_each  = var.maps_provider == "google" ? toset(["api", "worker"]) : toset([])
  secret_id = google_secret_manager_secret.secret["google-maps-api-key"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.service[each.key].email}"
}

resource "google_project_iam_member" "build" {
  project  = var.project_id
  for_each = toset(["roles/run.developer", "roles/artifactregistry.writer", "roles/logging.logWriter"])
  role     = each.key
  member   = "serviceAccount:${google_service_account.service["build"].email}"
}

resource "google_service_account_iam_member" "build_act_as" {
  for_each           = toset(["api", "web", "worker", "ingestion"])
  service_account_id = google_service_account.service[each.key].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.service["build"].email}"
}
