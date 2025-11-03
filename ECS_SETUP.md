# ECS/Fargate Deployment Setup Guide (MVP)

**Last Updated:** November 2, 2025

This document outlines the minimal AWS infrastructure setup required for MVP deployment to ECS/Fargate.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI configured
3. GitHub OIDC provider configured in AWS IAM
4. GitHub Actions workflow configured (see `.github/workflows/cd.yml`)
   - Requires secret: `AWS_IAM_ROLE_ARN` (the ARN of the IAM role created in Section 8)

## MVP Required AWS Resources (One-Time Setup)

These resources must be created manually before the CD pipeline can deploy.

### 1. ECR Repository

```bash
aws ecr create-repository \
  --repository-name ece461-backend \
  --region us-east-2
```

### 2. ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name ece461-backend-cluster \
  --region us-east-2
```

### 3. CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/ece461-backend-task \
  --region us-east-2
```

### 4. ECS Task Definition (Required for MVP)

1. Replace placeholders in `task-definition-mvp.json`:
   - `<ACCOUNT_ID>`: Your AWS account ID
   - `<ECR_REGISTRY>`: Your ECR registry (e.g., `123456789012.dkr.ecr.us-east-2.amazonaws.com`)

2. Register the task definition:
```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition-mvp.json \
  --region us-east-2
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

**Note**: For MVP, you can use the default VPC. To find your default VPC and subnets:
```bash
# Get default VPC ID
aws ec2 describe-vpcs --region us-east-2 --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text

# Get subnets in your VPC (replace <VPC_ID> with your VPC ID)
aws ec2 describe-subnets --region us-east-2 --filters "Name=vpc-id,Values=<VPC_ID>" --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output table
```

#### Security Group Configuration

```bash
# Create security group for ECS tasks
aws ec2 create-security-group \
  --group-name ece461-backend-ecs-sg \
  --description "Security group for ECS tasks" \
  --vpc-id <VPC_ID> \
  --region us-east-2

# Allow inbound HTTP traffic on port 8000
# Replace <SECURITY_GROUP_ID> with the GroupId from the command above
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --region us-east-2
```

**Subnet IDs**: Use your actual subnet IDs from the command above (you'll need at least 2 subnets in different availability zones).

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
  --region us-east-2

# Create target group
aws elbv2 create-target-group \
  --name ece461-part2-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <VPC_ID> \
  --target-type ip \
  --health-check-path /health \
  --region us-east-2

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn <ALB_ARN> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN> \
  --region us-east-2
```

### 7. ECS Service (Required for MVP)

**Important**: This service must be created before the CD pipeline can update it.

**Replace placeholders**:
- `<SUBNET_ID_1>`: First subnet ID from your VPC
- `<SUBNET_ID_2>`: Second subnet ID from your VPC (should be in a different availability zone)
- `<SECURITY_GROUP_ID>`: Security group ID from Step 5

```bash
aws ecs create-service \
  --cluster ece461-backend-cluster \
  --service-name ece461-backend-service \
  --task-definition ece461-backend-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_ID_1>,<SUBNET_ID_2>],securityGroups=[<SECURITY_GROUP_ID>],assignPublicIp=ENABLED}" \
  --region us-east-2
```

**MVP Option (No ALB)**: If not using an ALB, remove the `--load-balancers` flag. The service will have a public IP that you can access directly. The CD pipeline will work with either configuration.

### 8. IAM Role for GitHub Actions

This role is used by the CD pipeline (`.github/workflows/cd.yml`) to:
- Push Docker images to ECR
- Update ECS task definitions and services
- Write logs to CloudWatch

**Step 1**: Check if GitHub OIDC provider exists:
```bash
aws iam list-open-id-connect-providers
```

**Step 2**: Create GitHub OIDC provider (if it doesn't exist):
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**Step 3**: Create the trust policy file (replace placeholders):
- `<YOUR_GITHUB_USERNAME>`: Your GitHub username
- `<YOUR_REPO_NAME>`: Your repository name (e.g., `ECE461_Part2`)
- `<ACCOUNT_ID>`: Your AWS account ID

```bash
cat > github-actions-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>:*"
        }
      }
    }
  ]
}
EOF
```

**Step 4**: Create the permission policy file (replace `<ACCOUNT_ID>`):
```bash
cat > github-actions-permissions.json << 'EOF'
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
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
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
      "Resource": "arn:aws:logs:us-east-2:<ACCOUNT_ID>:log-group:/ecs/*"
    }
  ]
}
EOF
```

**Step 5**: Create the IAM role:
```bash
aws iam create-role \
  --role-name github-actions-deploy-role \
  --assume-role-policy-document file://github-actions-trust-policy.json \
  --description "IAM role for GitHub Actions to deploy to ECS"
```

**Step 6**: Attach the permission policy:
```bash
aws iam put-role-policy \
  --role-name github-actions-deploy-role \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-permissions.json
```

**Step 7**: Get the role ARN (save this for GitHub secret):
```bash
aws iam get-role \
  --role-name github-actions-deploy-role \
  --query 'Role.Arn' \
  --output text
```

**Step 8**: Add the role ARN as a GitHub secret:
1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `AWS_IAM_ROLE_ARN`
4. Value: Paste the ARN from Step 7 (e.g., `arn:aws:iam::<ACCOUNT_ID>:role/github-actions-deploy-role`)

### 9. ECS Task Execution Role

Required for ECS tasks to pull images from ECR and write logs to CloudWatch.

**Step 1**: Create the trust policy file:
```bash
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

**Step 2**: Create the role:
```bash
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json
```

**Step 3**: Attach the AWS managed policy:
```bash
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

**Step 4**: Verify the role was created:
```bash
aws iam get-role \
  --role-name ecsTaskExecutionRole \
  --query 'Role.[RoleName,Arn]' \
  --output table
```

The role ARN should match what's in your task definition: `arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole`

## MVP Cost Tips

1. **Scale to Zero**: Set `desired-count` to 0 when not testing (minimizes cost)
2. **Minimum Resources**: Using 512 CPU / 1024 MB (minimum Fargate) keeps costs low
3. **Clean Up**: Delete service/cluster when done testing to avoid charges
4. **Delete Old ECR Images**: Clean up test images to avoid storage costs

**Note**: For MVP, you don't need auto-scaling or advanced monitoring.

## Cleaning Up ECR Images

To delete Docker images from ECR (useful when testing):

**List images in repository:**
```bash
aws ecr list-images \
  --repository-name ece461-backend \
  --region us-east-2 \
  --output table
```

**Delete a specific image by tag:**
```bash
aws ecr batch-delete-image \
  --repository-name ece461-backend \
  --image-ids imageTag=<TAG_NAME> \
  --region us-east-2
```

**Delete all untagged images (dangling images):**
```bash
aws ecr list-images \
  --repository-name ece461-backend \
  --region us-east-2 \
  --filter "tagStatus=UNTAGGED" \
  --query 'imageIds[*]' \
  --output json | \
aws ecr batch-delete-image \
  --repository-name ece461-backend \
  --region us-east-2 \
  --image-ids file:///dev/stdin
```

**Delete all images (⚠️ use with caution):**
```bash
aws ecr list-images \
  --repository-name ece461-backend \
  --region us-east-2 \
  --query 'imageIds[*]' \
  --output json | \
aws ecr batch-delete-image \
  --repository-name ece461-backend \
  --region us-east-2 \
  --image-ids file:///dev/stdin
```

**Note**: You can't delete images that are currently being used by running ECS tasks. Stop or scale down the service first.

## Monitoring

- CloudWatch Logs: `/ecs/ece461-backend-task`
- ECS Service Metrics: Available in CloudWatch automatically
- Health Checks: Configured via ALB or ECS service health checks

## Pre-Deployment Verification

Before testing your CD pipeline, run this comprehensive verification to ensure everything is configured correctly:

### Quick Verification Script

Upload `verify-aws-setup.sh` to CloudShell and run:
```bash
chmod +x verify-aws-setup.sh
./verify-aws-setup.sh
```

### Manual Verification Checklist

**1. ECR Repository:**
```bash
aws ecr describe-repositories --repository-names ece461-backend --region us-east-2 --query 'repositories[0].repositoryUri' --output text
```
**Expected**: Should return the repository URI

**2. ECS Cluster:**
```bash
aws ecs describe-clusters --clusters ece461-backend-cluster --region us-east-2 --query 'clusters[0].status' --output text
```
**Expected**: `ACTIVE`

**3. CloudWatch Log Group:**
```bash
aws logs describe-log-groups --log-group-name-prefix "/ecs/ece461-backend-task" --region us-east-2 --query 'logGroups[0].logGroupName' --output text
```
**Expected**: `/ecs/ece461-backend-task`

**4. Task Definition:**
```bash
aws ecs describe-task-definition --task-definition ece461-backend-task --region us-east-2 --query 'taskDefinition.[family,status,revision]' --output table
```
**Expected**: Should show `ece461-backend-task`, `ACTIVE`, and revision number

**5. ECS Service:**
```bash
aws ecs describe-services --cluster ece461-backend-cluster --services ece461-backend-service --region us-east-2 --query 'services[0].[serviceName,status,desiredCount,runningCount]' --output table
```
**Expected**: `ACTIVE`, desiredCount=1, runningCount=0 (until image exists)

**6. Security Group:**
```bash
aws ec2 describe-security-groups --filters "Name=group-name,Values=ece461-backend-ecs-sg" --region us-east-2 --query 'SecurityGroups[0].GroupId' --output text
```
**Expected**: Should return security group ID

**7. ECS Task Execution Role:**
```bash
aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text
```
**Expected**: Should return role ARN

**8. GitHub Actions Role:**
```bash
aws iam get-role --role-name github-actions-deploy-role --query 'Role.Arn' --output text
```
**Expected**: Should return role ARN (this is what goes in GitHub secret)

**9. OIDC Provider:**
```bash
aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[*]' --output table
```
**Expected**: Should show GitHub OIDC provider

**10. Verify GitHub Secret is Set:**
- Go to: `https://github.com/<YOUR_USERNAME>/<YOUR_REPO>/settings/secrets/actions`
- Verify `AWS_IAM_ROLE_ARN` secret exists

## Troubleshooting

1. **Tasks not starting**: Check CloudWatch Logs, IAM roles, security groups
2. **Cannot reach service**: Verify security groups and ALB/listener configuration
3. **Image pull errors**: Verify ECR permissions and image URI
4. **Task definition errors**: Check JSON syntax and required fields
5. **CD Pipeline fails**: Verify GitHub secret is set and IAM role has correct permissions

## Next Steps

1. Create the ECS cluster
2. Set up VPC/networking (or use existing)
3. Create CloudWatch log group
4. Create/configure IAM roles
5. Create ECS service (or let CD pipeline create on first deploy)
6. Optionally set up ALB for production

