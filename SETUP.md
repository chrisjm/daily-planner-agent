# Quick Setup Guide

## 1. Get API Keys

### Google Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

### Todoist API Token

1. Go to [Todoist Settings → Integrations](https://todoist.com/prefs/integrations)
2. Find "API token" section
3. Copy your token

### Google Calendar OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google Calendar API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop app"
   - Download the JSON file
   - Rename it to `credentials.json`
   - Place it in the project root directory

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:

```bash
GOOGLE_API_KEY=AIzaSy...your_actual_key
TODOIST_API_KEY=abc123...your_actual_token
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

## 3. Run the App

```bash
uv run streamlit run app.py
```

On first run:

- Browser will open for Google OAuth
- Sign in and grant calendar permissions
- Token saved to `token.pickle` for future use

## 4. Start Planning

Navigate to `http://localhost:8501` and try:

- "Help me plan tomorrow focusing on deep work"
- "I need to prepare for my presentation next week"
- "Balance my workload for the next 3 days"

## Troubleshooting

**Calendar authentication fails?**

- Delete `token.pickle` and restart
- Verify `credentials.json` is in project root

**Todoist errors?**

- Check your API token in `.env`
- Verify token at [Todoist Integrations](https://todoist.com/prefs/integrations)

**Import errors?**

```bash
uv sync
```

## File Checklist

Ensure these files exist:

- ✅ `.env` (with your actual keys)
- ✅ `credentials.json` (Google OAuth file)
- ✅ `app.py`, `graph.py`, `tools.py`

After first successful run:

- ✅ `token.pickle` (auto-generated)
