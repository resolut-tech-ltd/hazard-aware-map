# Setup Checklist

Use this checklist to verify your Bump Aware Map installation.

## Pre-Installation Checks

### System Requirements
- [ ] Docker Desktop installed and running
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.11+ installed (`python --version`)
- [ ] Android Studio installed (for mobile development)
- [ ] Git installed

### Network Requirements
- [ ] Port 8080 available (backend API)
- [ ] Port 5432 available (PostgreSQL)
- [ ] Port 5050 available (pgAdmin - optional)
- [ ] Internet connection active

## 📱 Mobile App Setup

### Dependencies
- [ ] Navigate to mobile directory: `cd mobile`
- [ ] Install npm packages: `npm install`
- [ ] Verify no errors in installation

### Configuration
- [ ] Open `src/services/ApiService.ts`
- [ ] Update `baseURL` to match your setup:
  - [ ] Android Emulator: `http://10.0.2.2:8080/api/v1`
  - [ ] Physical Device: `http://YOUR_COMPUTER_IP:8080/api/v1`
  - [ ] Same network required for physical device

### Android Setup
- [ ] Android Studio SDK installed
- [ ] ANDROID_HOME environment variable set
- [ ] Android device connected OR emulator running
- [ ] Verify device: `adb devices` shows device

### Build & Run
- [ ] Start Metro bundler: `npm start`
- [ ] Run on Android: `npm run android` (in new terminal)
- [ ] App installs and launches successfully
- [ ] No red screen errors

### Permissions
- [ ] Location permission granted (fine location)
- [ ] Background location permission granted (Android 10+)

## 🐳 Backend Setup

### Docker Services
- [ ] Navigate to project root
- [ ] Start services: `docker-compose up -d`
- [ ] Wait 30 seconds for services to initialize
- [ ] Check status: `docker-compose ps`
- [ ] All services show "healthy" or "running"

### Database Initialization
- [ ] Enter backend container: `docker exec -it bump_aware_api bash`
- [ ] Run migrations: `alembic upgrade head`
- [ ] Exit container: `exit`
- [ ] No errors during migration

### API Verification
- [ ] Open browser to http://localhost:8080
- [ ] See API welcome message
- [ ] Open http://localhost:8080/docs
- [ ] See Swagger API documentation
- [ ] Test health endpoint: `curl http://localhost:8080/health`
- [ ] Returns `{"status": "healthy"}`

### Database Access (Optional)
- [ ] Open http://localhost:5050 (pgAdmin)
- [ ] Login: admin@bumpaware.com / admin
- [ ] Add server:
  - Host: postgres
  - Port: 5432
  - Database: bump_aware
  - Username: postgres
  - Password: password
- [ ] Connect successfully
- [ ] See tables: users, detections, hazards, hazard_verifications

## Functional Testing

### User Registration
- [ ] Open API docs: http://localhost:8080/docs
- [ ] Expand POST `/api/v1/auth/register`
- [ ] Try it out with test data:
  ```json
  {
    "email": "test@example.com",
    "password": "testpass123",
    "device_id": "test-device"
  }
  ```
- [ ] Response: 201 Created
- [ ] Copy `access_token` from response

### Mobile App Login
- [ ] Open mobile app
- [ ] Tap "Start Monitoring"
- [ ] Location permission prompt appears
- [ ] Grant location permission
- [ ] Monitoring status shows "Active"

### Detection Recording
- [ ] With monitoring active, shake device vigorously
- [ ] OR drive over actual speed bump
- [ ] Statistics update (Total Detections increases)
- [ ] Pending count increases

### Data Sync
- [ ] Tap "Sync Data" button in app
- [ ] Pending count decreases to 0
- [ ] Uploaded count increases
- [ ] No error messages

### Backend Data Verification
- [ ] In pgAdmin or terminal: `docker exec -it bump_aware_db psql -U postgres -d bump_aware`
- [ ] Query: `SELECT COUNT(*) FROM detections;`
- [ ] Should see > 0 detections
- [ ] Query: `SELECT * FROM detections ORDER BY created_at DESC LIMIT 1;`
- [ ] See your recent detection

### Hazard Query
- [ ] Use API docs: GET `/api/v1/hazards/nearby`
- [ ] Parameters:
  - lat: 37.7749
  - lon: -122.4194
  - radius: 5000
- [ ] Execute
- [ ] Returns empty list (no hazards yet - need 3+ detections)

## Troubleshooting Verification

### Docker Issues
If services won't start:
- [ ] Check Docker Desktop is running
- [ ] Check port conflicts: `lsof -i :8080 -i :5432 -i :5050`
- [ ] View logs: `docker-compose logs backend`
- [ ] Restart: `docker-compose restart`

### Mobile Connection Issues
If app can't connect to backend:
- [ ] Verify backend is running: `curl http://localhost:8080/health`
- [ ] Check API URL in `ApiService.ts` is correct
- [ ] For emulator: MUST use `10.0.2.2`, not `localhost`
- [ ] For device: Both on same WiFi network
- [ ] Test from device browser: http://YOUR_IP:8080
- [ ] Check firewall not blocking port 8080

### Sensor Issues
If sensors not detecting:
- [ ] Check permissions granted (Location + Sensors)
- [ ] Verify device has accelerometer & gyroscope
- [ ] Check app logs: `npx react-native log-android`
- [ ] Try adjusting threshold in `SensorService.ts`

### Database Issues
If migrations fail:
- [ ] Check PostgreSQL running: `docker-compose ps postgres`
- [ ] Check PostGIS extension: `docker exec bump_aware_db psql -U postgres -d bump_aware -c "SELECT PostGIS_Version();"`
- [ ] Reset if needed: `docker-compose down -v` (WARNING: deletes data)
- [ ] Start fresh: `docker-compose up -d`

## 📊 Feature Verification Matrix

| Feature | Mobile | Backend | Status |
|---------|--------|---------|--------|
| User Registration | - | ✅ | [ ] Tested |
| User Login | - | ✅ | [ ] Tested |
| Sensor Monitoring | ✅ | - | [ ] Tested |
| GPS Tracking | ✅ | - | [ ] Tested |
| Bump Detection | ✅ | - | [ ] Tested |
| Local Storage | ✅ | - | [ ] Tested |
| Data Upload | ✅ | ✅ | [ ] Tested |
| Nearby Hazards Query | - | ✅ | [ ] Tested |
| Alert Generation | - | ✅ | [ ] Tested |
| Spatial Clustering | - | ✅ | [ ] Pending |
| Confidence Scoring | - | ✅ | [ ] Pending |
| Hazard Verification | ✅ | ✅ | [ ] Pending |

## Production Readiness Checklist

### Security
- [ ] Change `SECRET_KEY` in backend `.env`
- [ ] Use strong database password
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Review and test authentication
- [ ] Implement rate limiting

### Performance
- [ ] Load test with 100+ concurrent users
- [ ] Optimize database queries
- [ ] Enable connection pooling
- [ ] Set up caching (Redis)
- [ ] CDN for static assets

### Monitoring
- [ ] Set up application logging
- [ ] Configure error tracking (Sentry)
- [ ] Set up uptime monitoring
- [ ] Database backup strategy
- [ ] Alert notifications

### Documentation
- [ ] API documentation complete
- [ ] User guide written
- [ ] Developer documentation
- [ ] Deployment guide
- [ ] Troubleshooting guide

### Legal & Compliance
- [ ] Privacy policy
- [ ] Terms of service
- [ ] Data retention policy
- [ ] GDPR compliance (if EU users)
- [ ] License chosen

## Next Development Steps

Once everything above is checked:

1. **Week 1**:
   - [ ] Create actual test users
   - [ ] Generate sample detection data
   - [ ] Verify clustering works with 3+ detections
   - [ ] Test alert generation with real coordinates

2. **Week 2**:
   - [ ] Add map view to mobile app
   - [ ] Implement push notifications
   - [ ] Background service for monitoring
   - [ ] Improve UI/UX

3. **Week 3-4**:
   - [ ] Automated clustering job (cron/Celery)
   - [ ] Admin dashboard
   - [ ] Analytics and reporting
   - [ ] Performance optimization

4. **Month 2+**:
   - [ ] iOS app development
   - [ ] Machine learning improvements
   - [ ] Social features
   - [ ] Production deployment

## Notes & Issues

Use this space to track any issues or notes during setup:

```
Date: ___________
Issue:
Solution:

Date: ___________
Issue:
Solution:
```

## Final Sign-off

- [ ] All critical features tested and working
- [ ] Documentation reviewed and understood
- [ ] Development environment fully operational
- [ ] Ready to start Phase 3 implementation

**Completed by**: ________________
**Date**: ________________
**Ready for development**: YES / NO
