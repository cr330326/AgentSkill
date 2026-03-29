---
name: cloud-infra
description: >
  Manage cloud infrastructure across AWS, GCP, and Azure. Compares provider services,
  generates Terraform configurations, and enforces cloud-native best practices.
  Use when the user asks to "set up infrastructure", "choose a cloud provider",
  "compare AWS vs GCP vs Azure", "write Terraform", "provision cloud resources",
  "cloud-native architecture", "deploy to the cloud", "IaC setup", or needs help
  selecting the right managed service for a workload. Also use when the user mentions
  specific services (e.g., "S3 vs GCS vs Blob Storage", "EKS vs GKE vs AKS") or asks
  about multi-cloud strategy, cost optimization, or infrastructure security hardening.
  Do NOT use for CI/CD pipeline setup (use a CI/CD skill), container orchestration
  details beyond provider-managed Kubernetes, or application-level code changes.
---

# Cloud Infrastructure Skill

Help users design, provision, and manage cloud infrastructure across AWS, GCP, and Azure
using Terraform and cloud-native best practices.

## Workflow

### Phase 1: Clarify Requirements

Before recommending anything, establish these facts:

1. **Workload type** -- web app, data pipeline, ML training, static site, API backend, event-driven
2. **Scale expectations** -- requests/sec, data volume, user count
3. **Constraints** -- existing provider commitment, compliance (HIPAA, SOC2, GDPR), team expertise, budget
4. **State** -- greenfield vs. migrating existing infrastructure

If the user hasn't specified these, ask. Do not guess at compliance requirements.

### Phase 2: Recommend Provider and Services

Use the service comparison table below to map the workload to concrete services.
When the user has no existing provider preference, recommend based on strengths:

| Strength area | Recommended provider | Reasoning |
|---------------|---------------------|-----------|
| Broadest service catalog | AWS | Most mature, largest ecosystem |
| Data/analytics/ML | GCP | BigQuery, Vertex AI, strong Kubernetes (GKE) |
| Enterprise/hybrid/Windows | Azure | Active Directory integration, Arc, strong .NET support |
| Cost-sensitive startups | GCP or AWS | GCP sustained-use discounts; AWS free tier breadth |

For multi-cloud scenarios, prefer provider-agnostic tooling (Terraform, Pulumi, Crossplane)
and call out the operational complexity cost honestly.

#### Core Service Comparison

| Capability | AWS | GCP | Azure |
|-----------|-----|-----|-------|
| Compute (VMs) | EC2 | Compute Engine | Virtual Machines |
| Containers (managed K8s) | EKS | GKE | AKS |
| Serverless functions | Lambda | Cloud Functions | Azure Functions |
| Serverless containers | Fargate / App Runner | Cloud Run | Container Apps |
| Object storage | S3 | Cloud Storage (GCS) | Blob Storage |
| Relational DB (managed) | RDS / Aurora | Cloud SQL / AlloyDB | Azure SQL / Flexible Server |
| NoSQL (document) | DynamoDB | Firestore | Cosmos DB |
| Message queue | SQS | Pub/Sub | Service Bus |
| CDN | CloudFront | Cloud CDN | Azure CDN / Front Door |
| DNS | Route 53 | Cloud DNS | Azure DNS |
| IAM | IAM | IAM | Entra ID (AAD) |
| IaC native | CloudFormation | Deployment Manager | Bicep / ARM |
| Monitoring | CloudWatch | Cloud Monitoring | Azure Monitor |

For detailed service catalogs, see the provider reference files:
- `references/aws.md` -- AWS services, naming conventions, Terraform provider details
- `references/gcp.md` -- GCP services, project structure, Terraform provider details
- `references/azure.md` -- Azure services, resource hierarchy, Terraform provider details

### Phase 3: Generate Terraform Configuration

Follow these rules when writing Terraform:

#### Project structure

```
infrastructure/
  modules/
    <resource>/
      main.tf
      variables.tf
      outputs.tf
  environments/
    dev/
      main.tf        # calls modules with dev values
      backend.tf     # remote state config
      terraform.tfvars
    staging/
      ...
    prod/
      ...
  versions.tf        # required_providers block
```

#### Terraform best practices

1. **Remote state** -- always configure a remote backend (S3+DynamoDB, GCS, Azure Storage).
   Never commit `terraform.tfstate` to version control.
2. **State locking** -- enable it. S3 uses DynamoDB; GCS and Azure Storage support it natively.
3. **Variables over hardcoding** -- every environment-specific value goes in `variables.tf`
   with a description and type constraint. Use `terraform.tfvars` per environment.
4. **Modules for reuse** -- extract repeated resource groups into modules. Keep modules
   focused on one concern (e.g., `modules/vpc`, `modules/database`).
5. **Least privilege IAM** -- generate IAM policies/roles with minimal permissions.
   Never use `*` in production resource ARNs or action lists.
6. **Tagging** -- require tags on every resource: `project`, `environment`, `owner`, `cost-center`.
   Use a `locals` block for common tags and merge them.
7. **Provider pinning** -- pin provider versions in `versions.tf` using `~>` for minor version flexibility.
8. **Plan before apply** -- always generate and review a plan. In CI, save the plan file and apply it exactly.
9. **Sensitive values** -- mark sensitive variables with `sensitive = true`. Store secrets in
   a vault (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault), not in tfvars.
10. **Formatting and validation** -- run `terraform fmt` and `terraform validate` before committing.

#### Provider configuration templates

**AWS:**
```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "env/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.common_tags
  }
}
```

**GCP:**
```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "my-terraform-state"
    prefix = "env"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
```

**Azure:**
```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "env.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}
```

### Phase 4: Apply Cloud-Native Best Practices

#### Security checklist

- [ ] Enable encryption at rest for all storage and databases
- [ ] Enable encryption in transit (TLS everywhere)
- [ ] Use managed identity / service accounts instead of long-lived keys
- [ ] Enable audit logging (CloudTrail, Cloud Audit Logs, Activity Log)
- [ ] Restrict network access with security groups / firewall rules
- [ ] Enable MFA on root/admin accounts
- [ ] Scan Terraform with `tfsec` or `checkov` before applying

#### Reliability checklist

- [ ] Deploy across multiple availability zones
- [ ] Configure health checks and auto-scaling
- [ ] Set up monitoring and alerting on key metrics
- [ ] Implement automated backups with tested restore procedures
- [ ] Define and enforce resource quotas

#### Cost optimization checklist

- [ ] Right-size instances based on actual utilization (start small)
- [ ] Use spot/preemptible instances for fault-tolerant workloads
- [ ] Enable auto-scaling to zero where possible (serverless, scale-to-zero containers)
- [ ] Set up billing alerts and budgets
- [ ] Review and delete unused resources monthly
- [ ] Use committed use discounts / savings plans for stable workloads

### Phase 5: Validate and Hand Off

Before presenting Terraform to the user:

1. Run `terraform fmt` mentally -- ensure consistent formatting
2. Verify all referenced variables are declared in `variables.tf`
3. Confirm the backend configuration matches the target provider
4. Check that IAM follows least privilege
5. Ensure tagging is applied to all taggable resources
6. Confirm sensitive values are not hardcoded

Present the output as:
- A summary of architectural decisions and why they were made
- The Terraform file tree with all files
- Next steps the user should take (init, plan, apply, CI integration)
