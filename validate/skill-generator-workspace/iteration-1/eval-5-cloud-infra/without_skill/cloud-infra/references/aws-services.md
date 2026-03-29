# AWS Services Reference

## Service Selection by Workload

### Compute

| Use Case | Service | When to Use |
|---|---|---|
| Containers (orchestrated) | **EKS** | Production microservices needing Kubernetes |
| Containers (simple) | **ECS on Fargate** | Containerized apps without managing servers |
| Serverless functions | **Lambda** | Event-driven, short-duration tasks (<15 min) |
| VMs | **EC2** | Full OS control, long-running processes, GPU workloads |
| Batch processing | **AWS Batch** | Large-scale parallel or sequential batch jobs |
| Edge compute | **Lambda@Edge / CloudFront Functions** | Low-latency compute at CDN edge |

### Storage

| Use Case | Service | When to Use |
|---|---|---|
| Object storage | **S3** | Files, backups, data lakes, static assets |
| Block storage | **EBS** | Persistent disks attached to EC2 |
| File storage (NFS) | **EFS** | Shared file systems across instances |
| Archive | **S3 Glacier** | Long-term archival with infrequent access |

### Databases

| Use Case | Service | When to Use |
|---|---|---|
| Relational (managed) | **RDS** (PostgreSQL, MySQL, etc.) | Standard OLTP workloads |
| Relational (serverless) | **Aurora Serverless v2** | Variable or unpredictable traffic |
| NoSQL (key-value) | **DynamoDB** | High-throughput, low-latency key-value or document |
| In-memory cache | **ElastiCache** (Redis/Memcached) | Session store, caching layer |
| Data warehouse | **Redshift** | Analytical queries over large datasets |
| Graph | **Neptune** | Highly connected data (social, fraud detection) |
| Time series | **Timestream** | IoT, metrics, time-series analytics |

### Networking

| Use Case | Service | When to Use |
|---|---|---|
| Virtual network | **VPC** | Isolated network for all resources |
| Load balancing | **ALB** (HTTP/S), **NLB** (TCP/UDP) | Distributing traffic to targets |
| DNS | **Route 53** | Domain registration and DNS routing |
| CDN | **CloudFront** | Global content delivery, caching |
| API gateway | **API Gateway** | REST/WebSocket/HTTP APIs in front of Lambda or services |
| Service mesh | **App Mesh** | Service-to-service communication control |
| VPN / private link | **Site-to-Site VPN**, **PrivateLink** | Secure connectivity to on-prem or between VPCs |

### Messaging & Events

| Use Case | Service | When to Use |
|---|---|---|
| Message queue | **SQS** | Decoupled async processing |
| Pub/sub | **SNS** | Fan-out notifications to multiple subscribers |
| Event bus | **EventBridge** | Event-driven architectures, cross-service events |
| Streaming | **Kinesis** | Real-time data streaming and analytics |

### Identity & Security

| Use Case | Service | When to Use |
|---|---|---|
| Identity / access | **IAM** | Users, roles, policies for all AWS access |
| Secrets | **Secrets Manager** | Database passwords, API keys, credentials |
| Parameters | **SSM Parameter Store** | Non-secret configuration values (free tier) |
| Certificate management | **ACM** | Free TLS/SSL certificates for AWS services |
| Web application firewall | **WAF** | Protect against common web exploits |
| DDoS protection | **Shield** | DDoS mitigation (Standard is free) |

### Observability

| Use Case | Service | When to Use |
|---|---|---|
| Metrics & alarms | **CloudWatch Metrics + Alarms** | Infrastructure and application metrics |
| Logs | **CloudWatch Logs** | Centralized log aggregation |
| Tracing | **X-Ray** | Distributed tracing across services |

### CI/CD & Developer Tools

| Use Case | Service | When to Use |
|---|---|---|
| Container registry | **ECR** | Private Docker image storage |
| CI/CD | **CodePipeline + CodeBuild** | AWS-native pipelines (or use GitHub Actions) |
| Infrastructure as Code | **CloudFormation** or **Terraform** | Terraform recommended for multi-cloud |

## AWS Naming Conventions

Follow a consistent naming pattern for all resources:

```
{project}-{environment}-{service}-{descriptor}
```

Examples:
- `myapp-prod-vpc-main`
- `myapp-dev-rds-postgres`
- `myapp-staging-lambda-process-orders`
- `myapp-prod-s3-assets`

## AWS Terraform Provider Configuration

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "env/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

## AWS Best Practices

1. **Use `default_tags`** on the AWS provider to apply tags to all resources automatically.
2. **Enable S3 bucket versioning** on state buckets for recovery.
3. **Use DynamoDB for state locking** to prevent concurrent modifications.
4. **Prefer Fargate** over self-managed EC2 for containers unless you need GPU or custom AMIs.
5. **Use IAM roles** (not access keys) for service-to-service authentication.
6. **Enable VPC Flow Logs** for network audit trails.
7. **Use private subnets** for databases and backend services; only place load balancers in public subnets.
8. **Set S3 buckets to private by default** — use CloudFront or pre-signed URLs for public access.
9. **Enable encryption** at rest for RDS, EBS, S3, and any service that supports it.
10. **Use multi-AZ deployments** for production databases and critical services.
