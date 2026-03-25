# Wartungssoftware MVP

Eine lauffähige MVP-Webanwendung gemäß `PRODUCT_DEFINITION.md` mit:

- Login (Admin/Mitarbeiter-Basis)
- Kundenverwaltung
- Anlagenverwaltung
- automatischer Erzeugung fälliger Wartungsvorgänge
- Dashboard für heute/überfällig/diese Woche
- manuellem und vorgangsgebundenem Start von Wartungsprotokollen
- Protokollhistorie

## Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Dann im Browser öffnen:

- `http://localhost:5000/login`

Demo-Login:

- E-Mail: `admin@example.com`
- Passwort: `admin123`

Die App legt beim Start automatisch `app.db` an und seedet Demo-Daten.
