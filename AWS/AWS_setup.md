# ECE461 Part 2 - AWS Setup Overview

**Team:** ECE30861 Team 4  
**Last Updated:** November 13, 2025  
**Region:** us-east-2 (Ohio)  
**AWS Account:** <YOUR_AWS_ACCOUNT_ID>

> 💡 **Quick Start:** See `README.txt` in this folder for links to all AWS verification commands

---

## What We Have Running on AWS

Our project uses AWS to host a FastAPI backend (ECS/Fargate) and a static HTML frontend (S3). Everything is automated through GitHub Actions, so when we push to `main`, it deploys automatically.

**Current Status:** ✅ Active and deployed  
- **Deployments:** 8 Docker images in ECR, latest from November 13, 2025
- **Running Tasks:** 1 of 1 desired (Fargate)
- **Task Revision:** 13 (512 CPU units, 1024 MB memory)
- **Frontend Files:** 2 files in S3 bucket with website hosting enabled

---

## Quick Reference - Key Resources

| Resource | Name/ID | Status/Details |
|----------|---------|----------------|
| **ECR Repository** | `ece461-backend` | ✅ 8 Docker images |
| **ECS Cluster** | `ece461-backend-cluster` | ✅ ACTIVE |
| **ECS Service** | `ece461-backend-service` | ✅ ACTIVE (1/1 tasks) |
| **ECS Task Definition** | `ece461-backend-task` | ✅ Revision 13 (512 CPU, 1024 MB) |
| **CloudWatch Logs** | `/ecs/ece461-backend-task` | ✅ Active (~0.04 MB stored) |
| **S3 Bucket** | `ece461-frontend` | ✅ 2 files, hosting enabled |
| **Security Group** | `sg-0a84d66f656c7bf66` | ✅ Port 8000 open |
| **VPC** | `vpc-044c2485fbca6f3bc` | ✅ 172.31.0.0/16 |
| **Subnets** | `subnet-0b38e3a84d56d67df`<br>`subnet-0049c81939aca1fe5` | ✅ us-east-2c, us-east-2a |
| **IAM Roles** | `github-actions-deploy-role`<br>`ecsTaskExecutionRole` | ✅ Active |

---

## Architecture Overview

```
GitHub Actions (push to main)
    ↓
    ├─→ Build Docker Image → Push to ECR
    ↓
    ├─→ Deploy to ECS/Fargate (Backend API)
    ↓
    └─→ Deploy to S3 (Frontend HTML)
```

---

## Core Components

### 1. **ECR (Elastic Container Registry)**
- **What it is:** Docker image storage (like Docker Hub, but private)
- **Name:** `ece461-backend`
- **Purpose:** Stores our FastAPI backend Docker images
- **Repository URI:** `<AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/ece461-backend`
- **Current Images:** 8 total (Git SHA-based tags)

### 2. **ECS Cluster (Elastic Container Service)**
- **What it is:** Orchestrates Docker containers
- **Name:** `ece461-backend-cluster`
- **Purpose:** Manages where and how our containers run
- **Running Tasks:** 1 (our backend API)

### 3. **ECS Service**
- **What it is:** Ensures our container stays running
- **Name:** `ece461-backend-service`
- **Purpose:** Keeps 1 instance of our API running at all times
- **Launch Type:** Fargate (serverless - no EC2 management needed)
- **Current Status:** 1 task running (desired: 1)

### 4. **ECS Task Definition**
- **What it is:** Blueprint for our container (CPU, memory, ports, environment)
- **Name:** `ece461-backend-task`
- **Current Revision:** 13
- **Container:** FastAPI app on port 8000
- **Resources:** 512 CPU units, 1024 MB RAM (0.5 vCPU, 1 GB)
- **Network Mode:** awsvpc (required for Fargate)

### 5. **CloudWatch Logs**
- **What it is:** Application log storage
- **Log Group:** `/ecs/ece461-backend-task`
- **Purpose:** View backend logs (errors, requests, debug info)
- **Current Size:** ~0.04 MB stored
- **Retention:** Never expire (default)

### 6. **S3 Frontend Bucket**
- **What it is:** Static website hosting
- **Bucket Name:** `ece461-frontend`
- **Purpose:** Hosts HTML/CSS/JS files
- **Current Files:** 2 files (index.html + assets)
- **Website Hosting:** ✅ Enabled (index.html)
- **URL:** `http://ece461-frontend.s3-website.us-east-2.amazonaws.com`

### 7. **Security Group & Networking**
- **What it is:** Firewall rules for our containers
- **Security Group ID:** `sg-0a84d66f656c7bf66`
- **Security Group Name:** `ece461-backend-ecs-sg`
- **Rules:** Allows incoming traffic on port 8000 (our API)
- **VPC ID:** `vpc-044c2485fbca6f3bc` (172.31.0.0/16 - default VPC)
- **Subnets:** 
  - `subnet-0b38e3a84d56d67df` (us-east-2c, 172.31.32.0/20)
  - `subnet-0049c81939aca1fe5` (us-east-2a, 172.31.0.0/20)
- **Public IP:** Enabled (changes when task restarts - use `quick_status.txt` to get current IP)

### 8. **IAM Roles (Permissions)**

#### GitHub Actions Deploy Role
- **Name:** `github-actions-deploy-role`
- **Purpose:** Allows GitHub Actions to deploy to AWS
- **Permissions:** Push to ECR, update ECS, write to S3
- **GitHub Secret:** `AWS_IAM_ROLE_ARN` (already configured)

#### ECS Task Execution Role
- **Name:** `ecsTaskExecutionRole`
- **Purpose:** Allows ECS to pull images and write logs
- **Permissions:** Pull from ECR, write to CloudWatch
- **Status:** Active and in use by running tasks

### 9. **GitHub OIDC Provider**
- **Purpose:** Allows GitHub Actions to authenticate with AWS without long-lived credentials
- **Provider URL:** `token.actions.githubusercontent.com`
- **Status:** ✅ Configured for repository

---

## How Deployment Works

1. **Developer pushes to `main` branch**
2. **GitHub Actions triggers** (`.github/workflows/cd.yml` for backend, `cd-frontend.yml` for frontend)
3. **Backend deployment:**
   - Runs tests
   - Builds Docker image
   - Pushes to ECR
   - Updates ECS task definition with new image
   - ECS automatically rolls out new version
4. **Frontend deployment:**
   - Builds static files
   - Syncs to S3 bucket
5. **Done!** - API and frontend are live

---

## Accessing Your Services

### Backend API
Your API runs on a public IP that changes when the task restarts.

**Access Points:**
- Health check: `http://<PUBLIC_IP>:8000/health`
- API docs: `http://<PUBLIC_IP>:8000/docs`
- Root endpoint: `http://<PUBLIC_IP>:8000/`

**To find current IP:** Use `quick_status.txt` or `URL_grab` in this folder

### Frontend (S3 Static Website)
- **URL:** `http://ece461-frontend.s3-website.us-east-2.amazonaws.com`
- **Status:** Active with 2 files deployed

---

## Viewing Logs

### AWS CloudWatch
- **Log Group:** `/ecs/ece461-backend-task`
- **Location:** AWS Console → CloudWatch → Log groups
- **Content:** Application logs, errors, requests, debug info
- **Current Size:** ~0.04 MB stored

---

## Monitoring & Metrics

Our backend publishes custom metrics to CloudWatch:
- **Namespace:** `ECE461/API`
- **Metrics:**
  - `RequestCount` - Number of API requests
  - `APILatency` - Response time in milliseconds
  - `ErrorCount` - Number of errors

**Location:** CloudWatch → Metrics → Custom namespaces → "ECE461/API"

---

## Cost Estimates (Approximate)

Based on current usage:
- **ECS Fargate:** ~$10-15/month (1 task, 512 CPU, 1024 MB RAM, running 24/7)
- **ECR:** ~$0.01/month (8 images, <100 MB total storage)
- **S3:** <$0.01/month (2 files, minimal storage)
- **CloudWatch Logs:** <$0.01/month (0.04 MB stored, first 5 GB free)
- **CloudWatch Metrics:** $0/month (3 custom metrics, first 10 free)
- **Data Transfer:** ~$1-2/month (minimal outbound data)

**Current estimated total:** ~$11-17/month

---

## GitHub Secrets Required

These are already set up in the repository (Settings → Secrets and variables → Actions):

| Secret Name | Value | Purpose | Status |
|------------|-------|---------|--------|
| `AWS_IAM_ROLE_ARN` | ARN of `github-actions-deploy-role` | Allows GitHub Actions to authenticate with AWS | ✅ Configured |
| `GEN_AI_STUDIO_API_KEY` | Purdue GenAI API key | Used by performance metrics (injected from AWS Parameter Store) | ✅ Configured |

**Note:** The `GEN_AI_STUDIO_API_KEY` is stored in AWS Systems Manager Parameter Store at `/myapp/GEN_AI_STUDIO_API_KEY` and automatically injected into the container at runtime.

---

## Troubleshooting

### API not responding
1. Verify task is running (use `quick_status.txt`)
2. Check CloudWatch logs at `/ecs/ece461-backend-task`
3. Verify security group `sg-0a84d66f656c7bf66` allows port 8000

### Deployment fails
1. Check GitHub Actions workflow logs
2. Verify IAM role `github-actions-deploy-role` has correct permissions
3. Check ECS service events in AWS Console

### Can't find public IP
- ECS tasks get new public IPs when they restart
- Use `URL_grab` or `quick_status.txt` to get current IP

---

## Additional Resources

- **AWS Console:** [https://console.aws.amazon.com](https://console.aws.amazon.com)
- **Verification Commands:** See `README.txt` in this folder
- **Detailed Setup Status:** See `../setup_instrucs/AWS_SETUP_STATUS.md`
- **CloudWatch IAM Setup:** See `../setup_instrucs/CLOUDWATCH_IAM_PERMISSIONS.md`
- **S3 Frontend Setup:** See `../setup_instrucs/S3_FRONTEND_SETUP.md`

