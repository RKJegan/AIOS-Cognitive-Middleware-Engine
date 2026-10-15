"""SMTP send + IMAP read. Credentials via security/credential_vault.py (keyring) -
register once with CredentialVault().save_credential('email', address, app_password)."""
import smtplib
import imaplib
import email as email_lib
from email.message import EmailMessage
from core.logger import get_logger
from core.narrator import narrate
from config.settings import Settings
from security.credential_vault import CredentialVault
from security.safety_layer import SafetyLayer

log = get_logger()


class EmailController:
    def __init__(self, settings=None, vault=None, safety=None):
        self.settings = settings or Settings.load()
        self.vault = vault or CredentialVault()
        self.safety = safety or SafetyLayer()

    def _creds(self):
        return self.vault.get_credential("email")

    def send(self, to_contact, body):
        creds = self._creds()
        if not creds:
            narrate("No email account saved. Register one with the credential vault first.")
            return {"status": "needs_credentials", "message": "No email credentials saved", "data": None}

        to_addr = self.settings.contacts.get((to_contact or "").lower().strip(), to_contact)
        check = self.safety.validate("send", f"email to {to_addr}")
        if check["status"] != "approved":
            return check

        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = creds["username"], to_addr, "Message from Cognitive Middleware"
        msg.set_content(body or "")
        try:
            with smtplib.SMTP_SSL(self.settings.email_smtp_host, self.settings.email_smtp_port) as s:
                s.login(creds["username"], creds["password"])
                s.send_message(msg)
            narrate(f"Email sent to {to_contact}")
            return {"status": "success", "message": f"Sent to {to_addr}", "data": None}
        except Exception as e:
            return {"status": "error", "message": f"Send failed: {e}", "data": None}

    def read(self, limit=5):
        creds = self._creds()
        if not creds:
            return {"status": "needs_credentials", "message": "No email credentials saved", "data": None}
        try:
            with imaplib.IMAP4_SSL(self.settings.email_imap_host) as m:
                m.login(creds["username"], creds["password"])
                m.select("inbox")
                _, data = m.search(None, "ALL")
                ids = data[0].split()[-limit:]
                subjects = []
                for i in reversed(ids):
                    _, msg_data = m.fetch(i, "(RFC822)")
                    msg = email_lib.message_from_bytes(msg_data[0][1])
                    subjects.append(msg.get("Subject", "(no subject)"))
            narrate(f"{len(subjects)} recent email(s)")
            return {"status": "success", "message": f"{len(subjects)} email(s)", "data": subjects}
        except Exception as e:
            return {"status": "error", "message": f"Read failed: {e}", "data": None}

    def handle(self, intent):
        action, name, dest = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        if action == "send":
            return self.send(name, dest)
        if action == "read":
            return self.read()
        return {"status": "unhandled", "message": f"Email action '{action}' not implemented yet", "data": None}
