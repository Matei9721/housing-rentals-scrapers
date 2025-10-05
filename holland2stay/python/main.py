import os
import time
import re
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from dotenv import load_dotenv
import smtplib

URL = "https://www.holland2stay.com/residences?page=1&filter=Leiden&city%5Bfilter%5D=Leiden%2C6293"
CHECK_INTERVAL = 60  # seconds
BOOKING_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "booking_history.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "app.log")

load_dotenv()
GMAIL_FROM_EMAIL = os.getenv("GMAIL_FROM_EMAIL")
GMAIL_FROM_EMAIL_PASSWORD = os.getenv("GMAIL_FROM_EMAIL_PASSWORD")
GMAIL_TO_EMAILS = [email.strip() for email in os.getenv("GMAIL_TO_EMAIL", "").split(",") if email.strip()]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_last_booking():
    if not os.path.exists(BOOKING_HISTORY_FILE):
        return None
    try:
        with open(BOOKING_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and data:
                return data[-1]
    except Exception as e:
        logger.error(f"Error reading booking history: {e}")
    return None


def append_booking_change(count, timestamp):
    entry = {"count": count, "timestamp": timestamp, "url": URL}
    data = []
    if os.path.exists(BOOKING_HISTORY_FILE):
        try:
            with open(BOOKING_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except Exception as e:
            logger.error(f"Error reading booking history for append: {e}")
            data = []
    data.append(entry)
    try:
        with open(BOOKING_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing booking history: {e}")


def get_available_count():
    # Driver setup
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")  # suppress logs
    options.add_argument("--disable-logging")  # optional
    options.add_argument("--disable-notifications")  # Avoid push notifications
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(URL)

        time.sleep(5)  # Wait for JavaScript to load content

        soup = BeautifulSoup(driver.page_source, "html.parser")
        for label in soup.find_all("label", class_="checkbox_container"):
            if "Available to book" in label.get_text():
                logger.info(f"Found 'Available to book' label: {label.get_text()}")
                match = re.search(r"\((\d+)\)", label.get_text())
                if match:
                    number = int(match.group(1))
                    logger.info(f"Number of available bookings: {number}")
                else:
                    logger.info("No available bookings found.")
                    number = 0

                return number
                break
        logger.info("'Available to book' label not found or no number present.")
        return None
    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver. {e}")


def send_email(subject, body, to_emails):
    if not GMAIL_FROM_EMAIL or not GMAIL_FROM_EMAIL_PASSWORD or not to_emails:
        logger.error("Gmail credentials or recipient email(s) not set in .env file.")
        return
    try:
        message = f"Subject: {subject}\nTo: {', '.join(to_emails)}\nFrom: {GMAIL_FROM_EMAIL}\n\n{body}"
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_FROM_EMAIL, GMAIL_FROM_EMAIL_PASSWORD)
            server.sendmail(GMAIL_FROM_EMAIL, to_emails, message)
        logger.info(f"Notification email sent to: {', '.join(to_emails)}.")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


if __name__ == "__main__":
    last_entry = load_last_booking()
    last_count = last_entry["count"] if last_entry else None
    while True:
        try:
            count = get_available_count()
            now_iso = datetime.now().isoformat()
            if count is not None:
                logger.info(f"Available rentals for selected filters: {count}")
                if last_count is not None and count != last_count:
                    logger.info(f"Number changed from {last_count} to {count}!")
                    send_email(
                        "Holland2Stay Rentals Numbers Changed",
                        f"The count of available rentals has changed from {last_count} to {count}. Check {URL}",
                        GMAIL_TO_EMAILS
                    )
                    append_booking_change(count, now_iso)
                elif last_count is None:
                    append_booking_change(count, now_iso)
                last_count = count
            else:
                logger.warning("Could not find rental count.")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        time.sleep(CHECK_INTERVAL)