# 3D Auftragsmanager (self-hosted, Docker)

Bitte nicht verwenden, mit AI geschrieben!

Kleiner Web‑Service zum Managen von 3D‑Druckaufträgen:
- Kunden können **Link** und/oder **Bild** hochladen
- Du siehst alles in einer **Admin‑Queue**
- Du kannst **annehmen/ablehnen**, einen **Preis festlegen**, und der Kunde kann **Preis annehmen/ablehnen**
- Danach kannst du den Auftrag **abschließen**

## Quickstart

1. Projektordner öffnen
2. `.env` anlegen:

```bash
cp .env.example .env
```

3. In `.env` mindestens setzen:
- `SESSION_SECRET` (lang & zufällig)
- `ADMIN_PASSWORD` (stark)

4. Starten:

```bash
docker compose up -d --build
```

5. Öffnen:
- Kunden‑Seite: `http://localhost:8080/`
- Admin: `http://localhost:8080/admin`

> Daten & Uploads bleiben persistent in `./data` (Docker‑Volume).

## Workflow / Status

- **NEW**: Kunde hat eingereicht (Queue)
- **REJECTED**: von Admin abgelehnt
- **AWAITING_PRICE**: Admin hat angenommen, Preis fehlt noch
- **PRICE_SENT**: Preisangebot ist an Kunden raus (auf seiner Tracking‑Seite sichtbar)
- **PRICE_ACCEPTED / PRICE_REJECTED**: Kunde hat entschieden
- **COMPLETED**: erledigt & aus der aktiven Queue

## Produktion (empfohlen)

- Hinter einen Reverse Proxy (Caddy/Traefik/Nginx) mit HTTPS
- `.env` wirklich geheim halten
- Admin‑Passwort nie auf “admin/admin” lassen (die Realität ist grausam)

## Backup

Sichere einfach den `data/` Ordner:
- `data/app.db` (Datenbank)
- `data/uploads/` (Bilder)

## Lizenz

Mach damit, was du willst. 🙂
