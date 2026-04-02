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

Alla mottagare skickas som `Bcc`. Faltet `To` satts till avsandaradressen.

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

Du kan ocksa lasa mottagare fran en CSV-fil i projektmappen:

```bash
curl -X POST http://127.0.0.1:8080/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_csv_file": "mottagare.csv",
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

Eller via CSV-fil:

```bash
python3 smtp_server.py send \
  --to-csv-file mottagare.csv \
  --subject "Inbjudan till forelasning" \
  --html-file email.html \
  --text "HTML-version finns i mejlet."
```

## CSV-format

CSV-filen ska ligga i projektmappen. Skriptet letar efter den forsta cellen med en e-postadress pa varje rad och ignorerar tomma rader.

```csv
anna@example.com
bert@example.com
```

Det fungerar ocksa om filen har fler kolumner, sa lange varje rad innehaller en e-postadress.
Det finns en exempel-fil i projektet: `mottagare.example.csv`.

## Om bilder

Om `email.html` refererar till lokala bilder i samma projektmapp, forsoker skriptet automatiskt lagga dem som inline-bilagor med CID. Det gor att bilderna kan visas utan publika bild-URL:er, beroende pa mottagarens mejlklient.
