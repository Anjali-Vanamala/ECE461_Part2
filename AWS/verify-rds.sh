#!/bin/bash
# Verification script for RDS PostgreSQL setup
# Run this after completing the setup steps in rds_setup.md

set -e

REGION="us-east-2"
INSTANCE_ID="ece461-postgres"
SG_NAME="ece461-rds-sg"
SUBNET_GROUP="ece461-rds-subnet-group"

echo "🔍 Verifying RDS PostgreSQL Setup..."
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
  ENGINE=$(aws rds describe-db-instances \
    --db-instance-identifier $INSTANCE_ID \
    --region $REGION \
    --query 'DBInstances[0].Engine' \
    --output text)
  ENGINE_VERSION=$(aws rds describe-db-instances \
    --db-instance-identifier $INSTANCE_ID \
    --region $REGION \
    --query 'DBInstances[0].EngineVersion' \
    --output text)
  DB_NAME=$(aws rds describe-db-instances \
    --db-instance-identifier $INSTANCE_ID \
    --region $REGION \
    --query 'DBInstances[0].DBName' \
    --output text)
  
  echo "   ✅ Instance exists: $INSTANCE_ID"
  echo "   ✅ Status: $STATUS"
  echo "   ✅ Engine: $ENGINE $ENGINE_VERSION"
  echo "   ✅ Database: $DB_NAME"
  echo "   ✅ Endpoint: $ENDPOINT"
  
  if [ "$STATUS" != "available" ]; then
    echo "   ⚠️  Instance is not available yet (status: $STATUS)"
    echo "      Wait for status to be 'available' before using"
  fi
else
  echo "   ❌ Instance not found: $INSTANCE_ID"
  echo "   Run Step 3 from rds_setup.md"
  exit 1
fi

# Check Security Group
echo ""
echo "2. Checking Security Group..."
if aws ec2 describe-security-groups \
  --group-names $SG_NAME \
  --region $REGION >/dev/null 2>&1; then
  SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SG_NAME \
    --region $REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text)
  
  INBOUND_RULES=$(aws ec2 describe-security-groups \
    --group-names $SG_NAME \
    --region $REGION \
    --query 'SecurityGroups[0].IpPermissions[?FromPort==`5432`]' \
    --output json)
  
  echo "   ✅ Security group exists: $SG_ID"
  
  if [ "$INBOUND_RULES" != "[]" ] && [ "$INBOUND_RULES" != "null" ]; then
    echo "   ✅ Port 5432 is open"
  else
    echo "   ⚠️  Port 5432 may not be open - check security group rules"
  fi
else
  echo "   ❌ Security group not found: $SG_NAME"
  echo "   Run Step 1 from rds_setup.md"
  exit 1
fi

# Check DB Subnet Group
echo ""
echo "3. Checking DB Subnet Group..."
if aws rds describe-db-subnet-groups \
  --db-subnet-group-name $SUBNET_GROUP \
  --region $REGION >/dev/null 2>&1; then
  echo "   ✅ DB subnet group exists"
else
  echo "   ❌ DB subnet group not found: $SUBNET_GROUP"
  echo "   Run Step 2 from rds_setup.md"
  exit 1
fi

# Test connection (if credentials available)
echo ""
echo "4. Testing Database Connection..."
if [ -f "/tmp/rds-password.txt" ]; then
  DB_PASSWORD=$(cat /tmp/rds-password.txt | cut -d'=' -f2)
  
  # Try Python connection test
  python3 << EOF 2>/dev/null || echo "   ⚠️  Python connection test skipped (psycopg2 may not be installed)"
import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host="$ENDPOINT",
        database="$DB_NAME",
        user="postgres",
        password="$DB_PASSWORD",
        port=5432,
        connect_timeout=5
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"   ✅ Connection successful!")
    print(f"   ✅ PostgreSQL: {version.split(',')[0]}")
    
    # Check if artifacts table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'artifacts'
        );
    """)
    table_exists = cur.fetchone()[0]
    if table_exists:
        print(f"   ✅ 'artifacts' table exists")
    else:
        print(f"   ⚠️  'artifacts' table not found - run: python scripts/init_rds_schema.py")
    
    cur.close()
    conn.close()
except psycopg2.OperationalError as e:
    if "timeout" in str(e).lower():
        print(f"   ⚠️  Connection timeout - check security group rules")
    else:
        print(f"   ⚠️  Connection failed: {e}")
    sys.exit(0)
except Exception as e:
    print(f"   ⚠️  Error: {e}")
    sys.exit(0)
EOF
else
  echo "   ⚠️  Password file not found - skipping connection test"
  echo "      (Password should be in /tmp/rds-password.txt if you saved it)"
fi

echo ""
echo "✅ Verification complete!"
echo ""
echo "📝 Next Steps:"
if [ "$STATUS" = "available" ]; then
  echo "   1. Set environment variables:"
  echo "      export RDS_ENDPOINT=$ENDPOINT"
  echo "      export RDS_DB_NAME=$DB_NAME"
  echo "      export RDS_USERNAME=postgres"
  echo "      export RDS_PASSWORD=<your-password>"
  echo "      export RDS_PORT=5432"
  echo "      export STORAGE_BACKEND=rds_postgres"
  echo ""
  echo "   2. Initialize database schema:"
  echo "      python scripts/init_rds_schema.py"
  echo ""
  echo "   3. Test your application with RDS backend"
else
  echo "   1. Wait for RDS instance to be available (status: $STATUS)"
  echo "   2. Check status: aws rds describe-db-instances --db-instance-identifier $INSTANCE_ID --region $REGION"
fi
