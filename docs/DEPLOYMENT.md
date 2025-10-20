# 🚀 ManuScan AI - Production Deployment Guide

Complete guide for deploying ManuScan AI to production environments.

## Table of Contents

- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Performance Optimization](#performance-optimization)
- [Monitoring & Logging](#monitoring--logging)
- [Security](#security)
- [Scaling](#scaling)

---

## Deployment Options

### 1. Static Site Deployment (Recommended)

Deploy the frontend as a static site with client-side AI inference.

**Pros:**
- No server costs
- Infinite scalability
- Fast global CDN delivery
- No backend maintenance

**Cons:**
- Limited to browser capabilities
- Model size constraints
- No server-side processing

**Best for:** Public demos, lightweight analysis, cost-effective deployment

### 2. Full-Stack Deployment

Deploy both frontend and backend with API server.

**Pros:**
- Full feature set
- Server-side GPU acceleration
- Large model support
- Advanced processing capabilities

**Cons:**
- Higher infrastructure costs
- Server maintenance required
- Scaling complexity

**Best for:** Enterprise deployments, heavy processing, custom integrations

### 3. Hybrid Deployment

Frontend as static site with optional API backend.

**Pros:**
- Best of both worlds
- Fallback capabilities
- Cost optimization
- Flexible scaling

**Best for:** Production applications with varying load patterns

---

## Docker Deployment

### Prerequisites

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Production Docker Setup

#### 1. Create Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/ssl/certs
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    depends_on:
      - api

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
      - CUDA_VISIBLE_DEVICES=0
      - WORKERS=4
    volumes:
      - ./models:/app/models
      - ./data:/app/data
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - frontend
      - api
    restart: unless-stopped

volumes:
  redis_data:
```

#### 2. Create Production Dockerfiles

**Frontend Dockerfile:**
```dockerfile
# frontend/Dockerfile.prod
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
```

**Backend Dockerfile:**
```dockerfile
# backend/Dockerfile.prod
FROM nvidia/cuda:11.8-runtime-ubuntu20.04

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "api.main:app"]
```

#### 3. Deploy to Production

```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

---

## Cloud Deployment

### AWS Deployment

#### 1. ECS with Fargate

```yaml
# aws-ecs-task-definition.json
{
  "family": "manuscan-ai",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "manuscan-frontend",
      "image": "your-ecr-repo/manuscan-frontend:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/manuscan-ai",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "frontend"
        }
      }
    }
  ]
}
```

#### 2. CloudFormation Template

```yaml
# cloudformation-template.yml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ManuScan AI Production Infrastructure'

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
  CertificateArn:
    Type: String

Resources:
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: manuscan-ai-cluster
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT

  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: manuscan-ai-alb
      Scheme: internet-facing
      Type: application
      Subnets: !Ref SubnetIds
      SecurityGroups:
        - !Ref ALBSecurityGroup

  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Origins:
          - Id: ALBOrigin
            DomainName: !GetAtt ApplicationLoadBalancer.DNSName
            CustomOriginConfig:
              HTTPPort: 80
              HTTPSPort: 443
              OriginProtocolPolicy: https-only
        DefaultCacheBehavior:
          TargetOriginId: ALBOrigin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad
        Enabled: true
        HttpVersion: http2
        PriceClass: PriceClass_100
```

### Google Cloud Platform

#### 1. Cloud Run Deployment

```yaml
# cloudbuild.yaml
steps:
  # Build frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/manuscan-frontend', './frontend']
  
  # Build backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/manuscan-backend', './backend']
  
  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/manuscan-frontend']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/manuscan-backend']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'manuscan-ai',
      '--image', 'gcr.io/$PROJECT_ID/manuscan-frontend',
      '--platform', 'managed',
      '--region', 'us-central1',
      '--allow-unauthenticated'
    ]
```

#### 2. Kubernetes Deployment

```yaml
# k8s-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: manuscan-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: manuscan-ai
  template:
    metadata:
      labels:
        app: manuscan-ai
    spec:
      containers:
      - name: frontend
        image: gcr.io/PROJECT_ID/manuscan-frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      - name: backend
        image: gcr.io/PROJECT_ID/manuscan-backend:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
            nvidia.com/gpu: 1
          limits:
            memory: "4Gi"
            cpu: "2000m"
            nvidia.com/gpu: 1
---
apiVersion: v1
kind: Service
metadata:
  name: manuscan-ai-service
spec:
  selector:
    app: manuscan-ai
  ports:
  - name: http
    port: 80
    targetPort: 80
  - name: api
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### Vercel/Netlify (Static Deployment)

#### Vercel Configuration

```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "https://your-backend-api.com/api/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/frontend/$1"
    }
  ],
  "env": {
    "NODE_ENV": "production",
    "VITE_API_URL": "https://your-backend-api.com"
  }
}
```

#### Netlify Configuration

```toml
# netlify.toml
[build]
  base = "frontend/"
  publish = "dist/"
  command = "npm run build"

[build.environment]
  NODE_ENV = "production"
  VITE_API_URL = "https://your-backend-api.com"

[[redirects]]
  from = "/api/*"
  to = "https://your-backend-api.com/api/:splat"
  status = 200

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[dev]
  command = "npm run dev"
  port = 5173
```

---

## Performance Optimization

### Frontend Optimization

#### 1. Bundle Optimization

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          three: ['three'],
          tensorflow: ['@tensorflow/tfjs']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },
  optimizeDeps: {
    include: ['@tensorflow/tfjs']
  }
});
```

#### 2. Model Optimization

```python
# scripts/optimize_model.py
import tensorflow as tf

# Load PyTorch model
model = torch.load('model.pth')

# Convert to TensorFlow.js with quantization
converter = tf.lite.TFLiteConverter.from_saved_model('saved_model')
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.float16]

tflite_model = converter.convert()

# Save optimized model
with open('model_optimized.tflite', 'wb') as f:
    f.write(tflite_model)
```

### Backend Optimization

#### 1. Gunicorn Configuration

```python
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 300
keepalive = 2
preload_app = True
```

#### 2. Redis Caching

```python
# backend/cache.py
import redis
import json
import hashlib

redis_client = redis.Redis(host='redis', port=6379, db=0)

def cache_analysis_result(mesh_hash: str, result: dict, ttl: int = 3600):
    """Cache analysis result with TTL"""
    key = f"analysis:{mesh_hash}"
    redis_client.setex(key, ttl, json.dumps(result))

def get_cached_result(mesh_hash: str) -> dict:
    """Get cached analysis result"""
    key = f"analysis:{mesh_hash}"
    cached = redis_client.get(key)
    return json.loads(cached) if cached else None

def generate_mesh_hash(mesh_data: bytes) -> str:
    """Generate hash for mesh data"""
    return hashlib.sha256(mesh_data).hexdigest()
```

---

## Monitoring & Logging

### Application Monitoring

#### 1. Prometheus Metrics

```python
# backend/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
analysis_requests = Counter('analysis_requests_total', 'Total analysis requests')
analysis_duration = Histogram('analysis_duration_seconds', 'Analysis duration')
active_analyses = Gauge('active_analyses', 'Currently running analyses')
gpu_utilization = Gauge('gpu_utilization_percent', 'GPU utilization')

def track_analysis(func):
    def wrapper(*args, **kwargs):
        analysis_requests.inc()
        active_analyses.inc()
        
        with analysis_duration.time():
            result = func(*args, **kwargs)
        
        active_analyses.dec()
        return result
    return wrapper
```

#### 2. Grafana Dashboard

```json
{
  "dashboard": {
    "title": "ManuScan AI Monitoring",
    "panels": [
      {
        "title": "Analysis Requests/sec",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(analysis_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Analysis Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, analysis_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "GPU Utilization",
        "type": "singlestat",
        "targets": [
          {
            "expr": "gpu_utilization_percent",
            "legendFormat": "GPU %"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

#### 1. Structured Logging

```python
# backend/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/manuscan/app.log')
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

#### 2. ELK Stack Integration

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

---

## Security

### SSL/TLS Configuration

#### 1. Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d manuscan-ai.com -d www.manuscan-ai.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 2. Nginx SSL Configuration

```nginx
# nginx.conf
server {
    listen 80;
    server_name manuscan-ai.com www.manuscan-ai.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name manuscan-ai.com www.manuscan-ai.com;

    ssl_certificate /etc/letsencrypt/live/manuscan-ai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/manuscan-ai.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # File upload limits
        client_max_body_size 100M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### API Security

#### 1. Rate Limiting

```python
# backend/middleware/rate_limit.py
from fastapi import Request, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import redis

redis_client = redis.Redis(host='redis', port=6379, db=1)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        # Get current request count
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, 60, 1)  # 1 request per minute window
        else:
            count = int(current)
            if count >= 10:  # Max 10 requests per minute
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            redis_client.incr(key)
        
        response = await call_next(request)
        return response
```

#### 2. Input Validation

```python
# backend/validation.py
from pydantic import BaseModel, validator
from typing import Optional

class AnalysisRequest(BaseModel):
    min_thickness: Optional[float] = 2.0
    draft_angle: Optional[float] = 3.0
    max_file_size: Optional[int] = 100_000_000  # 100MB
    
    @validator('min_thickness')
    def validate_thickness(cls, v):
        if v <= 0 or v > 100:
            raise ValueError('Thickness must be between 0 and 100mm')
        return v
    
    @validator('draft_angle')
    def validate_draft_angle(cls, v):
        if v < 0 or v > 90:
            raise ValueError('Draft angle must be between 0 and 90 degrees')
        return v
```

---

## Scaling

### Horizontal Scaling

#### 1. Load Balancer Configuration

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - api

  api:
    build: ./backend
    environment:
      - WORKERS=2
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 3

  worker:
    build: ./backend
    command: celery worker -A tasks --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    deploy:
      replicas: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

#### 2. Auto-scaling with Kubernetes

```yaml
# k8s-hpa.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: manuscan-ai-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: manuscan-ai
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Scaling

#### 1. PostgreSQL with Read Replicas

```yaml
# docker-compose.db.yml
version: '3.8'

services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: manuscan
      POSTGRES_USER: manuscan
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf

  postgres-replica:
    image: postgres:15
    environment:
      PGUSER: replicator
      POSTGRES_PASSWORD: ${REPLICATION_PASSWORD}
      POSTGRES_PRIMARY_HOST: postgres-primary
      POSTGRES_PRIMARY_PORT: 5432
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
    command: |
      bash -c "
      until pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --host=postgres-primary --port=5432
      do
        echo 'Waiting for primary to connect...'
        sleep 1s
      done
      echo 'Backup done, starting replica...'
      chmod 0700 /var/lib/postgresql/data
      postgres
      "
    depends_on:
      - postgres-primary

volumes:
  postgres_primary_data:
  postgres_replica_data:
```

---

## Health Checks & Monitoring

### Health Check Endpoints

```python
# backend/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis
import torch

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies"""
    checks = {}
    
    # Database check
    try:
        # db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Redis check
    try:
        redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # GPU check
    try:
        if torch.cuda.is_available():
            checks["gpu"] = f"healthy: {torch.cuda.get_device_name(0)}"
        else:
            checks["gpu"] = "not available"
    except Exception as e:
        checks["gpu"] = f"unhealthy: {str(e)}"
    
    # Model check
    try:
        # Load and test model
        checks["model"] = "healthy"
    except Exception as e:
        checks["model"] = f"unhealthy: {str(e)}"
    
    overall_status = "healthy" if all("healthy" in status for status in checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow()
    }
```

### Deployment Checklist

#### Pre-deployment

- [ ] Code review completed
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks meet requirements
- [ ] Security scan completed
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] SSL certificates obtained
- [ ] Database migrations ready
- [ ] Monitoring dashboards configured

#### Deployment

- [ ] Blue-green deployment strategy
- [ ] Database backup created
- [ ] Rolling deployment with health checks
- [ ] Load balancer configuration updated
- [ ] CDN cache invalidated
- [ ] Monitoring alerts configured
- [ ] Log aggregation working

#### Post-deployment

- [ ] Health checks passing
- [ ] Performance metrics within SLA
- [ ] Error rates acceptable
- [ ] User acceptance testing
- [ ] Rollback plan tested
- [ ] Documentation updated
- [ ] Team notified

---

## Troubleshooting

### Common Issues

#### 1. High Memory Usage

```bash
# Check memory usage
docker stats

# Optimize model loading
export CUDA_CACHE_DISABLE=1
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

#### 2. GPU Out of Memory

```python
# backend/gpu_management.py
import torch

def clear_gpu_cache():
    """Clear GPU memory cache"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

def get_gpu_memory_usage():
    """Get current GPU memory usage"""
    if torch.cuda.is_available():
        return {
            'allocated': torch.cuda.memory_allocated(),
            'cached': torch.cuda.memory_reserved(),
            'max_allocated': torch.cuda.max_memory_allocated()
        }
    return None
```

#### 3. Slow Analysis Performance

```python
# Performance profiling
import cProfile
import pstats

def profile_analysis(func):
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)
        
        return result
    return wrapper
```

For additional support and advanced deployment scenarios, please refer to our [support documentation](../SUPPORT.md) or contact the development team.
