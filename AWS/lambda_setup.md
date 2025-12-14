# Lambda Setup - AWS CLI Commands

**Region:** us-east-2 (Ohio)  
**Function Name:** ece461-backend-lambda  
**Runtime:** Python 3.11

> ⚠️ **Note:** The GitHub Actions workflow can create the Lambda function automatically, but you need to set up the IAM role and API Gateway first.

---

## Quick Reference - Important URLs & Info

### API Gateway URL
```bash
# Get your API Gateway URL
API_ID=$(aws apigatewayv2 get-apis \
  --region us-east-2 \
  --query "Items[?Name=='ece461-backend-api'].ApiId" \
  --output text)

API_URL="https://${API_ID}.execute-api.us-east-2.amazonaws.com"
echo "API URL: $API_URL"
```

**Current API URL:** `https://6d924g49aa.execute-api.us-east-2.amazonaws.com`

### Test Endpoints
```bash
# Health check
curl "https://6d924g49aa.execute-api.us-east-2.amazonaws.com/health"

# Root endpoint
curl "https://6d924g49aa.execute-api.us-east-2.amazonaws.com/"

# List models
curl "https://6d924g49aa.execute-api.us-east-2.amazonaws.com/artifacts/model"
```

### Lambda Function Info
- **Function Name:** `ece461-backend-lambda`
- **Handler:** `backend.lambda_handler.handler`
- **Runtime:** `python3.11`
- **Timeout:** 900 seconds (15 minutes)
- **Memory:** 1024 MB
- **Region:** `us-east-2`

**View in Console:** https://console.aws.amazon.com/lambda/home?region=us-east-2#/functions/ece461-backend-lambda

### Environment Variables
```bash
# Current environment variables
aws lambda get-function-configuration \
  --function-name ece461-backend-lambda \
  --region us-east-2 \
  --query 'Environment.Variables' \
  --output json
```

**Required Variables:**
- `COMPUTE_BACKEND=lambda` (set automatically)
- `LOG_FILE=/tmp/error_logs.log` (for logger.py)
- `LOG_LEVEL=1` (0=silent, 1=info, 2=debug)

**Optional Variables:**
- `STORAGE_BACKEND=dynamodb` or `rds_postgres` (default: in-memory)
- `USE_DYNAMODB=1` (legacy, use STORAGE_BACKEND instead)

### View Logs
```bash
# Tail logs in real-time
aws logs tail /aws/lambda/ece461-backend-lambda --follow --region us-east-2

# Get recent logs
aws logs tail /aws/lambda/ece461-backend-lambda --since 10m --region us-east-2
```

**View in Console:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-2#logsV2:log-groups/log-group/%2Faws%2Flambda%2Fece461-backend-lambda

---

## Step 1: Create IAM Role for Lambda

Create a trust policy file (no editor needed):

```bash
cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

Create the IAM role:

```bash
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --region us-east-2
```

Attach basic Lambda execution policy:

```bash
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
  --region us-east-2
```

Attach DynamoDB access policy (for metadata storage):

```bash
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess \
  --region us-east-2
```

Attach S3 access policy (for file storage):

```bash
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --region us-east-2
```

Get the role ARN (save this for later):

```bash
aws iam get-role --role-name lambda-execution-role --query 'Role.Arn' --output text --region us-east-2
```

---

## Step 2: Create API Gateway (HTTP API - Recommended)

Create HTTP API:

```bash
aws apigatewayv2 create-api \
  --name ece461-backend-api \
  --protocol-type HTTP \
  --cors-configuration AllowOrigins="*",AllowMethods="*",AllowHeaders="*" \
  --region us-east-2 \
  --output json > /tmp/api-info.json
```

Get API ID:

```bash
API_ID=$(cat /tmp/api-info.json | grep -o '"ApiId":"[^"]*' | cut -d'"' -f4)
echo "API ID: $API_ID"
echo "API_ID=$API_ID" > /tmp/api-id.txt
```

Create integration with Lambda (replace with your function name after it's created):

```bash
API_ID=$(cat /tmp/api-id.txt | cut -d'=' -f2)
FUNCTION_NAME="ece461-backend-lambda"

# Get Lambda function ARN (will fail if function doesn't exist yet - that's OK)
FUNCTION_ARN=$(aws lambda get-function \
  --function-name $FUNCTION_NAME \
  --region us-east-2 \
  --query 'Configuration.FunctionArn' \
  --output text 2>/dev/null || echo "")

if [ -z "$FUNCTION_ARN" ]; then
  echo "⚠️  Lambda function not created yet. Run this after deploying Lambda:"
  echo "   See Step 3 below"
else
  # Create integration
  aws apigatewayv2 create-integration \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-method ANY \
    --integration-uri "arn:aws:apigateway:us-east-2:lambda:path/2015-03-31/functions/$FUNCTION_ARN/invocations" \
    --payload-format-version "2.0" \
    --region us-east-2 \
    --output json > /tmp/integration-info.json
  
  INTEGRATION_ID=$(cat /tmp/integration-info.json | grep -o '"IntegrationId":"[^"]*' | cut -d'"' -f4)
  echo "Integration ID: $INTEGRATION_ID"
fi
```

Create route (catch-all):

```bash
API_ID=$(cat /tmp/api-id.txt | cut -d'=' -f2)
INTEGRATION_ID=$(cat /tmp/integration-info.json | grep -o '"IntegrationId":"[^"]*' | cut -d'"' -f4)

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "\$default" \
  --target "integrations/$INTEGRATION_ID" \
  --region us-east-2
```

Create stage (for deployment):

```bash
API_ID=$(cat /tmp/api-id.txt | cut -d'=' -f2)

aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name \$default \
  --auto-deploy \
  --region us-east-2
```

---

## Step 3: Grant API Gateway Permission to Invoke Lambda

After Lambda function is created (by GitHub Actions or manually), grant API Gateway permission:

```bash
API_ID=$(cat /tmp/api-id.txt | cut -d'=' -f2)
FUNCTION_NAME="ece461-backend-lambda"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-2:$ACCOUNT_ID:$API_ID/*/*" \
  --region us-east-2
```

---

## Step 4: Get API Gateway URL

Get your API endpoint URL:

```bash
API_ID=$(cat /tmp/api-id.txt | cut -d'=' -f2)
echo "API Gateway URL: https://$API_ID.execute-api.us-east-2.amazonaws.com"
echo "Test endpoint: https://$API_ID.execute-api.us-east-2.amazonaws.com/health"
```

---

## Verification Script

Run this to verify everything is set up correctly:

```bash
#!/bin/bash
set -e

REGION="us-east-2"
FUNCTION_NAME="ece461-backend-lambda"
ROLE_NAME="lambda-execution-role"

echo "🔍 Verifying Lambda Setup..."
echo ""

# Check IAM Role
echo "1. Checking IAM Role..."
if aws iam get-role --role-name $ROLE_NAME --region $REGION >/dev/null 2>&1; then
  ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)
  echo "   ✅ Role exists: $ROLE_ARN"
else
  echo "   ❌ Role not found: $ROLE_NAME"
  exit 1
fi

# Check Lambda Function
echo "2. Checking Lambda Function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
  FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION)
  FUNCTION_STATUS=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.State' --output text --region $REGION)
  echo "   ✅ Function exists: $FUNCTION_ARN"
  echo "   ✅ Status: $FUNCTION_STATUS"
else
  echo "   ⚠️  Function not found: $FUNCTION_NAME"
  echo "   (This is OK if you haven't deployed yet - GitHub Actions will create it)"
fi

# Check API Gateway
echo "3. Checking API Gateway..."
API_ID=$(aws apigatewayv2 get-apis \
  --region $REGION \
  --query "Items[?Name=='ece461-backend-api'].ApiId" \
  --output text 2>/dev/null || echo "")

if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
  echo "   ✅ API Gateway found: $API_ID"
  API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com"
  echo "   ✅ API URL: $API_URL"
  
  # Test health endpoint (if Lambda is deployed)
  if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "4. Testing API endpoint..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" 2>/dev/null || echo "000")
    if [ "$RESPONSE" = "200" ]; then
      echo "   ✅ Health check passed (HTTP $RESPONSE)"
    else
      echo "   ⚠️  Health check returned HTTP $RESPONSE (may need to wait for deployment)"
    fi
  else
    echo "4. ⚠️  Skipping API test (Lambda function not deployed yet)"
  fi
else
  echo "   ❌ API Gateway not found: ece461-backend-api"
  exit 1
fi

echo ""
echo "✅ Verification complete!"
echo ""
echo "📝 Next Steps:"
echo "   1. Push to main branch to trigger Lambda deployment"
echo "   2. After deployment, run the permission command in Step 3"
echo "   3. Test your API: curl $API_URL/health"
```

Save and run the verification script:

```bash
cat > verify-lambda.sh << 'EOF'
#!/bin/bash
set -e

REGION="us-east-2"
FUNCTION_NAME="ece461-backend-lambda"
ROLE_NAME="lambda-execution-role"

echo "🔍 Verifying Lambda Setup..."
echo ""

# Check IAM Role
echo "1. Checking IAM Role..."
if aws iam get-role --role-name $ROLE_NAME --region $REGION >/dev/null 2>&1; then
  ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --region $REGION)
  echo "   ✅ Role exists: $ROLE_ARN"
else
  echo "   ❌ Role not found: $ROLE_NAME"
  exit 1
fi

# Check Lambda Function
echo "2. Checking Lambda Function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
  FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION)
  FUNCTION_STATUS=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.State' --output text --region $REGION)
  echo "   ✅ Function exists: $FUNCTION_ARN"
  echo "   ✅ Status: $FUNCTION_STATUS"
else
  echo "   ⚠️  Function not found: $FUNCTION_NAME"
  echo "   (This is OK if you haven't deployed yet - GitHub Actions will create it)"
fi

# Check API Gateway
echo "3. Checking API Gateway..."
API_ID=$(aws apigatewayv2 get-apis \
  --region $REGION \
  --query "Items[?Name=='ece461-backend-api'].ApiId" \
  --output text 2>/dev/null || echo "")

if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
  echo "   ✅ API Gateway found: $API_ID"
  API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com"
  echo "   ✅ API URL: $API_URL"
  
  # Test health endpoint (if Lambda is deployed)
  if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "4. Testing API endpoint..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" 2>/dev/null || echo "000")
    if [ "$RESPONSE" = "200" ]; then
      echo "   ✅ Health check passed (HTTP $RESPONSE)"
    else
      echo "   ⚠️  Health check returned HTTP $RESPONSE (may need to wait for deployment)"
    fi
  else
    echo "4. ⚠️  Skipping API test (Lambda function not deployed yet)"
  fi
else
  echo "   ❌ API Gateway not found: ece461-backend-api"
  exit 1
fi

echo ""
echo "✅ Verification complete!"
echo ""
echo "📝 Next Steps:"
if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
  echo "   1. Push to main branch to trigger Lambda deployment"
  echo "   2. After deployment, run the permission command in Step 3"
  echo "   3. Test your API: curl $API_URL/health"
else
  echo "   1. Complete API Gateway setup (Step 2)"
  echo "   2. Push to main branch to trigger Lambda deployment"
fi
EOF

chmod +x verify-lambda.sh
./verify-lambda.sh
```

---

## Quick Reference

| Resource | Name | Command to Get Info |
|----------|------|---------------------|
| **IAM Role** | `lambda-execution-role` | `aws iam get-role --role-name lambda-execution-role --region us-east-2` |
| **Lambda Function** | `ece461-backend-lambda` | `aws lambda get-function --function-name ece461-backend-lambda --region us-east-2` |
| **API Gateway** | `ece461-backend-api` | `aws apigatewayv2 get-apis --region us-east-2 --query "Items[?Name=='ece461-backend-api']"` |

---

## Troubleshooting

**Issue: "Role not found" when creating Lambda**
- Solution: Make sure Step 1 completed successfully. Check with: `aws iam get-role --role-name lambda-execution-role --region us-east-2`

**Issue: "Function not found" in verification**
- Solution: This is normal if you haven't deployed yet. Push to main branch to trigger GitHub Actions deployment.

**Issue: API Gateway returns 500/502 errors**
- Solution: Make sure you ran Step 3 (grant API Gateway permission to invoke Lambda)

**Issue: CORS errors**
- Solution: API Gateway CORS is configured, but also check Lambda function CORS settings in `backend/app.py`

---

## Cleanup (if needed)

To delete everything:

```bash
# Delete Lambda function
aws lambda delete-function --function-name ece461-backend-lambda --region us-east-2

# Delete API Gateway
API_ID=$(aws apigatewayv2 get-apis --region us-east-2 --query "Items[?Name=='ece461-backend-api'].ApiId" --output text)
aws apigatewayv2 delete-api --api-id $API_ID --region us-east-2

# Delete IAM role (detach policies first)
aws iam detach-role-policy --role-name lambda-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --region us-east-2
aws iam detach-role-policy --role-name lambda-execution-role --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess --region us-east-2
aws iam detach-role-policy --role-name lambda-execution-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess --region us-east-2
aws iam delete-role --role-name lambda-execution-role --region us-east-2
```
