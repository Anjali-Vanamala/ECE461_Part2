# ECE30861_Team4

A Github repository made for the ECE 30861 Project at Purdue University in Fall 2025.
Members are Hilal B Tasdemir, Georgia Griffin, Navya Datla, and Sai Ganadavarapu 

Hilal Tasdemir

Georgia Griffin

Sai Gandavarapu

Navya Datla

---

Deployment (Delivery 1)
-----------------------

# TODO: Replace <ACCOUNT_ID> placeholder in .github/workflows/cd.yml with actual AWS account ID
# TODO: Complete AWS setup: ECR repo, Lambda function, API Gateway, OIDC role
# TODO: Add OpenAPI specification for API documentation
# TODO: Add monitoring dashboard and CloudWatch metrics
# TODO: Consider adding authentication for production use

API Endpoints (Lambda + API Gateway)
- POST `/rate`: body `{ "lines": ["<code_url>,<dataset_url>,<model_url>"] }` → returns `{"results": [...]}`
- GET `/health`: returns `{ "status": "ok", "service": "ece461-part2", ... }`

Runtime
- AWS Region: `us-east-1`
- No auth initially (public for grading)
- Logs: CloudWatch; app writes to `LOG_FILE=/tmp/error_logs.log` when `LOG_LEVEL` set

Continuous Deployment
- Auto-deploy on push to `main`
- Manual deploy via GitHub Actions “CD - Deploy Lambda Container (API Gateway integration manual)” → Run workflow

One-time AWS setup (outside this repo)
1) Create ECR repo `ece461-part2`
2) Create Lambda function `ece461-part2-lambda` (container image), set env:
   - `LOG_LEVEL=1`
   - `LOG_FILE=/tmp/error_logs.log`
3) Create public API Gateway (HTTP API) integrating to the Lambda; map routes:
   - GET `/health` → Lambda
   - POST `/rate` → Lambda
4) Configure GitHub OIDC role `github-actions-deploy-role` with permissions to push to ECR and update Lambda. Set role ARN in `.github/workflows/cd.yml`.

Local usage (CLI)
```
export LOG_LEVEL=1
export LOG_FILE=$(pwd)/error_logs.log
python input.py sample_input.txt
```

Invoke (API example)
```
POST https://<api-id>.execute-api.us-east-1.amazonaws.com/rate
Content-Type: application/json

{
  "lines": [
    "https://github.com/google-research/bert,https://huggingface.co/datasets/bookcorpus/bookcorpus,https://huggingface.co/google-bert/bert-base-uncased"
  ]
}
```