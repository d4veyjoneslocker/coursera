from __future__ import print_function

import base64
import os
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# ---------- EDIT THESE ----------
TO_EMAILS = ["drew@smearcase.com, joe@eatsmearcase.com"]
FROM_NAME = "SKUba"
SUBJECT = "Smearcase x SKUba Critical Inventory Updates (10.19.26)"
HTML_FILE = "smearcase_weekly_inventory_final.html"
# -------------------------------

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_credentials():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not os.path.exists("credentials.json"):
            raise FileNotFoundError(
                "\nMissing credentials.json.\n"
                "Download an OAuth Desktop App credentials file from Google Cloud, "
                "rename it credentials.json, and put it in this same folder.\n"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES,
        )
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def build_message(html):
    msg = MIMEText(html, "html", "utf-8")
    msg["To"] = ", ".join(TO_EMAILS)
    msg["From"] = FROM_NAME
    msg["Subject"] = SUBJECT

    return {
        "raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()
    }


def main():
    html_path = Path(__file__).resolve().parent / HTML_FILE

    if not html_path.exists():
        raise FileNotFoundError(
            f"\nCould not find {HTML_FILE}.\n"
            "Put the HTML file in the same folder as this script.\n"
        )

    if TO_EMAILS == "YOUR_EMAIL@gmail.com":
        raise ValueError(
            "\nOpen send_test_email.py and change TO_EMAIL "
            "to your own email address first.\n"
        )

    html = html_path.read_text(encoding="utf-8")

    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = build_message(html)

    result = (
        service.users()
        .messages()
        .send(userId="me", body=message)
        .execute()
    )

    print("\nSent!")
    print("Gmail message ID:", result["id"])
    print("Check your inbox on desktop and mobile.")


if __name__ == "__main__":
    main()
