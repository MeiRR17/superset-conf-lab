# Telephony Load Monitoring System

A complete, production-grade local MVP for monitoring telephony load from Cisco servers (UCCX and CUCM). This system includes a mock data server, metrics collection gateway, PostgreSQL database, Apache Superset dashboards, Redis caching, and Nginx reverse proxy.

## Architecture Overview

```
┌─────────────┐
│   Nginx     │  Port 80 (Single Entry Point)
│  (Proxy)    │
└──────┬──────┘
       │
       ├──────────┬──────────┐
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Superset │ │  Proxy   │ │  Mock    │
│  Port    │ │ Gateway  │ │ Server   │
│  8088    │ │ Port     │ │ Port     │
│          │ │ 8000     │ │ 8001     │
└──────────┘ └────┬─────┘ └──────────┘
                  │
                  ▼
           ┌──────────┐
           │  PostgreSQL │ Port 5432
           │  (telephony_db + superset_db)
           └──────────┘
                  ▲
           ┌──────────┐
           │   Redis   │ Port 6379
           │  (Cache)  │
           └──────────┘
```

## Tech Stack

- **Python 3.11** - FastAPI applications (Mock Server & Proxy Gateway)
- **PostgreSQL 15** - Time-series metrics and metadata storage
- **Apache Superset** - Business intelligence and visualization
- **Redis 7** - Caching and async task broker
- **Nginx** - Reverse proxy and load balancer
- **Docker & Docker Compose** - Container orchestration

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Ports 80, 5432, 6379, 8000, 8001, 8088 available

### Start the System

```bash
# Build and start all services
docker-compose up -d --build

# Wait for all services to be healthy (about 60-90 seconds)
docker-compose ps

# View logs
docker-compose logs -f
```

### Access the Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Superset Dashboards | http://localhost | admin/admin |
| Nginx Proxy | http://localhost | - |
| Proxy Gateway API | http://localhost/api/ | - |
| Mock Server (UCCX) | http://localhost/mock/api/uccx/stats | - |
| Mock Server (CUCM) | http://localhost/mock/api/cucm/system/stats | - |
| PostgreSQL | localhost:5432 | postgres/password |
| Redis | localhost:6379 | - |

### Direct Port Access (for testing)

- Superset: http://localhost:8088
- Proxy Gateway: http://localhost:8000
- Mock Server: http://localhost:8001

## Project Structure

```
.
├── docker-compose.yml          # Main orchestration file
├── README.md                   # This file
├──
├── postgres/
│   └── init.sql                 # Database initialization script
│
├── mock-server/
│   ├── Dockerfile               # Mock server container image
│   ├── requirements.txt         # Python dependencies
│   └── main.py                  # FastAPI mock Cisco endpoints
│
├── proxy-gateway/
│   ├── Dockerfile               # Gateway container image
│   ├── requirements.txt         # Python dependencies
│   ├── main.py                  # FastAPI collection service
│   └── models.py                # SQLAlchemy database models
│
├── superset/
│   ├── Dockerfile               # Custom Superset image
│   ├── superset_config.py       # Superset configuration
│   └── superset-init.sh         # Initialization script
│
└── nginx/
    └── nginx.conf               # Reverse proxy configuration
```

## API Endpoints

### Proxy Gateway (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/collect` | Trigger manual metrics collection |
| GET | `/api/metrics/recent` | Get recent metrics from database |
| GET | `/api/metrics/summary` | Get metrics statistics |

### Mock Server (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/uccx/stats` | UCCX call center metrics |
| GET | `/api/cucm/system/stats` | CUCM system metrics |

## Database Schema

### telephony_metrics Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing ID |
| timestamp | TIMESTAMP WITH TIME ZONE | When metric was recorded |
| server_type | VARCHAR(50) | 'uccx' or 'cucm' |
| metric_name | VARCHAR(100) | e.g., 'active_agents', 'cpu_usage_percent' |
| metric_value | DOUBLE PRECISION | The measurement value |
| unit | VARCHAR(20) | 'count', 'percent', 'seconds', etc. |

## Configuration

### Environment Variables

All services can be configured via environment variables defined in `docker-compose.yml`:

#### PostgreSQL
- `POSTGRES_USER` - Database superuser (default: postgres)
- `POSTGRES_PASSWORD` - Database password (default: password)

#### Proxy Gateway
- `DATABASE_URL` - PostgreSQL connection string
- `MOCK_SERVER_URL` - URL of mock server
- `ENABLE_POLLING` - Enable automatic collection (true/false)
- `POLLING_INTERVAL` - Collection interval in seconds (default: 60)

#### Superset
- `DB_*` - Database connection settings
- `REDIS_*` - Redis connection settings
- `SUPERSET_SECRET_KEY` - Encryption key (change in production!)

## Usage

### Automatic Collection

The proxy-gateway automatically collects metrics every 60 seconds (configurable via `POLLING_INTERVAL`). No manual intervention required.

### Manual Collection

```bash
# Trigger immediate collection via API
curl http://localhost/api/collect

# Or using the direct port
curl http://localhost:8000/api/collect
```

### View Recent Metrics

```bash
# Get last 100 metrics
curl "http://localhost/api/metrics/recent?limit=100"

# Filter by server type
curl "http://localhost/api/metrics/recent?server_type=uccx"
```

### Create Superset Dashboards

1. Log in to Superset at http://localhost (admin/admin)
2. Navigate to **Data → Databases** → "Telephony Metrics" should be pre-configured
3. Go to **SQL Lab** to explore the `telephony_metrics` table
4. Create datasets and charts
5. Build dashboards with real-time telephony metrics

## Monitoring

### Health Checks

All services include Docker health checks:

```bash
# View service health
docker-compose ps

# Check individual service
docker-compose exec <service> <health-command>
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f <service-name>

# Example: proxy-gateway logs
docker-compose logs -f proxy-gateway
```

## Troubleshooting

### Services Not Starting

```bash
# Check for port conflicts
netstat -tlnp | grep -E '80|5432|6379|8000|8001|8088'

# View detailed logs
docker-compose logs --tail=100 <service-name>

# Restart specific service
docker-compose restart <service-name>
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose exec postgres pg_isready -U postgres

# Check proxy-gateway database connection
docker-compose exec proxy-gateway python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:password@postgres:5432/telephony_db')
print(engine.connect().execute('SELECT 1').fetchone())
"
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## Production Considerations

### Security

1. **Change default passwords** - Update all `password` values in `docker-compose.yml`
2. **Generate new secret key** - Run `openssl rand -base64 42` for Superset
3. **Enable HTTPS** - Configure SSL certificates in Nginx
4. **Restrict ports** - Remove direct port mappings (5432, 6379, 8000-8088)
5. **Use Docker secrets** - Move sensitive data to Docker secrets

### Performance

1. **Add PostgreSQL connection pooling** - Configure PgBouncer
2. **Enable Superset query caching** - Already configured via Redis
3. **Scale horizontally** - Run multiple Superset and gateway instances
4. **Add monitoring** - Prometheus/Grafana for infrastructure metrics

### Backups

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres telephony_db > backup.sql

# Backup Superset metadata
docker-compose exec postgres pg_dump -U postgres superset_db > superset_backup.sql
```

## Development

### Adding New Metrics

1. Add new endpoint in `mock-server/main.py`
2. Update `proxy-gateway/main.py` to fetch and parse the new endpoint
3. The database schema is flexible - new metrics are stored automatically

### Modifying Database Schema

1. Edit `postgres/init.sql`
2. For existing databases, use migrations or manual ALTER TABLE commands

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues and questions:
- Open a GitHub issue
- Check existing troubleshooting section
- Review service logs with `docker-compose logs`
