# S3 Frontend Deployment Setup (Quick Guide)

**Last Updated:** November 3, 2025

This guide sets up S3 static website hosting for the frontend.

## Steps to Complete

### 1. Create S3 Bucket

```bash
aws s3 mb s3://ece461-frontend --region us-east-2
```

### 2. Enable Static Website Hosting

```bash
cat > website-config.json << 'EOF'
{
  "IndexDocument": {
    "Suffix": "index.html"
  },
  "ErrorDocument": {
    "Key": "index.html"
  }
}
EOF

aws s3api put-bucket-website \
  --bucket ece461-frontend \
  --website-configuration file://website-config.json \
  --region us-east-2
```

### 3. Allow Public Access (Do This FIRST!)

**⚠️ IMPORTANT**: You must disable Block Public Access BEFORE applying the bucket policy, otherwise you'll get an `AccessDenied` error.

```bash
aws s3api put-public-access-block \
  --bucket ece461-frontend \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
  --region us-east-2
```

### 4. Configure Bucket Policy for Public Read Access

Now create and apply the bucket policy:

```bash
cat > s3-bucket-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::ece461-frontend/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket ece461-frontend \
  --policy file://s3-bucket-policy.json \
  --region us-east-2
```

### 5. Update GitHub Actions IAM Role for S3 Access

Add S3 permissions to your existing `github-actions-deploy-role`:

**Option A: Automatic (Recommended - uses jq):**

```bash
# Get current policy
aws iam get-role-policy \
  --role-name github-actions-deploy-role \
  --policy-name GitHubActionsDeployPolicy \
  --query 'PolicyDocument' \
  --output json > current-policy.json

# Add S3 statement using jq (automatically adds to Statement array)
jq '.Statement += [{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:DeleteObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::ece461-frontend",
    "arn:aws:s3:::ece461-frontend/*"
  ]
}]' current-policy.json > updated-policy.json

# Update the policy
aws iam put-role-policy \
  --role-name github-actions-deploy-role \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://updated-policy.json
```

**Option B: Manual (if jq doesn't work):**

1. Get the current policy:
```bash
aws iam get-role-policy \
  --role-name github-actions-deploy-role \
  --policy-name GitHubActionsDeployPolicy \
  --query 'PolicyDocument' \
  --output json > current-policy.json
```

2. Open `current-policy.json` and find the `"Statement": [...]` array. Add this new statement inside that array (before the closing `]`):

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:DeleteObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::ece461-frontend",
    "arn:aws:s3:::ece461-frontend/*"
  ]
}
```

3. Save the file, then update:
```bash
aws iam put-role-policy \
  --role-name github-actions-deploy-role \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://current-policy.json
```

### 6. Verify Setup

```bash
# Check bucket exists
aws s3 ls s3://ece461-frontend --region us-east-2

# Get website endpoint
aws s3api get-bucket-website \
  --bucket ece461-frontend \
  --region us-east-2 \
  --query 'WebsiteConfiguration' \
  --output json

# Get bucket policy
aws s3api get-bucket-policy \
  --bucket ece461-frontend \
  --region us-east-2 \
  --query 'Policy' \
  --output text | jq .
```

## Accessing Your Frontend

After deployment, your frontend will be accessible at:
```
http://ece461-frontend.s3-website.us-east-2.amazonaws.com
```

Or if you set up CloudFront:
```
https://your-cloudfront-distribution.cloudfront.net
```

## Next Steps

1. Push code to `main` branch
2. GitHub Actions will build and deploy to S3
3. Access your frontend via the S3 website endpoint

## Optional: CloudFront Setup (For Production)

For better performance and HTTPS, set up CloudFront:

```bash
# Create CloudFront distribution pointing to S3 bucket
aws cloudfront create-distribution \
  --origin-domain-name ece461-frontend.s3-website.us-east-2.amazonaws.com \
  --default-root-object index.html \
  --region us-east-2
```

## Troubleshooting

1. **403 Forbidden**: Check bucket policy and public access block settings
2. **404 Not Found**: Ensure `index.html` exists in the bucket
3. **Deployment fails**: Verify IAM role has S3 permissions
4. **Files not updating**: Check CloudFront cache if using CDN

