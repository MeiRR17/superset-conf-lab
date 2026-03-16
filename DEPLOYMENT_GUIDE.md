# 🚀 Telephony Load Monitoring System - Deployment Guide

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [File Transfer](#2-file-transfer)
3. [Environment Setup](#3-environment-setup)
4. [Service Deployment](#4-service-deployment)
5. [Health Verification](#5-health-verification)
6. [Superset Configuration](#6-superset-configuration)
7. [Data Collection Testing](#7-data-collection-testing)
8. [Dashboard Creation](#8-dashboard-creation)
9. [Monitoring & Troubleshooting](#9-monitoring--troubleshooting)
10. [Production Hardening](#10-production-hardening)
11. [API Testing](#11-api-testing)
12. [Common Issues](#12-common-issues)
13. [Pre-Deployment Checklist](#13-pre-deployment-checklist)

---

## 1️⃣ Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: Minimum 20GB free space
- **Network**: Ports 80, 5432, 6379, 8000, 8001, 8088 available

### Software Installation
```bash
# Install Docker on Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Reboot to apply group changes
sudo reboot
```

---

## 2️⃣ File Transfer

### Option A: SCP Transfer
```bash
# From local machine to server
scp -r /path/to/telephony-project/ user@server:/home/user/telephony-monitoring/

# Or using rsync for better performance
rsync -avz --progress /path/to/telephony-project/ user@server:/home/user/telephony-monitoring/
```

### Option B: Git Clone
```bash
# If project is in Git repository
git clone https://github.com/your-repo/telephony-monitoring.git
cd telephony-monitoring
git checkout production-branch
```

### Option C: Direct Download
```bash
# Download and extract
wget https://your-domain.com/telephony-monitoring.tar.gz
tar -xzf telephony-monitoring.tar.gz
cd telephony-monitoring
```

### Verify File Integrity
```bash
# Check all required files exist
ls -la

# Verify file permissions
chmod +x superset/superset-init.sh
chmod +x nginx/nginx.conf

# Validate YAML syntax
docker-compose config --quiet
```

---

## 3️⃣ Environment Setup

### Create Project Directory
```bash
# Create deployment directory
sudo mkdir -p /opt/telephony-monitoring
sudo chown $USER:$USER /opt/telephony-monitoring
cd /opt/telephony-monitoring

# Copy project files
cp -r /path/to/downloaded/project/* .
```

### Environment Configuration
```bash
# Create production environment file
cp .env.example .env.production

# Edit production values
nano .env.production
```

**Critical Security Settings:**
```bash
# Generate secure passwords
openssl rand -base64 32  # For PostgreSQL
openssl rand -base64 42  # For Superset secret

# Update .env.production with secure values
POSTGRES_PASSWORD=your-generated-postgres-password
SECRET_KEY=your-generated-superset-secret
```

### Docker Network Configuration
```bash
# Create dedicated Docker network
docker network create --driver bridge telephony-network

# Verify network creation
docker network ls | grep telephony
```

---

## 4️⃣ Service Deployment

### Initial Deployment
```bash
# Build and start all services
docker-compose -f docker-compose.yml --env-file .env.production up -d --build

# Monitor startup progress
docker-compose logs -f --tail=50
```

### Startup Sequence Verification
```bash
# Wait for PostgreSQL (should start first)
echo "Waiting for PostgreSQL..."
until docker-compose exec postgres pg_isready -U postgres; do
  echo "PostgreSQL unavailable - sleeping..."
  sleep 2
done
echo "✅ PostgreSQL is ready"

# Wait for Redis
echo "Waiting for Redis..."
until docker-compose exec redis redis-cli ping; do
  echo "Redis unavailable - sleeping..."
  sleep 2
done
echo "✅ Redis is ready"

# Wait for application services
sleep 30

# Check all services status
docker-compose ps
```

### Expected Service Status
```
NAME                    COMMAND                  SERVICE             STATUS              PORTS
telephony-postgres       "docker-entrypoint.s…"      postgres             healthy             5432/tcp
telephony-redis          "docker-entrypoint.s…"      redis                healthy             6379/tcp
telephony-mock-server    "uvicorn main:app --…"   mock-server          healthy             8001/tcp
telephony-proxy-gateway  "uvicorn main:app --…"   proxy-gateway        healthy             8000/tcp
telephony-superset       "/app/superset-init.sh"   superset             healthy             8088/tcp
telephony-nginx          "nginx -g 'daemon of…"    nginx                healthy             80/tcp
```

---

## 5️⃣ Health Verification

### Comprehensive Health Check
```bash
#!/bin/bash
# health-check.sh - Comprehensive service health verification

echo "🔍 Telephony Monitoring System Health Check"
echo "=========================================="

# Function to check service health
check_service() {
    local service_name=$1
    local health_url=$2
    local expected_status=$3
    
    echo -n "Checking $service_name... "
    
    if curl -sf --max-time 10 "$health_url" >/dev/null 2>&1; then
        echo "✅ OK"
        return 0
    else
        echo "❌ FAILED"
        echo "   Expected: $expected_status"
        echo "   URL: $health_url"
        return 1
    fi
}

# Check all services
check_service "Nginx" "http://localhost/nginx-health" "healthy"
check_service "Proxy Gateway" "http://localhost:8000/health" "healthy"
check_service "Mock Server" "http://localhost:8001/health" "healthy"
check_service "Superset" "http://localhost:8088/health/" "healthy"

# Database checks
echo -n "Checking PostgreSQL... "
if docker-compose exec postgres pg_isready -U postgres >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

echo -n "Checking Redis... "
if docker-compose exec redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

echo "=========================================="
echo "Health check completed!"
```

### Port Connectivity Test
```bash
# Test all required ports
for port in 80 5432 6379 8000 8001 8088; do
    echo -n "Testing port $port... "
    if nc -z localhost $port; then
        echo "✅ Open"
    else
        echo "❌ Closed"
    fi
done
```

---

## 6️⃣ Superset Configuration

### Initial Setup
```bash
# Access Superset web interface
open http://localhost

# Default credentials (CHANGE IMMEDIATELY):
# Username: admin
# Password: admin
```

### Database Connection Setup
1. **Login to Superset**
   - URL: `http://localhost`
   - Username: `admin`
   - Password: `admin`

2. **Add Telephony Database**
   - Navigate: **Data → Databases**
   - Click: **+ Connect Database**
   - Fill in details:
     ```
     Display Name: Telephony Metrics Production
     SQLAlchemy URI: postgresql://postgres:YOUR_PASSWORD@postgres:5432/telephony_db
     Username: postgres
     Password: YOUR_PASSWORD
     Host: postgres
     Port: 5432
     Database Name: telephony_db
     ```
   - Click: **Connect**

3. **Verify Connection**
   - Should see "Telephony Metrics Production" in database list
   - Test with: **Data → SQL Lab**
   - Run: `SELECT COUNT(*) FROM telephony_metrics;`

### Security Configuration
```bash
# Change admin password immediately
# Navigate: Admin → Security → List Users
# Click on admin user → Edit
# Set new secure password

# Create additional users with appropriate permissions
# Navigate: Admin → Security → List Users
# Click: + Add User
```

---

## 7️⃣ Data Collection Testing

### Manual Collection Test
```bash
# Trigger immediate data collection
echo "Triggering manual collection..."
curl -X GET http://localhost/api/collect

# Expected response:
# {
#   "success": true,
#   "uccx_metrics_count": 5,
#   "cucm_metrics_count": 6,
#   "total_saved": 11,
#   "errors": [],
#   "timestamp": "2025-03-05T05:32:00.000Z"
# }
```

### Verify Data Persistence
```bash
# Check data in PostgreSQL
docker-compose exec postgres psql -U postgres -d telephony_db -c "
SELECT 
    server_type,
    COUNT(*) as metric_count,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record
FROM telephony_metrics 
GROUP BY server_type;
"

# Expected output:
#  server_type | metric_count | first_record          | last_record
# -------------+--------------+---------------------+---------------------
#  uccx        | 5            | 2025-03-05 05:32:00 | 2025-03-05 05:32:00
#  cucm        | 6            | 2025-03-05 05:32:00 | 2025-03-05 05:32:00
```

### Automatic Collection Verification
```bash
# Check if background polling is working
curl -s http://localhost:8000/health | jq '.polling_enabled, .polling_interval_seconds'

# Wait 2 minutes and check for new data
sleep 120
curl -s "http://localhost/api/metrics/recent?limit=5" | jq '.count'
```

---

## 8️⃣ Dashboard Creation

### Create First Dashboard
```bash
# Access Superset
open http://localhost

# Step-by-step dashboard creation:
```

**Step 1: Create Chart**
1. Click: **+ (Create) → Chart**
2. Select dataset: **Telephony Metrics Production**
3. Choose table: **telephony_metrics**
4. Select chart type: **Time Series Line Chart**
5. Configure chart:
   - **Time Column**: `timestamp`
   - **Metric Column**: `metric_value`
   - **Series**: `server_type`
   - **Entity**: `metric_name`
6. Click: **Run Query**
7. Customize appearance (colors, labels, legend)
8. Click: **Save**

**Step 2: Create Dashboard**
1. Click: **+ (Create) → Dashboard**
2. Enter dashboard name: "Telephony System Overview"
3. Drag your saved chart onto the dashboard
4. Adjust size and position
5. Add filters (optional):
   - Server type filter
   - Time range filter
6. Click: **Save**

**Step 3: Create Additional Charts**
- CPU/Memory usage gauge charts
- Call volume bar charts
- Service level percentage indicators
- Agent availability status
```

### Advanced Dashboard Features
```sql
-- Example SQL queries for different visualizations

-- Real-time metrics by server type
SELECT 
    timestamp,
    server_type,
    metric_name,
    metric_value,
    unit
FROM telephony_metrics 
WHERE timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Daily averages
SELECT 
    DATE_TRUNC('day', timestamp) as date,
    server_type,
    metric_name,
    AVG(metric_value) as avg_value,
    unit
FROM telephony_metrics 
GROUP BY DATE_TRUNC('day', timestamp), server_type, metric_name
ORDER BY date DESC;

-- Current status snapshot
SELECT 
    server_type,
    metric_name,
    metric_value,
    unit,
    timestamp
FROM telephony_metrics 
WHERE timestamp = (
    SELECT MAX(timestamp) 
    FROM telephony_metrics t2 
    WHERE t2.server_type = telephony_metrics.server_type 
    AND t2.metric_name = telephony_metrics.metric_name
);
```

---

## 9️⃣ Monitoring & Troubleshooting

### Real-time Monitoring
```bash
# Monitor all service logs
docker-compose logs -f

# Monitor specific service
docker-compose logs -f proxy-gateway
docker-compose logs -f mock-server
docker-compose logs -f superset

# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

### Log Analysis
```bash
# Check for errors in logs
docker-compose logs --tail=100 | grep -i error

# Check collection failures
docker-compose logs proxy-gateway | grep "Failed to fetch"

# Check database issues
docker-compose logs postgres | grep -i error

# Monitor collection frequency
docker-compose logs proxy-gateway | grep "Collection cycle complete"
```

### Performance Monitoring
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/api/health

# curl-format.txt content:
#      time_namelookup:  %{time_namelookup}\n
#         time_connect:  %{time_connect}\n
#      time_appconnect:  %{time_appconnect}\n
#     time_pretransfer:  %{time_pretransfer}\n
#        time_redirect:  %{time_redirect}\n
#   time_starttransfer:  %{time_starttransfer}\n
#                      ----------\n
#           time_total:  %{time_total}\n

# Database performance
docker-compose exec postgres psql -U postgres -d telephony_db -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables 
WHERE schemaname = 'public';
"
```

---

## 🔟 Production Hardening

### Security Configuration
```bash
# 1. Change all default passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 42)

# 2. Update environment file
cat > .env.production << EOF
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
SECRET_KEY=$SECRET_KEY
DB_PASSWORD=$POSTGRES_PASSWORD
EOF

# 3. Configure SSL (optional but recommended)
# Generate SSL certificates
sudo certbot --nginx -d your-domain.com

# 4. Remove direct port exposures
# Edit docker-compose.yml - comment out direct ports:
# - "5432:5432"  # Remove
# - "6379:6379"  # Remove
# - "8000:8000"  # Remove
# - "8001:8001"  # Remove
# - "8088:8088"  # Remove
# Keep only: - "80:80"   # Nginx only
```

### Resource Limits
```yaml
# Add to docker-compose.yml for production
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
  
  superset:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Backup Configuration
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/telephony"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup databases
docker-compose exec postgres pg_dump -U postgres telephony_db > $BACKUP_DIR/telephony_db_$DATE.sql
docker-compose exec postgres pg_dump -U postgres superset_db > $BACKUP_DIR/superset_db_$DATE.sql

# Backup configurations
tar -czf $BACKUP_DIR/config_$DATE.tar.gz docker-compose.yml .env.production nginx/ superset/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh

# Schedule daily backups
echo "0 2 * * * /opt/telephony-monitoring/backup.sh" | sudo crontab -
```

---

## 1️⃣1️⃣ API Testing

### Health Endpoints
```bash
# Test all health endpoints
echo "Testing API endpoints..."

# Nginx health
curl -f http://localhost/nginx-health && echo "✅ Nginx healthy"

# Proxy Gateway health
curl -s http://localhost:8000/health | jq

# Mock Server health  
curl -s http://localhost:8001/health | jq

# Superset health
curl -f http://localhost:8088/health/ && echo "✅ Superset healthy"
```

### Data Collection API
```bash
# Manual collection
curl -X GET http://localhost/api/collect

# Get recent metrics with filters
curl -X GET "http://localhost/api/metrics/recent?limit=10&server_type=uccx"

# Get metrics summary
curl -X GET http://localhost/api/metrics/summary

# Test with time range (if implemented)
curl -X GET "http://localhost/api/metrics/range?start=2025-03-04T00:00:00Z&end=2025-03-05T00:00:00Z"
```

### Mock Server API
```bash
# Test mock endpoints directly
curl -s http://localhost/mock/api/uccx/stats | jq '.metrics | keys'

curl -s http://localhost/mock/api/cucm/system/stats | jq '.metrics | keys'

# Verify data structure
curl -s http://localhost/mock/api/uccx/stats | jq '.server_type'
curl -s http://localhost/mock/api/uccx/stats | jq '.timestamp'
```

### Load Testing
```bash
# Simple load test
for i in {1..10}; do
    curl -s http://localhost/api/collect > /dev/null &
done
wait

# Concurrent collection test
ab -n 100 -c 10 http://localhost/api/health
```

---

## 1️⃣2️⃣ Common Issues

### Service Startup Issues

| Issue | Symptoms | Diagnosis | Solution |
|-------|-----------|------------|----------|
| PostgreSQL won't start | `Exit 1` in logs | Check disk space, permissions, port conflicts |
| Redis connection refused | `Connection refused` | Verify Redis container is running |
| Mock Server crashes | `Exit 137` | Check memory limits, Python errors |
| Proxy Gateway DB errors | `SQLAlchemy error` | Verify connection string, credentials |
| Superset 502 errors | `Bad Gateway` | Check upstream services, Nginx config |

### Database Issues
```bash
# Check PostgreSQL logs
docker-compose logs postgres | tail -50

# Test database connection manually
docker-compose exec postgres psql -U postgres -d telephony_db -c "SELECT 1;"

# Check table structure
docker-compose exec postgres psql -U postgres -d telephony_db -c "\d telephony_metrics"

# Check indexes
docker-compose exec postgres psql -U postgres -d telephony_db -c "\di"
```

### Performance Issues
```bash
# Check resource usage
docker stats --no-stream

# Identify bottlenecks
docker-compose exec proxy-gateway ps aux
docker-compose exec postgres top

# Optimize database
docker-compose exec postgres psql -U postgres -d telephony_db -c "VACUUM ANALYZE telephony_metrics;"
```

### Network Issues
```bash
# Check Docker network
docker network ls
docker network inspect telephony-network

# Test connectivity between containers
docker-compose exec proxy-gateway ping mock-server
docker-compose exec proxy-gateway ping postgres

# Check Nginx configuration
docker-compose exec nginx nginx -t
```

---

## 1️⃣3️⃣ Pre-Deployment Checklist

### ✅ Security Checklist
- [ ] Change all default passwords
- [ ] Generate new SECRET_KEY for Superset
- [ ] Configure SSL certificates (if using domain)
- [ ] Remove unnecessary port exposures
- [ ] Set up firewall rules
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts

### ✅ Performance Checklist
- [ ] Verify resource requirements
- [ ] Configure Docker resource limits
- [ ] Set up log rotation
- [ ] Optimize database indexes
- [ ] Configure caching properly
- [ ] Test load capacity

### ✅ Reliability Checklist
- [ ] Test service restart procedures
- [ ] Verify health checks work
- [ ] Test backup/restore procedures
- [ ] Document emergency procedures
- [ ] Set up monitoring dashboards
- [ ] Test failover scenarios

### ✅ Final Verification
```bash
#!/bin/bash
# final-check.sh - Complete deployment verification

echo "🚀 Final Deployment Verification"
echo "================================="

# Check all services are healthy
services=("nginx" "proxy-gateway" "mock-server" "superset" "postgres" "redis")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*healthy"; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is not healthy"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo "🎉 All services are healthy!"
    echo "🌐 Access the system at: http://localhost"
    echo "📊 Superset dashboard: http://localhost (admin/admin)"
    echo "📈 API documentation: http://localhost/api/docs"
else
    echo "⚠️  Some services need attention"
    echo "📋 Check logs: docker-compose logs"
fi

echo "================================="
echo "Deployment verification complete!"
```

---

## 🎯 Success Criteria

Your deployment is successful when:

1. ✅ All 6 services show `healthy` status
2. ✅ Nginx responds on port 80
3. ✅ Superset web interface is accessible
4. ✅ Database connection works in Superset
5. ✅ Data collection is working (manual and automatic)
6. ✅ Metrics appear in Superset dashboards
7. ✅ All health endpoints respond correctly
8. ✅ No errors in service logs

---

## 📞 Support & Troubleshooting

### Quick Commands
```bash
# View all service status
docker-compose ps

# View logs for specific service
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart [service-name]

# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Force rebuild
docker-compose up -d --build --force-recreate
```

### Emergency Procedures
```bash
# Complete system reset
docker-compose down -v
docker system prune -f
docker-compose up -d --build

# Database recovery
docker-compose exec postgres psql -U postgres -d telephony_db -c "
SELECT COUNT(*) FROM telephony_metrics WHERE timestamp > NOW() - INTERVAL '1 hour';
"
```

---

**🎉 Deployment Complete!**

Your Telephony Load Monitoring System is now running. Access it at:
- **Main Interface**: http://localhost
- **Direct Superset**: http://localhost:8088
- **API Documentation**: http://localhost/api/docs

For ongoing maintenance, use the monitoring commands and troubleshooting sections above.
