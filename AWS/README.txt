# AWS Documentation Files
# ECE461 Part 2 - Team 4

**Current Deployment Status:** ✅ Active (8 Docker images, 1 running task)  
**Region:** us-east-2 (Ohio)  
**Account ID:** [REDACTED]

**Backend API URL (For Autograders):**
- **API Gateway:** `https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod`

## Quick Reference

📋 **AWS_setup.md**
   → Overview of AWS setup, architecture, and how everything works
   → Read this first to understand the deployment

🚀 **quick_status.txt**
   → Copy the ENTIRE file and paste into AWS CLI
   → Gets a nice formatted summary of all deployed resources
   → Use this to quickly check if everything is running

🔗 **URL_grab**
   → Get all backend access URLs (API Gateway, ALB, and direct task IP)
   → **Recommended for autograders:** Use API Gateway URL (stable, HTTPS)
   → **Alternative:** Use ALB DNS (stable, HTTP)
   → **Legacy:** Direct task IP (changes when task restarts - not recommended)

📊 **detailed_commands.txt**
   → 10 standalone command blocks (like quick_status but by section)
   → Copy a section from "(" to ")" and paste to get formatted output
   → Sections: ECR, ECS Cluster, ECS Service, Task Definition, Running Tasks,
     CloudWatch Logs, IAM Roles, Security/Networking, S3, Account Info

## Usage

### Quick Status Check:
Copy all of `quick_status.txt` and paste into AWS CLI for a complete overview.

### Get Backend Access URLs:
- **For Autograders/Testing:** 
  - **Primary URL:** `https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod`
  - Run `URL_grab` to get all available URLs (API Gateway, ALB, direct task IP)
- **For Full Status:** Run `quick_status.txt` to see all URLs and deployment status
- **Note:** API Gateway and ALB URLs are stable and don't change - use these instead of direct task IPs

### Detailed Info by Section:
Open `detailed_commands.txt`, find the section you need (e.g., "SECTION 6: CloudWatch Logs"), copy from "(" to ")", and paste into AWS CLI.

## What's Actually Deployed

**Backend (ECS/Fargate):**
- ECR Repository: ece461-backend (8 Docker images)
- ECS Cluster: ece461-backend-cluster (ACTIVE)
- ECS Service: ece461-backend-service (1/1 tasks running)
- Task Definition: ece461-backend-task (revision 13, 512 CPU, 1024 MB memory)
- CloudWatch Logs: /ecs/ece461-backend-task

**Load Balancing & API Gateway:**
- Application Load Balancer: ece461-alb (ACTIVE)
- Target Group: ece461-api-tg (port 8000, health check: /health)
- API Gateway REST API: ece461-api-gateway
- **API Gateway URL:** `https://9tiiou1yzj.execute-api.us-east-2.amazonaws.com/prod`
- Methods: GET, POST, PUT, DELETE, OPTIONS (all configured with HTTP_PROXY)
- **Note:** The `/prod` stage name is required in the URL path

**Frontend (S3):**
- S3 Bucket: ece461-frontend (2 files, website hosting enabled)
- URL: http://ece461-frontend.s3-website.us-east-2.amazonaws.com

**Security & Networking:**
- IAM Roles: github-actions-deploy-role, ecsTaskExecutionRole
- OIDC Provider: token.actions.githubusercontent.com (for GitHub Actions)
- Security Groups: ece461-backend-ecs-sg, ece461-alb-sg (IDs queried dynamically)
- VPC and Subnets: Queried dynamically from ECS service configuration
- **Note:** Run `quick_status.txt` to see current security group IDs, VPC, and subnet details

## Files in ../setup_instrucs/ (for reference)

- AWS_SETUP_STATUS.md - Detailed status tracker
- CLOUDWATCH_IAM_PERMISSIONS.md - CloudWatch setup guide
- S3_FRONTEND_SETUP.md - S3 frontend setup guide
- verify-aws-setup.sh - Original bash script (use quick_status.txt instead)

