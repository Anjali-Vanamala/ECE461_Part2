# AWS Documentation Files
# ECE461 Part 2 - Team 4

**Current Deployment Status:** ✅ Active (8 Docker images, 1 running task)  
**Region:** us-east-2 (Ohio)  
**Account ID:** 978794836526

## Quick Reference

📋 **AWS_setup.md**
   → Overview of AWS setup, architecture, and how everything works
   → Read this first to understand the deployment

🚀 **quick_status.txt**
   → Copy the ENTIRE file and paste into AWS CLI
   → Gets a nice formatted summary of all deployed resources
   → Use this to quickly check if everything is running

🔗 **URL_grab**
   → Quick command to get your API's public IP address
   → Returns just the IP (e.g., 18.191.123.45)

📊 **detailed_commands.txt**
   → 10 standalone command blocks (like quick_status but by section)
   → Copy a section from "(" to ")" and paste to get formatted output
   → Sections: ECR, ECS Cluster, ECS Service, Task Definition, Running Tasks,
     CloudWatch Logs, IAM Roles, Security/Networking, S3, Account Info

## Usage

### Quick Status Check:
Copy all of `quick_status.txt` and paste into AWS CLI for a complete overview.

### Get API URL:
Copy all of `URL_grab` and paste into AWS CLI to get the current public IP.

### Detailed Info by Section:
Open `detailed_commands.txt`, find the section you need (e.g., "SECTION 6: CloudWatch Logs"), copy from "(" to ")", and paste into AWS CLI.

## What's Actually Deployed

**Backend (ECS/Fargate):**
- ECR Repository: ece461-backend (8 Docker images)
- ECS Cluster: ece461-backend-cluster (ACTIVE)
- ECS Service: ece461-backend-service (1/1 tasks running)
- Task Definition: ece461-backend-task (revision 13, 512 CPU, 1024 MB memory)
- CloudWatch Logs: /ecs/ece461-backend-task
- Current API IP: Changes when task restarts (use quick_status.txt to get current IP)

**Frontend (S3):**
- S3 Bucket: ece461-frontend (2 files, website hosting enabled)
- URL: http://ece461-frontend.s3-website.us-east-2.amazonaws.com

**Security & Networking:**
- IAM Roles: github-actions-deploy-role, ecsTaskExecutionRole
- OIDC Provider: token.actions.githubusercontent.com (for GitHub Actions)
- Security Group: ece461-backend-ecs-sg (sg-xxxxxxxxxxxxxxxxx)
- VPC: vpc-xxxxxxxxxxxxxxxxx (172.31.0.0/16)
- Subnets: subnet-xxxxxxxxxxxxxxxxx (us-east-2c), subnet-xxxxxxxxxxxxxxxxx (us-east-2a)

## Files in ../setup_instrucs/ (for reference)

- AWS_SETUP_STATUS.md - Detailed status tracker
- CLOUDWATCH_IAM_PERMISSIONS.md - CloudWatch setup guide
- S3_FRONTEND_SETUP.md - S3 frontend setup guide
- verify-aws-setup.sh - Original bash script (use quick_status.txt instead)

