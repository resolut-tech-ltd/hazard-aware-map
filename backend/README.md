# Bump Aware Backend

FastAPI-based backend infrastructure for crowd-sourced road hazard detection, validation, and alerting.

## Features

### Backend Infrastructure

#### Cloud Database Architecture
- **PostgreSQL 15+** with **PostGIS** extension for geospatial queries
- Spatial indexing for fast location-based lookups
- Optimized for 10,000+ concurrent users
- Efficient query patterns for mobile data constraints

#### Hazard Validation System
- **DBSCAN spatial clustering** (15-20m radius)
- **Temporal weighting**: Recent reports (30 days) receive higher priority
- **Consensus mechanism**: Minimum 3 independent detections required
- **Time-decay function**: Confidence decreases over 90 days
- **Outlier detection**: Statistical filtering of spurious reports
- **Vehicle-type normalization** (planned)
- **Manual verification** pathway

#### Alert Generation Logic
- **Dynamic warning distances** based on vehicle speed (15-30 second lead time)
- **Priority scoring**: severity × confidence × proximity
- **Alert suppression**: Maximum 1 alert per 500m to prevent fatigue
- **Predictive queuing** for route-based navigation
- **Customizable sensitivity** levels

## Technology Stack

- **Framework**: FastAPI 0.109+ (async Python 3.11+)
- **Database**: PostgreSQL 15+ with PostGIS 3.3+
- **ORM**: SQLAlchemy 2.0 (async) + GeoAlchemy2
- **Authentication**: JWT tokens with passlib (bcrypt)
- **Clustering**: scikit-learn (DBSCAN)
- **Geospatial**: Shapely, PostGIS
- **Testing**: pytest, pytest-asyncio
- **Deployment**: Docker, Uvicorn + Gunicorn

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ with PostGIS extension
- Docker & Docker Compose (recommended)
- pip or poetry for dependency management

## Installation

### Option 1: Docker Compose (Recommended)

From the project root:

```bash
docker-compose up -d
```

This starts:
- PostgreSQL with PostGIS on port 5432
- Backend API on port 8080
- pgAdmin on port 5050

### Option 2: Local Development

#### 1. Install PostgreSQL with PostGIS

**macOS (Homebrew)**:
```bash
brew install postgresql@15 postgis
brew services start postgresql@15
```

**Ubuntu/Debian**:
```bash
sudo apt-get install postgresql-15 postgresql-15-postgis-3
sudo systemctl start postgresql
```

#### 2. Create Database

```bash
createdb bump_aware
psql bump_aware -c "CREATE EXTENSION postgis;"
```

#### 3. Install Python Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 4. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/bump_aware
SECRET_KEY=generate-a-secure-random-key-here
DEBUG=True
```

#### 5. Initialize Database

```bash
# Run migrations (when implemented)
alembic upgrade head
```

#### 6. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## API Documentation

Once running, access interactive API documentation:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

## Project Structure

```
backend/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── auth.py            # Authentication (register, login)
│   │   ├── detections.py      # Detection upload endpoints
│   │   └── hazards.py         # Hazard queries and alerts
│   ├── core/                   # Core configuration
│   │   ├── config.py          # Settings management
│   │   └── security.py        # JWT, password hashing
│   ├── db/                     # Database layer
│   │   ├── base.py            # Session management
│   │   └── models.py          # SQLAlchemy models
│   ├── models/
│   │   └── schemas.py         # Pydantic schemas
│   ├── services/               # Business logic
│   │   ├── clustering.py      # DBSCAN spatial clustering
│   │   ├── validation.py      # Hazard validation logic
│   │   └── alerts.py          # Alert generation
│   └── main.py                 # FastAPI application
├── requirements.txt
├── Dockerfile
└── README.md
```

## Database Schema

### Users Table
- User authentication and management
- Links to detections and verifications

### Detections Table
- Raw sensor data from mobile apps
- Location (PostGIS Geography type)
- Accelerometer and gyroscope readings
- Processing status

### Hazards Table
- Validated, clustered hazards
- Location (PostGIS Geography type)
- Severity, confidence scores
- Detection counts, temporal tracking
- Active status

### Hazard Verifications Table
- User confirmations/disputes
- Improves confidence scoring

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Detections
- `POST /api/v1/detections/batch` - Upload batch of detections (authenticated)
- `GET /api/v1/detections/my` - Get user's detections (authenticated)

### Hazards
- `GET /api/v1/hazards/nearby?lat={}&lon={}&radius={}` - Get nearby hazards
- `GET /api/v1/hazards/bounds?min_lat={}&max_lat={}...` - Get hazards in bounding box
- `GET /api/v1/hazards/alerts?lat={}&lon={}&speed_mps={}` - Get prioritized alerts
- `GET /api/v1/hazards/{id}` - Get specific hazard details
- `POST /api/v1/hazards/{id}/verify` - Submit verification (authenticated)

### System
- `GET /` - API information
- `GET /health` - Health check
- `GET /api/v1/stats` - System statistics

## Core Algorithms

### 1. DBSCAN Spatial Clustering

Groups nearby detections into hazard clusters:

```python
# Key parameters
eps_meters = 15.0  # Maximum distance between detections
min_samples = 3    # Minimum detections to form cluster

# Uses Haversine distance for lat/lon coordinates
# Accounts for GPS accuracy (±10m)
```

### 2. Confidence Scoring

Multi-factor confidence calculation:

```
confidence = detection_score(0-0.4)
           + user_score(0-0.3)
           + recency_score(0-0.2)
           + verification_score(0-0.1)

where:
  detection_score = min(0.4, (count / 10) * 0.4)
  user_score = min(0.3, (unique_users / 5) * 0.3)
  recency_score = based on days_since_last_detection
  verification_score = (positive / total) * 0.1
```

### 3. Temporal Weighting

Recent detections weighted higher:

```
weight = 1.0                           # if age <= 30 days
weight = 1.0 - 0.9 * decay_factor      # if 30 < age < 90 days
weight = 0.1                           # if age >= 90 days
```

### 4. Alert Distance Calculation

Dynamic alert distance based on speed and severity:

```
lead_time = 20 seconds * severity_factor (0.5 to 1.0)
distance = speed_mps * lead_time
distance = clamp(distance, 50m, 1000m)
```

### 5. Alert Priority Scoring

```
priority = severity * confidence * (1 - normalized_distance)

Sorted by priority (descending)
Suppression applied: max 1 alert per 500m
```

## Configuration

All settings in [.env](.env.example):

### Database
- `DATABASE_URL`: Connection string
- `DATABASE_POOL_SIZE`: Connection pool size (default: 20)

### Security
- `SECRET_KEY`: JWT signing key (CHANGE IN PRODUCTION!)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime (default: 7 days)

### Validation
- `MIN_DETECTIONS_FOR_HAZARD`: Consensus threshold (default: 3)
- `SPATIAL_CLUSTER_RADIUS_METERS`: Clustering distance (default: 15m)
- `TEMPORAL_WEIGHT_DAYS`: High-priority window (default: 30)
- `CONFIDENCE_DECAY_DAYS`: Decay period (default: 90)
- `MAX_GPS_ACCURACY_METERS`: Outlier filter (default: 10m)

### Alerts
- `MIN_ALERT_DISTANCE_METERS`: Minimum warning distance (default: 50m)
- `MAX_ALERT_DISTANCE_METERS`: Maximum warning distance (default: 1000m)
- `ALERT_SUPPRESSION_RADIUS_METERS`: Suppression radius (default: 500m)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_clustering.py
```

## Database Migrations

Using Alembic for schema migrations:

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance Optimization

### Spatial Indexing
All location columns use PostGIS GIST indexes:

```sql
CREATE INDEX idx_detection_location ON detections USING gist(location);
CREATE INDEX idx_hazard_location ON hazards USING gist(location);
```

### Query Optimization
- Use `ST_DWithin` for radius queries (uses index)
- Batch inserts for detections
- Async database operations
- Connection pooling

### Caching (Future)
- Redis for frequently accessed hazards
- Cache invalidation on updates
- Session caching

## Deployment

### Production Checklist

1. **Security**
   - [ ] Change `SECRET_KEY` to strong random value
   - [ ] Set `DEBUG=False`
   - [ ] Use HTTPS only
   - [ ] Configure CORS properly
   - [ ] Set up firewall rules
   - [ ] Use secure database password

2. **Database**
   - [ ] Enable connection pooling
   - [ ] Set up backups
   - [ ] Configure replication (optional)
   - [ ] Optimize PostgreSQL settings

3. **Application**
   - [ ] Use Gunicorn with multiple Uvicorn workers
   - [ ] Set up Nginx reverse proxy
   - [ ] Configure logging
   - [ ] Set up monitoring (Prometheus/Grafana)

4. **Scaling**
   - [ ] Load balancer for multiple instances
   - [ ] Database read replicas
   - [ ] CDN for static assets
   - [ ] Rate limiting

### Docker Production

```bash
# Build production image
docker build -t bump-aware-api:latest .

# Run with environment file
docker run -d \
  --name bump-aware-api \
  -p 8080:8080 \
  --env-file .env.production \
  bump-aware-api:latest
```

### Systemd Service

Create `/etc/systemd/system/bump-aware.service`:

```ini
[Unit]
Description=Bump Aware API
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/bump-aware/backend
Environment="PATH=/opt/bump-aware/backend/venv/bin"
ExecStart=/opt/bump-aware/backend/venv/bin/gunicorn \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 0.0.0.0:8080 \
  app.main:app

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8080/health

# Database connectivity
curl http://localhost:8080/api/v1/stats
```

### Logs

```bash
# Docker logs
docker logs bump_aware_api -f

# Production logs (systemd)
journalctl -u bump-aware -f
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
psql postgresql://postgres:password@localhost:5432/bump_aware

# Check PostGIS extension
psql bump_aware -c "SELECT PostGIS_Version();"
```

### Migration Issues

```bash
# Reset database (CAUTION: deletes all data)
alembic downgrade base
alembic upgrade head
```

### Performance Issues

```bash
# Check slow queries
psql bump_aware -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Analyze query plans
EXPLAIN ANALYZE SELECT ...
```

## Future Enhancements

- [ ] Background job processing (Celery/RQ)
- [ ] Real-time WebSocket alerts
- [ ] Machine learning for hazard classification
- [ ] Vehicle type normalization
- [ ] Route planning integration
- [ ] Analytics dashboard
- [ ] Mobile notification push
- [ ] API rate limiting and quotas
- [ ] Multi-region deployment

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit pull request

## License

[To be determined]

## Support

For issues or questions:
- GitHub Issues
- API Documentation: http://localhost:8080/docs
- Check logs for error details
