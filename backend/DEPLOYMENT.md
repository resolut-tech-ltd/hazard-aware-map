# Deploying Bump Aware API to Google Cloud Platform

This guide will walk you through deploying the Bump Aware backend API to GCP using Cloud Run and Cloud SQL.

## Architecture

- **Cloud Run**: Serverless container runtime for the FastAPI application
- **Cloud SQL (PostgreSQL + PostGIS)**: Managed PostgreSQL database with geospatial extensions
- **Cloud Build**: Automated container builds
- **Custom Domain**: `bump-api.resoluttech.ltd`

## Prerequisites

1. **GCP Account**: Active Google Cloud Platform account
2. **gcloud CLI**: Install from https://cloud.google.com/sdk/docs/install
3. **Billing Enabled**: Project must have billing enabled
4. **Domain Access**: Access to DNS settings for `resoluttech.ltd`

## Step-by-Step Deployment

### 1. Install gcloud CLI

```bash
# macOS
brew install google-cloud-sdk

# Or download installer from:
# https://cloud.google.com/sdk/docs/install
```

### 2. Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### 3. Create GCP Project (if needed)

```bash
# Create new project
gcloud projects create bump-aware-XXXXX --name="Bump Aware"

# Set as active project
gcloud config set project bump-aware-XXXXX

# Enable billing (required)
# Go to: https://console.cloud.google.com/billing
```

### 4. Set Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"  # or your preferred region
```

### 5. Create Cloud SQL Instance

```bash
# Create PostgreSQL instance with PostGIS
gcloud sql instances create bump-aware-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION \
    --database-flags=cloudsql.enable_pgaudit=on

# Set root password
gcloud sql users set-password postgres \
    --instance=bump-aware-db \
    --password="REPLACE_WITH_SECURE_PASSWORD"

# Create database
gcloud sql databases create bump_aware \
    --instance=bump-aware-db

# Create database user
gcloud sql users create bump_aware_user \
    --instance=bump-aware-db \
    --password="REPLACE_WITH_SECURE_PASSWORD"

# Enable PostGIS extension (connect via Cloud SQL Proxy or console)
# Run in PostgreSQL: CREATE EXTENSION postgis;
```

### 6. Enable PostGIS Extension

Option A: Using Cloud SQL Console
1. Go to https://console.cloud.google.com/sql/instances
2. Click on `bump-aware-db`
3. Click "DATABASES" tab
4. Click `bump_aware` database
5. Click "Open Cloud Shell" and run:
```sql
\c bump_aware
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

Option B: Using Cloud SQL Proxy locally
```bash
# Download Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy

# Start proxy (replace with your connection name)
./cloud-sql-proxy PROJECT_ID:REGION:bump-aware-db &

# Connect with psql
psql "host=127.0.0.1 port=5432 dbname=bump_aware user=postgres"

# In psql:
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
\q
```

### 7. Generate Secret Key

```bash
# Generate a secure secret key
openssl rand -hex 32
# Save this for the next step
```

### 8. Update Environment Configuration

Edit `.env.production` with your actual values:

```bash
# Get your Cloud SQL connection name
gcloud sql instances describe bump-aware-db --format="value(connectionName)"

# Update .env.production with:
DATABASE_URL=postgresql+asyncpg://bump_aware_user:YOUR_DB_PASSWORD@/bump_aware?host=/cloudsql/YOUR_CONNECTION_NAME
SECRET_KEY=YOUR_GENERATED_SECRET_KEY
```

### 9. Run Database Migrations

Before deploying the app, run migrations:

```bash
# Using Cloud SQL Proxy
./cloud-sql-proxy PROJECT_ID:REGION:bump-aware-db &

# Update alembic.ini or set DATABASE_URL temporarily
export DATABASE_URL="postgresql://bump_aware_user:PASSWORD@127.0.0.1:5432/bump_aware"

# Run migrations
cd backend
alembic upgrade head
```

### 10. Deploy to Cloud Run

```bash
cd backend
./deploy.sh
```

The script will prompt for:
- GCP Project ID
- Database URL
- Secret Key
- Cloud SQL connection name

### 11. Map Custom Domain

After deployment:

```bash
# Add domain mapping
gcloud run domain-mappings create \
    --service bump-aware-api \
    --domain bump-api.resoluttech.ltd \
    --region $GCP_REGION
```

The command will output DNS records to add. You'll need to add these to your domain's DNS settings:

**For Cloudflare/DNS Provider:**
1. Add CNAME record:
   - Name: `bump-api`
   - Target: `ghs.googlehosted.com`
   - Proxy status: DNS only (gray cloud in Cloudflare)

### 12. Verify Deployment

```bash
# Test health endpoint
curl https://bump-api.resoluttech.ltd/api/v1/health

# Expected response:
# {"status":"healthy"}
```

### 13. Update Mobile App

Update the API URL in your mobile app:

```typescript
// mobile/src/services/ApiService.ts
private baseURL: string = 'https://bump-api.resoluttech.ltd/api/v1';
```

## Cost Estimation

**Free Tier Eligible:**
- Cloud Run: 2M requests/month, 360,000 GB-seconds/month
- Cloud SQL: db-f1-micro instance (shared CPU, 614 MB RAM)
- Cloud Build: 120 build-minutes/day

**Estimated Monthly Cost (low traffic):**
- Cloud SQL db-f1-micro: ~$7-10/month
- Cloud Run: Free tier should cover initial usage
- Storage: ~$0.50/month
- **Total: ~$10-15/month**

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Cloud SQL connection string | `postgresql+asyncpg://user:pass@/db?host=/cloudsql/proj:region:inst` |
| `SECRET_KEY` | JWT signing key | Generate with `openssl rand -hex 32` |
| `ALLOWED_ORIGINS` | CORS origins | `https://bump-api.resoluttech.ltd` |
| `DEBUG` | Debug mode (production=False) | `False` |

## Monitoring & Logs

### View Logs
```bash
# Cloud Run logs
gcloud run services logs read bump-aware-api --region $GCP_REGION

# Live tail
gcloud run services logs tail bump-aware-api --region $GCP_REGION
```

### Monitor Performance
Visit: https://console.cloud.google.com/run

## Troubleshooting

### Issue: Cloud SQL connection fails

**Solution:** Check that:
1. Cloud SQL instance is running
2. Connection name is correct in DATABASE_URL
3. Database user has proper permissions
4. PostGIS extension is installed

```bash
# Verify Cloud SQL status
gcloud sql instances describe bump-aware-db

# Test connection via proxy
./cloud-sql-proxy PROJECT_ID:REGION:bump-aware-db
psql "host=127.0.0.1 dbname=bump_aware user=bump_aware_user"
```

### Issue: Domain mapping not working

**Solution:**
1. Verify DNS records are propagated: `dig bump-api.resoluttech.ltd`
2. Wait up to 24 hours for DNS propagation
3. Check domain verification status:
```bash
gcloud run domain-mappings describe --domain bump-api.resoluttech.ltd --region $GCP_REGION
```

### Issue: PostGIS not found

**Solution:** Install PostGIS extension:
```sql
-- Connect to database
\c bump_aware

-- Install PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Verify installation
SELECT PostGIS_version();
```

## Updating the Deployment

To deploy updates:

```bash
cd backend
./deploy.sh
```

Or manually:

```bash
# Build new image
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/bump-aware-api .

# Deploy to Cloud Run
gcloud run deploy bump-aware-api \
    --image gcr.io/$GCP_PROJECT_ID/bump-aware-api \
    --region $GCP_REGION
```

## Security Best Practices

1. **Rotate Secret Keys**: Change SECRET_KEY periodically
2. **Use Secret Manager**: Store sensitive values in GCP Secret Manager
3. **Enable Cloud Armor**: DDoS protection for production
4. **Set up VPC**: Use VPC connector for secure Cloud SQL access
5. **Enable Cloud Audit Logs**: Track API access

## Backup & Recovery

### Automatic Backups
Cloud SQL automatically creates daily backups (7 days retention by default).

### Manual Backup
```bash
gcloud sql backups create --instance=bump-aware-db
```

### Restore from Backup
```bash
gcloud sql backups list --instance=bump-aware-db
gcloud sql backups restore BACKUP_ID --backup-instance=bump-aware-db
```

## Scaling Configuration

Adjust Cloud Run settings for higher traffic:

```bash
gcloud run services update bump-aware-api \
    --min-instances=1 \
    --max-instances=100 \
    --memory=1Gi \
    --cpu=2 \
    --region=$GCP_REGION
```

## Support

For issues or questions:
- GCP Documentation: https://cloud.google.com/run/docs
- Cloud SQL: https://cloud.google.com/sql/docs
- PostGIS: https://postgis.net/documentation/
