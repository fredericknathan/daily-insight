"""
Gmail SMTP + app password, per the outline's §3.4 decision. Requires:
  - 2FA enabled on the sending Gmail account
  - An app password generated at myaccount.google.com/apppasswords
  - GMAIL_ADDRESS and GMAIL_APP_PASSWORD set as repo secrets
"""

from __future__ import annotations
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_brief(subject: str, html_body: str, heatmap_path: str, to_address: str) -> None:
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_address

    alt = MIMEMultipart("alternative")
    msg.attach(alt)

    # Plaintext fallback — required by the outline's email build rules,
    # some clients/previews render this instead of the HTML.
    plaintext = "Your Daily Macro Brief is best viewed in an HTML-capable email client."
    alt.attach(MIMEText(plaintext, "plain"))
    alt.attach(MIMEText(html_body, "html"))

    with open(heatmap_path, "rb") as f:
        img = MIMEImage(f.read())
        img.add_header("Content-ID", "<heatmap>")
        img.add_header("Content-Disposition", "inline", filename="heatmap.png")
        msg.attach(img)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

    logger.info("Brief sent to %s", to_address)
