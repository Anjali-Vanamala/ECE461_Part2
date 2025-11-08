# AWS Setup Status Tracker

**Purpose:** Track which AWS resources have been created and their details. Update this as you set things up.

**Last Updated:** November 8, 2025

---

## AWS Account Information

- **Account ID:** `<REDACTED>` (12-digit number - stored securely, not in public repo)
- **Region:** `us-east-2`
- **Access Method:** AWS Access Portal (SSO)
- **Access Status:** ✅ **ACTIVE** - Access granted

---

## Required Resources Checklist

**Current Status:** ✅ **MOSTLY COMPLETE** - Core resources created, but deployment has issues (8549 failed tasks)

### ✅/❌ ECR Repository
- **Status:** ✅ **CREATED**
- **Name:** `ece461-backend`
- **Region:** `us-east-2`
- **Registry URL:** `<ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/ece461-backend`
- **Created Date:** `2025-11-03`
- **Notes:** 

### ✅/❌ ECS Cluster
- **Status:** ✅ **CREATED** - ACTIVE
- **Name:** `ece461-backend-cluster`
- **Region:** `us-east-2`
- **Running Tasks:** 1
- **Active Services:** 2
- **Created Date:** `2025-11-03` (estimated)
- **Notes:** 

### ✅/❌ CloudWatch Log Group
- **Status:** ✅ **CREATED**
- **Name:** `/ecs/ece461-backend-task`
- **Region:** `us-east-2`
- **Created Date:** `2025-11-03` (estimated)
- **Stored Bytes:** 19276
- **Notes:** 

### ✅/❌ ECS Task Definition
- **Status:** ✅ **CREATED**
- **Family:** `ece461-backend-task`
- **Region:** `us-east-2`
- **Current Revision:** `6`
- **Created Date:** `2025-11-03` (estimated)
- **Notes:** Created from `task-definition-mvp.json` with placeholders replaced

### ✅/❌ ECS Service
- **Status:** ✅ **CREATED** - ACTIVE (⚠️ Deployment in progress)
- **Name:** `ece461-backend-service`
- **Cluster:** `ece461-backend-cluster`
- **Task Definition:** `ece461-backend-task:6`
- **Desired Count:** `1`
- **Running Count:** `1`
- **Launch Type:** `FARGATE`
- **Region:** `us-east-2`
- **Created Date:** `2025-11-03` (estimated)
- **Subnets:** 
  - `subnet-0b38e3a84d56d67df`
  - `subnet-0049c81939aca1fe5`
- **Security Group:** `sg-0a84d66f656c7bf66`
- **Public IP:** `ENABLED`
- **Public IP/ALB URL:** `_________________` (need to get from running task)
- **⚠️ Warning:** High failed task count (8549) in previous deployment - investigate task logs
- **Notes:** 

### ✅/❌ VPC & Networking
- **Status:** ✅ **CONFIGURED** (using existing VPC)
- **VPC ID:** `_________________` (need to check from subnet)
- **Subnet IDs:** 
  - Subnet 1: `subnet-0b38e3a84d56d67df`
  - Subnet 2: `subnet-0049c81939aca1fe5`
- **Security Group ID:** `sg-0a84d66f656c7bf66`
- **Security Group Name:** `ece461-backend-ecs-sg` (assumed, need to verify)
- **Port Allowed:** `8000`
- **Notes:** 

### ✅/❌ Application Load Balancer (Optional for MVP)
- **Status:** [ ] Created / [ ] Not Created / [ ] Not Needed
- **Name:** `ece461-backend-alb`
- **ARN:** `_________________`
- **DNS Name:** `_________________`
- **Target Group:** `ece461-backend-tg`
- **Target Group ARN:** `_________________`
- **Notes:** 

### ✅/❌ IAM Roles

#### GitHub Actions Deploy Role
- **Status:** ✅ **CREATED**
- **Role Name:** `github-actions-deploy-role`
- **Created Date:** `2025-11-03`
- **Last Used:** `2025-11-03` (us-east-2)
- **GitHub Secret Name:** `AWS_IAM_ROLE_ARN`
- **GitHub Secret Status:** ✅ **SET**
- **Notes:** 

#### ECS Task Execution Role
- **Status:** ✅ **CREATED**
- **Role Name:** `ecsTaskExecutionRole`
- **Created Date:** `2025-11-03`
- **Last Used:** `2025-11-08` (us-east-2)
- **Notes:** 

### ✅/❌ GitHub OIDC Provider
- **Status:** ✅ **CONFIGURED** (part of IAM role setup)
- **Provider URL:** `token.actions.githubusercontent.com`
- **Audience:** `sts.amazonaws.com`
- **Repository Scope:** `repo:Anjali-Vanamala/ECE461_Part2:*`
- **Notes:** 

---

## Quick Reference Commands

### Check if resources exist:

```bash
# Check ECR repo
aws ecr describe-repositories --repository-names ece461-backend --region us-east-2

# Check ECS cluster
aws ecs describe-clusters --clusters ece461-backend-cluster --region us-east-2

# Check ECS service
aws ecs describe-services --cluster ece461-backend-cluster --services ece461-backend-service --region us-east-2

# Check task definition
aws ecs describe-task-definition --task-definition ece461-backend-task --region us-east-2

# Check log group
aws logs describe-log-groups --log-group-name-prefix /ecs/ece461-backend-task --region us-east-2

# Check IAM roles
aws iam get-role --role-name github-actions-deploy-role
aws iam get-role --role-name ecsTaskExecutionRole
```

### Get Account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

---

## Deployment Status

- **First Deployment:** ✅ **ATTEMPTED** - Service is running but has issues
- **Last Deployment Date:** `2025-11-08` (last service update)
- **Current Task Definition Revision:** `6`
- **Service Status:** ACTIVE, but deployment IN_PROGRESS
- **Running Tasks:** 1/1 desired
- **⚠️ Failed Tasks:** 8549 (in previous deployment) - **INVESTIGATE LOGS**
- **Service URL:** `_________________` (need to get public IP from running task)
- **Health Check:** [ ] Passing / [ ] Failing / [ ] Not Tested

---

## Notes & Issues

**Current Status:**
- ✅ AWS Access Portal - Active
- ✅ GitHub Actions Deploy Role - Created
- ✅ GitHub OIDC Provider - Configured
- ✅ GitHub Secret `AWS_IAM_ROLE_ARN` - Set
- ✅ ECR Repository - Created
- ✅ ECS Cluster - Created and ACTIVE
- ✅ ECS Task Definition - Created (revision 6)
- ✅ ECS Service - Created and ACTIVE
- ✅ VPC/Networking - Configured
- ✅ CloudWatch Log Group - Created
- ✅ ECS Task Execution Role - Created
- ⚠️ **ISSUE:** High failed task count (8549) - need to investigate task logs

**Deployment Code Status:**
- ✅ CD Pipeline (`.github/workflows/cd.yml`) - Complete and ready
- ✅ Dockerfile - Complete and ready  
- ✅ Task Definition Template (`task-definition-mvp.json`) - Ready, needs Account ID filled
- ✅ FastAPI Backend - Ready

**Next Steps:**
1. ✅ ~~Get AWS Account ID~~ - Done
2. ✅ ~~Create AWS resources~~ - Done (ECR, ECS cluster, service, task definition, log group, IAM roles)
3. ✅ ~~Create GitHub Secret `AWS_IAM_ROLE_ARN`~~ - Done
4. **URGENT:** Investigate failed tasks (8549 failures) - check CloudWatch logs for `/ecs/ece461-backend-task`
5. Get public IP of running task to test API endpoint
6. Verify service health and API accessibility

