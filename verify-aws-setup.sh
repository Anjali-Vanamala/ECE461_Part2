#!/bin/bash
# AWS ECS Setup Verification Script
# Run this in AWS CloudShell or with AWS CLI configured
# Last Updated: November 2, 2025

REGION="us-east-2"
# Auto-detect account ID (or replace with your account ID)
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || echo "YOUR_ACCOUNT_ID")

echo "=========================================="
echo "AWS ECS Setup Verification"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_passed=0
check_failed=0

# Function to check and report
check_resource() {
    local name=$1
    local command=$2
    local expected_pattern=$3
    
    echo -n "Checking $name... "
    if eval "$command" | grep -q "$expected_pattern" 2>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((check_passed++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((check_failed++))
        return 1
    fi
}

echo "=== 1. ECR Repository ==="
if aws ecr describe-repositories --repository-names ece461-backend --region $REGION --query 'repositories[0].repositoryUri' --output text 2>/dev/null | grep -q "ece461-backend"; then
    echo -e "${GREEN}✓ ECR repository 'ece461-backend' exists${NC}"
    ECR_URI=$(aws ecr describe-repositories --repository-names ece461-backend --region $REGION --query 'repositories[0].repositoryUri' --output text)
    echo "  URI: $ECR_URI"
    ((check_passed++))
else
    echo -e "${RED}✗ ECR repository 'ece461-backend' NOT FOUND${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 2. ECS Cluster ==="
if aws ecs describe-clusters --clusters ece461-backend-cluster --region $REGION --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo -e "${GREEN}✓ ECS cluster 'ece461-backend-cluster' is ACTIVE${NC}"
    ((check_passed++))
else
    echo -e "${RED}✗ ECS cluster 'ece461-backend-cluster' NOT FOUND or NOT ACTIVE${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 3. CloudWatch Log Group ==="
if aws logs describe-log-groups --log-group-name-prefix "/ecs/ece461-backend-task" --region $REGION --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q "ece461-backend-task"; then
    echo -e "${GREEN}✓ CloudWatch log group '/ecs/ece461-backend-task' exists${NC}"
    ((check_passed++))
else
    echo -e "${RED}✗ CloudWatch log group '/ecs/ece461-backend-task' NOT FOUND${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 4. ECS Task Definition ==="
TASK_DEF=$(aws ecs describe-task-definition --task-definition ece461-backend-task --region $REGION --query 'taskDefinition.[family,status,revision]' --output text 2>/dev/null)
if [ $? -eq 0 ] && echo "$TASK_DEF" | grep -q "ece461-backend-task"; then
    echo -e "${GREEN}✓ Task definition 'ece461-backend-task' exists${NC}"
    echo "  Status: $(echo $TASK_DEF | awk '{print $2}')"
    echo "  Revision: $(echo $TASK_DEF | awk '{print $3}')"
    
    # Check if execution role is correct
    EXEC_ROLE=$(aws ecs describe-task-definition --task-definition ece461-backend-task --region $REGION --query 'taskDefinition.executionRoleArn' --output text)
    if echo "$EXEC_ROLE" | grep -q "ecsTaskExecutionRole"; then
        echo -e "  ${GREEN}✓ Execution role configured: $EXEC_ROLE${NC}"
    else
        echo -e "  ${YELLOW}⚠ Execution role check: $EXEC_ROLE${NC}"
    fi
    
    # Check log configuration
    LOG_GROUP=$(aws ecs describe-task-definition --task-definition ece461-backend-task --region $REGION --query 'taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-group"' --output text)
    if echo "$LOG_GROUP" | grep -q "ece461-backend-task"; then
        echo -e "  ${GREEN}✓ Log group configured: $LOG_GROUP${NC}"
    else
        echo -e "  ${YELLOW}⚠ Log group: $LOG_GROUP${NC}"
    fi
    
    ((check_passed++))
else
    echo -e "${RED}✗ Task definition 'ece461-backend-task' NOT FOUND${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 5. ECS Service ==="
SERVICE_STATUS=$(aws ecs describe-services --cluster ece461-backend-cluster --services ece461-backend-service --region $REGION --query 'services[0].status' --output text 2>/dev/null)
if [ "$SERVICE_STATUS" = "ACTIVE" ]; then
    echo -e "${GREEN}✓ ECS service 'ece461-backend-service' is ACTIVE${NC}"
    
    DESIRED=$(aws ecs describe-services --cluster ece461-backend-cluster --services ece461-backend-service --region $REGION --query 'services[0].desiredCount' --output text)
    RUNNING=$(aws ecs describe-services --cluster ece461-backend-cluster --services ece461-backend-service --region $REGION --query 'services[0].runningCount' --output text)
    echo "  Desired: $DESIRED, Running: $RUNNING"
    
    if [ "$RUNNING" = "0" ]; then
        echo -e "  ${YELLOW}⚠ No tasks running (expected if no image in ECR yet)${NC}"
    fi
    
    ((check_passed++))
else
    echo -e "${RED}✗ ECS service 'ece461-backend-service' NOT FOUND or NOT ACTIVE${NC}"
    echo "  Status: $SERVICE_STATUS"
    ((check_failed++))
fi
echo ""

echo "=== 6. Security Group ==="
SG_COUNT=$(aws ec2 describe-security-groups --region $REGION --filters "Name=group-name,Values=ece461-backend-ecs-sg" --query 'length(SecurityGroups)' --output text 2>/dev/null || echo "0")
if [ "$SG_COUNT" -gt 0 ]; then
    SG_ID=$(aws ec2 describe-security-groups --region $REGION --filters "Name=group-name,Values=ece461-backend-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text)
    echo -e "${GREEN}✓ Security group 'ece461-backend-ecs-sg' exists${NC}"
    echo "  ID: $SG_ID"
    
    # Check port 8000 rule
    PORT_8000=$(aws ec2 describe-security-groups --group-ids $SG_ID --region $REGION --query 'SecurityGroups[0].IpPermissions[?ToPort==`8000`]' --output json 2>/dev/null)
    if [ "$PORT_8000" != "[]" ] && [ -n "$PORT_8000" ]; then
        echo -e "  ${GREEN}✓ Port 8000 ingress rule configured${NC}"
    else
        echo -e "  ${RED}✗ Port 8000 ingress rule NOT FOUND${NC}"
        ((check_failed++))
    fi
    
    ((check_passed++))
else
    echo -e "${RED}✗ Security group 'ece461-backend-ecs-sg' NOT FOUND${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 7. IAM Roles ==="

# Check ECS Task Execution Role
EXEC_ROLE_EXISTS=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.RoleName' --output text 2>/dev/null || echo "")
if [ "$EXEC_ROLE_EXISTS" = "ecsTaskExecutionRole" ]; then
    echo -e "${GREEN}✓ ECS Task Execution Role 'ecsTaskExecutionRole' exists${NC}"
    EXEC_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text)
    echo "  ARN: $EXEC_ROLE_ARN"
    ((check_passed++))
else
    echo -e "${RED}✗ ECS Task Execution Role 'ecsTaskExecutionRole' NOT FOUND${NC}"
    ((check_failed++))
fi

# Check GitHub Actions Role
GITHUB_ROLE_EXISTS=$(aws iam get-role --role-name github-actions-deploy-role --query 'Role.RoleName' --output text 2>/dev/null || echo "")
if [ "$GITHUB_ROLE_EXISTS" = "github-actions-deploy-role" ]; then
    echo -e "${GREEN}✓ GitHub Actions Role 'github-actions-deploy-role' exists${NC}"
    GITHUB_ROLE_ARN=$(aws iam get-role --role-name github-actions-deploy-role --query 'Role.Arn' --output text)
    echo "  ARN: $GITHUB_ROLE_ARN"
    echo -e "  ${YELLOW}⚠ Add this ARN as GitHub secret: AWS_IAM_ROLE_ARN${NC}"
    
    # Check trust policy (OIDC)
    TRUST_POLICY=$(aws iam get-role --role-name github-actions-deploy-role --query 'Role.AssumeRolePolicyDocument' --output json 2>/dev/null)
    if echo "$TRUST_POLICY" | grep -q "token.actions.githubusercontent.com"; then
        echo -e "  ${GREEN}✓ OIDC trust policy configured for GitHub${NC}"
    else
        echo -e "  ${RED}✗ OIDC trust policy NOT configured correctly${NC}"
        ((check_failed++))
    fi
    
    # Check inline policy
    POLICY_EXISTS=$(aws iam list-role-policies --role-name github-actions-deploy-role --query 'length(PolicyNames)' --output text 2>/dev/null || echo "0")
    if [ "$POLICY_EXISTS" -gt 0 ]; then
        echo -e "  ${GREEN}✓ Permission policy attached${NC}"
    else
        echo -e "  ${RED}✗ Permission policy NOT attached${NC}"
        ((check_failed++))
    fi
    
    ((check_passed++))
else
    echo -e "${RED}✗ GitHub Actions Role 'github-actions-deploy-role' NOT FOUND${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 8. OIDC Provider ==="
OIDC_PROVIDER=$(aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[?contains(Arn, `token.actions.githubusercontent.com`)]' --output json 2>/dev/null)
if [ "$OIDC_PROVIDER" != "[]" ] && [ -n "$OIDC_PROVIDER" ]; then
    echo -e "${GREEN}✓ GitHub OIDC provider configured${NC}"
    ((check_passed++))
else
    echo -e "${YELLOW}⚠ GitHub OIDC provider NOT FOUND (may need to create)${NC}"
    ((check_failed++))
fi
echo ""

echo "=== 9. VPC and Networking ==="
VPC_COUNT=$(aws ec2 describe-vpcs --region $REGION --filters "Name=isDefault,Values=true" --query 'length(Vpcs)' --output text)
if [ "$VPC_COUNT" -gt 0 ]; then
    VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
    echo -e "${GREEN}✓ Default VPC found${NC}"
    echo "  VPC ID: $VPC_ID"
    
    SUBNET_COUNT=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'length(Subnets)' --output text)
    if [ "$SUBNET_COUNT" -ge 2 ]; then
        echo -e "  ${GREEN}✓ Found $SUBNET_COUNT subnets (need at least 2)${NC}"
    else
        echo -e "  ${YELLOW}⚠ Only $SUBNET_COUNT subnet(s) found (need at least 2)${NC}"
    fi
    
    ((check_passed++))
else
    echo -e "${YELLOW}⚠ No default VPC found (you'll need to specify VPC ID)${NC}"
fi
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $check_passed${NC}"
echo -e "${RED}Failed: $check_failed${NC}"
echo ""

if [ $check_failed -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ All checks passed! Ready for deployment. ✓✓✓${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Ensure GitHub secret 'AWS_IAM_ROLE_ARN' is set"
    echo "2. Push to your branch or trigger workflow manually"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review and fix issues above.${NC}"
    exit 1
fi

