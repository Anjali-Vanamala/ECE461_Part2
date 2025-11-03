# ECS/Fargate Deployment Setup Guide - Frontend (MVP)

**Last Updated:** November 3, 2025

This document outlines the minimal AWS infrastructure setup required for MVP frontend deployment to ECS/Fargate.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI configured
3. GitHub OIDC provider configured in AWS IAM (can reuse the same provider from backend setup)
4. GitHub Actions workflow configured (see `.github/workflows/cd.yml`)
   - Requires secret: `AWS_IAM_ROLE_ARN` (can reuse the same role as backend, or create a separate one)
5. **Frontend folder** created in repository root (e.g., `frontend/` with `package.json`)

## MVP Required AWS Resources (One-Time Setup)

These resources must be created manually before the CD pipeline can deploy the frontend.

### 1. ECR Repository (Frontend)

```bash
aws ecr create-repository \
  --repository-name ece461-frontend \
  --region us-east-2
```

### 2. ECS Cluster (Can Reuse Backend Cluster)

**Option A: Reuse existing cluster** (recommended for MVP):
```bash
# Just verify it exists
aws ecs describe-clusters \
  --clusters ece461-backend-cluster \
  --region us-east-2
```

**Option B: Create separate cluster**:
```bash
aws ecs create-cluster \
  --cluster-name ece461-frontend-cluster \
  --region us-east-2
```

**Recommendation**: Use the same cluster (`ece461-backend-cluster`) for MVP to minimize costs.

### 3. CloudWatch Log Group (Frontend)

```bash
aws logs create-log-group \
  --log-group-name /ecs/ece461-frontend-task \
  --region us-east-2
```

### 4. ECS Task Definition (Required for MVP)

1. Create `task-definition-frontend.json` with the following content (replace placeholders):
   - `<ACCOUNT_ID>`: Your AWS account ID
   - `<ECR_REGISTRY>`: Your ECR registry (e.g., `123456789012.dkr.ecr.us-east-2.amazonaws.com`)

```json
{
  "family": "ece461-frontend-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "frontend-app",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/ece461-frontend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ece461-frontend-task",
          "awslogs-region": "us-east-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

2. Register the task definition:
```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition-frontend.json \
  --region us-east-2
```

**MVP Configuration**:
- **CPU**: 256 (0.25 vCPU) - lower than backend since nginx is lightweight
- **Memory**: 512 MB - sufficient for static site serving
- **Launch Type**: FARGATE
- **Network Mode**: awsvpc
- **Port**: 80 (standard HTTP port for nginx)

### 5. VPC and Networking (Can Reuse Backend Setup)

You can reuse the same VPC, subnets, and security group from the backend setup, **OR** create a separate security group for the frontend.

#### Option A: Reuse Backend Security Group

If reusing the backend security group, add port 80 rule:

```bash
# Allow inbound HTTP traffic on port 80
# Replace <SECURITY_GROUP_ID> with your existing ECS security group ID
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region us-east-2
```

#### Option B: Create Separate Frontend Security Group

```bash
# Create security group for frontend ECS tasks
aws ec2 create-security-group \
  --group-name ece461-frontend-ecs-sg \
  --description "Security group for frontend ECS tasks" \
  --vpc-id <VPC_ID> \
  --region us-east-2

# Allow inbound HTTP traffic on port 80
# Replace <SECURITY_GROUP_ID> with the GroupId from the command above
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region us-east-2
```

**Recommendation**: Option A (reuse security group) for MVP simplicity.

### 6. Application Load Balancer (ALB) - Optional for MVP

**For MVP**: ALB is not required if you can access the service directly via public IP.
**For production**: ALB recommended for better reliability, SSL termination, and routing.

To set up ALB (optional):

```bash
# Create ALB (or reuse backend ALB)
aws elbv2 create-load-balancer \
  --name ece461-frontend-alb \
  --subnets <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-groups <ALB_SECURITY_GROUP_ID> \
  --region us-east-2

# Create target group
aws elbv2 create-target-group \
  --name ece461-frontend-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id <VPC_ID> \
  --target-type ip \
  --health-check-path / \
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
- `<SUBNET_ID_1>`: First subnet ID from your VPC (same as backend)
- `<SUBNET_ID_2>`: Second subnet ID from your VPC (same as backend)
- `<SECURITY_GROUP_ID>`: Security group ID (can reuse backend security group, or use frontend-specific one)

```bash
aws ecs create-service \
  --cluster ece461-backend-cluster \
  --service-name ece461-frontend-service \
  --task-definition ece461-frontend-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_ID_1>,<SUBNET_ID_2>],securityGroups=[<SECURITY_GROUP_ID>],assignPublicIp=ENABLED}" \
  --region us-east-2
```

**MVP Option (No ALB)**: If not using an ALB, remove the `--load-balancers` flag. The service will have a public IP that you can access directly.

**Note**: If using the same cluster as backend, both services will run on the same cluster, which is fine for MVP.

### 8. IAM Role for GitHub Actions

**Option A: Reuse Backend Role** (recommended for MVP):
- The existing `github-actions-deploy-role` already has ECR and ECS permissions
- Just verify it has access to the new ECR repository (permissions are resource-level `*`, so it should work)

**Option B: Create Separate Frontend Role**:
If you prefer separation, follow the same steps as backend setup (Section 8 in `ECS_SETUP.md`), but name it `github-actions-deploy-frontend-role` and update the GitHub secret accordingly.

**Recommendation**: Use Option A for MVP simplicity.

### 9. ECS Task Execution Role (Can Reuse)

The same `ecsTaskExecutionRole` created for the backend can be reused for the frontend. It already has permissions to pull from ECR and write to CloudWatch Logs.

Verify it exists:
```bash
aws iam get-role \
  --role-name ecsTaskExecutionRole \
  --query 'Role.[RoleName,Arn]' \
  --output table
```

## Frontend Dockerfile

Create `Dockerfile.frontend` in the repository root:

```dockerfile
# syntax=docker/dockerfile:1
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ .

# Build the frontend (adjust build command if needed)
RUN npm run build

# Production stage - serve with nginx
FROM nginx:alpine

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Optional: Copy custom nginx config if needed
# COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check for ECS
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

**Note**: Adjust the `COPY` paths and `npm run build` command based on your frontend framework structure.

## Updating CD Pipeline

The CD pipeline (`.github/workflows/cd.yml`) needs to be updated to deploy the frontend. Add these steps **after** the backend deployment steps:

```yaml
- name: Build and push frontend image
  env:
    ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
  run: |
    docker build -f Dockerfile.frontend -t $ECR_REGISTRY/ece461-frontend:${{ env.IMAGE_TAG }} .
    docker push $ECR_REGISTRY/ece461-frontend:${{ env.IMAGE_TAG }}
    echo "FRONTEND_IMAGE_URI=$ECR_REGISTRY/ece461-frontend:${{ env.IMAGE_TAG }}" >> $GITHUB_ENV

- name: Update frontend task definition
  run: |
    aws ecs describe-task-definition \
      --task-definition ece461-frontend-task \
      --query taskDefinition > task-definition-frontend.json
    jq --arg IMAGE "$FRONTEND_IMAGE_URI" \
      '.containerDefinitions[0].image = $IMAGE' \
      task-definition-frontend.json > task-definition-frontend-updated.json
    jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
      task-definition-frontend-updated.json > task-definition-frontend-final.json

- name: Register and deploy frontend
  run: |
    aws ecs register-task-definition \
      --cli-input-json file://task-definition-frontend-final.json \
      --region ${{ env.AWS_REGION }}
    aws ecs update-service \
      --cluster ${{ env.ECS_CLUSTER }} \
      --service ece461-frontend-service \
      --task-definition ece461-frontend-task \
      --force-new-deployment \
      --region ${{ env.AWS_REGION }}
```

**Alternative**: Create a separate workflow file (e.g., `cd-frontend.yml`) if you want to deploy frontend independently.

## MVP Cost Tips

1. **Reuse Resources**: Use the same cluster and security group as backend to minimize setup
2. **Scale to Zero**: Set `desired-count` to 0 when not testing
3. **Lower Resources**: Frontend uses less CPU/memory (256 CPU / 512 MB) than backend
4. **Clean Up**: Delete service when done testing to avoid charges

## Monitoring

- CloudWatch Logs: `/ecs/ece461-frontend-task`
- ECS Service Metrics: Available in CloudWatch automatically
- Health Checks: Configured via ALB or ECS service health checks

## Pre-Deployment Verification

Before testing your CD pipeline, verify everything is configured correctly:

### Quick Verification Script

You can modify `verify-aws-setup.sh` to check frontend resources, or run these commands:

```bash
# 1. ECR Repository
aws ecr describe-repositories --repository-names ece461-frontend --region us-east-2 --query 'repositories[0].repositoryUri' --output text

# 2. ECS Cluster (should exist if backend is set up)
aws ecs describe-clusters --clusters ece461-backend-cluster --region us-east-2 --query 'clusters[0].status' --output text

# 3. CloudWatch Log Group
aws logs describe-log-groups --log-group-name-prefix "/ecs/ece461-frontend-task" --region us-east-2 --query 'logGroups[0].logGroupName' --output text

# 4. Task Definition
aws ecs describe-task-definition --task-definition ece461-frontend-task --region us-east-2 --query 'taskDefinition.[family,status,revision]' --output table

# 5. ECS Service
aws ecs describe-services --cluster ece461-backend-cluster --services ece461-frontend-service --region us-east-2 --query 'services[0].[serviceName,status,desiredCount,runningCount]' --output table

# 6. Security Group (verify port 80 is open)
aws ec2 describe-security-groups --filters "Name=group-name,Values=ece461-backend-ecs-sg" --region us-east-2 --query 'SecurityGroups[0].IpPermissions[?ToPort==`80`]' --output json
```

### Manual Verification Checklist

**1. ECR Repository:**
```bash
aws ecr describe-repositories --repository-names ece461-frontend --region us-east-2 --query 'repositories[0].repositoryUri' --output text
```
**Expected**: Should return the repository URI

**2. ECS Cluster:**
```bash
aws ecs describe-clusters --clusters ece461-backend-cluster --region us-east-2 --query 'clusters[0].status' --output text
```
**Expected**: `ACTIVE`

**3. CloudWatch Log Group:**
```bash
aws logs describe-log-groups --log-group-name-prefix "/ecs/ece461-frontend-task" --region us-east-2 --query 'logGroups[0].logGroupName' --output text
```
**Expected**: `/ecs/ece461-frontend-task`

**4. Task Definition:**
```bash
aws ecs describe-task-definition --task-definition ece461-frontend-task --region us-east-2 --query 'taskDefinition.[family,status,revision]' --output table
```
**Expected**: Should show `ece461-frontend-task`, `ACTIVE`, and revision number

**5. ECS Service:**
```bash
aws ecs describe-services --cluster ece461-backend-cluster --services ece461-frontend-service --region us-east-2 --query 'services[0].[serviceName,status,desiredCount,runningCount]' --output table
```
**Expected**: `ACTIVE`, desiredCount=1, runningCount=0 (until image exists)

**6. Security Group:**
```bash
aws ec2 describe-security-groups --filters "Name=group-name,Values=ece461-backend-ecs-sg" --region us-east-2 --query 'SecurityGroups[0].IpPermissions[?ToPort==`80`]' --output json
```
**Expected**: Should show port 80 ingress rule

**7. ECS Task Execution Role:**
```bash
aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text
```
**Expected**: Should return role ARN (can reuse from backend)

## Troubleshooting

1. **Tasks not starting**: Check CloudWatch Logs (`/ecs/ece461-frontend-task`), verify IAM roles, security groups
2. **Cannot reach service**: Verify security groups allow port 80 and service has public IP
3. **Image pull errors**: Verify ECR permissions and image URI in task definition
4. **Build failures**: Check Dockerfile.frontend paths match your frontend folder structure
5. **CD Pipeline fails**: Verify GitHub secret is set and IAM role has correct permissions (ECR access)
6. **404 errors**: Check nginx is serving from correct directory (`/usr/share/nginx/html`)

## Differences from Backend Setup

| Aspect | Backend | Frontend |
|--------|---------|----------|
| **Port** | 8000 | 80 |
| **CPU** | 512 (0.5 vCPU) | 256 (0.25 vCPU) |
| **Memory** | 1024 MB | 512 MB |
| **Base Image** | Python 3.11-slim | Node 18-alpine (build) + Nginx Alpine (runtime) |
| **Build Process** | Copy dependencies, install | npm ci, npm run build |
| **Runtime** | uvicorn | nginx |
| **Health Check** | `/health` endpoint | `/` or root path |

## Next Steps

1. Create the frontend folder structure
2. Create `Dockerfile.frontend` in repository root
3. Create ECR repository for frontend
4. Create CloudWatch log group
5. Create ECS task definition
6. Update security group to allow port 80
7. Create ECS service
8. Update CD pipeline to include frontend deployment
9. Test deployment via GitHub Actions

