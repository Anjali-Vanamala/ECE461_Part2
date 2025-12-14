# RDS PostgreSQL Setup - AWS CLI Commands

**Region:** us-east-2 (Ohio)  
**Database Engine:** PostgreSQL 15.x  
**Instance Class:** db.t3.micro (free tier eligible)  
**Database Name:** artifacts_db

> ⚠️ **Note:** RDS instances take 5-10 minutes to create. Make sure you have appropriate AWS permissions.

---

## Current Progress & Status

### ✅ Completed Steps
1. **Security Group Created**: `ece461-rds-sg` (sg-08d87976fec1b8ed3)
2. **DB Subnet Group Created**: `ece461-rds-subnet-group` (VPC: vpc-044c2485fbca6f3bc)
3. **RDS Instance Created**: `ece461-postgres` (Status: `available`)
   - Endpoint: `ece461-postgres.cnee4ueesi3l.us-east-2.rds.amazonaws.com`
   - Engine: PostgreSQL 15.15
   - Instance Class: db.t3.micro
   - Storage: 20GB gp2

### ⚠️ In Progress / Pending
1. **Making RDS Publicly Accessible**: Modification requested but may not be complete
2. **Security Group Rules**: Need to add CloudShell IP for initialization
3. **Database Schema Initialization**: Waiting for connectivity

### 🔧 Next Steps Required
See **"Troubleshooting: Connection Timeout from CloudShell"** section below for commands to:
- Verify and complete the public accessibility modification
- Add CloudShell IP to security group
- Initialize the database schema

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
  --engine-version 15.15 \
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

# Note: If engine-version 15.15 is not available, omit --engine-version to use default
# Or list available versions:
# aws rds describe-db-engine-versions --engine postgres --region us-east-2 --query 'DBEngineVersions[?contains(EngineVersion, `15`)].EngineVersion' --output text

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

**Issue: "Connection timeout" or "Connection refused" from CloudShell**

This occurs when:
1. RDS instance is not publicly accessible (created with `--no-publicly-accessible`)
2. Security group doesn't allow CloudShell's IP address

**Solution Steps:**

**Step 1: Check RDS Modification Status**
```bash
aws rds describe-db-instances \
  --db-instance-identifier ece461-postgres \
  --region us-east-2 \
  --query 'DBInstances[0].[DBInstanceStatus,PubliclyAccessible,PendingModifiedValues]' \
  --output table
```

**Step 2: Make RDS Publicly Accessible (if not already)**
```bash
aws rds modify-db-instance \
  --db-instance-identifier ece461-postgres \
  --publicly-accessible \
  --apply-immediately \
  --region us-east-2

# Wait for modification to complete (may take 5-10 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier ece461-postgres \
  --region us-east-2

echo "✅ RDS instance is now publicly accessible"
```

**Step 3: Get CloudShell IP and Add to Security Group**
```bash
# Get CloudShell's public IP
CLOUDSHELL_IP=$(curl -s https://checkip.amazonaws.com)
echo "CloudShell IP: $CLOUDSHELL_IP"

# Get security group ID from RDS instance
SG_ID=$(aws rds describe-db-instances \
  --db-instance-identifier ece461-postgres \
  --region us-east-2 \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)

echo "Security Group ID: $SG_ID"

# Add CloudShell IP to security group
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $CLOUDSHELL_IP/32 \
  --region us-east-2

echo "✅ Added CloudShell IP ($CLOUDSHELL_IP) to security group"
```

**Step 4: Verify Public Accessibility**
```bash
aws rds describe-db-instances \
  --db-instance-identifier ece461-postgres \
  --region us-east-2 \
  --query 'DBInstances[0].PubliclyAccessible' \
  --output text
```

**Step 5: Initialize Schema (after connectivity is established)**
```bash
RDS_ENDPOINT=$(cat /tmp/rds-endpoint.txt | cut -d'=' -f2)
DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)

python3 << EOF
import psycopg2

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
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id VARCHAR(255) PRIMARY KEY,
            artifact_type VARCHAR(50) NOT NULL,
            name VARCHAR(500) NOT NULL,
            name_normalized VARCHAR(500),
            url VARCHAR(2000) NOT NULL,
            artifact_data JSONB NOT NULL,
            rating JSONB,
            license VARCHAR(200),
            dataset_id VARCHAR(255),
            dataset_name VARCHAR(500),
            dataset_name_normalized VARCHAR(500),
            dataset_url VARCHAR(2000),
            code_id VARCHAR(255),
            code_name VARCHAR(500),
            code_name_normalized VARCHAR(500),
            code_url VARCHAR(2000),
            processing_status VARCHAR(50) DEFAULT 'completed'
        )
    """)
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_artifact_type ON artifacts(artifact_type)",
        "CREATE INDEX IF NOT EXISTS idx_name_normalized ON artifacts(name_normalized)",
        "CREATE INDEX IF NOT EXISTS idx_url ON artifacts(url)",
        "CREATE INDEX IF NOT EXISTS idx_dataset_id ON artifacts(dataset_id)",
        "CREATE INDEX IF NOT EXISTS idx_code_id ON artifacts(code_id)",
        "CREATE INDEX IF NOT EXISTS idx_dataset_name_normalized ON artifacts(dataset_name_normalized)",
        "CREATE INDEX IF NOT EXISTS idx_code_name_normalized ON artifacts(code_name_normalized)",
        "CREATE INDEX IF NOT EXISTS idx_artifact_type_name ON artifacts(artifact_type, name_normalized)",
        "CREATE INDEX IF NOT EXISTS idx_artifact_type_url ON artifacts(artifact_type, url)"
    ]
    
    for index_sql in indexes:
        cur.execute(index_sql)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("✅ Database schema initialized successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF
```

**Note:** For production, consider making RDS private again after initialization and accessing it only from within the VPC (Lambda/ECS).

**Issue: "Authentication failed"**
- Solution: Verify password matches what you set in Step 3. Password is stored in `/tmp/rds-password.txt` (if you didn't delete it).

**Issue: "Database does not exist"**
- Solution: Run the initialization script: `python scripts/init_rds_schema.py` (with environment variables set)

**Issue: "Insufficient permissions"**
- Solution: Ensure your AWS credentials have `rds:*`, `ec2:*` permissions, or use an IAM user/role with RDS and EC2 access.

**Issue: "Cannot find version 15.4 for postgres"**
- Solution: List available versions: `aws rds describe-db-engine-versions --engine postgres --region us-east-2 --query 'DBEngineVersions[?contains(EngineVersion, `15`)].EngineVersion' --output text`
- Use a valid version (e.g., `15.15`) or omit `--engine-version` to use the default.

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
