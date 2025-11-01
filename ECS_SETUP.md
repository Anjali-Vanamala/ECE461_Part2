# ECS/Fargate Deployment Setup Guide (MVP)

This document outlines the minimal AWS infrastructure setup required for MVP deployment to ECS/Fargate.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI configured
3. GitHub OIDC provider configured in AWS IAM

## MVP Required AWS Resources (One-Time Setup)

These resources must be created manually before the CD pipeline can deploy.

### 1. ECR Repository

```bash
aws ecr create-repository \
  --repository-name ece461-part2 \
  --region us-east-1
```

### 2. ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name ece461-part2-cluster \
  --region us-east-1
```

### 3. CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/ece461-part2-task \
  --region us-east-1
```

### 4. ECS Task Definition (Required for MVP)

1. Replace placeholders in `task-definition-mvp.json`:
   - `<ACCOUNT_ID>`: Your AWS account ID
   - `<ECR_REGISTRY>`: Your ECR registry (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com`)

2. Register the task definition:
```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition-mvp.json \
  --region us-east-1
```

**MVP Configuration**:
- **CPU**: 512 (0.5 vCPU) - minimum for Fargate
- **Memory**: 1024 MB (1 GB) - minimum for Fargate
- **Launch Type**: FARGATE
- **Network Mode**: awsvpc
- **Port**: 8000

### 5. VPC and Networking

You'll need:
- **VPC** with public/private subnets
- **Security Group** allowing inbound traffic on port 8000
- **Internet Gateway** (for public subnets)
- **NAT Gateway** (if using private subnets)

#### Security Group Configuration

```bash
# Create security group for ECS tasks
aws ec2 create-security-group \
  --group-name ece461-part2-ecs-sg \
  --description "Security group for ECS tasks" \
  --vpc-id <VPC_ID>

# Allow inbound HTTP traffic on port 8000
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0
```

### 6. Application Load Balancer (ALB) - Optional for MVP

**For MVP**: ALB is not required if you can access the service directly via public IP.
**For production**: ALB recommended for better reliability and SSL termination.

To set up ALB (optional):

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name ece461-part2-alb \
  --subnets <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-groups <ALB_SECURITY_GROUP_ID> \
  --region us-east-1

# Create target group
aws elbv2 create-target-group \
  --name ece461-part2-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <VPC_ID> \
  --target-type ip \
  --health-check-path /health \
  --region us-east-1

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn <ALB_ARN> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN> \
  --region us-east-1
```

### 7. ECS Service (Required for MVP)

```bash
aws ecs create-service \
  --cluster ece461-part2-cluster \
  --service-name ece461-part2-service \
  --task-definition ece461-part2-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_ID_1>,<SUBNET_ID_2>],securityGroups=[<SECURITY_GROUP_ID>],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=<TARGET_GROUP_ARN>,containerName=fastapi-app,containerPort=8000 \
  --region us-east-1
```

**MVP Option (No ALB)**: Remove `--load-balancers` flag to deploy without ALB. Service will have a public IP that you can access directly.

### 8. IAM Role for GitHub Actions

The GitHub Actions role needs these additional permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ecs-tasks.amazonaws.com"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:<ACCOUNT_ID>:log-group:/ecs/*"
    }
  ]
}
```

### 9. ECS Task Execution Role

Required for ECS tasks to pull images and write logs:

```bash
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

# Attach AWS managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

## MVP Cost Tips

1. **Scale to Zero**: Set `desired-count` to 0 when not testing (minimizes cost)
2. **Minimum Resources**: Using 512 CPU / 1024 MB (minimum Fargate) keeps costs low
3. **Clean Up**: Delete service/cluster when done testing to avoid charges

**Note**: For MVP, you don't need auto-scaling or advanced monitoring.

## Monitoring

- CloudWatch Logs: `/ecs/ece461-part2-task`
- ECS Service Metrics: Available in CloudWatch automatically
- Health Checks: Configured via ALB or ECS service health checks

## Troubleshooting

1. **Tasks not starting**: Check CloudWatch Logs, IAM roles, security groups
2. **Cannot reach service**: Verify security groups and ALB/listener configuration
3. **Image pull errors**: Verify ECR permissions and image URI
4. **Task definition errors**: Check JSON syntax and required fields

## Next Steps

1. Create the ECS cluster
2. Set up VPC/networking (or use existing)
3. Create CloudWatch log group
4. Create/configure IAM roles
5. Create ECS service (or let CD pipeline create on first deploy)
6. Optionally set up ALB for production

