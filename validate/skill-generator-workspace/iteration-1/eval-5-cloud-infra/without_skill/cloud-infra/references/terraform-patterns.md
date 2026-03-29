# Terraform Patterns & Best Practices

## Project Structure

### Single-Cloud Project

```
infra/
  main.tf                  # Root module — resource composition
  variables.tf             # Input variable declarations
  outputs.tf               # Output value declarations
  providers.tf             # Provider and backend configuration
  versions.tf              # Terraform and provider version constraints
  terraform.tfvars.example # Example variable values (never commit real .tfvars)
  modules/
    networking/
      main.tf
      variables.tf
      outputs.tf
    compute/
      main.tf
      variables.tf
      outputs.tf
    database/
      main.tf
      variables.tf
      outputs.tf
```

### Multi-Environment Structure

Use directory-based separation for environments (preferred over workspaces for most teams):

```
infra/
  modules/                 # Shared modules
    networking/
    compute/
    database/
  environments/
    dev/
      main.tf
      variables.tf
      outputs.tf
      providers.tf
      terraform.tfvars
    staging/
      main.tf
      variables.tf
      outputs.tf
      providers.tf
      terraform.tfvars
    prod/
      main.tf
      variables.tf
      outputs.tf
      providers.tf
      terraform.tfvars
```

### Multi-Cloud Project

```
infra/
  modules/
    aws/
      networking/
      compute/
    gcp/
      networking/
      compute/
    azure/
      networking/
      compute/
  environments/
    aws-prod/
    gcp-prod/
    azure-prod/
```

## Module Design

### Module Interface Pattern

Every module should follow this structure:

```hcl
# modules/example/variables.tf
variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
```

```hcl
# modules/example/outputs.tf
output "id" {
  description = "The ID of the created resource"
  value       = aws_example.this.id
}

output "arn" {
  description = "The ARN of the created resource"
  value       = aws_example.this.arn
}
```

### Module Composition in Root

```hcl
# main.tf
module "networking" {
  source = "./modules/networking"

  project_name = var.project_name
  environment  = var.environment
  cidr_block   = var.vpc_cidr
  tags         = local.common_tags
}

module "compute" {
  source = "./modules/compute"

  project_name = var.project_name
  environment  = var.environment
  subnet_ids   = module.networking.private_subnet_ids
  tags         = local.common_tags
}

module "database" {
  source = "./modules/database"

  project_name = var.project_name
  environment  = var.environment
  subnet_ids   = module.networking.database_subnet_ids
  vpc_id       = module.networking.vpc_id
  tags         = local.common_tags
}
```

## State Management

### Remote State Configuration

Always use remote state with locking for team environments.

**AWS (S3 + DynamoDB):**
```hcl
backend "s3" {
  bucket         = "myproject-terraform-state"
  key            = "env/prod/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "terraform-locks"
  encrypt        = true
}
```

**GCP (GCS):**
```hcl
backend "gcs" {
  bucket = "myproject-terraform-state"
  prefix = "env/prod"
}
```

**Azure (Blob Storage):**
```hcl
backend "azurerm" {
  resource_group_name  = "rg-terraform-state"
  storage_account_name = "stterraformstate"
  container_name       = "tfstate"
  key                  = "env/prod/terraform.tfstate"
}
```

### State Separation Rules

1. **One state file per environment** — never share state between dev and prod
2. **One state file per application/service** — large monolithic states are fragile and slow
3. **Use data sources** to reference resources across state boundaries:

```hcl
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket = "myproject-terraform-state"
    key    = "env/prod/networking.tfstate"
    region = "us-east-1"
  }
}

# Reference: data.terraform_remote_state.networking.outputs.vpc_id
```

## Version Constraints

### Terraform Version

```hcl
terraform {
  required_version = ">= 1.5.0"
}
```

### Provider Versions

Pin to minor version to allow patch updates:

```hcl
required_providers {
  aws = {
    source  = "hashicorp/aws"
    version = "~> 5.0"
  }
  google = {
    source  = "hashicorp/google"
    version = "~> 5.0"
  }
  azurerm = {
    source  = "hashicorp/azurerm"
    version = "~> 4.0"
  }
}
```

## Common Patterns

### Conditional Resource Creation

```hcl
variable "enable_monitoring" {
  description = "Whether to create monitoring resources"
  type        = bool
  default     = true
}

resource "aws_cloudwatch_metric_alarm" "cpu" {
  count = var.enable_monitoring ? 1 : 0
  # ...
}
```

### Dynamic Blocks

```hcl
variable "ingress_rules" {
  description = "List of ingress rules"
  type = list(object({
    port        = number
    protocol    = string
    cidr_blocks = list(string)
  }))
}

resource "aws_security_group" "this" {
  name   = "${var.project_name}-sg"
  vpc_id = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
    }
  }
}
```

### For-Each over Maps

```hcl
variable "subnets" {
  description = "Map of subnet configurations"
  type = map(object({
    cidr_block        = string
    availability_zone = string
  }))
}

resource "aws_subnet" "this" {
  for_each = var.subnets

  vpc_id            = var.vpc_id
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.availability_zone

  tags = merge(var.tags, {
    Name = "${var.project_name}-${each.key}"
  })
}
```

### Locals for Computed Values

```hcl
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  name_prefix = "${var.project_name}-${var.environment}"

  is_production = var.environment == "prod"

  instance_type = local.is_production ? "m5.xlarge" : "t3.medium"
}
```

## Security Patterns

### Sensitive Variables

```hcl
variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}
```

### No Hardcoded Secrets

Never do this:
```hcl
# BAD - never hardcode secrets
password = "my-secret-password"
```

Instead:
```hcl
# GOOD - reference from secret manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "myapp/db-password"
}

password = data.aws_secretsmanager_secret_version.db_password.secret_string
```

### Restrict Provider Permissions

Use `allowed_account_ids` (AWS) or equivalent to prevent accidental deployment to wrong accounts:

```hcl
provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
}
```

## Lifecycle Rules

### Prevent Accidental Destruction

```hcl
resource "aws_db_instance" "main" {
  # ... configuration ...

  lifecycle {
    prevent_destroy = true
  }
}
```

### Ignore External Changes

```hcl
resource "aws_ecs_service" "main" {
  # ... configuration ...

  lifecycle {
    ignore_changes = [desired_count]  # Managed by auto-scaling
  }
}
```

## CI/CD Integration

### Recommended Pipeline Steps

1. `terraform fmt -check` — Verify formatting
2. `terraform init` — Initialize providers and modules
3. `terraform validate` — Syntax and configuration validation
4. `terraform plan -out=tfplan` — Generate and save execution plan
5. Manual approval (for staging/prod)
6. `terraform apply tfplan` — Apply the saved plan

### Plan File Best Practices

- Always use `-out=tfplan` to save the plan
- Apply the exact plan that was reviewed — never run `apply` without a saved plan in CI
- Store the plan artifact for audit trails

## Anti-Patterns to Avoid

1. **Monolithic state** — Don't put all infrastructure in one state file
2. **Hardcoded values** — Use variables for anything that differs between environments
3. **No backend** — Always use remote state; local state files are for learning only
4. **Unpinned versions** — Always constrain provider and Terraform versions
5. **Manual changes** — Never modify infrastructure manually after Terraform manages it; use `terraform import` if needed
6. **Secrets in state** — Mark sensitive variables as `sensitive = true` and use encryption on state backends
7. **Count for named resources** — Prefer `for_each` with maps over `count` for resources that have logical names
8. **Nested modules too deep** — Keep module nesting to 2 levels maximum for readability
