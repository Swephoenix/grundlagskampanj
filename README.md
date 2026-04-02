# SMTP sender

Detta projekt innehaller nu en minimal lokal SMTP-tjanst som skickar HTML-mejl via din riktiga SMTP-server.

## Filer

- `smtp_server.py`: lokal HTTP-tjanst och CLI for utskick
- `.env.example`: mall for SMTP- och avsandarkonfiguration
- `email.html`: e-postanpassad HTML-mall

## Konfiguration

Skapa `.env` utifran `.env.example` och fyll i riktiga uppgifter:

```env
SMTP_HOST=nesaku.oderland.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USERNAME=din-brevlada@doman.se
SMTP_PASSWORD=ditt-losenord
MAIL_FROM=din-brevlada@doman.se
MAIL_FROM_NAME=Ambition Sverige
SERVER_HOST=127.0.0.1
SERVER_PORT=8080
```

## Starta servern

```bash
python3 smtp_server.py
```

Den exponerar:

- `GET /health`
- `POST /send`

## Skicka mejl via HTTP

```bash
curl -X POST http://127.0.0.1:8080/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["mottagare@example.com"],
    "subject": "Inbjudan till forelasning",
    "html_file": "email.html",
    "text": "Om HTML inte visas, oppna mejlet i en klient som visar HTML."
  }'
```

## Skicka mejl via CLI

```bash
python3 smtp_server.py send \
  --to mottagare@example.com \
  --subject "Inbjudan till forelasning" \
  --html-file email.html \
  --text "HTML-version finns i mejlet."
```

## Om bilder

Om `email.html` refererar till lokala bilder i samma projektmapp, forsoker skriptet automatiskt lagga dem som inline-bilagor med CID. Det gor att bilderna kan visas utan publika bild-URL:er, beroende pa mottagarens mejlklient.
