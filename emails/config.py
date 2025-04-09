import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MAIL_SERVER = 'smtp.gmail.com'  # Use your email provider's SMTP server
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'rajeaditya999@gmail.com')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')  # Get from environment variable
MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME', 'rajeaditya999@gmail.com')
