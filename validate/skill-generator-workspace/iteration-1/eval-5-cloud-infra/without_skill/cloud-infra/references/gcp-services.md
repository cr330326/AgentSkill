# GCP Services Reference

## Service Selection by Workload

### Compute

| Use Case | Service | When to Use |
|---|---|---|
| Containers (orchestrated) | **GKE** | Production Kubernetes; GKE Autopilot for hands-off management |
| Containers (simple) | **Cloud Run** | Stateless containers with auto-scaling to zero |
| Serverless functions | **Cloud Functions** | Event-driven, short tasks (2nd gen supports up to 60 min) |
| VMs | **Compute Engine** | Full OS control, long-running processes, GPU/TPU workloads |
| Batch processing | **Batch** | Large-scale batch jobs on Compute Engine |
| App hosting | **App Engine** | Managed platform for web apps (Standard or Flexible) |

### Storage

| Use Case | Service | When to Use |
|---|---|---|
| Object storage | **Cloud Storage** | Files, backups, data lakes, static assets |
| Block storage | **Persistent Disk** | Disks attached to Compute Engine VMs |
| File storage (NFS) | **Filestore** | Managed NFS for shared file access |
| Archive | **Cloud Storage Archive** | Long-term archival with infrequent access |

### Databases

| Use Case | Service | When to Use |
|---|---|---|
| Relational (managed) | **Cloud SQL** (PostgreSQL, MySQL, SQL Server) | Standard OLTP workloads |
| Relational (scalable) | **AlloyDB** | High-performance PostgreSQL-compatible |
| Global relational | **Spanner** | Globally distributed, strongly consistent relational DB |
| NoSQL (document) | **Firestore** | Mobile/web document database with real-time sync |
| NoSQL (wide-column) | **Bigtable** | High-throughput, low-latency analytics and IoT |
| In-memory cache | **Memorystore** (Redis/Memcached) | Caching, session store |
| Data warehouse | **BigQuery** | Serverless analytics at petabyte scale |

### Networking

| Use Case | Service | When to Use |
|---|---|---|
| Virtual network | **VPC** | Isolated network (global by default in GCP) |
| Load balancing | **Cloud Load Balancing** | Global and regional L4/L7 load balancing |
| DNS | **Cloud DNS** | Managed DNS with 100% SLA |
| CDN | **Cloud CDN** | Global content delivery integrated with Load Balancing |
| API gateway | **API Gateway** or **Apigee** | Managed API gateway (Apigee for enterprise) |
| Service mesh | **Traffic Director** or **Anthos Service Mesh** | Service-to-service traffic management |
| VPN / interconnect | **Cloud VPN**, **Cloud Interconnect** | Hybrid connectivity to on-prem |

### Messaging & Events

| Use Case | Service | When to Use |
|---|---|---|
| Message queue / pub-sub | **Pub/Sub** | Async messaging, event ingestion, streaming |
| Task queue | **Cloud Tasks** | Asynchronous task execution with rate controls |
| Workflow orchestration | **Workflows** | Serverless workflow orchestration |
| Streaming | **Dataflow** (Apache Beam) | Real-time and batch data processing |

### Identity & Security

| Use Case | Service | When to Use |
|---|---|---|
| Identity / access | **IAM** | Users, service accounts, roles, policies |
| Secrets | **Secret Manager** | Store and manage API keys, passwords, certificates |
| Certificate management | **Certificate Manager** | Managed TLS certificates |
| Web application firewall | **Cloud Armor** | DDoS protection and WAF rules |
| Org policies | **Organization Policy Service** | Enforce constraints across projects |

### Observability

| Use Case | Service | When to Use |
|---|---|---|
| Metrics & monitoring | **Cloud Monitoring** | Infrastructure and application metrics, alerting |
| Logs | **Cloud Logging** | Centralized log aggregation and analysis |
| Tracing | **Cloud Trace** | Distributed tracing across services |
| Error tracking | **Error Reporting** | Aggregate and track application errors |

### CI/CD & Developer Tools

| Use Case | Service | When to Use |
|---|---|---|
| Container registry | **Artifact Registry** | Docker images, language packages, OS packages |
| CI/CD | **Cloud Build** | GCP-native build and deploy (or use GitHub Actions) |
| Infrastructure as Code | **Deployment Manager** or **Terraform** | Terraform recommended for multi-cloud |

## GCP Naming Conventions

GCP resource names have specific constraints. Follow this pattern:

```
{project}-{environment}-{service}-{descriptor}
```

Rules:
- Use lowercase letters, numbers, and hyphens only
- Must start with a letter
- Maximum 63 characters for most resources
- GCP project IDs are globally unique — include org abbreviation

Examples:
- `myapp-prod-gke-main`
- `myapp-dev-cloudsql-postgres`
- `myapp-staging-run-api`
- `myapp-prod-gcs-assets`

## GCP Terraform Provider Configuration

```hcl
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "myproject-terraform-state"
    prefix = "env/prod"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region

  default_labels = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}
```

## GCP Best Practices

1. **Use `default_labels`** on the Google provider (v5+) to label all resources automatically.
2. **Prefer Cloud Run** over GKE for stateless HTTP workloads — simpler, scales to zero, lower cost.
3. **Use GKE Autopilot** unless you need specific node-level control.
4. **GCP VPCs are global** — use regional subnets rather than creating per-region VPCs.
5. **Use service accounts** (not user accounts) for all automated workloads.
6. **Enable Workload Identity** for GKE pods to access GCP services without key files.
7. **Use Private Google Access** so resources in private subnets can reach GCP APIs.
8. **BigQuery is serverless** — no infrastructure to manage; prefer it for analytics over self-managed alternatives.
9. **Enable Uniform Bucket-Level Access** on Cloud Storage to simplify permissions.
10. **Use Cloud Armor** in front of external load balancers to mitigate DDoS and apply WAF rules.
