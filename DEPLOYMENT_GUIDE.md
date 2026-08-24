# Deployment Guide

This guide covers production deployment for Railway (backend) and Vercel (frontend).

---

## Railway Backend Deployment

### Prerequisites

- GitHub account with repository
- Railway account (free tier available)
- PostgreSQL database (Railway provides managed PostgreSQL)
- Redis instance (Railway provides managed Redis)

### Step 1: Connect Repository

1. Visit [Railway](https://railway.app/)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects Python/FastAPI

### Step 2: Configure Environment Variables

In Railway dashboard, add all variables from `.env.example`:

```env
# Database
DATABASE_URL=postgresql://user:password@host.railway.internal:5432/railway

# Authentication
JWT_SECRET=<generate-secure-random-string>
JWT_EXPIRATION_MINUTES=60
BCRYPT_ROUNDS=12

# Email
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=noreply@yourdomain.com

# Google Calendar
GOOGLE_CLIENT_ID=xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://your-backend.railway.app/api/v1/calendar/callback
GOOGLE_SCOPES=https://www.googleapis.com/auth/calendar.events

# AI/LLM
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_TIMEOUT_SECONDS=30

# Redis
REDIS_URL=redis://default:password@redis.railway.internal:6379
CELERY_BROKER_URL=redis://default:password@redis.railway.internal:6379
CELERY_RESULT_BACKEND=redis://default:password@redis.railway.internal:6379

# Application
ENVIRONMENT=production
DEBUG=False
FRONTEND_URL=https://your-frontend.vercel.app
BACKEND_URL=https://your-backend.railway.app
API_VERSION=v1

# Slot Management
SLOT_HOLD_MINUTES=10
MAX_APPOINTMENTS_PER_DAY=20
DEFAULT_SLOT_DURATION_MINUTES=30

# Notifications
REMINDER_HOURS_BEFORE=24
MEDICATION_REMINDER_TIME=09:00
EMAIL_MAX_RETRIES=3
EMAIL_RETRY_DELAY_SECONDS=300
```

### Step 3: Build Commands

Railway auto-detects, but you can override in `railway.toml`:

```toml
[build]
builder = "NIXPACKFILE"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

Or create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 4: Database Setup

1. In Railway, click "New" → "Database" → "PostgreSQL"
2. Railway auto-provisions `DATABASE_URL`
3. Run migrations:
```bash
railway run alembic upgrade head
```

### Step 5: Redis Setup

1. In Railway, click "New" → "Redis"
2. Railway auto-provisions `REDIS_URL`
3. No additional configuration needed

### Step 6: Start Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Railway sets `$PORT` automatically.

### Step 7: Celery Worker

Create a separate service for Celery:

1. In Railway, click "New" → "Empty Service"
2. Set start command:
```bash
celery -A app.background_jobs.tasks worker --loglevel=info
```
3. Add same environment variables
4. Link to same repository

### Step 8: Domain Configuration

1. In Railway, go to "Settings" → "Domains"
2. Add custom domain: `api.yourdomain.com`
3. Configure DNS (Railway provides CNAME)

---

## Vercel Frontend Deployment

### Prerequisites

- Vercel account (free tier available)
- Frontend code in repository

### Step 1: Connect Repository

1. Visit [Vercel](https://vercel.com/)
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Select frontend directory (if monorepo)

### Step 2: Configure Environment Variables

In Vercel dashboard, add:

```env
# API Configuration
NEXT_PUBLIC_API_URL=https://your-backend.railway.app/api/v1

# Google OAuth
NEXT_PUBLIC_GOOGLE_CLIENT_ID=xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com

# Application
NEXT_PUBLIC_APP_NAME="Healthcare Appointment System"
NEXT_PUBLIC_APP_URL=https://your-frontend.vercel.app
```

### Step 3: Build Settings

Vercel auto-detects Next.js/React. Override if needed:

**Framework Preset**: Create React App / Next.js / Vite

**Build Command**:
```bash
npm run build
```

**Output Directory**:
```bash
dist
```

**Install Command**:
```bash
npm install
```

### Step 4: API URL Configuration

Ensure frontend API calls use environment variable:

```typescript
// frontend/src/config.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
```

### Step 5: Domain Configuration

1. In Vercel, go to "Settings" → "Domains"
2. Add custom domain: `app.yourdomain.com`
3. Configure DNS (Vercel provides nameservers)

---

## Production Verification Checklist

### Backend

- [ ] Environment variables set correctly
- [ ] Database migrations applied
- [ ] Redis connection working
- [ ] Celery worker running
- [ ] Email service configured
- [ ] Google Calendar OAuth working
- [ ] LLM API responding
- [ ] HTTPS enabled
- [ ] CORS configured for frontend domain
- [ ] Rate limiting enabled
- [ ] Error logging configured (Sentry, etc.)

### Frontend

- [ ] API URL points to production backend
- [ ] Environment variables set
- [ ] Build successful
- [ ] HTTPS enabled
- [ ] Custom domain configured
- [ ] OAuth redirect URIs updated

### Database

- [ ] PostgreSQL version 14+
- [ ] Backups enabled (daily)
- [ ] Connection pooling configured
- [ ] Indexes created
- [ ] Read replicas (if needed)

### Security

- [ ] JWT_SECRET is strong random string
- [ ] DEBUG=False
- [ ] CORS restricted to frontend domain
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (parameterized queries)
- [ ] XSS protection (React default)
- [ ] CSRF protection (state parameter in OAuth)

### Monitoring

- [ ] Error tracking (Sentry, LogRocket)
- [ ] Uptime monitoring (UptimeRobot, Pingdom)
- [ ] Performance monitoring (New Relic, Datadog)
- [ ] Log aggregation (Railway logs, external service)

### Testing

- [ ] User registration works
- [ ] Login works
- [ ] Appointment booking works
- [ ] Email notifications sent
- [ ] Google Calendar events created
- [ ] AI summaries generated
- [ ] Doctor leave handling works
- [ ] Medication reminders scheduled
- [ ] Admin dashboard accessible

### Documentation

- [ ] README updated with production URLs
- [ ] API documentation accessible
- [ ] User guide available
- [ ] Support contact information provided

---

## Rollback Plan

### Backend Rollback

1. In Railway, go to "Deployments"
2. Click previous successful deployment
3. Click "Promote to Production"

### Frontend Rollback

1. In Vercel, go to "Deployments"
2. Click previous successful deployment
3. Click "Promote to Production"

### Database Rollback

1. In Railway, go to PostgreSQL
2. Restore from point-in-time backup
3. Re-run migrations if schema changed

---

## Disaster Recovery

### Backup Strategy

- **Database**: Daily automated backups (Railway default)
- **Code**: GitHub version control
- **Environment Variables**: Documented in secure vault
- **OAuth Tokens**: Re-authorizable (not backed up)

### Recovery Steps

1. **Database Loss**: Restore from backup, re-run migrations
2. **Code Loss**: Re-deploy from GitHub
3. **Environment Loss**: Re-add from documentation
4. **OAuth Loss**: Users re-authorize (provide instructions)

---

## Cost Estimation

### Railway (Free Tier)

- Backend: 500 hours/month free
- PostgreSQL: 1GB free
- Redis: 256MB free
- **Estimated Cost**: $0-5/month (small scale)

### Vercel (Free Tier)

- Frontend: 100GB bandwidth/month free
- **Estimated Cost**: $0/month (small scale)

### External Services

- SendGrid: 100 emails/day free
- Groq: Free tier available
- Google Calendar: Free

**Total Estimated Monthly Cost**: $0-20 (small scale)

---

## Scaling Plan

### Phase 1: 0-1000 Users

- Railway free tier
- Single backend instance
- Single Celery worker
- Managed PostgreSQL

### Phase 2: 1000-10000 Users

- Railway paid tier ($5-20/month)
- Multiple backend instances
- Multiple Celery workers
- PostgreSQL with read replicas
- Redis cluster

### Phase 3: 10000+ Users

- Migrate to AWS/GCP
- Kubernetes orchestration
- Auto-scaling groups
- Load balancer
- Multi-region deployment
