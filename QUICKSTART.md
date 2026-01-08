# Quick Start Guide

Get the Bump Aware system up and running in minutes.

## Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for mobile app)
- Android Studio (for Android development)

## Step 1: Start Backend Services

From the project root:

```bash
# Start PostgreSQL and Backend API
docker-compose up -d

# Wait for services to be ready (30 seconds)
# Check status
docker-compose ps
```

Services will be available at:
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **PostgreSQL**: localhost:5432
- **pgAdmin**: http://localhost:5050

### Initialize Database

```bash
# Enter the backend container
docker exec -it bump_aware_api bash

# Run migrations (creates tables)
alembic upgrade head

# Exit container
exit
```

## Step 2: Setup Mobile App

```bash
cd mobile

# Install dependencies
npm install

# Note: First install may take 5-10 minutes
```

### Configure Backend URL

Edit `mobile/src/services/ApiService.ts` and update the base URL:

```typescript
// For Android emulator
private baseURL: string = 'http://10.0.2.2:8080/api/v1';

// For physical device on same network
private baseURL: string = 'http://YOUR_COMPUTER_IP:8080/api/v1';
```

### Android Setup

1. **Start Android Emulator** or connect physical device
2. **Enable USB debugging** (physical device only)

```bash
# Verify device connection
adb devices

# Start Metro bundler
npm start

# In a new terminal, run the app
npm run android
```

The app should install and launch on your device/emulator.

## Step 3: Test the System

### 1. Register a User

Using the mobile app or via API:

```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "device_id": "test-device"
  }'
```

Save the `access_token` from the response.

### 2. Upload Test Detection

```bash
TOKEN="your-access-token-here"

curl -X POST http://localhost:8080/api/v1/detections/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "detections": [{
      "latitude": 37.7749,
      "longitude": -122.4194,
      "accuracy": 5.0,
      "magnitude": 2.5,
      "timestamp": "2024-01-15T10:30:00Z",
      "accelerometer": {
        "x": 0.5,
        "y": 0.3,
        "z": 9.8,
        "timestamp": "2024-01-15T10:30:00Z"
      },
      "gyroscope": {
        "x": 0.1,
        "y": 0.05,
        "z": 0.02,
        "timestamp": "2024-01-15T10:30:00Z"
      }
    }]
  }'
```

### 3. Query Nearby Hazards

```bash
curl "http://localhost:8080/api/v1/hazards/nearby?lat=37.7749&lon=-122.4194&radius=5000"
```

### 4. Get Alerts

```bash
# Simulate vehicle at 20 m/s (72 km/h)
curl "http://localhost:8080/api/v1/hazards/alerts?lat=37.7749&lon=-122.4194&speed_mps=20"
```

## Step 4: Mobile App Usage

1. **Open the app**
2. **Grant location permissions** when prompted
3. **Tap "Start Monitoring"** to begin detection
4. **Simulate bumps**:
   - In emulator: Use sensor simulation tools
   - With physical device: Drive over speed bumps or rough roads
5. **View statistics** on home screen
6. **Tap "Sync Data"** to upload to backend

## Verify System is Working

### Check API Health

```bash
curl http://localhost:8080/health
# Should return: {"status": "healthy"}
```

### Check Database

```bash
# Access pgAdmin at http://localhost:5050
# Login: admin@bumpaware.com / admin
# Add server: postgres / password

# Or use psql
docker exec -it bump_aware_db psql -U postgres -d bump_aware

# Query detections
SELECT COUNT(*) FROM detections;

# Query hazards
SELECT COUNT(*) FROM hazards;
```

### Check Logs

```bash
# Backend logs
docker logs bump_aware_api -f

# Database logs
docker logs bump_aware_db -f

# Mobile app logs
npx react-native log-android
```

## Common Issues

### Backend won't start

```bash
# Check if port 8080 is already in use
lsof -i :8080

# Restart services
docker-compose restart

# View logs
docker-compose logs backend
```

### Database connection failed

```bash
# Ensure PostgreSQL is running
docker-compose ps postgres

# Check connection string in .env
# Should be: postgresql+asyncpg://postgres:password@postgres:5432/bump_aware
```

### Mobile app can't connect to API

1. **Check backend is accessible**:
   ```bash
   curl http://localhost:8080/health
   ```

2. **For Android emulator**, use `10.0.2.2` instead of `localhost`

3. **For physical device**, ensure both are on same network and use computer's IP

4. **Check firewall** isn't blocking port 8080

### Sensors not working in mobile app

1. **Check permissions**: Location and sensors should be granted
2. **Verify device has sensors**: Some emulators don't support all sensors
3. **Check logs**: `npx react-native log-android`

## Next Steps

1. **Read the full documentation**:
   - [Main README](README.md)
   - [Mobile README](mobile/README.md)
   - [Backend README](backend/README.md)

2. **Configure for your environment**:
   - Update API URLs
   - Configure sensor thresholds
   - Adjust validation parameters

3. **Implement Phase 3 features**:
   - Background processing jobs
   - Real-time clustering
   - Advanced UI with maps
   - Push notifications

4. **Deploy to production**:
   - Set up cloud infrastructure
   - Configure HTTPS
   - Set proper security keys
   - Enable monitoring

## Architecture Overview

```
┌─────────────────┐
│  Mobile App     │  React Native
│  (Android/iOS)  │  - Sensors (100-200Hz)
└────────┬────────┘  - GPS tracking
         │           - Local SQLite
         │ HTTPS
         │ REST API
         │
┌────────▼────────┐
│  FastAPI        │  Python 3.11+
│  Backend        │  - JWT auth
└────────┬────────┘  - Async processing
         │           - DBSCAN clustering
         │
┌────────▼────────┐
│  PostgreSQL     │  15+ with PostGIS
│  + PostGIS      │  - Spatial indexing
└─────────────────┘  - Geospatial queries
```

## Support

- **Documentation**: Check README files in each directory
- **API Docs**: http://localhost:8080/docs
- **Issues**: Open a GitHub issue
- **Logs**: Check Docker logs for errors

## Development Tips

### Hot Reload

- **Backend**: Uvicorn auto-reloads on file changes
- **Mobile**: Metro bundler enables fast refresh (shake device → "Enable Fast Refresh")

### Debugging

- **Backend**: Use `print()` or logging, check Docker logs
- **Mobile**: Use React Native Debugger or Chrome DevTools
- **Database**: Use pgAdmin or psql for direct queries

### Testing

```bash
# Backend tests
cd backend
pytest

# Mobile tests (when implemented)
cd mobile
npm test
```

Enjoy building with Bump Aware!
