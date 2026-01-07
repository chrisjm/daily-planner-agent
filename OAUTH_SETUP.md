# OAuth Setup Guide for Web Application Credentials

## Current Configuration

The project is configured to use **Web Application** credentials (not Desktop) for production deployment readiness.

## Google Cloud Console Setup

### 1. Configure Authorized Redirect URIs

In your [Google Cloud Console OAuth Client](https://console.cloud.google.com/apis/credentials/oauthclient/446969876220-hi1p08ebacdemiug2h2gq7sj1gpmht8f.apps.googleusercontent.com?project=turnkey-point-232117):

Add these **Authorized redirect URIs**:

```
http://localhost:8080/
http://localhost:8080
```

**Important Notes:**

- Port **8080** is the OAuth callback port (configured in `src/config/settings.py`)
- This is **NOT** the Streamlit port (8501)
- Include both with and without trailing slash
- Changes may take 5 minutes to propagate

### 2. Verify Credentials Type

Your `credentials.json` should contain:

```json
{
  "web": {
    "client_id": "...",
    "client_secret": "...",
    ...
  }
}
```

The code automatically detects "web" type and uses the fixed port (8080).

## Local Development Flow

1. **Start the app:**

   ```bash
   uv run streamlit run app.py
   ```

2. **First-time OAuth:**

   - Browser opens automatically to Google OAuth consent screen
   - Sign in and grant calendar permissions
   - Browser redirects to `http://localhost:8080/` (OAuth callback)
   - Success message appears
   - Token saved to `token.pickle`

3. **Subsequent runs:**
   - Uses cached `token.pickle`
   - No OAuth flow needed unless token expires

## Production Deployment

For production (e.g., deployed on a server):

### Option 1: Service Account (Recommended for Server)

- Create a Service Account in Google Cloud Console
- Grant calendar access to the service account
- Use service account JSON key instead of OAuth

### Option 2: Web Application OAuth

- Update redirect URIs to match production domain
- Example: `https://yourdomain.com/oauth/callback`
- Implement proper OAuth callback endpoint
- Store tokens securely (database, not pickle file)

## Troubleshooting

### Error: redirect_uri_mismatch

- Verify redirect URIs in Google Cloud Console match exactly
- Check for trailing slash differences
- Wait 5-10 minutes after changing settings
- Clear browser cache and try again

### Error: ModuleNotFoundError: google_auth_oauthlib

```bash
uv sync
```

### Token expired

Delete `token.pickle` and restart app to re-authenticate:

```bash
rm token.pickle
uv run streamlit run app.py
```

## Configuration

To change the OAuth redirect port, edit `src/config/settings.py`:

```python
OAUTH_REDIRECT_PORT = 8080  # Change to your preferred port
```

Then update Google Cloud Console redirect URIs to match.
