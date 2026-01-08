"""Application configuration and constants."""

import os
from dotenv import load_dotenv

load_dotenv()

# Calendar settings
LOOKBACK_DAYS = 3
LOOKAHEAD_DAYS = 7

# Agent confidence threshold
CONFIDENCE_THRESHOLD = 0.75

# LLM model names
STRATEGIST_MODEL = "gemini-2.5-pro"  # Latest Pro model for reasoning
CLARIFICATION_MODEL = "gemini-2.0-flash-exp"  # Fast experimental for clarification
PLANNER_MODEL = "gemini-2.5-pro"  # Latest Pro model for planning

# API Keys (loaded from environment)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Google Calendar OAuth
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PICKLE_PATH = "token.pickle"
OAUTH_REDIRECT_PORT = 8080  # Fixed port for Web Application credentials

# Text truncation limits
EVENT_DESCRIPTION_MAX_LENGTH = 100
TASK_DESCRIPTION_MAX_LENGTH = 80
