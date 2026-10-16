import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs folder if not exists
os.makedirs("logs", exist_ok=True)

# Logger setup
logger = logging.getLogger("FastAPI-Logger")
logger.setLevel(logging.INFO)

# Format: Time - Level - Message
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# File Handler - saves to logs/app.log
file_handler = RotatingFileHandler("logs/app.log", maxBytes=5*1024*1024, backupCount=3)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Console Handler - shows in terminal
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Add both handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)