# RDS PostgreSQL Setup - AWS CLI Commands

**Region:** us-east-2 (Ohio)  
**Database Engine:** PostgreSQL 15.x  
**Instance Class:** db.t3.micro (free tier eligible)  
**Database Name:** artifacts_db

> ⚠️ **Note:** RDS instances take 5-10 minutes to create. Make sure you have appropriate AWS permissions.

---

## Step 1: Create Security Group for RDS

Get your current IP address (for local development access):

```bash
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: $MY_IP"
```

Create security group:

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name ece461-rds-sg \
  --description "Security group for ECE461 RDS PostgreSQL instance" \
  --region us-east-2 \
  --query 'GroupId' \
  --output text)

echo "Security Group ID: $SG_ID"
echo "SG_ID=$SG_ID" > /tmp/rds-sg-id.txt
```

Add inbound rule for PostgreSQL (port 5432) from your IP:

```bash
SG_ID=$(cat /tmp/rds-sg-id.txt | cut -d'=' -f2)
MY_IP=$(curl -s https://checkip.amazonaws.com)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $MY_IP/32 \
  --region us-east-2

echo "✅ Added rule for your IP: $MY_IP"
```

**Optional:** Allow access from VPC (for Lambda/ECS):

```bash
SG_ID=$(cat /tmp/rds-sg-id.txt | cut -d'=' -f2)
VPC_ID=$(aws ec2 describe-vpcs \
  --region us-east-2 \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

# Get VPC CIDR
VPC_CIDR=$(aws ec2 describe-vpcs \
  --vpc-ids $VPC_ID \
  --region us-east-2 \
  --query 'Vpcs[0].CidrBlock' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $VPC_CIDR \
  --region us-east-2

echo "✅ Added rule for VPC: $VPC_CIDR"
```

---

## Step 2: Create DB Subnet Group

Get default VPC subnets:

```bash
VPC_ID=$(aws ec2 describe-vpcs \
  --region us-east-2 \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --region us-east-2 \
  --query 'Subnets[*].SubnetId' \
  --output text)

echo "Subnets: $SUBNET_IDS"
echo "SUBNET_IDS=\"$SUBNET_IDS\"" > /tmp/rds-subnets.txt
```

Create DB subnet group:

```bash
SUBNET_IDS=$(cat /tmp/rds-subnets.txt | cut -d'"' -f2)
SUBNET_1=$(echo $SUBNET_IDS | cut -d' ' -f1)
SUBNET_2=$(echo $SUBNET_IDS | cut -d' ' -f2)

aws rds create-db-subnet-group \
  --db-subnet-group-name ece461-rds-subnet-group \
  --db-subnet-group-description "Subnet group for ECE461 RDS" \
  --subnet-ids $SUBNET_1 $SUBNET_2 \
  --region us-east-2

echo "✅ DB subnet group created"
```

---

## Step 3: Create RDS PostgreSQL Instance

**Set your database password** (change this to a secure password):

```bash
DB_PASSWORD="YourSecurePassword123!"
echo "DB_PASSWORD=$DB_PASSWORD" > /tmp/rds-password.txt
echo "⚠️  Save this password securely!"
```

Create RDS instance:

```bash
SG_ID=$(cat /tmp/rds-sg-id.txt | cut -d'=' -f2)
DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)

aws rds create-db-instance \
  --db-instance-identifier ece461-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp2 \
  --db-name artifacts_db \
  --db-subnet-group-name ece461-rds-subnet-group \
  --vpc-security-group-ids $SG_ID \
  --backup-retention-period 7 \
  --no-multi-az \
  --no-publicly-accessible \
  --region us-east-2 \
  --output json > /tmp/rds-instance.json

echo "✅ RDS instance creation started"
echo "⏳ This will take 5-10 minutes. Check status with:"
echo "   aws rds describe-db-instances --db-instance-identifier ece461-postgres --region us-east-2 --query 'DBInstances[0].DBInstanceStatus' --output text"
```

Wait for instance to be available:

```bash
echo "Waiting for RDS instance to be available..."
aws rds wait db-instance-available \
  --db-instance-identifier ece461-postgres \
  --region us-east-2

echo "✅ RDS instance is available!"
```

---

## Step 4: Get RDS Endpoint and Connection Info

Get endpoint:

```bash
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier ece461-postgres \
  --region us-east-2 \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "RDS Endpoint: $RDS_ENDPOINT"
echo "RDS_ENDPOINT=$RDS_ENDPOINT" > /tmp/rds-endpoint.txt
```

Get connection details:

```bash
RDS_ENDPOINT=$(cat /tmp/rds-endpoint.txt | cut -d'=' -f2)
DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)

echo ""
echo "📋 Connection Details:"
echo "   Endpoint: $RDS_ENDPOINT"
echo "   Port: 5432"
echo "   Database: artifacts_db"
echo "   Username: postgres"
echo "   Password: $DB_PASSWORD"
echo ""
echo "📝 Environment Variables:"
echo "   export RDS_ENDPOINT=$RDS_ENDPOINT"
echo "   export RDS_DB_NAME=artifacts_db"
echo "   export RDS_USERNAME=postgres"
echo "   export RDS_PASSWORD=$DB_PASSWORD"
echo "   export RDS_PORT=5432"
echo "   export STORAGE_BACKEND=rds_postgres"
```

---

## Step 5: Initialize Database Schema

Run the initialization script:

```bash
# Set environment variables
RDS_ENDPOINT=$(cat /tmp/rds-endpoint.txt | cut -d'=' -f2)
DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)

export RDS_ENDPOINT=$RDS_ENDPOINT
export RDS_DB_NAME=artifacts_db
export RDS_USERNAME=postgres
export RDS_PASSWORD=$DB_PASSWORD
export RDS_PORT=5432

# Run initialization script
python scripts/init_rds_schema.py
```

---

## Step 6: Test Connection

Test with psql (if installed):

```bash
RDS_ENDPOINT=$(cat /tmp/rds-endpoint.txt | cut -d'=' -f2)
DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)

PGPASSWORD=$DB_PASSWORD psql -h $RDS_ENDPOINT -U postgres -d artifacts_db -c "SELECT version();" 2>/dev/null || echo "⚠️  psql not installed - connection test skipped"
```

Or test with Python:

```bash
RDS_ENDPOINT=$(cat /tmp/rds-endpoint.txt | cut -d'=' -f2)
DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)

python3 << EOF
import psycopg2
import os

try:
    conn = psycopg2.connect(
        host="$RDS_ENDPOINT",
        database="artifacts_db",
        user="postgres",
        password="$DB_PASSWORD",
        port=5432,
        connect_timeout=10
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"✅ Connection successful!")
    print(f"   PostgreSQL version: {version[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
EOF
```

---

## Verification Script

Run the verification script:

```bash
./AWS/verify-rds.sh
```

Or manually verify:

```bash
REGION="us-east-2"
INSTANCE_ID="ece461-postgres"

echo "🔍 Verifying RDS Setup..."
echo ""

# Check RDS Instance
echo "1. Checking RDS Instance..."
if aws rds describe-db-instances \
  --db-instance-identifier $INSTANCE_ID \
  --region $REGION >/dev/null 2>&1; then
  STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier $INSTANCE_ID \
    --region $REGION \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text)
  ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $INSTANCE_ID \
    --region $REGION \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)
  echo "   ✅ Instance exists: $INSTANCE_ID"
  echo "   ✅ Status: $STATUS"
  echo "   ✅ Endpoint: $ENDPOINT"
else
  echo "   ❌ Instance not found: $INSTANCE_ID"
  exit 1
fi

# Check Security Group
echo "2. Checking Security Group..."
SG_NAME="ece461-rds-sg"
if aws ec2 describe-security-groups \
  --group-names $SG_NAME \
  --region $REGION >/dev/null 2>&1; then
  SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SG_NAME \
    --region $REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text)
  echo "   ✅ Security group exists: $SG_ID"
else
  echo "   ❌ Security group not found: $SG_NAME"
  exit 1
fi

# Check DB Subnet Group
echo "3. Checking DB Subnet Group..."
if aws rds describe-db-subnet-groups \
  --db-subnet-group-name ece461-rds-subnet-group \
  --region $REGION >/dev/null 2>&1; then
  echo "   ✅ DB subnet group exists"
else
  echo "   ❌ DB subnet group not found"
  exit 1
fi

echo ""
echo "✅ Verification complete!"
```

---

## Quick Reference

| Resource | Name | Command to Get Info |
|----------|------|---------------------|
| **RDS Instance** | `ece461-postgres` | `aws rds describe-db-instances --db-instance-identifier ece461-postgres --region us-east-2` |
| **Security Group** | `ece461-rds-sg` | `aws ec2 describe-security-groups --group-names ece461-rds-sg --region us-east-2` |
| **DB Subnet Group** | `ece461-rds-subnet-group` | `aws rds describe-db-subnet-groups --db-subnet-group-name ece461-rds-subnet-group --region us-east-2` |

---

## Troubleshooting

**Issue: "DB instance not found"**
- Solution: Wait for instance creation to complete (5-10 minutes). Check status with: `aws rds describe-db-instances --db-instance-identifier ece461-postgres --region us-east-2 --query 'DBInstances[0].DBInstanceStatus' --output text`

**Issue: "Connection timeout" or "Connection refused"**
- Solution: Check security group rules allow your IP. Update with: `aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 5432 --cidr <YOUR_IP>/32 --region us-east-2`

**Issue: "Authentication failed"**
- Solution: Verify password matches what you set in Step 3. Password is stored in `/tmp/rds-password.txt` (if you didn't delete it).

**Issue: "Database does not exist"**
- Solution: Run the initialization script: `python scripts/init_rds_schema.py` (with environment variables set)

**Issue: "Insufficient permissions"**
- Solution: Ensure your AWS credentials have `rds:*`, `ec2:*` permissions, or use an IAM user/role with RDS and EC2 access.

---

## Cleanup (if needed)

To delete everything:

```bash
REGION="us-east-2"
INSTANCE_ID="ece461-postgres"
SG_NAME="ece461-rds-sg"
SUBNET_GROUP="ece461-rds-subnet-group"

# Delete RDS instance (takes a few minutes)
aws rds delete-db-instance \
  --db-instance-identifier $INSTANCE_ID \
  --skip-final-snapshot \
  --region $REGION

echo "⏳ Waiting for instance deletion..."
aws rds wait db-instance-deleted \
  --db-instance-identifier $INSTANCE_ID \
  --region $REGION

# Delete DB subnet group
aws rds delete-db-subnet-group \
  --db-subnet-group-name $SUBNET_GROUP \
  --region $REGION

# Delete security group
SG_ID=$(aws ec2 describe-security-groups \
  --group-names $SG_NAME \
  --region $REGION \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

aws ec2 delete-security-group \
  --group-id $SG_ID \
  --region $REGION

echo "✅ Cleanup complete"
```

---

## Cost Notes

- **db.t3.micro**: Free tier eligible (750 hours/month for 12 months), then ~$15/month
- **Storage**: 20GB gp2 storage is ~$2.30/month
- **Backups**: 7-day retention included in storage cost
- **Total**: ~$0/month (free tier) or ~$17/month after free tier expires

To minimize costs:
- Use `db.t3.micro` (smallest instance)
- Set `--no-multi-az` (single-AZ deployment)
- Delete instance when not in use
