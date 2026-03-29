# Azure Services Reference

## Service Selection by Workload

### Compute

| Use Case | Service | When to Use |
|---|---|---|
| Containers (orchestrated) | **AKS** | Production Kubernetes workloads |
| Containers (simple) | **Container Apps** | Serverless containers with auto-scaling, Dapr support |
| Containers (single) | **Container Instances (ACI)** | Quick single-container runs, sidecar tasks |
| Serverless functions | **Azure Functions** | Event-driven, short-duration tasks |
| VMs | **Virtual Machines** | Full OS control, legacy apps, GPU/HPC |
| Batch processing | **Azure Batch** | Large-scale parallel compute jobs |
| App hosting | **App Service** | Managed PaaS for web apps and APIs |

### Storage

| Use Case | Service | When to Use |
|---|---|---|
| Object storage | **Blob Storage** | Files, backups, data lakes, static assets |
| Block storage | **Managed Disks** | Persistent disks attached to VMs |
| File storage (SMB/NFS) | **Azure Files** | Managed file shares (SMB and NFS) |
| Archive | **Blob Storage (Archive tier)** | Long-term archival with infrequent access |
| Data Lake | **Azure Data Lake Storage Gen2** | Big data analytics with hierarchical namespace |

### Databases

| Use Case | Service | When to Use |
|---|---|---|
| Relational (managed) | **Azure Database for PostgreSQL/MySQL** | Standard OLTP workloads |
| Relational (enterprise) | **Azure SQL Database** | SQL Server-compatible, auto-tuning, hyperscale |
| NoSQL (document) | **Cosmos DB** | Globally distributed, multi-model (document, key-value, graph, column-family) |
| In-memory cache | **Azure Cache for Redis** | Caching, session store |
| Data warehouse | **Synapse Analytics** | Enterprise analytics and data warehousing |
| Graph | **Cosmos DB (Gremlin API)** | Graph queries on globally distributed data |
| Time series | **Azure Data Explorer** | Log and telemetry analytics, time-series |

### Networking

| Use Case | Service | When to Use |
|---|---|---|
| Virtual network | **VNet** | Isolated network for resources in a region |
| Load balancing (L7) | **Application Gateway** | HTTP/S load balancing with WAF |
| Load balancing (L4) | **Azure Load Balancer** | TCP/UDP load balancing |
| Global load balancing | **Front Door** | Global HTTP load balancing + CDN + WAF |
| DNS | **Azure DNS** | Managed DNS hosting |
| CDN | **Azure CDN** or **Front Door** | Global content delivery |
| API gateway | **API Management (APIM)** | Full-featured API gateway and developer portal |
| VPN / private link | **VPN Gateway**, **Private Link** | Hybrid connectivity, private endpoints |

### Messaging & Events

| Use Case | Service | When to Use |
|---|---|---|
| Message queue | **Service Bus Queue** | Enterprise messaging with transactions, ordering |
| Pub/sub | **Service Bus Topics** | Publish-subscribe with filtering |
| Event streaming | **Event Hubs** | High-throughput event ingestion (Kafka-compatible) |
| Event routing | **Event Grid** | Reactive event-driven architectures |
| Lightweight queue | **Storage Queue** | Simple, high-volume queue (less features than Service Bus) |

### Identity & Security

| Use Case | Service | When to Use |
|---|---|---|
| Identity / access | **Entra ID (Azure AD)** + **RBAC** | Users, groups, service principals, managed identities |
| Secrets | **Key Vault** | Secrets, keys, and certificates |
| Managed identity | **Managed Identity** | Passwordless auth for Azure resources |
| Web application firewall | **WAF** (on App Gateway or Front Door) | Protect against web exploits |
| DDoS protection | **DDoS Protection** | Network-level DDoS mitigation |

### Observability

| Use Case | Service | When to Use |
|---|---|---|
| Metrics & monitoring | **Azure Monitor** | Infrastructure and application metrics, alerting |
| Logs | **Log Analytics (Azure Monitor Logs)** | Centralized log aggregation with KQL |
| Tracing | **Application Insights** | APM, distributed tracing, live metrics |

### CI/CD & Developer Tools

| Use Case | Service | When to Use |
|---|---|---|
| Container registry | **Azure Container Registry (ACR)** | Private Docker image storage |
| CI/CD | **Azure DevOps Pipelines** or **GitHub Actions** | Build and deploy pipelines |
| Infrastructure as Code | **Bicep / ARM Templates** or **Terraform** | Terraform recommended for multi-cloud |

## Azure Naming Conventions

Azure resources have varied naming constraints. Follow the Cloud Adoption Framework convention:

```
{resource-type-prefix}-{project}-{environment}-{region}-{instance}
```

Common prefixes (from Azure CAF):
- `rg-` — Resource Group
- `vnet-` — Virtual Network
- `snet-` — Subnet
- `aks-` — AKS Cluster
- `func-` — Function App
- `st` — Storage Account (no hyphens, 3-24 chars, lowercase+numbers only)
- `kv-` — Key Vault
- `sql-` — Azure SQL
- `appi-` — Application Insights
- `log-` — Log Analytics Workspace

Examples:
- `rg-myapp-prod-eastus`
- `vnet-myapp-prod-eastus`
- `aks-myapp-prod-eastus-001`
- `stmyappprodeastus` (storage accounts can't have hyphens)

## Azure Terraform Provider Configuration

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "env/prod/terraform.tfstate"
  }
}

provider "azurerm" {
  features {}

  subscription_id = var.azure_subscription_id
}
```

Note: The `azurerm` provider does not support `default_tags`. Apply tags using a local variable and spread them on each resource:

```hcl
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}-${var.azure_region}"
  location = var.azure_region
  tags     = local.common_tags
}
```

## Azure Best Practices

1. **Use Resource Groups** to organize related resources by application and environment.
2. **Prefer Managed Identity** over service principals with secrets for Azure-to-Azure authentication.
3. **Use Container Apps** for serverless containers — simpler than AKS for most microservice workloads.
4. **Store all secrets in Key Vault** — never in app configuration or environment variables directly.
5. **Use Private Endpoints** to keep traffic to PaaS services within the VNet.
6. **Enable diagnostic settings** on all resources to send logs and metrics to Log Analytics.
7. **Use Azure Front Door** for global applications requiring low-latency, WAF, and automatic failover.
8. **Follow the Cloud Adoption Framework (CAF)** naming conventions for consistency.
9. **Use availability zones** for production workloads to protect against datacenter failures.
10. **Tag all resources** — Azure Policy can enforce tagging requirements across subscriptions.
