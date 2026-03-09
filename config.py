"""Configuration module for FAP Discord Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_COMMAND_PREFIX = os.getenv("DISCORD_COMMAND_PREFIX", "!")

# FAP Credentials
FAP_USERNAME = os.getenv("FAP_USERNAME")
FAP_PASSWORD = os.getenv("FAP_PASSWORD")

# Encryption
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# FlareSolverr Configuration
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191/v1")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "fap.db"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "fap_bot.log"))

# Scheduler
SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "Asia/Ho_Chi_Minh")

# Notification Channel
DEFAULT_CHANNEL_ID = os.getenv("DEFAULT_CHANNEL_ID")

# Check Intervals (in seconds)
ATTENDANCE_CHECK_INTERVAL = int(os.getenv("ATTENDANCE_CHECK_INTERVAL", "300"))
GRADE_CHECK_INTERVAL = int(os.getenv("GRADE_CHECK_INTERVAL", "3600"))
APPLICATION_CHECK_INTERVAL = int(os.getenv("APPLICATION_CHECK_INTERVAL", "3600"))
EXAM_CHECK_INTERVAL = int(os.getenv("EXAM_CHECK_INTERVAL", "3600"))

# Keep-Alive Heartbeat Configuration
HEARTBEAT_INTERVAL_MINUTES = int(os.getenv("HEARTBEAT_INTERVAL_MINUTES", "12"))
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "30"))
HEARTBEAT_MAX_RETRIES = int(os.getenv("HEARTBEAT_MAX_RETRIES", "2"))
HEARTBEAT_RETRY_DELAY_SECONDS = int(os.getenv("HEARTBEAT_RETRY_DELAY_SECONDS", "5"))
HEARTBEAT_CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("HEARTBEAT_CIRCUIT_BREAKER_THRESHOLD", "3"))
HEARTBEAT_CIRCUIT_BREAKER_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_CIRCUIT_BREAKER_TIMEOUT_SECONDS", "300"))

# FAP URLs
FAP_BASE_URL = "https://fap.fpt.edu.vn"
FAP_LOGIN_URL = f"{FAP_BASE_URL}/Account/Login.aspx"
FAP_SCHEDULE_URL = f"{FAP_BASE_URL}/Schedule.aspx"
FAP_GRADES_URL = f"{FAP_BASE_URL}/Grade/StudentGrade.aspx"
FAP_EXAMS_URL = f"{FAP_BASE_URL}/Exam/ExamList.aspx"
FAP_APPLICATIONS_URL = f"{FAP_BASE_URL}/Application/StudentApplication.aspx"

# Discord Embed Colors
COLOR_SUCCESS = 0x00ff00
COLOR_WARNING = 0xffff00
COLOR_ERROR = 0xff0000
COLOR_INFO = 0x00bfff
COLOR_EXAM = 0x9b59b6
COLOR_GRADE = 0x00ff00

# Validation
def validate_config() -> list[str]:
    """Validate required configuration values."""
    errors = []

    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN is required")
    if not ENCRYPTION_KEY:
        errors.append("ENCRYPTION_KEY is required (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')")

    return errors
