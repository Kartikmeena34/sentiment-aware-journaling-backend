# Serein

**Sentiment-Aware Journaling Application — v1.0**

A mobile-first emotional well-being platform that transforms journal entries into epistemically grounded emotional insights using confidence-weighted sentiment analytics and comparative pattern detection.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-production-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Table of Contents

1. [Overview](#overview)
2. [Core Research Contribution](#core-research-contribution)
3. [Features](#features)
4. [Architecture](#architecture)
5. [Technology Stack](#technology-stack)
6. [Getting Started](#getting-started)
7. [API Documentation](#api-documentation)
8. [Analytics Logic](#analytics-logic)
9. [Model Details](#model-details)
10. [Deployment](#deployment)
11. [Testing](#testing)
12. [Project Structure](#project-structure)
13. [Roadmap](#roadmap)

---

## Overview

Serein helps users gain meaningful insight into their emotional patterns through AI-powered journaling — going beyond surface-level emotion labeling into comparative, confidence-qualified analytics.

Unlike traditional emotion detection apps that mirror user input back ("You're feeling happy"), Serein surfaces patterns that users could not see themselves: baseline shifts, entropy trends, and emotional arc detection across journaling sessions.

### The Core Problem

Traditional sentiment apps commit **emotion mirroring** — presenting classifier outputs as emotional facts without uncertainty qualification. If a model predicts "joy" with 52% confidence, telling the user "you're feeling joyful" is epistemically dishonest.

### The Solution

A **confidence-weighted sentiment analytics framework** that:

- Weights all emotional signals by model confidence before aggregating
- Uses Shannon entropy to measure emotional diversity, not just dominant emotion
- Compares current state to a rolling 30-day baseline to surface real change
- Distinguishes low-confidence observations from high-confidence insights
- Detects emotional arc across guided reflection sessions

---

## Core Research Contribution

This application accompanies an academic paper submitted to **HCI International 2026** (Springer LNCS, Scopus-indexed):

> *"Beyond Emotion Mirroring: Design and Implementation of a Confidence-Weighted Sentiment Analytics Framework for Mobile Journaling"*

**Key contributions:**
- Confidence-weighted emotion aggregation replacing naive averaging
- Shannon entropy as an operational measure of emotional range
- Rolling baseline comparison with ±20% significance thresholding
- Two-stream analytics: free-form journaling + guided Reflect mode
- Crisis detection logic using sustained distress signals (not single-entry flags)
- Fine-tuned `j-hartmann/emotion-english-distilroberta-base` on 219 domain-specific labeled entries

---

## Features

### Authentication & Security

- JWT-based authentication (24h access token, 30-day refresh)
- Automatic token refresh with queued request handling
- Secure token storage via AsyncStorage
- Auto-logout on refresh token expiration

### Journaling — Free-Form Mode

- Text journal entry creation
- Synchronous AI emotion detection via HuggingFace Inference API
- 7-label emotion classification: joy, sadness, fear, anger, disgust, surprise, neutral
- Confidence scoring per entry
- Entry saved regardless of AI availability (graceful degradation)

### Reflect Mode (Guided Journaling)

- Claude API-backed conversational journaling
- Personalized follow-up questions based on conversation history and time of day
- Emotional arc detection across the session (e.g., fear → neutral = resolution)
- Separate data model from free-form journals for independent analytics
- Session ends when the user decides — no forced structure

### Insights Engine

- **Baseline Shifts:** "Your joy has increased 45% compared to your usual baseline"
- **Emotional Range Trend:** "Your emotional range is expanding / narrowing"
- **Within-Week Trends:** Linear regression slope over current week entries
- **High Diversity Detection:** Entropy-based wide range observation
- **Reflect Arc Insight:** "You moved from anxiety to calm across today's reflection"
- **Divergence Insight:** "Your reflections surface more fear than your journals this week"
- Confidence badge visible when weekly confidence < 0.6

### Crisis Detection

- Triggered when: sadness + fear weighted score > 0.65 AND 4+ entries with sadness or fear as dominant emotion in 7 days
- Warm amber-toned supportive message — no clinical language, no helpline numbers
- Checked on both InsightsScreen and EmotionFeedbackScreen

### Progressive Intimacy

- Tone adjusts based on entry count (Entry 1–5 → neutral; 6–15 → warmer; 16+ → warm)
- Applied across Journal screen greeting, EmotionFeedback messages, and Reflect opening questions
- Prevents the "instant best friend" problem on first visit

### Analytics Dashboard

- Confidence-weighted weekly emotion distribution (animated bar charts)
- Emotional entropy visualization with interpreted range label
- Trend indicators (↑ increasing, ↓ decreasing) using linear regression
- Baseline shift display when 30-day history is available

### UX Details

- Warm journal aesthetic throughout: background `#FDF6EC`, accent `#C17B4E`
- Ruled paper lines on journal entry screens
- Emoji stamps per emotion on entry detail
- Insight unlock progress bars for new users
- Confidence tooltip modal explaining model uncertainty
- Pull-to-refresh on Trends, Insights, and History screens
- First-time user hint on Journal screen (disappears after first entry)
- Progressive entry count indicator: "1 of 3 entries this week"

---

## Architecture

### System Overview

```
┌─────────────────────┐
│      Serein     │
│    (React Native)   │
└────────┬────────────┘
         │ HTTPS/REST
         ▼
┌─────────────────────┐
│   Django Backend    │
│   (REST API)        │
└────┬────────────────┘
     │
  ┌──┴──────────┐
  ▼             ▼
┌──────────┐  ┌──────────────────────────┐
│PostgreSQL│  │   HuggingFace API        │
│(Render)  │  │ j-hartmann DistilRoBERTa │
└──────────┘  └──────────────────────────┘
                        +
              ┌──────────────────────────┐
              │   Anthropic Claude API   │
              │  (Reflect Mode only)     │
              └──────────────────────────┘
```

### Data Flow — Free-Form Journal

```
User writes entry
    → POST /api/journal/create/
    → Journal saved to DB immediately
    → Emotion detection via HuggingFace (async-safe — failure doesn't block save)
    → Analytics computed: weighted distribution, entropy, baseline comparison
    → Contextual message generated
    → Response: journal_id, dominant_emotion, confidence, contextual_message, has_insights
```

### Data Flow — Reflect Session

```
User enters Reflect mode
    → POST /api/reflect/start/ → Claude generates opening question
    → POST /api/reflect/message/ (repeated) → Claude reads full history, responds
    → POST /api/reflect/end/ → emotion detection on full conversation, arc computed
    → ReflectSession + ReflectMessages saved
    → EmotionFeedback screen shown as normal
```

### Key Backend Services

| File | Responsibility |
|------|----------------|
| `emotion_service.py` | HuggingFace API call, label extraction, confidence scoring |
| `analytics_service.py` | Weighted distribution, Shannon entropy, baseline computation, trend detection, crisis detection |
| `insight_service.py` | Priority-ordered human-readable insight generation |
| `views.py` | API endpoints with permission enforcement |
| `models.py` | Journal, ReflectSession, ReflectMessage schemas |

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React Native | 0.81.5 | Mobile framework |
| Expo | ~54.0.33 | Development platform |
| React Navigation | 7.x | Navigation (stack + bottom tabs) |
| Axios | 1.x | HTTP client with interceptors |
| AsyncStorage | 2.2.0 | Token and user data storage |
| Expo Linear Gradient | ~15.0.8 | UI gradients |
| Expo Haptics | ~15.0.8 | Tactile feedback |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Backend language |
| Django | 6.0.1 | Web framework |
| Django REST Framework | 3.14+ | API layer |
| PostgreSQL | 14+ | Production database |
| SQLite | — | Local development fallback |
| dj-database-url | — | DATABASE_URL parsing |
| djangorestframework-simplejwt | 5.x | JWT auth with blacklist |
| gunicorn | — | Production WSGI server |
| whitenoise | — | Static file serving |

### AI / ML

| Service | Model | Purpose |
|---------|-------|---------|
| HuggingFace Inference API | `j-hartmann/emotion-english-distilroberta-base` | 7-label emotion classification |
| Anthropic Claude API | `claude-haiku-4-5-20251001` | Reflect mode conversation |

### Infrastructure

| Service | Purpose |
|---------|---------|
| Render (free tier) | Backend hosting |
| PostgreSQL on Render | Production database |
| UptimeRobot | Pings backend every 5 minutes to prevent cold starts |
| EAS (Expo Application Services) | Android APK builds |

---

## Getting Started

### Prerequisites

**Backend:**
- Python 3.10+
- PostgreSQL 14+ (or use SQLite for local dev)
- pip

**Frontend:**
- Node.js 16+
- npm or yarn
- Expo CLI (`npm install -g expo-cli`)

**API Keys:**
- HuggingFace account — [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (Read access)
- Anthropic API key — required only if running Reflect mode

---

### Backend Setup

```bash
git clone https://github.com/Kartikmeena34/journaling-backend.git
cd journaling-backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

**Environment Variables**

Create `.env`:
```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/Serein_db
HF_TOKEN=your-huggingface-token
ANTHROPIC_API_KEY=your-anthropic-key
```

For local development without PostgreSQL, `DATABASE_URL` can be omitted — the app falls back to SQLite automatically.

**Run migrations and start:**
```bash
python manage.py migrate
python manage.py runserver
```

**Production start command (Render):**
```bash
python manage.py migrate && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --worker-class gthread --max-requests 100
```

The `--workers 1` flag is intentional: it prevents Render free-tier memory pressure from the HuggingFace model being loaded into multiple worker processes simultaneously.

---

### Frontend Setup

```bash
git clone https://github.com/Kartikmeena34/journaling-frontend.git
cd journaling-frontend

npm install
```

**Configure API URL**

Edit `src/service/api.js`:
```javascript
const BASE_URL = "http://localhost:8000";           // Local development
// const BASE_URL = "https://your-app.onrender.com"; // Production
```

**Start development server:**
```bash
npx expo start
```

- **Android emulator:** press `a`
- **iOS simulator:** press `i`
- **Physical device:** scan QR with Expo Go app

---

## API Documentation

### Authentication

#### Register
```http
POST /api/auth/register/
Content-Type: application/json

{
  "username": "kartik",
  "email": "kartik@example.com",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": { "id": 1, "username": "kartik", "email": "kartik@example.com" },
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{ "username": "kartik", "password": "SecurePass123" }
```

#### Refresh Token
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{ "refresh": "<refresh_token>" }
```

---

### Journal Endpoints

#### Create Journal Entry
```http
POST /api/journal/create/
Authorization: Bearer <access_token>

{ "text": "Today I finally understood what I've been afraid of." }
```

**Response:**
```json
{
  "journal_id": 42,
  "dominant_emotion": "fear",
  "confidence": 0.81,
  "contextual_message": "This entry feels different from your recent ones.",
  "has_insights": true
}
```

`contextual_message` is `null` when no meaningful deviation is detected. `has_insights` is `false` until the user has at least 3 entries in the current week.

#### Get Journal History
```http
GET /api/journal/history/
Authorization: Bearer <access_token>
```

---

### Analytics & Insights

#### Get Analytics (Trends Screen)
```http
GET /api/journal/analytics/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "weekly_distribution": { "fear": 0.42, "sadness": 0.30, "neutral": 0.18, "joy": 0.10 },
  "emotional_entropy": 1.72,
  "trends": { "fear": "increasing", "joy": "decreasing" },
  "data_sufficiency": true,
  "weekly_confidence": 0.77,
  "baseline_shifts": {
    "fear": { "change": 0.38, "direction": "increased", "magnitude": 38 }
  },
  "range_trend": { "trend": "contracting", "change": -0.19 },
  "crisis_flag": false
}
```

#### Get Insights (Insights Screen)
```http
GET /api/journal/insights/
Authorization: Bearer <access_token>
```

**Optional query param:** `?format=single` returns one string instead of a card array.

**Response:**
```json
{
  "insights": [
    {
      "type": "baseline_shift",
      "title": "Fear Has Increased",
      "message": "Your fear has increased by 38% compared to your usual baseline over the last month.",
      "confidence": 0.77
    },
    {
      "type": "range_contracting",
      "title": "Emotional Range Narrowing",
      "message": "Your recent entries show less emotional variety than before.",
      "confidence": 0.77
    }
  ],
  "data_sufficiency": true,
  "weekly_confidence": 0.77
}
```

---

### Reflect Mode Endpoints

```http
POST /api/reflect/start/          → Begin session, return first Claude question
POST /api/reflect/message/        → Send user reply, return next question
POST /api/reflect/end/            → Close session, run emotion detection on full arc
GET  /api/reflect/history/        → Past reflect sessions
```

---

## Analytics Logic

### Confidence-Weighted Distribution

Raw emotion probabilities are weighted by model confidence before aggregation, preventing low-confidence predictions from distorting the distribution.

```python
weighted_score = emotion_probability × confidence_score
aggregate[emotion] += weighted_score
normalized[emotion] = aggregate[emotion] / total_confidence
```

### Shannon Entropy (Emotional Range)

```python
entropy = -Σ (p × log₂(p))   for all emotions with p > 0
```

| Entropy | Interpretation |
|---------|----------------|
| ≥ 2.0 | Wide emotional range |
| 1.0 – 2.0 | Moderate range |
| < 1.0 | Focused / narrow range |

### Rolling Baseline Comparison

```python
baseline_dist = compute_weighted_distribution(last_30_days)
current_dist  = compute_weighted_distribution(last_7_days)
shift = (current - baseline) / baseline   # Reported as percentage
```

Shifts below ±20% are suppressed as statistical noise.

### Trend Detection (Linear Regression)

Applied to per-emotion weighted time series within the current week:

```python
slope = (n×Σxy - Σx×Σy) / (n×Σx² - (Σx)²)
# slope > 0.02  → "increasing"
# slope < -0.02 → "decreasing"
```

Requires minimum 4 entries and at least 3 data points per emotion.

### Crisis Detection

```python
crisis_flag = (
    sadness_weighted + fear_weighted > 0.65
    AND count(entries where dominant in ['sadness', 'fear'], last 7 days) >= 4
)
```

Both conditions must hold simultaneously. Designed to avoid false positives on isolated difficult days.

### Data Sufficiency Thresholds

| Insight Type | Minimum Requirement |
|---|---|
| Basic analytics | 3 valid entries (last 7 days) |
| Within-week trend | 4 entries (last 7 days) |
| Baseline comparison | 7 entries (last 30 days) |
| Range trend | 3 entries in each of: recent 7 days + prior 23 days |
| Crisis flag | 4 entries (last 7 days) + weighted score threshold |

---

## Model Details

**Model:** [`j-hartmann/emotion-english-distilroberta-base`](https://huggingface.co/j-hartmann/emotion-english-distilroberta-base)

**Labels (7):** joy, sadness, fear, anger, disgust, surprise, neutral

**Fine-tuning:** The base model was fine-tuned on 219 labeled journal entries collected via Google Forms. Self-reported labels from users were used as ground truth. Class imbalance (joy=52, sadness=37, fear=37, disgust=25, neutral=25, surprise=25, anger=18) was addressed using weighted loss during fine-tuning.

**Inference:** Via HuggingFace Inference API (synchronous call, 20s timeout, graceful degradation on failure).

**Deployment note:** The model is not loaded in-process. All inference runs through the HuggingFace hosted API, which eliminates memory pressure on the Render free tier.

---

## Deployment

### Backend (Render Free Tier)

The backend is live at: `https://sentiment-aware-journaling-backend.onrender.com`

**Environment variables required on Render:**

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | Render PostgreSQL internal connection string |
| `HF_TOKEN` | HuggingFace API token (Read access) |
| `ANTHROPIC_API_KEY` | Required for Reflect mode |
| `DEBUG` | Set to `False` in production |

**Cold start mitigation:** UptimeRobot is configured to ping the backend every 5 minutes, keeping the Render free-tier instance warm.

**Gunicorn configuration for Render free tier:**
```bash
gunicorn backend.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 1 \
  --threads 2 \
  --worker-class gthread \
  --max-requests 100
```

### APK Build (Android)

```bash
npm install -g eas-cli
eas login
eas init
```

`eas.json`:
```json
{
  "build": {
    "preview": {
      "android": {
        "buildType": "apk"
      }
    }
  }
}
```

```bash
eas build --platform android --profile preview
```

Download the APK from the Expo dashboard once the build completes.

---

## Testing

### Backend Tests

Run the full test suite:
```bash
python manage.py test
```

**Current test coverage (6/6 passing):**

| Test | Description |
|---|---|
| `test_register_user` | User registration creates account |
| `test_login_returns_tokens` | Login returns valid access + refresh tokens |
| `test_refresh_token` | Refresh endpoint issues new access token |
| `test_journal_requires_auth` | Unauthenticated journal creation returns 401 |
| `test_create_journal_authenticated` | Authenticated creation returns expected fields |
| `test_analytics_structure` | Analytics endpoint returns all required keys |

### Manual Testing Checklist

**Authentication:**
- [ ] Register new account
- [ ] Login with valid credentials
- [ ] Login with invalid credentials (error message shown)
- [ ] Token auto-refresh on expiry
- [ ] Logout clears all stored tokens

**Journal Flow:**
- [ ] Create entry — emotion detection succeeds
- [ ] Create entry — HuggingFace unavailable (entry still saves)
- [ ] EmotionFeedback screen shows correct contextual message
- [ ] EmotionFeedback shows crisis message when threshold met

**Analytics:**
- [ ] Insights screen empty state (< 3 entries)
- [ ] Insights screen with sufficient data
- [ ] Trends screen animated bars
- [ ] Pull-to-refresh on Insights and Trends

**Reflect Mode:**
- [ ] Toggle between Journal and Reflect modes
- [ ] Conversation continues coherently across turns
- [ ] "I'm done" closes session and triggers EmotionFeedback

**Edge Cases:**
- [ ] Network error state on all screens (retry button)
- [ ] Server error state (500)
- [ ] Very long journal entry (>2000 chars, should be rejected)
- [ ] Empty journal entry (should be rejected client-side)

---

## Project Structure

### Backend

```
backend/
├── backend/
│   ├── settings.py         # Django config, JWT settings, DB config
│   ├── urls.py             # Root URL routing
│   ├── exceptions.py       # Custom DRF exception handler
│   └── wsgi.py
├── accounts/
│   ├── views.py            # register_user, login_user
│   └── urls.py
├── journals/
│   ├── models.py           # Journal, ReflectSession, ReflectMessage
│   ├── views.py            # create_journal, user_insights, journal_history, analytics
│   ├── urls.py
│   └── services/
│       ├── emotion_service.py      # HuggingFace API wrapper
│       ├── analytics_service.py   # Weighted distribution, entropy, baseline, crisis
│       └── insight_service.py     # Priority-ordered insight generation
├── manage.py
└── requirements.txt
```

### Frontend

```
src/
├── context/
│   └── AuthContext.js          # Global auth state, login/logout, token check
├── navigation/
│   └── AppNavigator.js         # Stack + Tab navigator setup
├── screens/
│   ├── LoginScreen.js
│   ├── RegisterScreen.js
│   ├── JournalScreen.js        # Free-form entry + Reflect mode toggle
│   ├── ReflectScreen.js        # Conversational journaling UI
│   ├── EmotionFeedbackScreen.js
│   ├── InsightsScreen.js       # Animated insight cards, crisis banner
│   ├── TrendScreen.js          # Emotion distribution, entropy, trend indicators
│   ├── ProfileScreen.js        # Stats, history, logout
│   ├── HistoryScreen.js
│   └── EntryDetailScreen.js    # Emoji stamp, ruled paper layout
├── service/
│   └── api.js                  # Axios instance, request/response interceptors, token refresh
├── theme/
│   ├── colors.js               # Warm journal palette (bg: #FDF6EC, accent: #C17B4E)
│   ├── tokens.js               # Spacing, radius, elevation
│   └── typography.js           # Title, section, body, caption
└── components/
    └── PrimaryButton.js
```

---

## Troubleshooting

**No insights showing:**  
User needs ≥ 3 entries in the last 7 days with valid emotion data. Check that HF_TOKEN is valid and HuggingFace API is reachable.

**Emotion detection always fails:**  
Check `HF_TOKEN` is set as an environment variable on Render. Verify the token has Read access on HuggingFace.

**Token errors on protected routes:**  
The Axios interceptor handles refresh automatically. If it fails (expired refresh token), the user is logged out. This is expected behavior after 30 days of inactivity.

**Render cold starts:**  
UptimeRobot should prevent most cold starts. If the backend is slow on first request, wait 30–60 seconds for the instance to wake.

**Android octagon border on EntryDetailScreen:**  
This is a known React Native issue with `borderRadius` on certain Android versions. The fix uses explicit `overflow: hidden` on the container — already applied.

**`--workers 1` seems too low:**  
Intentional for Render free tier. The HuggingFace API call (not the model itself) is the bottleneck, not compute. Single worker with 2 threads handles concurrent requests adequately within free-tier memory limits.

---

## Roadmap

### v1.1 — Post-Submission (May 2026)

- [ ] Journal streak tracking
- [ ] Weekly summary push notifications
- [ ] Dark mode
- [ ] Data export (JSON / CSV)
- [ ] Entry tagging and categories

### v2.0 — Q3 2026

- [ ] Voice journaling mode
- [ ] Photo attachment to entries
- [ ] Mood calendar heatmap
- [ ] Temporal pattern detection (by day of week, time of day)
- [ ] Multi-language support

### v3.0 — Q4 2026

- [ ] Predictive mood modeling
- [ ] Context-aware journaling prompts
- [ ] Web version (React)
- [ ] Secure data sharing with mental health professionals

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Contact

**Lead Developer:** Kartik Meena  
**GitHub:** [@Kartikmeena34](https://github.com/Kartikmeena34)  
**Email:** kartikmeena34@gmail.com


---

**Last Updated:** April 2026 | **Version:** 1.0.0 | **Status:** ✅ Production
