# Docker ARM64 / Apple Silicon Notes

## Issue Fixed

The original Docker setup encountered this error on Apple Silicon (M1/M2/M3) Macs:

```
The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8)
```

## Solution Applied

The [docker-compose.yml](docker-compose.yml) has been updated to explicitly specify the ARM64 platform for PostgreSQL:

```yaml
services:
  postgres:
    image: postgis/postgis:15-3.3
    platform: linux/arm64  # ← Added this line
    container_name: bump_aware_db
```

## Port Configuration

The system is configured to use **port 8080** for the backend API:

- **External access**: http://localhost:8080
- **Internal container**: Port 8000 (mapped to 8080)
- **Docker port mapping**: `8080:8000`

### Why This Mapping?

```yaml
ports:
  - "8080:8000"  # host:container
```

- **Host (8080)**: What you access from your computer/mobile device
- **Container (8000)**: What the FastAPI app listens on inside Docker

The FastAPI app runs on port 8000 internally, but Docker maps it to 8080 externally.

## Verification Steps

### 1. Check Docker Platform Support

```bash
# Verify your system architecture
uname -m
# Should show: arm64

# Check Docker is using ARM64 images
docker inspect bump_aware_db | grep Architecture
# Should show: arm64
```

### 2. Test the Services

```bash
# Start services
docker-compose up -d

# Check all containers are running
docker-compose ps

# Test API health
curl http://localhost:8080/health
# Should return: {"status":"healthy"}

# Check PostgreSQL
docker exec bump_aware_db psql -U postgres -d bump_aware -c "SELECT version();"
# Should show PostgreSQL version with no errors
```

### 3. Check Logs

```bash
# Backend logs
docker logs bump_aware_api

# Database logs
docker logs bump_aware_db

# Should see no platform mismatch errors
```

## Alternative: Force AMD64 (Not Recommended)

If you need to force AMD64 images (slower due to emulation):

```yaml
services:
  postgres:
    image: postgis/postgis:15-3.3
    platform: linux/amd64  # Forces AMD64 with emulation
```

**Note**: This will work but run slower due to Rosetta 2 translation.

## Mobile App Configuration

The mobile app is configured to connect to port 8080:

**File**: [mobile/src/services/ApiService.ts](mobile/src/services/ApiService.ts:7)

```typescript
private baseURL: string = 'http://localhost:8080/api/v1';
```

### For Android Emulator

```typescript
private baseURL: string = 'http://10.0.2.2:8080/api/v1';
```

The special IP `10.0.2.2` is how the Android emulator accesses the host machine.

### For Physical Device

```typescript
private baseURL: string = 'http://YOUR_COMPUTER_IP:8080/api/v1';
```

Replace `YOUR_COMPUTER_IP` with your Mac's local IP address:

```bash
# Find your local IP
ifconfig | grep "inet " | grep -v 127.0.0.1
# Or on newer macOS
ipconfig getifaddr en0
```

## Common Issues

### Issue: Container fails to start on ARM64

**Error**:
```
exec format error
```

**Solution**: Ensure `platform: linux/arm64` is specified in docker-compose.yml

### Issue: Slow performance

**Symptom**: Services are very slow to respond

**Cause**: Running AMD64 images on ARM64 requires emulation

**Solution**:
1. Verify ARM64 images are being used: `docker inspect <container> | grep Architecture`
2. If showing `amd64`, stop services and rebuild:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Issue: Port 8080 already in use

**Error**:
```
bind: address already in use
```

**Solution**:
```bash
# Find what's using port 8080
lsof -i :8080

# Kill the process or change the port in docker-compose.yml
ports:
  - "8081:8000"  # Use port 8081 instead
```

Then update mobile app to use the new port.

## Performance on Apple Silicon

With native ARM64 images, you should see:

- ✅ **Fast startup**: Containers start in 5-10 seconds
- ✅ **Low CPU usage**: ~5-10% CPU when idle
- ✅ **Native performance**: No emulation overhead
- ✅ **Better battery life**: Compared to AMD64 emulation

## Additional Resources

- [Docker ARM64 Support](https://docs.docker.com/desktop/mac/apple-silicon/)
- [PostGIS ARM64 Images](https://hub.docker.com/r/postgis/postgis)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)

## System Requirements

### Minimum
- Apple Silicon Mac (M1/M2/M3)
- macOS 12.0 (Monterey) or later
- Docker Desktop 4.0+ (with Apple Silicon support)
- 8GB RAM
- 10GB free disk space

### Recommended
- Apple Silicon Mac (M1 Pro/Max/Ultra, M2/M3 Pro/Max)
- macOS 13.0 (Ventura) or later
- Docker Desktop 4.15+
- 16GB+ RAM
- 50GB free disk space (for development)

## Docker Desktop Settings

For optimal performance on Apple Silicon:

1. **Resources**:
   - CPUs: 4-6 cores
   - Memory: 4-8GB
   - Swap: 2GB
   - Disk: 50GB+

2. **Features**:
   - ✅ Use Virtualization framework
   - ✅ Enable VirtioFS (faster file sharing)
   - ✅ Use Rosetta for x86/amd64 emulation (if needed)

3. **Docker Compose Settings**:
   - ✅ Use Docker Compose V2
   - ✅ Enable BuildKit

## Troubleshooting Commands

```bash
# Complete reset (if nothing works)
docker-compose down -v  # WARNING: Deletes all data
docker system prune -a  # Clean up everything
docker-compose up -d    # Start fresh

# Check system info
docker info | grep -i arch

# Check image platforms
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Force rebuild with platform
docker-compose build --no-cache --build-arg BUILDPLATFORM=linux/arm64

# View real-time logs
docker-compose logs -f backend
```

## Success Indicators

When everything is working correctly:

```bash
$ docker-compose ps
NAME                 IMAGE                    STATUS
bump_aware_api       bump-aware-backend       Up (healthy)
bump_aware_db        postgis/postgis:15-3.3   Up (healthy)
bump_aware_pgadmin   dpage/pgadmin4:latest    Up

$ curl http://localhost:8080/health
{"status":"healthy"}

$ curl http://localhost:8080/docs
[HTML response with API documentation]
```

---

**Last Updated**: 2026-01-07
**Platform**: Apple Silicon (ARM64)
**Status**: ✅ Fixed and Tested
