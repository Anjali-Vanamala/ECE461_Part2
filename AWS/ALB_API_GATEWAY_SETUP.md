# ALB + REST API Gateway Setup Guide

**Region:** us-east-2

## Prerequisites

**Existing Resources:**
- VPC ID: `vpc-044c2485fbca6f3bc`
- Subnets: `subnet-0b38e3a84d56d67df`, `subnet-0049c81939aca1fe5`
- Security Group (ECS): `sg-0a84d66f656c7bf66`
- ECS Cluster: `ece461-backend-cluster`
- ECS Service: `ece461-backend-service`

---

## Phase 1: ALB Infrastructure Setup

### Step 1.1: Create ALB Security Group

**Purpose:** Allow HTTP traffic (port 80) from internet to ALB

**Action:** Create security group with inbound rule for port 80 from 0.0.0.0/0

**AWS CLI Commands:**
```bash
# Create security group for ALB
aws ec2 create-security-group \
  --group-name ece461-alb-sg \
  --description "Security group for ALB" \
  --vpc-id vpc-044c2485fbca6f3bc \
  --region us-east-2

# Save the GroupId from output, then allow HTTP traffic
aws ec2 authorize-security-group-ingress \
  --group-id <ALB_SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region us-east-2
```

**Output:** Security Group ID (save this for Step 1.2)

---

### Step 1.2: Create Application Load Balancer

**Purpose:** Stable endpoint for your API

**Action:** Create ALB in public subnets with the security group from Step 1.1

**Configuration:**
- Type: Application Load Balancer
- Scheme: Internet-facing
- Subnets: Your two public subnets
- Security Group: From Step 1.1

**AWS CLI Commands:**
```bash
aws elbv2 create-load-balancer \
  --name ece461-alb \
  --subnets subnet-0b38e3a84d56d67df subnet-0049c81939aca1fe5 \
  --security-groups <ALB_SECURITY_GROUP_ID> \
  --scheme internet-facing \
  --type application \
  --region us-east-2
```

**Output:** ALB ARN and DNS name (save DNS name - this is your stable endpoint)

---

### Step 1.3: Create Target Group

**Purpose:** Register ECS tasks as targets

**Action:** Create target group for HTTP on port 8000

**Configuration:**
- Protocol: HTTP
- Port: 8000
- Target type: IP (for Fargate)
- VPC: Your VPC
- Health check path: `/health`

**AWS CLI Commands:**
```bash
aws elbv2 create-target-group \
  --name ece461-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-044c2485fbca6f3bc \
  --target-type ip \
  --health-check-path /health \
  --health-check-protocol HTTP \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --region us-east-2
```

**Output:** Target Group ARN (save this for Steps 1.4 and 1.5)

---

### Step 1.4: Create ALB Listener

**Purpose:** Route traffic from ALB to target group

**Action:** Create listener on port 80 forwarding to target group

**Configuration:**
- Protocol: HTTP
- Port: 80
- Default action: Forward to target group from Step 1.3

**AWS CLI Commands:**
```bash
aws elbv2 create-listener \
  --load-balancer-arn <ALB_ARN> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN> \
  --region us-east-2
```

**Output:** Listener ARN

---

### Step 1.5: Update ECS Service

**Purpose:** Attach ALB to ECS service so tasks register automatically

**Action:** Update ECS service to use load balancer

**Configuration:**
- Load balancer: Target group from Step 1.3
- Container name: `fastapi-app`
- Container port: 8000

**AWS CLI Commands:**
```bash
aws ecs update-service \
  --cluster ece461-backend-cluster \
  --service ece461-backend-service \
  --load-balancers targetGroupArn=<TARGET_GROUP_ARN>,containerName=fastapi-app,containerPort=8000 \
  --region us-east-2
```

**Output:** Updated service (tasks will register with ALB automatically)

---

### Step 1.6: Verify ALB Setup

**Purpose:** Ensure everything works before API Gateway

**Action:** Test ALB DNS name directly

**Test:**
```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names ece461-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text \
  --region us-east-2)

# Test health endpoint
curl http://${ALB_DNS}/health
```

**Expected:** Should return health check response from your backend

---

## Phase 2: REST API Gateway Setup

### Step 2.1: Create REST API

**Purpose:** Create the API Gateway REST API

**Action:** Create REST API (not HTTP API)

**Configuration:**
- Name: `ece461-api-gateway`
- Description: API Gateway for ECE461 backend
- Endpoint type: Regional

**AWS CLI Commands:**
```bash
aws apigateway create-rest-api \
  --name ece461-api-gateway \
  --description "API Gateway for ECE461 backend" \
  --endpoint-configuration types=REGIONAL \
  --region us-east-2
```

**Output:** REST API ID (save this - you'll need it for GitHub secrets)

---

### Step 2.2: Create Proxy Resource

**Purpose:** Catch-all route to forward all requests

**Action:** Create resource with path `{proxy+}`

**Configuration:**
- Path: `{proxy+}` (this catches all paths)
- Parent: Root resource `/`

**AWS CLI Commands:**
```bash
# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id <API_ID> \
  --query 'items[?path==`/`].id' \
  --output text \
  --region us-east-2)

# Create proxy resource
aws apigateway create-resource \
  --rest-api-id <API_ID> \
  --parent-id ${ROOT_RESOURCE_ID} \
  --path-part '{proxy+}' \
  --region us-east-2
```

**Output:** Resource ID (save this for Step 2.3)

---

### Step 2.3: Create ANY Method

**Purpose:** Handle all HTTP methods (GET, POST, PUT, DELETE, etc.)

**Action:** Create method on `{proxy+}` resource

**Configuration:**
- Method: ANY (or create individual methods if preferred)
- Authorization: None (for now)

**AWS CLI Commands:**
```bash
# Get proxy resource ID
PROXY_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id <API_ID> \
  --query 'items[?path==`/{proxy+}`].id' \
  --output text \
  --region us-east-2)

# Create ANY method
aws apigateway put-method \
  --rest-api-id <API_ID> \
  --resource-id ${PROXY_RESOURCE_ID} \
  --http-method ANY \
  --authorization-type NONE \
  --region us-east-2
```

**Output:** Method ID

---

### Step 2.4: Create Integration

**Purpose:** Connect API Gateway to ALB

**Action:** Create HTTP_PROXY integration pointing to ALB

**Configuration:**
- Integration type: HTTP_PROXY
- Integration method: ANY (or match your method)
- Integration URI: `http://<ALB_DNS_NAME>/{proxy}`
- Content handling: Passthrough

**AWS CLI Commands:**
```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names ece461-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text \
  --region us-east-2)

# Create integration
aws apigateway put-integration \
  --rest-api-id <API_ID> \
  --resource-id ${PROXY_RESOURCE_ID} \
  --http-method ANY \
  --type HTTP_PROXY \
  --integration-http-method ANY \
  --uri "http://${ALB_DNS}/{proxy}" \
  --region us-east-2
```

**Output:** Integration ID

---

### Step 2.5: Configure CORS

**Purpose:** Allow frontend to call API from browser

**Action:** Enable CORS on the API

**Configuration:**
- Allow origins: `*` (or your S3 bucket URL)
- Allow methods: `GET, POST, PUT, DELETE, OPTIONS`
- Allow headers: `*`
- Expose headers: (optional)

**Action:** Create OPTIONS method for CORS preflight

**AWS CLI Commands:**
```bash
# Create OPTIONS method for CORS
aws apigateway put-method \
  --rest-api-id <API_ID> \
  --resource-id ${PROXY_RESOURCE_ID} \
  --http-method OPTIONS \
  --authorization-type NONE \
  --region us-east-2

# Create mock integration for OPTIONS
aws apigateway put-integration \
  --rest-api-id <API_ID> \
  --resource-id ${PROXY_RESOURCE_ID} \
  --http-method OPTIONS \
  --type MOCK \
  --request-templates '{"application/json":"{\"statusCode\":200}"}' \
  --region us-east-2

# Set method response for OPTIONS
aws apigateway put-method-response \
  --rest-api-id <API_ID> \
  --resource-id ${PROXY_RESOURCE_ID} \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters 'method.response.header.Access-Control-Allow-Headers=true,method.response.header.Access-Control-Allow-Methods=true,method.response.header.Access-Control-Allow-Origin=true' \
  --region us-east-2

# Set integration response for OPTIONS
aws apigateway put-integration-response \
  --rest-api-id <API_ID> \
  --resource-id ${PROXY_RESOURCE_ID} \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'GET,POST,PUT,DELETE,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
  --region us-east-2
```

**Note:** CORS is also configured in the backend (already done in `backend/app.py`)

---

### Step 2.6: Deploy API

**Purpose:** Make API accessible via public URL

**Action:** Create stage and deploy

**Configuration:**
- Stage name: `prod` (or `dev`)
- Deployment description: "Initial deployment"
- Enable logging: (optional, for debugging)

**AWS CLI Commands:**
```bash
# Create deployment
aws apigateway create-deployment \
  --rest-api-id <API_ID> \
  --stage-name prod \
  --description "Initial deployment" \
  --region us-east-2
```

**Output:** Invoke URL (save this - this is your API endpoint)
- Format: `https://<API_ID>.execute-api.us-east-2.amazonaws.com/prod`

---

### Step 2.7: Verify API Gateway

**Purpose:** Test API Gateway before frontend integration

**Action:** Test API Gateway URL directly

**Test:**
```bash
# Get API Gateway URL
API_URL="https://<API_ID>.execute-api.us-east-2.amazonaws.com/prod"

# Test health endpoint
curl ${API_URL}/health
```

**Expected:** Should return health check response

---

## Phase 3: Backend Code Changes

### Step 3.1: Add CORS Middleware

**Purpose:** Allow browser requests from frontend

**Action:** Add CORSMiddleware to FastAPI app

**File:** `backend/app.py`

**Status:** ✅ **Already completed**

The CORS middleware has been added to `backend/app.py` with:
- `allow_origins=["*"]` (can be restricted to S3 bucket URL in production)
- `allow_credentials=True`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

---

## Phase 4: Frontend Updates

### Step 4.1: Update HTML with API Gateway URL

**Purpose:** Connect frontend to API Gateway

**Action:** Replace any hardcoded backend URLs with API Gateway URL

**File:** `frontend/main.html`

**Status:** ✅ **Already completed**

The frontend has been updated with:
- Health check functionality
- API Gateway URL configuration constant
- Simple status display

**To configure:** Update line 30 in `frontend/main.html`:
```javascript
const API_GATEWAY_URL = 'https://YOUR_API_ID.execute-api.us-east-2.amazonaws.com/prod';
```

Replace `YOUR_API_ID` with your actual REST API ID from Step 2.1.

---

## Phase 5: CI/CD Integration

### Step 5.1: Add GitHub Secrets

**Purpose:** Store API Gateway info for CD pipeline

**Action:** Add secrets to GitHub repository

**Location:** GitHub → Settings → Secrets and variables → Actions

**Secrets to add:**

1. **`API_GATEWAY_ID`** (required if using API Gateway)
   - Value: Your REST API ID from Step 2.1
   - Example: `abc123xyz`

2. **`API_GATEWAY_STAGE`** (optional)
   - Value: Stage name (defaults to `prod` if not set)
   - Example: `prod` or `dev`

**Status:** ✅ **CI/CD workflow already updated**

The workflow (`.github/workflows/cd.yml`) has been updated to:
- Detect ALB configuration
- Retrieve ALB DNS name
- Construct API Gateway URL from secrets
- Verify ALB target health
- Output all URLs for reference

---

### Step 5.2: Update GitHub Actions Workflow

**Purpose:** Automate API Gateway updates if needed

**File:** `.github/workflows/cd.yml`

**Status:** ✅ **Already completed**

The workflow now includes:
- Step to get ALB DNS name (if ALB is configured)
- Step to get API Gateway URL (if API_GATEWAY_ID secret is set)
- Step to verify ALB health
- Enhanced output with ALB and API Gateway URLs

**Note:** The ALB DNS name is stable and doesn't change, so no updates are needed. The workflow just outputs it for reference.

---

### Step 5.3: Test CD Pipeline

**Purpose:** Verify automated deployment works

**Action:** Push changes and watch GitHub Actions

**Expected:** Pipeline completes, API Gateway integration works (no updates needed since ALB DNS is stable)

---

## Phase 6: Deployment and Verification

### Step 6.1: Deploy Backend

**Purpose:** Get updated backend with CORS deployed

**Action:** Push code changes, let CD pipeline deploy

**Verify:**
- ECS tasks are running
- Tasks are registered with ALB target group
- ALB health checks are passing

**Commands:**
```bash
# Check ECS service status
aws ecs describe-services \
  --cluster ece461-backend-cluster \
  --services ece461-backend-service \
  --region us-east-2

# Check ALB target health
TARGET_GROUP_ARN=$(aws ecs describe-services \
  --cluster ece461-backend-cluster \
  --services ece461-backend-service \
  --query 'services[0].loadBalancers[0].targetGroupArn' \
  --output text \
  --region us-east-2)

aws elbv2 describe-target-health \
  --target-group-arn ${TARGET_GROUP_ARN} \
  --region us-east-2
```

---

### Step 6.2: Verify ALB

**Purpose:** Ensure ALB is working before API Gateway

**Action:** Test ALB DNS name directly

**Test:**
```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names ece461-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text \
  --region us-east-2)

# Test health endpoint
curl http://${ALB_DNS}/health
```

**Expected:** 200 OK with health check response

---

### Step 6.3: Verify API Gateway

**Purpose:** Ensure API Gateway routes to ALB correctly

**Action:** Test API Gateway URL

**Test:**
```bash
# Test health endpoint via API Gateway
curl https://<API_ID>.execute-api.us-east-2.amazonaws.com/prod/health
```

**Expected:** 200 OK with health check response

---

### Step 6.4: Deploy Frontend

**Purpose:** Get updated frontend deployed to S3

**Action:** Deploy frontend HTML to S3 bucket

**Verify:** Frontend is accessible from S3 website URL

**Commands:**
```bash
# Deploy frontend (or use GitHub Actions workflow)
aws s3 sync frontend/dist s3://ece461-frontend \
  --region us-east-2 \
  --delete
```

---

### Step 6.5: End-to-End Test

**Purpose:** Verify complete flow works

**Action:** Test from S3 frontend

**Test:**
1. Open S3 website URL in browser
2. Check browser console for errors
3. Verify API calls succeed
4. Verify CORS headers are present

**Expected:** Frontend successfully calls API Gateway, gets responses

**S3 Website URL:**
```
http://ece461-frontend.s3-website.us-east-2.amazonaws.com
```

---

## Troubleshooting

- **502 Bad Gateway:** Check ALB target health, verify ECS tasks are running
- **CORS errors:** Verify CORS configured in both API Gateway (Step 2.5) and backend (`backend/app.py`)
- **ALB can't reach ECS:** ECS security group must allow inbound from ALB security group

