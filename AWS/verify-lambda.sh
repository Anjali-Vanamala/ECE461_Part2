#!/bin/bash
# Verification script for Lambda setup
# Run this after completing the setup steps in lambda_setup.md

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
  echo "   Run Step 1 from lambda_setup.md"
  exit 1
fi

# Check Lambda Function
echo "2. Checking Lambda Function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
  FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION)
  FUNCTION_STATUS=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.State' --output text --region $REGION)
  FUNCTION_RUNTIME=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.Runtime' --output text --region $REGION)
  echo "   ✅ Function exists: $FUNCTION_ARN"
  echo "   ✅ Status: $FUNCTION_STATUS"
  echo "   ✅ Runtime: $FUNCTION_RUNTIME"
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
      echo ""
      echo "   Test command: curl $API_URL/health"
    else
      echo "   ⚠️  Health check returned HTTP $RESPONSE"
      echo "   (May need to wait for deployment or check API Gateway integration)"
    fi
  else
    echo "4. ⚠️  Skipping API test (Lambda function not deployed yet)"
  fi
else
  echo "   ❌ API Gateway not found: ece461-backend-api"
  echo "   Run Step 2 from lambda_setup.md"
  exit 1
fi

echo ""
echo "✅ Verification complete!"
echo ""
echo "📝 Next Steps:"
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
  if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
    echo "   1. Test your API: curl $API_URL/health"
    echo "   2. Check Lambda logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
  else
    echo "   1. Complete API Gateway setup (Step 2 from lambda_setup.md)"
  fi
else
  echo "   1. Push to main branch to trigger Lambda deployment via GitHub Actions"
  echo "   2. After deployment, grant API Gateway permission (Step 3 from lambda_setup.md)"
  echo "   3. Test your API: curl $API_URL/health"
fi
