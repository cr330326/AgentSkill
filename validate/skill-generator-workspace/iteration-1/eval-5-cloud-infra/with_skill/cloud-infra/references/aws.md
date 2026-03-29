# AWS Reference

## Resource Naming Conventions

Use this pattern: `{project}-{environment}-{service}-{qualifier}`

Examples:
- `myapp-prod-vpc-main`
- `myapp-dev-rds-primary`
- `myapp-staging-lambda-api-handler`

Constraints:
- S3 buckets: globally unique, lowercase, hyphens only, 3-63 chars
- IAM roles: alphanumeric + `+=,.@_-`, up to 64 chars
- EC2 tags: up to 256 chars per key/value

## Terraform Provider: hashicorp/aws

Registry: https://registry.terraform.io/providers/hashicorp/aws/latest

### Authentication (in order of preference)

1. **IAM role via instance profile** -- for EC2, ECS, Lambda (no credentials in config)
2. **OIDC federation** -- for CI/CD (GitHub Actions, GitLab CI)
3. **SSO / AWS CLI profiles** -- for local development (`profile = "my-profile"`)
4. **Environment variables** -- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (last resort)

Never hardcode credentials in Terraform files.

### Key Resources and Modules

| Category | Resource / Module | Notes |
|----------|------------------|-------|
| Networking | `aws_vpc`, `aws_subnet`, `aws_internet_gateway`, `aws_nat_gateway` | Always create a custom VPC; never use default |
| Compute | `aws_instance`, `aws_launch_template`, `aws_autoscaling_group` | Use launch templates over launch configs |
| Containers | `aws_ecs_cluster`, `aws_ecs_service`, `aws_ecs_task_definition` | Fargate for serverless; EC2 for GPU/cost |
| Kubernetes | `aws_eks_cluster`, `aws_eks_node_group` | Use managed node groups; consider Fargate profiles |
| Serverless | `aws_lambda_function`, `aws_api_gateway_rest_api`, `aws_apigatewayv2_api` | API Gateway v2 (HTTP API) is cheaper and faster |
| Storage | `aws_s3_bucket`, `aws_s3_bucket_versioning`, `aws_s3_bucket_server_side_encryption_configuration` | Always enable versioning and encryption |
| Database | `aws_db_instance`, `aws_rds_cluster` (Aurora) | Aurora for production; RDS for dev/test |
| NoSQL | `aws_dynamodb_table` | Set billing_mode to PAY_PER_REQUEST unless predictable |
| IAM | `aws_iam_role`, `aws_iam_policy`, `aws_iam_role_policy_attachment` | One role per service; avoid inline policies |
| DNS | `aws_route53_zone`, `aws_route53_record` | Use alias records for AWS resources |
| CDN | `aws_cloudfront_distribution` | Origin access identity for S3 origins |
| Monitoring | `aws_cloudwatch_log_group`, `aws_cloudwatch_metric_alarm` | Set retention on log groups to control cost |
| Secrets | `aws_secretsmanager_secret`, `aws_ssm_parameter` | Secrets Manager for rotation; SSM for config |

### Common Terraform Patterns

#### VPC with public and private subnets

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project}-${var.environment}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true

  tags = local.common_tags
}
```

#### S3 bucket with best-practice defaults

```hcl
resource "aws_s3_bucket" "this" {
  bucket = "${var.project}-${var.environment}-${var.bucket_purpose}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

## AWS-Specific Best Practices

1. **Use AWS Organizations** for multi-account strategy (separate prod, dev, security, logging accounts)
2. **Enable AWS Config** rules to detect configuration drift and compliance violations
3. **Enable GuardDuty** for threat detection across all accounts
4. **Use VPC endpoints** for S3 and DynamoDB to avoid NAT gateway costs and improve security
5. **Set S3 lifecycle rules** to transition objects to cheaper storage classes
6. **Use reserved capacity or Savings Plans** for predictable workloads (up to 72% savings)
7. **Enable Cost Explorer** and set up AWS Budgets with alerts
