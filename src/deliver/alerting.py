"""
Failure alerting, per the outline's Q13 (email). This is intentionally
dead simple and has NO dependency on anything else in src/ succeeding —
if the main pipeline is broken, this must still be able to fire.
"""

from __future__ import annotations
import os
import smtplib
import logging
import traceback
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_failure_alert(error: Exception, to_address: str) -> None:
    try:
        sender = os.environ["GMAIL_ADDRESS"]
        password = os.environ["GMAIL_APP_PASSWORD"]

        body = (
            f"The daily macro brief pipeline failed.\n\n"
            f"Error: {error}\n\n"
            f"Traceback:\n{traceback.format_exc()}\n\n"
            f"Check the Actions log for the full run."
        )
        msg = MIMEText(body)
        msg["Subject"] = "⚠️ Daily Macro Brief FAILED to send"
        msg["From"] = sender
        msg["To"] = to_address

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        logger.info("Failure alert sent")
    except Exception as e:
        # If even the alert fails, log loudly — this is the last line of defence.
        logger.critical("FAILURE ALERT ITSELF FAILED TO SEND: %s", e)
