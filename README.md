# ECE461 Model Registry

A full-stack Model Registry application for storing, rating, and managing ML models, datasets, and code artifacts. Built for ECE 30861 at Purdue University.

**Team:** ECE30861 Team 3  
**Current Members:** Anjali Vanamala, Shaantanu Sriram, Andrew Diab, Pryce Tharpe  
**Repository:** [https://github.com/Anjali-Vanamala/ECE461_Part2](https://github.com/Anjali-Vanamala/ECE461_Part2)

**Original Contributors (Team 4):** Hilal B Tasdemir, Georgia Griffin, Navya Datla, Sai Ganadavarapu  
*Original team members who created the foundational codebase, including the initial 7 quality metrics and backend concurrency features.*

---

## Table of Contents

- [Purpose](#purpose)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Interacting with the Application](#interacting-with-the-application)
- [Development](#development)

---

## Purpose

The Model Registry is a web application that allows users to:

- **Ingest artifacts** (ML models, datasets, code) from HuggingFace and GitHub
- **Calculate quality metrics** automatically (bus factor, code quality, data quality, license compliance, performance claims, ramp-up time, reproducibility, reviewedness, size, tree score)
- **Rate and score models** based on comprehensive quality analysis
- **Track lineage** between models, datasets, and code
- **Search and browse** registered artifacts with filtering and metadata
- **Download artifacts** with S3-backed storage and proxy fallback
- **Monitor system health** with detailed metrics and benchmarking tools

The system supports both **serverless (Lambda)** and **containerized (ECS/Fargate)** deployment options on AWS.

---

## Architecture

### Components

- **Backend API**: FastAPI (Python 3.11) with REST endpoints
- **Frontend**: Next.js 16 (React 19, TypeScript) with Radix UI components
- **Storage**: DynamoDB (metadata), S3 (artifacts), in-memory (testing)
- **Compute**: AWS Lambda (serverless) or ECS/Fargate (containers)
- **CI/CD**: GitHub Actions with automated deployments

### Deployment Options

1. **Lambda + API Gateway** (Serverless)
   - Scales to zero, pay-per-request
   - API Gateway HTTP API with `/prod` stage
   - Cold start latency possible

2. **ECS/Fargate** (Containerized)
   - Always-on container service
   - Application Load Balancer (optional)
   - No cold starts

### Technology Stack

**Backend:**
- FastAPI, Uvicorn, Mangum (Lambda adapter)
- Boto3 (AWS SDK), HuggingFace Hub
- Pydantic (validation), Pytest (testing)

**Frontend:**
- Next.js 16, React 19, TypeScript
- Tailwind CSS 4, Radix UI
- Recharts (visualization), Zod (validation)

---

## Configuration

### Environment Variables

#### Required for Backend

| Variable | Description | Default | Required For |
|----------|-------------|---------|--------------|
| `GITHUB_TOKEN` | GitHub API token for code analysis | - | Code quality metrics |
| `LOG_LEVEL` | Logging verbosity (0=silent, 1=info, 2=debug) | `1` | All environments |
| `LOG_FILE` | Path to log file | `/tmp/error_logs.log` | All environments |

#### Optional for Backend

| Variable | Description | Default | Required For |
|----------|-------------|---------|--------------|
| `STORAGE_BACKEND` | Storage type: `dynamodb` or empty (in-memory) | `""` (in-memory) | Production |
| `USE_DYNAMODB` | Legacy flag: `1` or `true` to use DynamoDB | `0` | Legacy support |
| `AWS_REGION` | AWS region for services | `us-east-2` | AWS deployments |
| `DDB_TABLE_NAME` | DynamoDB table name | `artifacts_metadata` | DynamoDB storage |
| `S3_ARTIFACT_BUCKET` | S3 bucket for artifact storage | - | S3 storage |
| `BASE_URL` | Public API base URL (for download links) | Auto-detected | Download endpoints |
| `COMPUTE_BACKEND` | Compute type: `lambda` or empty | Auto-detected | Runtime behavior |
| `GEN_AI_STUDIO_API_KEY` | Purdue GenAI API key for performance metrics | - | Performance claims metric |

#### Frontend Configuration

The frontend API base URL is hardcoded in `frontend/lib/api.ts`. To use a different backend endpoint, update the `API_BASE_URL` constant at the top of that file.

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Anjali-Vanamala/ECE461_Part2.git
   cd ECE461_Part2
   ```

2. **Create a `.env` file** in the project root:
   ```bash
   # Required
   GITHUB_TOKEN=your_github_token_here
   LOG_LEVEL=1
   LOG_FILE=./log.txt
   
   # Optional (for local testing)
   STORAGE_BACKEND=dynamodb
   AWS_REGION=us-east-2
   DDB_TABLE_NAME=artifacts_metadata
   S3_ARTIFACT_BUCKET=your-bucket-name
   ```

3. **Install backend dependencies:**
   ```bash
   pip install -r dependencies.txt
   ```

4. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   ```

5. **Run backend locally:**
   ```bash
   # From project root
   uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Run frontend locally:**
   ```bash
   # From frontend directory
   npm run dev
   ```

   Frontend will be available at `http://localhost:3000`. Note: The frontend connects to the production AWS API Gateway by default. To use a local backend, update `API_BASE_URL` in `frontend/lib/api.ts` to `http://localhost:8000`.

### AWS Configuration

#### DynamoDB Setup

1. **Create DynamoDB table:**
   ```bash
   aws dynamodb create-table \
     --table-name artifacts_metadata \
     --attribute-definitions AttributeName=id,AttributeType=S \
     --key-schema AttributeName=id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-2
   ```

2. **Set environment variable:**
   ```bash
   export DDB_TABLE_NAME=artifacts_metadata
   export AWS_REGION=us-east-2
   ```

#### S3 Setup

1. **Create S3 bucket:**
   ```bash
   aws s3 mb s3://your-artifact-bucket-name --region us-east-2
   ```

2. **Set environment variable:**
   ```bash
   export S3_ARTIFACT_BUCKET=your-artifact-bucket-name
   ```

#### Lambda Configuration

Environment variables are set in the Lambda function configuration or via GitHub Actions workflow. See [Lambda Setup Guide](AWS/lambda_setup.md) for details.

#### ECS Configuration

Environment variables are injected via ECS task definition. Secrets (like `GEN_AI_STUDIO_API_KEY`) are stored in AWS Systems Manager Parameter Store. See [ECS Setup Guide](ECS_SETUP.md) for details.

---

## Deployment

### Automated Deployment (GitHub Actions)

The project includes three CI/CD workflows that deploy automatically on push to `main`:

1. **Backend to Lambda** (`.github/workflows/cd-lambda.yml`)
2. **Backend to ECS** (`.github/workflows/cd.yml`)
3. **Frontend to Amplify** (`.github/workflows/cd-frontend.yml`)

#### Prerequisites

1. **GitHub Secrets** (Settings → Secrets and variables → Actions):
   - `AWS_IAM_ROLE_ARN`: ARN of IAM role for GitHub Actions (OIDC)
   - `GEN_AI_STUDIO_API_KEY`: Optional, for performance metrics

2. **AWS Resources** (one-time setup):
   - **For Lambda**: IAM role, API Gateway (see [Lambda Setup](AWS/lambda_setup.md))
   - **For ECS**: ECR repository, ECS cluster, ECS service, CloudWatch log group (see [ECS Setup](ECS_SETUP.md))
   - **For Frontend**: AWS Amplify app connected to repository

#### Deployment Process

1. **Push to `main` branch:**
   ```bash
   git push origin main
   ```

2. **GitHub Actions will:**
   - Run tests and linting
   - Build Docker image (ECS) or package Lambda function
   - Push to ECR (ECS) or update Lambda code
   - Deploy to ECS service or update Lambda function
   - Deploy frontend to Amplify (if configured)

3. **Monitor deployment:**
   - GitHub Actions: Check workflow runs in the Actions tab
   - AWS Console: Monitor ECS service updates or Lambda function updates
   - CloudWatch Logs: View application logs

### Manual Deployment

#### Backend to Lambda

1. **Package Lambda function:**
   ```bash
   chmod +x scripts/package-lambda.sh
   ./scripts/package-lambda.sh
   ```

2. **Deploy to Lambda:**
   ```bash
   aws lambda update-function-code \
     --function-name ece461-backend-lambda \
     --zip-file fileb://lambda-deployment.zip \
     --region us-east-2
   ```

#### Backend to ECS

1. **Build and push Docker image:**
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com
   
   # Build image
   docker build -t ece461-backend:latest .
   
   # Tag and push
   docker tag ece461-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/ece461-backend:latest
   docker push <ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/ece461-backend:latest
   ```

2. **Update ECS service:**
   ```bash
   aws ecs update-service \
     --cluster ece461-backend-cluster \
     --service ece461-backend-service \
     --force-new-deployment \
     --region us-east-2
   ```

#### Frontend

1. **Build frontend:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Deploy to Amplify:**
   - Use AWS Amplify Console to connect repository and enable auto-deploy
   - Or manually upload build artifacts to S3 bucket

### Accessing Deployed Services

#### Lambda + API Gateway

- **API URL**: `https://<API_ID>.execute-api.us-east-2.amazonaws.com`
- **Health Check**: `https://<API_ID>.execute-api.us-east-2.amazonaws.com/health`
- **API Docs**: `https://<API_ID>.execute-api.us-east-2.amazonaws.com/docs`

#### ECS/Fargate

- **API URL**: `http://<PUBLIC_IP>:8000` (IP changes on restart)
- **Health Check**: `http://<PUBLIC_IP>:8000/health`
- **API Docs**: `http://<PUBLIC_IP>:8000/docs`

To find the current ECS public IP, check CloudWatch Logs or use AWS CLI:
```bash
aws ecs describe-tasks \
  --cluster ece461-backend-cluster \
  --tasks $(aws ecs list-tasks --cluster ece461-backend-cluster --query 'taskArns[0]' --output text) \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text | xargs -I {} aws ec2 describe-network-interfaces \
  --network-interface-ids {} \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text
```

#### Frontend

- **Amplify URL**: Provided in Amplify Console (e.g., `https://main.xxxxx.amplifyapp.com`)
- **S3 Static Website**: `http://ece461-frontend.s3-website.us-east-2.amazonaws.com` (if using S3 hosting)

---

## Interacting with the Application

### Web Interface

1. **Browse Models**: Navigate to the home page to see all registered models with search and filtering
2. **Ingest Artifacts**: Use the "Ingest" page to add new models, datasets, or code from HuggingFace/GitHub URLs
3. **View Details**: Click on any artifact to see detailed information, ratings, lineage, and download options
4. **Health Monitoring**: Visit the `/health` page to view system health, metrics, and run download benchmarks

### API Endpoints

#### Health Endpoints

```bash
# Basic health check
GET /health

# Detailed component health
GET /health/components?window_minutes=60&include_timeline=true

# Start download benchmark
POST /health/download-benchmark/start
Body: { "target_url": "https://api.example.com" }  # Optional

# Get benchmark status
GET /health/download-benchmark/{job_id}
```

#### Artifact Endpoints

```bash
# Register a new artifact
POST /artifact/{type}  # type: model, dataset, or code
Body: {
  "url": "https://huggingface.co/model-name",
  "name": "Optional Name"
}

# Get artifact by ID
GET /artifacts/{type}/{id}

# List all artifacts of a type
GET /artifacts/{type}

# Search artifacts by regex
POST /artifact/byRegEx
Body: { "regex": ".*" }  # Match all

# Get model rating
GET /artifact/model/{id}/rate

# Download artifact
GET /artifact/{type}/{id}/download

# Delete artifact
DELETE /artifacts/{type}/{id}
```

#### Example API Calls

**Register a model:**
```bash
curl -X POST "https://your-api-url.com/artifact/model" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://huggingface.co/gpt2",
    "name": "GPT-2"
  }'
```

**List all models:**
```bash
curl "https://your-api-url.com/artifacts/model"
```

**Get model rating:**
```bash
curl "https://your-api-url.com/artifact/model/{id}/rate"
```

**Search artifacts:**
```bash
curl -X POST "https://your-api-url.com/artifact/byRegEx" \
  -H "Content-Type: application/json" \
  -d '{"regex": "gpt.*"}'
```

### Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: `https://your-api-url.com/docs`
- **ReDoc**: `https://your-api-url.com/redoc`

### Frontend API Client

The frontend uses a TypeScript API client (`frontend/lib/api.ts`) with functions:

```typescript
import { fetchArtifacts, ingestArtifact, fetchHealth } from '@/lib/api'

// Fetch all models
const models = await fetchArtifacts('model')

// Ingest a new model
const result = await ingestArtifact('model', 'https://huggingface.co/gpt2')

// Check health
const health = await fetchHealth()
```

---

## Development

### Project Structure

```
ECE461_Part2/
├── backend/              # FastAPI application
│   ├── api/routes/      # API endpoint handlers
│   ├── models/          # Pydantic data models
│   ├── services/        # Business logic (rating, lineage, metrics)
│   ├── storage/         # Data layer (DynamoDB, S3, memory)
│   └── middleware/      # Logging, rate limiting
├── frontend/            # Next.js application
│   ├── app/             # App router pages
│   ├── components/      # React components
│   └── lib/             # Utilities and API client
├── metrics/             # Quality metric calculators
├── .github/workflows/   # CI/CD pipelines
└── tests_main.py        # Test suite
```

### Running Tests

The project maintains **minimum 60% test coverage** (enforced in CI).

**Backend tests:**
```bash
# Run all tests
pytest tests_main.py -v

# Run with coverage (CI requires 60% minimum)
coverage run -m pytest tests_main.py
coverage report -m --fail-under=60
```

**Integration tests:**
```bash
# PowerShell integration tests
pwsh ./integration_tests.ps1
```

### Code Quality

The project enforces code quality via CI/CD pipelines (`.github/workflows/python-lint.yml`):

- **Python**: `flake8`, `isort`, `mypy`
- **TypeScript**: `eslint` (run locally with `cd frontend && npm run lint`)

### Adding New Features

1. **Backend API endpoint**: Add route in `backend/api/routes/`
2. **Data model**: Define Pydantic model in `backend/models/`
3. **Business logic**: Implement service in `backend/services/`
4. **Frontend component**: Create React component in `frontend/components/`
5. **Tests**: Add test cases to `tests_main.py` or frontend test files

---

## Additional Resources

- **AWS Setup Guide**: [AWS/AWS_setup.md](AWS/AWS_setup.md)
- **ECS Deployment Guide**: [ECS_SETUP.md](ECS_SETUP.md)
- **Lambda Deployment Guide**: [AWS/lambda_setup.md](AWS/lambda_setup.md)
- **API Documentation**: Available at `/docs` endpoint when backend is running

---

## Acknowledgments

**Original Team Members (Team 4, Fall 2025):** Hilal B Tasdemir, Georgia Griffin, Navya Datla, Sai Ganadavarapu

This project is built upon the foundational codebase created by the original team members, which included:
- Initial 7 quality metrics (bus factor, code quality, data quality, license compliance, performance claims, ramp-up time, reproducibility)
- Backend concurrency and early performance optimizations
- Core artifact ingestion and storage systems

The current Team 3 forked and extended this foundational work to add additional features including the full-stack web application, AWS deployment infrastructure, and expanded metric capabilities.

---

## License

MIT License

---

## Support

For issues or questions, please open an issue in the [repository](https://github.com/Anjali-Vanamala/ECE461_Part2) or contact the team members.
