locals {
  shared_env = {
    APP_ENV               = "production", APPROVAL_STORE = "firestore", EVENT_BUS = "pubsub",
    WORKER_ENABLED        = "false", GOOGLE_CLOUD_PROJECT = var.project_id,
    GOOGLE_CLOUD_LOCATION = var.region, PUBSUB_TOPIC = "dispatch-approved",
    ANALYTICS_PROVIDER    = "bigquery", BIGQUERY_DATASET = "geoops",
    MODEL_PROVIDER        = var.model_provider, MODEL_NAME = var.model_name,
    MAPS_PROVIDER         = var.maps_provider, DOCUMENT_PROVIDER = "gcs", VECTOR_PROVIDER = "bigquery",
    DOCUMENTS_BUCKET      = google_storage_bucket.documents.name, CATALOG_PROVIDER = "bigquery"

  }
}

resource "google_cloud_run_v2_service" "backend" {
  for_each = {
    api = var.api_image, worker = var.worker_image
  }
  name                = "geoops-${each.key}"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account = google_service_account.service[each.key].email
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
    containers {
      image = each.value
      ports {
        container_port = 8000
      }
      resources {
        limits = {
          cpu = "1", memory = "1Gi"
        }
      }
      dynamic "env" {
        for_each = merge(local.shared_env, each.key == "worker" ? {
          MODEL_PROVIDER = "local", MODEL_NAME = "geoops-local-planner-v1"
        } : {})
        content {
          name  = env.key
          value = env.value
        }

      }
      env {
        name = "API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "geoops-api-token"
            version = "latest"
          }
        }

      }
      dynamic "env" {
        for_each = each.key == "api" && var.model_provider == "gemini_api" ? ["GEMINI_API_KEY"] : []
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = "gemini-api-key"
              version = "latest"
            }
          }

        }

      }
      dynamic "env" {
        for_each = var.maps_provider == "google" ? ["GOOGLE_MAPS_API_KEY"] : []
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = "google-maps-api-key"
              version = "latest"
            }
          }

        }

      }
      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
      }

    }

  }
  depends_on = [google_project_service.api, google_secret_manager_secret_iam_member.token]
}

resource "google_cloud_run_v2_service" "web" {
  name                = "geoops-web"
  location            = var.region
  deletion_protection = true
  template {
    service_account = google_service_account.service["web"].email
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
    containers {
      image = var.web_image
      ports {
        container_port = 3000
      }
      env {
        name  = "API_INTERNAL_BASE_URL"
        value = google_cloud_run_v2_service.backend["api"].uri
      }
      env {
        name  = "API_USE_GOOGLE_ID_TOKEN"
        value = "true"
      }
      env {
        name = "GEOOPS_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "geoops-api-token"
            version = "latest"
          }
        }

      }

    }

  }
  depends_on = [google_secret_manager_secret_iam_member.token]
}

resource "google_cloud_run_v2_service_iam_member" "web_to_api" {
  name     = google_cloud_run_v2_service.backend["api"].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.service["web"].email}"
}

resource "google_cloud_run_v2_service_iam_member" "web_user" {
  for_each = var.allowed_web_members
  name     = google_cloud_run_v2_service.web.name
  location = var.region
  role     = "roles/run.invoker"
  member   = each.value
}

resource "google_cloud_run_v2_job" "ingestion" {
  name                = "geoops-ingestion"
  location            = var.region
  deletion_protection = true
  template {
    template {
      service_account = google_service_account.service["ingestion"].email
      max_retries     = 2
      timeout         = "600s"
      containers {
        image = var.ingestion_image
        dynamic "env" {
          for_each = merge(local.shared_env, {
            DOCUMENT_PROVIDER = "gcs", DOCUMENTS_BUCKET = google_storage_bucket.documents.name,
            VECTOR_PROVIDER   = "bigquery", MAPS_PROVIDER = "mock"

          })
          content {
            name  = env.key
            value = env.value
          }

        }
        env {
          name = "API_TOKEN"
          value_source {
            secret_key_ref {
              secret  = "geoops-api-token"
              version = "latest"
            }
          }
        }
        dynamic "env" {
          for_each = var.model_provider == "gemini_api" ? ["GEMINI_API_KEY"] : []
          content {
            name = env.value
            value_source {
              secret_key_ref {
                secret  = "gemini-api-key"
                version = "latest"
              }
            }
          }
        }

      }

    }

  }
}

output "web_url" {
  value = google_cloud_run_v2_service.web.uri
}
output "api_url" {
  value = google_cloud_run_v2_service.backend["api"].uri
}
output "worker_url" {
  value = google_cloud_run_v2_service.backend["worker"].uri
}
output "documents_bucket" {
  value = google_storage_bucket.documents.name
}
