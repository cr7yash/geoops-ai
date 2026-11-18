mock_provider "google" {}

variables {
  project_id      = "geoops-offline-test"
  api_image       = "us-central1-docker.pkg.dev/geoops-offline-test/geoops/api:test"
  web_image       = "us-central1-docker.pkg.dev/geoops-offline-test/geoops/web:test"
  worker_image    = "us-central1-docker.pkg.dev/geoops-offline-test/geoops/worker:test"
  ingestion_image = "us-central1-docker.pkg.dev/geoops-offline-test/geoops/ingestion:test"
}

run "private_services_and_bounded_delivery" {
  command = plan
  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.web_user) == 0
    error_message = "The console must require explicit operator IAM members."
  }
  assert {
    condition     = google_pubsub_subscription.worker.dead_letter_policy[0].max_delivery_attempts == 10
    error_message = "Poison deliveries must reach the dead-letter topic after bounded retries."
  }
  assert {
    condition     = google_cloud_run_v2_service.backend["api"].template[0].scaling[0].min_instance_count == 0
    error_message = "The API must scale to zero in the default low-cost configuration."
  }
  assert {
    condition     = google_storage_bucket.documents.public_access_prevention == "enforced"
    error_message = "Source documents must remain private."
  }
}
