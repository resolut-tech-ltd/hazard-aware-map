# Local Development Setup (No Cloud Costs!)

This guide explains how to run the Bump Aware system locally without deploying to the cloud.

## Architecture

- **Backend**: FastAPI running on your Mac (localhost or local network IP)
- **Database**: PostgreSQL with PostGIS on your Mac
- **Mobile App**: Connect to your Mac's IP address on the same WiFi network
- **Data Transfer**: Export JSON files from mobile → manually import to local DB

## Prerequisites

- Mac with Python 3.11+
- PostgreSQL 15 with PostGIS installed
- Android emulator or physical Android device on same WiFi

## Backend Setup

### 1. Start PostgreSQL and Backend

```bash
# Start PostgreSQL (if using Homebrew)
brew services start postgresql@15

# OR if using Docker
docker-compose up -d

# Navigate to backend directory
cd backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

The backend will be accessible at:
- **Localhost**: http://localhost:8080
- **Local Network**: http://YOUR_MAC_IP:8080 (e.g., http://192.168.1.100:8080)

### 2. Find Your Mac's IP Address

```bash
# On macOS
ipconfig getifaddr en0  # WiFi
# or
ipconfig getifaddr en1  # Ethernet

# You'll get something like: 192.168.1.100
```

## Connecting Mobile App to Local Backend

There are three ways to connect your mobile device to the local backend:

### Option 1: ngrok Tunnel (Recommended for Physical Devices)

**Best for**: Physical Android devices, especially when local network IPs don't work due to Android cleartext traffic restrictions.

#### Why ngrok?
- Android 9+ blocks HTTP connections to local IPs by default (cleartext traffic policy)
- ngrok provides an HTTPS URL that Android accepts
- Works from anywhere (doesn't require same WiFi network)
- No need to modify network security configuration

#### Setup

1. **Install ngrok**:
   ```bash
   # macOS
   brew install ngrok

   # Or download from https://ngrok.com/download
   ```

2. **Create ngrok account** (free tier is sufficient):
   - Visit https://ngrok.com/signup
   - Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken

3. **Configure ngrok**:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

4. **Start ngrok tunnel**:
   ```bash
   # Make sure your backend is running on port 8080
   ngrok http 8080
   ```

5. **Copy the HTTPS URL** from ngrok output:
   ```
   Forwarding   https://abc123def456.ngrok-free.app -> http://localhost:8080
   ```

6. **Configure in Mobile App**:
   - Open the app
   - Go to **Settings** tab
   - Tap **API Base URL**
   - Enter: `https://abc123def456.ngrok-free.app/api/v1`
   - Tap **Save**

#### ngrok Output Example
```
ngrok

Session Status                online
Account                       yourname@email.com (Plan: Free)
Version                       3.5.0
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8080

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

#### Important Notes
- **Free tier limitations**:
  - URL changes every time you restart ngrok
  - Limited to 40 connections/minute
  - Session expires after 2 hours
- **Persistent URLs**: Upgrade to paid plan for static domains
- **Keep ngrok running**: Leave the terminal window open while testing
- **View requests**: Visit http://127.0.0.1:4040 for ngrok web interface showing all requests

### Option 2: Android Emulator

**Best for**: Quick testing without physical device.

The emulator can access your Mac's localhost via the special IP `10.0.2.2`:

**In Mobile App Settings**:
- API Base URL: `http://10.0.2.2:8080/api/v1`

This is the default configuration! No changes needed for emulator testing.

### Option 3: Local Network IP (WiFi)

**Best for**: Consistent local development when you can configure network security.

**Requirements**:
- Phone and Mac on same WiFi network
- Network security configuration to allow HTTP (already included in project)

#### Setup

1. **Find your Mac's IP**:
   ```bash
   ipconfig getifaddr en0  # WiFi
   # Output: 192.168.0.142
   ```

2. **Configure in Mobile App**:
   - Go to Settings
   - API Base URL: `http://192.168.0.142:8080/api/v1`
   - Save

3. **Verify network security config exists**:
   The file `mobile/android/app/src/main/res/xml/network_security_config.xml` allows HTTP to local IPs:
   ```xml
   <domain-config cleartextTrafficPermitted="true">
       <domain includeSubdomains="true">192.168.0.0/16</domain>
       <domain includeSubdomains="true">10.0.0.0/8</domain>
   </domain-config>
   ```

4. **Test connection**:
   - Open Chrome on your Android device
   - Visit: `http://192.168.0.142:8080/health`
   - Should see: `{"status":"healthy"}`

#### Troubleshooting WiFi Connection

If HTTP to local IP still doesn't work:

1. **Rebuild the app** (network config needs rebuild):
   ```bash
   cd mobile/android
   ./gradlew clean
   cd ../..
   npx react-native run-android --variant=release
   ```

2. **Check network security config is applied**:
   ```bash
   # Verify AndroidManifest.xml includes:
   grep "networkSecurityConfig" mobile/android/app/src/main/AndroidManifest.xml
   ```

3. **Use ngrok instead** (easier and more reliable)

## Development Workflow

### Testing with Live Sync

1. **Start Backend**:
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

2. **Start Mobile App**:
   ```bash
   cd mobile
   npm run android
   ```

3. **Use the App**:
   - Tap "Start Monitoring"
   - Tap "Simulate Bump (Test)" to generate test data
   - Tap "Sync Data" to upload to your local backend
   - Data is immediately saved to your local PostgreSQL database

4. **View Data**:
   ```bash
   # Connect to PostgreSQL
   psql bump_aware

   # Check detections
   SELECT id, latitude, longitude, magnitude, timestamp
   FROM detections
   ORDER BY timestamp DESC
   LIMIT 10;
   ```

### Manual Export/Import Workflow

If you prefer not to sync over the network or want to collect data offline:

#### 1. Export from Mobile App

1. In the mobile app, tap **"Export to File"** button
2. Choose where to save/share the JSON file
3. Transfer file to your Mac (AirDrop, email, USB, etc.)

#### 2. Import to Local Database

```bash
cd backend

# Import detections from exported JSON file
python import_detections.py path/to/bump_detections_1234567890.json --user-email test@example.com

# Example:
python import_detections.py ~/Downloads/bump_detections_1735123456789.json --user-email josh@resoluttech.ltd
```

The import script will:
- ✓ Read the JSON file
- ✓ Create user if doesn't exist
- ✓ Import all detections to the database
- ✓ Show summary of imported/skipped records

#### 3. Verify Import

```bash
# Connect to database
psql bump_aware

# Check imported detections
SELECT
    u.email,
    COUNT(d.id) as detection_count,
    MIN(d.timestamp) as first_detection,
    MAX(d.timestamp) as last_detection
FROM detections d
JOIN users u ON d.user_id = u.id
GROUP BY u.email;
```

## Network Troubleshooting

### Can't Connect from Physical Device?

1. **Check Firewall**:
   ```bash
   # Temporarily disable macOS firewall
   # System Settings > Network > Firewall > Turn Off
   ```

2. **Verify Backend is Running**:
   ```bash
   # On your Mac
   curl http://localhost:8080/api/v1/health
   # Should return: {"status":"healthy"}
   ```

3. **Test from Device**:
   - Open browser on Android device
   - Navigate to: `http://YOUR_MAC_IP:8080/api/v1/health`
   - Should see: `{"status":"healthy"}`

4. **Check Same Network**:
   ```bash
   # On Mac - get IP
   ipconfig getifaddr en0

   # On Android - Settings > WiFi > tap network name
   # IP should be in same range (e.g., 192.168.1.x)
   ```

### Backend Not Accessible?

Make sure you started with `--host 0.0.0.0` (not just `localhost`):

```bash
# ✓ Correct (accessible from network)
uvicorn app.main:app --host 0.0.0.0 --port 8080

# ✗ Wrong (only accessible from localhost)
uvicorn app.main:app --port 8080
```

## Viewing Imported Data

### Check Detection Count

```sql
-- Total detections
SELECT COUNT(*) FROM detections;

-- Detections by user
SELECT
    u.email,
    COUNT(d.id) as count
FROM detections d
JOIN users u ON d.user_id = u.id
GROUP BY u.email;
```

### View Recent Detections

```sql
SELECT
    d.id,
    u.email,
    d.latitude,
    d.longitude,
    d.magnitude,
    d.timestamp,
    d.accelerometer_data,
    d.gyroscope_data
FROM detections d
JOIN users u ON d.user_id = u.id
ORDER BY d.timestamp DESC
LIMIT 20;
```

### Check Clustered Hazards

```sql
-- View generated hazards
SELECT
    id,
    latitude,
    longitude,
    severity,
    confidence,
    detection_count,
    last_detected_at
FROM hazards
ORDER BY detection_count DESC;
```

### Trigger Clustering Manually

If hazards aren't being created automatically, you can trigger clustering via the API:

```bash
# Get auth token first
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "device_id": "test-device"
  }'

# The response will include an access_token
# Use it for subsequent requests:

curl -X POST http://localhost:8080/api/v1/detections/batch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "detections": [...]
  }'
```

## Cost Comparison

| Approach | Monthly Cost | Pros | Cons |
|----------|--------------|------|------|
| **Local Dev (This Guide)** | **$0** | Free, full control, fast iteration | Must keep Mac running, limited to local network |
| **GCP Cloud Run** | ~$10-15 | Always available, public domain, scalable | Costs money, requires setup |

## Tips for Local Development

1. **Keep Backend Running**: Use `screen` or `tmux` to keep backend running:
   ```bash
   screen -S backend
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8080
   # Press Ctrl+A then D to detach
   # Later: screen -r backend to reattach
   ```

2. **Auto-restart on Code Changes**: The `--reload` flag automatically restarts when you edit Python files

3. **View Logs**: All API requests are logged to console, useful for debugging

4. **Database Backups**:
   ```bash
   # Backup
   pg_dump bump_aware > backup_$(date +%Y%m%d).sql

   # Restore
   psql bump_aware < backup_20260107.sql
   ```

5. **Reset Database** (if needed):
   ```bash
   # Drop and recreate
   dropdb bump_aware
   createdb bump_aware
   psql bump_aware -c "CREATE EXTENSION postgis;"

   # Run migrations
   cd backend
   alembic upgrade head
   ```

## When to Move to Cloud

Consider deploying to GCP when:
- You want to access the API from anywhere (not just local network)
- You want to share the app with others
- You need the backend running 24/7
- You want to use a custom domain (bump-api.resoluttech.ltd)

Until then, local development is perfect for testing and low-volume usage!
