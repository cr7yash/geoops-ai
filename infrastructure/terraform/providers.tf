terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    google = {
      source = "hashicorp/google", version = "~> 7.0"
    }

  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "api_image" {
  type = string
}
variable "web_image" {
  type = string
}
variable "worker_image" {
  type = string
}
variable "ingestion_image" {
  type = string
}
variable "model_provider" {
  type    = string
  default = "local"
}
variable "model_name" {
  type    = string
  default = "geoops-local-planner-v1"
}
variable "maps_provider" {
  type    = string
  default = "mock"
}
variable "allowed_web_members" {
  type        = set(string)
  description = "IAM users or groups allowed to invoke the web console. No public access by default."
  default     = []
}

locals {
  services = toset(["run.googleapis.com", "bigquery.googleapis.com", "firestore.googleapis.com",
    "pubsub.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com", "cloudbuild.googleapis.com", "aiplatform.googleapis.com",
  "logging.googleapis.com", "monitoring.googleapis.com", "storage.googleapis.com"])
  identities = toset(["api", "web", "worker", "ingestion", "scheduler", "pubsub", "build"])
}

resource "google_project_service" "api" {
  for_each           = local.services
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "service" {
  for_each     = local.identities
  account_id   = "geoops-${each.key}"
  display_name = "GeoOps ${each.key}"
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "geoops"
  format        = "DOCKER"
  depends_on    = [google_project_service.api]
}

resource "google_secret_manager_secret" "secret" {
  for_each  = toset(["geoops-api-token", "gemini-api-key", "google-maps-api-key"])
  secret_id = each.key
  replication {
    auto {}
  }
  depends_on = [google_project_service.api]
}

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-geoops-documents"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning {
    enabled = true
  }
}

resource "google_firestore_database" "state" {
  name                    = "(default)"
  location_id             = var.region
  type                    = "FIRESTORE_NATIVE"
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  depends_on              = [google_project_service.api]
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = "geoops"
  location                   = "US"
  delete_contents_on_destroy = false
  depends_on                 = [google_project_service.api]
}

resource "google_bigquery_table" "table" {
  for_each            = jsondecode(file("${path.module}/tables.json"))
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = each.key
  schema              = jsonencode(each.value.fields)
  deletion_protection = true
  clustering          = each.value.clustering
  dynamic "time_partitioning" {
    for_each = each.value.partition == null ? [] : [each.value.partition]
    content {
      type  = "DAY"
      field = time_partitioning.value
    }

  }
}
