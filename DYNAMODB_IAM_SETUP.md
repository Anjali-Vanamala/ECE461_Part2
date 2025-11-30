# DynamoDB IAM Permissions Setup

## Overview

Your FastAPI application needs DynamoDB permissions to read/write artifacts. Currently, your ECS task definition only has an `executionRoleArn` (no `taskRoleArn`), which means the application uses the execution role for AWS operations.

## Option 1: Add DynamoDB Permissions to Execution Role (Simpler)

Add DynamoDB permissions to the existing `ecsTaskExecutionRole`:

### Step 1: Create IAM Policy for DynamoDB

Save this as `dynamodb-artifacts-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-2:<ACCOUNT_ID>:table/artifacts_metadata",
        "arn:aws:dynamodb:us-east-2:<ACCOUNT_ID>:table/artifacts_metadata/index/*"
      ]
    }
  ]
}
```

**Important**: Replace `<ACCOUNT_ID>` with your actual AWS account ID.

### Step 2: Create and Attach the Policy

```bash
# Create the policy
aws iam create-policy \
  --policy-name DynamoDBArtifactsAccess \
  --policy-document file://dynamodb-artifacts-policy.json \
  --description "Allows ECS tasks to access artifacts_metadata DynamoDB table"

# Get the policy ARN (save this output)
aws iam list-policies --query 'Policies[?PolicyName==`DynamoDBArtifactsAccess`].Arn' --output text

# Attach the policy to the execution role
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/DynamoDBArtifactsAccess
```

**Note**: Replace `<ACCOUNT_ID>` with your actual AWS account ID in the attach command.

### Step 3: Verify

```bash
aws iam list-attached-role-policies --role-name ecsTaskExecutionRole
```

You should see `DynamoDBArtifactsAccess` in the list.

---

## Option 2: Create Separate Task Role (Better Practice - Recommended)

A task role is specifically for your application code to access AWS services, while the execution role is only for ECS to pull images and write logs.

### Step 1: Create Task Role

```bash
# Trust policy (same as execution role)
cat > task-role-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document file://task-role-trust-policy.json \
  --description "IAM role for ECS tasks to access application AWS services"
```

### Step 2: Attach DynamoDB Policy

Use the same policy from Option 1, but attach it to `ecsTaskRole`:

```bash
# Create the policy (same as Option 1)
aws iam create-policy \
  --policy-name DynamoDBArtifactsAccess \
  --policy-document file://dynamodb-artifacts-policy.json

# Attach to task role
aws iam attach-role-policy \
  --role-name ecsTaskRole \
  --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/DynamoDBArtifactsAccess
```

### Step 3: Update Task Definition

Add `taskRoleArn` to your task definition (`task-definition-mvp.json`):

```json
{
  "family": "ece461-backend-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole",
  ...
}
```

Then register the updated task definition:

```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition-mvp.json \
  --region us-east-2
```

Then update the service to use the new task definition revision.

---

## Required DynamoDB Permissions Explained

| Permission | Purpose |
|------------|---------|
| `PutItem` | Save new artifacts |
| `GetItem` | Retrieve artifact by ID |
| `UpdateItem` | Update existing artifacts (including ratings) |
| `DeleteItem` | Delete artifacts |
| `Query` | Query artifacts by type or other indexed attributes |
| `Scan` | Scan all artifacts (used for regex search and queries) |
| `BatchGetItem` | Efficiently retrieve multiple artifacts |
| `BatchWriteItem` | Efficiently write multiple artifacts |

---

## Which Option Should You Choose?

- **Option 1** is faster to set up if you want to test immediately
- **Option 2** is better practice for production and security isolation

Both will work for your application!

