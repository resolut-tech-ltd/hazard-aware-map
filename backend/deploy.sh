#!/bin/bash

# Bump Aware API - GCP Deployment Script
# This script deploys the FastAPI backend to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-""}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="bump-aware-api"
DOMAIN="bump-api.resoluttech.ltd"

echo -e "${GREEN}=== Bump Aware API Deployment ===${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}GCP_PROJECT_ID not set. Please enter your GCP project ID:${NC}"
    read -r PROJECT_ID
fi

echo -e "${GREEN}Project ID:${NC} $PROJECT_ID"
echo -e "${GREEN}Region:${NC} $REGION"
echo -e "${GREEN}Service:${NC} $SERVICE_NAME"
echo -e "${GREEN}Domain:${NC} $DOMAIN\n"

# Set the project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "\n${YELLOW}Enabling required GCP APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com \
    containerregistry.googleapis.com

# Build and push Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" .

# Prompt for environment variables
echo -e "\n${YELLOW}Please provide environment variables:${NC}"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}Enter DATABASE_URL (e.g., postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/connection-name):${NC}"
    read -r DATABASE_URL
fi

if [ -z "$SECRET_KEY" ]; then
    echo -e "${YELLOW}Enter SECRET_KEY (generate with: openssl rand -hex 32):${NC}"
    read -r SECRET_KEY
fi

if [ -z "$CLOUD_SQL_CONNECTION" ]; then
    echo -e "${YELLOW}Enter Cloud SQL connection name (e.g., project:region:instance):${NC}"
    read -r CLOUD_SQL_CONNECTION
fi

# Deploy to Cloud Run
echo -e "\n${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=$DATABASE_URL,SECRET_KEY=$SECRET_KEY,API_V1_PREFIX=/api/v1,PROJECT_NAME=Bump Aware API,DEBUG=False,ALLOWED_ORIGINS=https://$DOMAIN" \
    --add-cloudsql-instances "$CLOUD_SQL_CONNECTION" \
    --max-instances 10 \
    --min-instances 0 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')

echo -e "\n${GREEN}=== Deployment Successful! ===${NC}"
echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Map your custom domain ($DOMAIN) to Cloud Run:"
echo -e "   ${GREEN}gcloud run domain-mappings create --service $SERVICE_NAME --domain $DOMAIN --region $REGION${NC}"
echo -e "\n2. Run database migrations:"
echo -e "   ${GREEN}# Connect to Cloud SQL and run: alembic upgrade head${NC}"
echo -e "\n3. Update mobile app API URL to: ${GREEN}https://$DOMAIN${NC}"
echo -e "\n4. Test the API:"
echo -e "   ${GREEN}curl https://$DOMAIN/api/v1/health${NC}"
