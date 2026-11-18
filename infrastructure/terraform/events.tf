resource "google_pubsub_topic" "dispatch" {
  name       = "dispatch-approved"
  depends_on = [google_project_service.api]
}
resource "google_pubsub_topic" "dead_letter" {
  name = "dispatch-dead-letter"
}
resource "google_pubsub_subscription" "dead_letter" {
  name                       = "dispatch-dead-letter-inspect"
  topic                      = google_pubsub_topic.dead_letter.id
  message_retention_duration = "604800s"
}
resource "google_pubsub_subscription" "worker" {
  name                 = "geoops-dispatch-worker"
  topic                = google_pubsub_topic.dispatch.id
  ack_deadline_seconds = 60
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.backend["worker"].uri}/events"
    oidc_token {
      service_account_email = google_service_account.service["pubsub"].email
      audience              = google_cloud_run_v2_service.backend["worker"].uri

    }

  }
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 10
  }
}
resource "google_pubsub_topic_iam_member" "publisher" {
  topic  = google_pubsub_topic.dispatch.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.service["worker"].email}"
}
resource "google_cloud_run_v2_service_iam_member" "worker_invoker" {
  for_each = toset(["pubsub", "scheduler"])
  name     = google_cloud_run_v2_service.backend["worker"].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.service[each.key].email}"
}
data "google_project" "current" {}
resource "google_project_iam_member" "pubsub_token" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_pubsub_topic_iam_member" "dead_letter_publisher" {
  topic  = google_pubsub_topic.dead_letter.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_pubsub_subscription_iam_member" "dead_letter_subscriber" {
  subscription = google_pubsub_subscription.worker.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_cloud_scheduler_job" "relay" {
  name     = "geoops-outbox-relay"
  region   = var.region
  schedule = "* * * * *"
  http_target {
    uri         = "${google_cloud_run_v2_service.backend["worker"].uri}/relay"
    http_method = "POST"
    oidc_token {
      service_account_email = google_service_account.service["scheduler"].email
      audience              = google_cloud_run_v2_service.backend["worker"].uri

    }

  }
}
resource "google_logging_metric" "failed_dispatch" {
  name   = "geoops/dispatch_failures"
  filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.message=\"dispatch_failed\""
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}
resource "google_monitoring_alert_policy" "dispatch_failures" {
  display_name = "GeoOps dispatch failures"
  combiner     = "OR"
  conditions {
    display_name = "Dispatch worker failed a business validation"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/geoops/dispatch_failures\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }

    }

  }
  depends_on = [google_logging_metric.failed_dispatch]
}
