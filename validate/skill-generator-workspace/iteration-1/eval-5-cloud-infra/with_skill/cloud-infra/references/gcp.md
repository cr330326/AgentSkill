# GCP Reference

## Resource Hierarchy

```
Organization
  └── Folder (optional, for departments/teams)
      └── Project (billing + resource boundary)
          └── Resources
```

- **Projects** are the primary unit of organization. Each project has a unique ID (immutable) and a display name.
- Use separate projects for each environment (e.g., `myapp-dev`, `myapp-prod`).
- Use folders to group projects by team or business unit.

## Naming Conventions

Use this pattern: `{project}-{environment}-{service}-{qualifier}`

Examples:
- `myapp-prod-gke-cluster`
- `myapp-dev-cloudsql-primary`
- `myapp-staging-gcf-api-handler`

Constraints:
- GCS buckets: globally unique, lowercase, hyphens and dots, 3-63 chars
- GKE clusters: lowercase alphanumeric + hyphens, up to 40 chars
- Project IDs: globally unique, 6-30 chars, lowercase + hyphens

## Terraform Provider: hashicorp/google

Registry: https://registry.terraform.io/providers/hashicorp/google/latest

Also consider `hashicorp/google-beta` for preview features.

### Authentication (in order of preference)

1. **Workload Identity Federation** -- for CI/CD (GitHub Actions, GitLab CI); no service account keys
2. **Attached service account** -- for GCE, GKE, Cloud Run (automatic credentials)
3. **Application Default Credentials (ADC)** -- for local dev (`gcloud auth application-default login`)
4. **Service account key file** -- last resort; rotate keys regularly if used

Never commit service account key JSON files. Use `GOOGLE_APPLICATION_CREDENTIALS` if key files are required.

### Key Resources and Modules

| Category | Resource / Module | Notes |
|----------|------------------|-------|
| Networking | `google_compute_network`, `google_compute_subnetwork`, `google_compute_firewall` | Use custom-mode VPCs; avoid default network |
| Compute | `google_compute_instance`, `google_compute_instance_template`, `google_compute_instance_group_manager` | Use instance templates for managed groups |
| Containers | `google_container_cluster`, `google_container_node_pool` | GKE Autopilot for hands-off; Standard for control |
| Serverless | `google_cloudfunctions2_function`, `google_cloud_run_v2_service` | Cloud Run for containers; Functions for event handlers |
| Storage | `google_storage_bucket` | Enable uniform bucket-level access |
| Database | `google_sql_database_instance`, `google_alloydb_cluster` | AlloyDB for PostgreSQL-compatible high-performance |
| NoSQL | `google_firestore_database` | Native mode for mobile/web; Datastore mode for server |
| Messaging | `google_pubsub_topic`, `google_pubsub_subscription` | Use dead-letter topics for failed messages |
| CDN | `google_compute_backend_bucket` with CDN enabled | Use Cloud CDN with Cloud Load Balancing |
| DNS | `google_dns_managed_zone`, `google_dns_record_set` | |
| IAM | `google_project_iam_member`, `google_service_account` | Prefer `_member` over `_binding` to avoid conflicts |
| Monitoring | `google_monitoring_alert_policy`, `google_logging_metric` | Export logs to BigQuery for analysis |
| Secrets | `google_secret_manager_secret`, `google_secret_manager_secret_version` | Automatic rotation with Cloud Functions |

### Common Terraform Patterns

#### VPC with private Google access

```hcl
resource "google_compute_network" "main" {
  name                    = "${var.project_name}-${var.environment}-vpc"
  auto_create_subnetworks = false
  project                 = var.gcp_project_id
}

resource "google_compute_subnetwork" "private" {
  name                     = "${var.project_name}-${var.environment}-private"
  ip_cidr_range            = "10.0.1.0/24"
  region                   = var.gcp_region
  network                  = google_compute_network.main.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

resource "google_compute_router" "router" {
  name    = "${var.project_name}-${var.environment}-router"
  region  = var.gcp_region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.project_name}-${var.environment}-nat"
  router                             = google_compute_router.router.name
  region                             = var.gcp_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
```

#### GCS bucket with best-practice defaults

```hcl
resource "google_storage_bucket" "this" {
  name          = "${var.gcp_project_id}-${var.environment}-${var.bucket_purpose}"
  location      = var.gcp_region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = var.kms_key_id  # omit for Google-managed keys
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  labels = local.common_labels
}
```

## GCP-Specific Best Practices

1. **Enable the API** before using a service (`google_project_service` in Terraform or `gcloud services enable`)
2. **Use Workload Identity** for GKE pods to access GCP services without key files
3. **Enable VPC Service Controls** for sensitive data perimeters
4. **Use Cloud Armor** for WAF and DDoS protection on load balancers
5. **Leverage sustained-use discounts** (automatic) and committed-use discounts (1yr/3yr)
6. **Export billing to BigQuery** for detailed cost analysis and custom dashboards
7. **Use organization policies** to restrict resource locations, disable external IPs, enforce uniform bucket access
8. **Prefer Cloud Run** over Cloud Functions for most workloads -- more flexible, same scale-to-zero, container-native
