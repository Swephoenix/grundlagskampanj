#!/usr/bin/env python3
import argparse
import csv
import json
import mimetypes
import os
import re
import smtplib
import ssl
import sys
import uuid
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = ROOT / ".env"


def load_env(env_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def env_config(env_path: Path) -> Dict[str, str]:
    config = load_env(env_path)
    merged = dict(config)
    merged.update({k: v for k, v in os.environ.items() if k.startswith("SMTP_") or k in {
        "MAIL_FROM",
        "MAIL_FROM_NAME",
        "SERVER_HOST",
        "SERVER_PORT",
        "DEFAULT_TO",
    }})
    return merged


def require(config: Dict[str, str], key: str) -> str:
    value = config.get(key, "").strip()
    if not value:
        raise ValueError(f"Missing required setting: {key}")
    return value


def parse_recipients(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_project_path(path_value: str, label: str) -> Path:
    file_path = (ROOT / path_value).resolve()
    try:
        file_path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} must point inside the project directory") from exc
    return file_path


def load_recipients_from_csv(csv_path: Path) -> List[str]:
    recipients: List[str] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            stripped = [cell.strip() for cell in row]
            if not any(stripped):
                continue
            for cell in stripped:
                if "@" in cell:
                    recipients.extend(parse_recipients(cell))
                    break

    deduped: List[str] = []
    seen = set()
    for recipient in recipients:
        if recipient not in seen:
            seen.add(recipient)
            deduped.append(recipient)
    return deduped


def parse_recipients_input(raw_recipients: object, csv_file: object = None) -> List[str]:
    if csv_file:
        csv_path = resolve_project_path(str(csv_file), "to_csv_file")
        if not csv_path.exists() or not csv_path.is_file():
            raise ValueError("to_csv_file does not exist")
        recipients = load_recipients_from_csv(csv_path)
    elif isinstance(raw_recipients, list):
        recipients = [str(item).strip() for item in raw_recipients if str(item).strip()]
    else:
        recipients = parse_recipients(str(raw_recipients or ""))

    if not recipients:
        raise ValueError("Missing recipient list")
    return recipients


def replace_local_images(html: str, base_dir: Path) -> Tuple[str, List[Tuple[Path, str]]]:
    attachments: List[Tuple[Path, str]] = []

    def repl(match: re.Match[str]) -> str:
        quote = match.group(1)
        src = match.group(2).strip()
        if re.match(r"^(https?:|cid:|data:)", src, re.IGNORECASE):
            return match.group(0)

        file_path = (base_dir / src).resolve()
        try:
            file_path.relative_to(base_dir.resolve())
        except ValueError:
            return match.group(0)

        if not file_path.exists() or not file_path.is_file():
            return match.group(0)

        cid = f"{uuid.uuid4().hex}@inline"
        attachments.append((file_path, cid))
        return f'src={quote}cid:{cid}{quote}'

    rewritten = re.sub(r'src=(["\'])([^"\']+)\1', repl, html, flags=re.IGNORECASE)
    return rewritten, attachments


def build_message(
    config: Dict[str, str],
    subject: str,
    html: str,
    text: str = "",
    base_dir: Path = ROOT,
) -> EmailMessage:
    sender_email = require(config, "MAIL_FROM")
    sender_name = config.get("MAIL_FROM_NAME", "").strip()
    from_header = f"{sender_name} <{sender_email}>" if sender_name else sender_email

    rewritten_html, inline_assets = replace_local_images(html, base_dir)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_header
    message.set_content(text or "This email contains HTML content.")
    message.add_alternative(rewritten_html, subtype="html")

    html_part = message.get_payload()[-1]
    for file_path, cid in inline_assets:
        mime_type, _ = mimetypes.guess_type(file_path.name)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        html_part.add_related(
            file_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            cid=f"<{cid}>",
            disposition="inline",
            filename=file_path.name,
        )

    return message


def validate_blind_only_headers(message: EmailMessage) -> None:
    for header in ("To", "Cc", "Bcc"):
        if message.get(header):
            raise ValueError(f"Recipient privacy check failed: '{header}' header must not be set")


def _send_with_server(server: smtplib.SMTP, message: EmailMessage, recipients: List[str]) -> None:
    for recipient in recipients:
        server.send_message(message, to_addrs=[recipient])


def send_via_smtp(config: Dict[str, str], message: EmailMessage, to_addresses: Iterable[str]) -> None:
    host = require(config, "SMTP_HOST")
    port = int(config.get("SMTP_PORT", "465"))
    username = require(config, "SMTP_USERNAME")
    password = require(config, "SMTP_PASSWORD")
    security = config.get("SMTP_SECURITY", "ssl").strip().lower()
    timeout = int(config.get("SMTP_TIMEOUT", "30"))
    recipients = list(to_addresses)

    if not recipients:
        raise ValueError("Missing recipient list")

    validate_blind_only_headers(message)

    if security not in {"ssl", "starttls", "none"}:
        raise ValueError("SMTP_SECURITY must be one of: ssl, starttls, none")

    if security == "ssl":
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as server:
            server.login(username, password)
            _send_with_server(server, message, recipients)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as server:
        server.ehlo()
        if security == "starttls":
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()
        server.login(username, password)
        _send_with_server(server, message, recipients)


def read_body(payload: bytes) -> Dict[str, object]:
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, object]) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class SMTPHandler(BaseHTTPRequestHandler):
    server_version = "MinimalSMTP/1.0"

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            json_response(self, 200, {"ok": True})
            return

        if self.path.rstrip("/") == "/":
            html = (
                "<html><body style='font-family:Arial,sans-serif'>"
                "<h1>SMTP Sender</h1>"
                "<p>POST JSON to <code>/send</code>.</p>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        json_response(self, 404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/send":
            json_response(self, 404, {"ok": False, "error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = read_body(self.rfile.read(content_length))
            config = env_config(self.server.env_path)

            recipients = payload.get("to") or config.get("DEFAULT_TO", "")
            to_addresses = parse_recipients_input(recipients, payload.get("to_csv_file"))

            subject = str(payload.get("subject") or "HTML email")
            html_file = payload.get("html_file")
            html_content = payload.get("html")
            text = str(payload.get("text") or "")

            if html_file:
                html_path = resolve_project_path(str(html_file), "html_file")
                html_content = html_path.read_text(encoding="utf-8")
                base_dir = html_path.parent
            elif html_content:
                html_content = str(html_content)
                base_dir = ROOT
            else:
                raise ValueError("Provide either 'html' or 'html_file'")

            message = build_message(
                config=config,
                subject=subject,
                html=str(html_content),
                text=text,
                base_dir=base_dir,
            )
            send_via_smtp(config, message, to_addresses)
            json_response(self, 200, {"ok": True, "sent_count": len(to_addresses), "subject": subject})
        except Exception as exc:  # pragma: no cover
            json_response(self, 400, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))


class ConfiguredHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: Tuple[str, int], handler_cls, env_path: Path):
        super().__init__(server_address, handler_cls)
        self.env_path = env_path


def serve(env_path: Path) -> None:
    config = env_config(env_path)
    host = config.get("SERVER_HOST", "127.0.0.1")
    port = int(config.get("SERVER_PORT", "8080"))
    server = ConfiguredHTTPServer((host, port), SMTPHandler, env_path)
    print(f"SMTP sender listening on http://{host}:{port}")
    server.serve_forever()


def cli_send(args: argparse.Namespace) -> None:
    config = env_config(Path(args.env))
    html_path = Path(args.html_file).resolve()
    html = html_path.read_text(encoding="utf-8")
    recipients = parse_recipients_input(args.to, args.to_csv_file)
    message = build_message(
        config=config,
        subject=args.subject,
        html=html,
        text=args.text,
        base_dir=html_path.parent,
    )
    send_via_smtp(config, message, recipients)
    print(f"Sent to {len(recipients)} recipient(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal SMTP sender for HTML emails.")
    parser.add_argument("--env", default=str(DEFAULT_ENV_PATH), help="Path to .env file")
    subparsers = parser.add_subparsers(dest="command")

    send_parser = subparsers.add_parser("send", help="Send one email directly from the CLI")
    recipient_group = send_parser.add_mutually_exclusive_group(required=True)
    recipient_group.add_argument("--to", help="Comma-separated recipient list")
    recipient_group.add_argument("--to-csv-file", help="CSV file inside the project directory with recipient emails")
    send_parser.add_argument("--subject", required=True, help="Email subject")
    send_parser.add_argument("--html-file", required=True, help="Path to HTML file")
    send_parser.add_argument("--text", default="", help="Plain-text fallback")

    args = parser.parse_args()
    if args.command == "send":
        cli_send(args)
        return

    serve(Path(args.env))


if __name__ == "__main__":
    main()
