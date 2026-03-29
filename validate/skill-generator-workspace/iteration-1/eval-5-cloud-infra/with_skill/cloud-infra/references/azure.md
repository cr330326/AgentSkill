# Azure Reference

## Resource Hierarchy

```
Tenant (Entra ID / Azure AD)
  └── Management Group (optional, for governance)
      └── Subscription (billing + resource boundary)
          └── Resource Group (lifecycle + access boundary)
              └── Resources
```

- **Subscriptions** are the billing boundary. Use separate subscriptions for prod vs. non-prod.
- **Resource Groups** are logical containers. Group resources that share the same lifecycle.
- Delete a resource group to delete everything inside it -- plan group boundaries carefully.

## Naming Conventions

Use the Azure CAF (Cloud Adoption Framework) conventions:

Pattern: `{resource-type-prefix}-{project}-{environment}-{region}-{instance}`

Examples:
- `rg-myapp-prod-eastus` (resource group)
- `vnet-myapp-prod-eastus` (virtual network)
- `sql-myapp-prod-eastus-001` (SQL server)
- `st-myapp-prod-eastus` (storage account -- no hyphens allowed)

Common prefixes:
| Resource | Prefix |
|----------|--------|
| Resource group | `rg-` |
| Virtual network | `vnet-` |
| Subnet | `snet-` |
| Network security group | `nsg-` |
| Virtual machine | `vm-` |
| AKS cluster | `aks-` |
| App Service | `app-` |
| Function App | `func-` |
| Storage account | `st` (no hyphen, 3-24 lowercase alphanumeric) |
| Key Vault | `kv-` (3-24 alphanumeric + hyphens) |
| SQL Server | `sql-` |
| Cosmos DB | `cosmos-` |

## Terraform Provider: hashicorp/azurerm

Registry: https://registry.terraform.io/providers/hashicorp/azurerm/latest

### Authentication (in order of preference)

1. **Managed Identity** -- for Azure-hosted compute (VMs, AKS, App Service); no credentials needed
2. **OIDC federation (Federated Identity Credential)** -- for CI/CD (GitHub Actions, Azure DevOps)
3. **Azure CLI** -- for local development (`az login`)
4. **Service Principal with client secret** -- last resort; rotate secrets regularly

Never hardcode `client_secret` in Terraform files. Use environment variables or Key Vault.

### The features {} block

The `azurerm` provider requires a `features {}` block. Common settings:

```hcl
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true  # safety net for prod
    }
    key_vault {
      purge_soft_delete_on_destroy = false  # keep soft-deleted vaults recoverable
    }
  }
}
```

### Key Resources and Modules

| Category | Resource / Module | Notes |
|----------|------------------|-------|
| Networking | `azurerm_virtual_network`, `azurerm_subnet`, `azurerm_network_security_group` | Use NSGs on subnets, not NICs |
| Compute | `azurerm_linux_virtual_machine`, `azurerm_virtual_machine_scale_set` | Use VMSS for auto-scaling groups |
| Containers | `azurerm_kubernetes_cluster` | Enable workload identity; use system node pool + user pools |
| Serverless | `azurerm_function_app`, `azurerm_container_app` | Container Apps for microservices; Functions for event-driven |
| App hosting | `azurerm_linux_web_app`, `azurerm_service_plan` | App Service for traditional web apps |
| Storage | `azurerm_storage_account`, `azurerm_storage_container` | Enable blob versioning and soft delete |
| Database | `azurerm_mssql_server`, `azurerm_postgresql_flexible_server` | Flexible Server is the current-gen PaaS DB |
| NoSQL | `azurerm_cosmosdb_account` | Choose API: SQL (document), MongoDB, Cassandra, Gremlin, Table |
| Messaging | `azurerm_servicebus_namespace`, `azurerm_servicebus_queue` | Service Bus for enterprise; Event Hubs for streaming |
| CDN | `azurerm_cdn_frontdoor_profile` | Front Door for global load balancing + CDN + WAF |
| DNS | `azurerm_dns_zone`, `azurerm_dns_a_record` | Use Private DNS Zones for internal resolution |
| IAM | `azurerm_role_assignment`, `azurerm_user_assigned_identity` | Prefer user-assigned managed identity for explicit control |
| Monitoring | `azurerm_monitor_action_group`, `azurerm_monitor_metric_alert` | Enable diagnostic settings on all resources |
| Secrets | `azurerm_key_vault`, `azurerm_key_vault_secret` | Enable soft delete and purge protection in prod |

### Common Terraform Patterns

#### VNet with subnets and NSG

```hcl
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-${var.environment}-${var.location}"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${var.project}-${var.environment}-${var.location}"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
  service_endpoints    = ["Microsoft.Sql", "Microsoft.Storage"]
}

resource "azurerm_network_security_group" "app" {
  name                = "nsg-app-${var.project}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}
```

#### Storage account with best-practice defaults

```hcl
resource "azurerm_storage_account" "this" {
  name                          = "st${var.project}${var.environment}"  # no hyphens allowed
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  account_tier                  = "Standard"
  account_replication_type      = var.environment == "prod" ? "GRS" : "LRS"
  min_tls_version               = "TLS1_2"
  public_network_access_enabled = false

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
  }

  tags = local.common_tags
}
```

## Azure-Specific Best Practices

1. **Use Azure Landing Zones** as a starting architecture for enterprise deployments
2. **Enable Microsoft Defender for Cloud** for security posture management and threat protection
3. **Use Azure Policy** to enforce tagging, allowed regions, required encryption, and SKU restrictions
4. **Enable diagnostic settings** on every resource -- send logs to Log Analytics Workspace
5. **Use Private Endpoints** for PaaS services to keep traffic on the Azure backbone
6. **Leverage reserved instances** for VMs and Azure SQL (1yr/3yr, up to 72% savings)
7. **Use Azure Cost Management** + budgets with action groups for cost alerts
8. **Adopt the Azure CAF naming convention** consistently across all resources
9. **Enable soft delete** on Key Vaults and Storage accounts in production
10. **Use Availability Zones** (not just availability sets) for production VMs and managed services
