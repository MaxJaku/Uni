# Produktdefinition MVP – Wartungssoftware für private Kläranlagen

## 1) Zielbild

Ein Benutzer meldet sich an und sieht im Dashboard sofort:

- heute automatisch fällige Wartungen
- Status der heutigen Vorgänge
- direkte Suche nach Kunden/Anlagen
- Schnellaktion: **manuell neues Wartungsprotokoll starten**

**Kernfokus der Software**

1. Anlagen verwalten
2. Wartungsintervalle automatisch berechnen
3. fällige Wartungen erzeugen und anzeigen
4. Wartungsprotokolle durchführen
5. Historie revisionssicher speichern

---

## 2) Fachregeln (verbindlich für MVP)

### 2.1 Wann ist eine Wartung fällig?

Eine Anlage ist fällig, wenn `naechste_wartung_am <= heute`.

Berechnung von `naechste_wartung_am`:

- Basis: `letzte_regulaere_wartung_am + wartungsintervall_monate`
- Falls keine letzte reguläre Wartung existiert:
  - Startwert aus `inbetriebnahme + wartungsintervall_monate`
- Datum wird immer auf Kalendertag (ohne Uhrzeit) normalisiert.

### 2.2 Wann gilt ein Protokoll als reguläre Wartung?

Jedes Protokoll hat:

- `protokoll_typ` (z. B. `regulaer`, `zusatz`, `nachkontrolle`, `sonder`)
- `zaehlt_als_regulaere_wartung` (Boolean)

Regel:

- Nur wenn `zaehlt_als_regulaere_wartung = true`, beeinflusst das Protokoll den Wartungszyklus.

### 2.3 Wann wird die nächste Wartung neu berechnet?

Bei Abschluss eines Protokolls mit `zaehlt_als_regulaere_wartung = true`:

1. `letzte_regulaere_wartung_am = protokoll_datum`
2. `naechste_wartung_am = protokoll_datum + wartungsintervall_monate`

Bei `false` bleibt der bestehende Zyklus unverändert.

### 2.4 Was passiert bei Überfälligkeit?

- Ein geplanter Vorgang ist überfällig, wenn `faellig_am < heute` und `status != abgeschlossen`.
- Überfällige Vorgänge erscheinen im Dashboard in eigenem Filter.
- Überfälligkeit verändert den Intervall nicht automatisch.
- Erst ein abgeschlossenes Protokoll mit `zaehlt_als_regulaere_wartung = true` startet den Zyklus neu.

### 2.5 Automatik-Job (täglich)

Ein täglicher Hintergrundjob (z. B. 00:05 Uhr) führt aus:

1. Fällige Wartungen für `heute` erzeugen (falls nicht schon vorhanden).
2. Offene Vorgänge mit altem Fälligkeitsdatum als überfällig markieren.
3. Dashboard-Kennzahlen aktualisieren (heute fällig, überfällig, heute abgeschlossen, diese Woche fällig).

---

## 3) Protokollstruktur (MVP)

## 3.1 Pflichtfelder im Wartungsprotokoll

- Kunde
- Anlage
- Protokolldatum/-uhrzeit
- Bearbeiter (Benutzer)
- `protokoll_typ`
- `zaehlt_als_regulaere_wartung`
- Checklisten-Ergebnis
- Abschlussstatus (`abgeschlossen`, `abgebrochen`)
- Zusammenfassung / Bemerkungen

## 3.2 Messwerte (MVP-Kern)

Messwerte werden als Liste gespeichert:

- `bezeichnung`
- `wert`
- `einheit`

MVP-Regel:

- Validierung auf numerischen Wert, sofern Messwert numerisch definiert ist.
- Erfassung auch ohne vollständige Messwertliste zulässig, sofern mindestens ein Abschlusskommentar vorhanden ist.

## 3.3 Mängelkategorien (MVP)

Mindestens folgende Kategorien:

- Mechanik
- Elektrik
- Steuerung
- Sicherheit
- Sonstiges

Pro Mangel:

- Beschreibung
- Schweregrad (`niedrig`, `mittel`, `hoch`, `kritisch`)
- Empfehlung / Maßnahme

## 3.4 Abschlussarten

- **Reguläre Wartung abgeschlossen** (wirkt auf Zyklus, wenn Flag = true)
- **Zusatzkontrolle abgeschlossen** (wirkt nicht auf Zyklus)
- **Nachkontrolle abgeschlossen** (wirkt je nach Flag)
- **Abgebrochen** (wirkt nie auf Zyklus)

## 3.5 Kopplung an geplanten Vorgang

- Wird Protokoll aus geplanter Wartung gestartet, ist `geplante_wartung_id` gesetzt.
- Nach erfolgreichem Abschluss:
  - geplanter Vorgang auf `abgeschlossen`
  - `abgeschlossen_am` setzen

Manuell gestartete Protokolle haben `geplante_wartung_id = null`.

---

## 4) Bildschirmstruktur (MVP)

## 4.1 Login

- E-Mail + Passwort
- Passwort-zurücksetzen-Link
- Rollen: `admin`, `mitarbeiter`

## 4.2 Dashboard (Startseite nach Login)

### Kopfbereich (Kennzahlen)

- Heute fällig
- Überfällig
- Heute abgeschlossen
- Diese Woche fällig

### Hauptliste „Heutige Wartungen“

Spalten:

- Kunde
- Anlage
- Ort
- Fällig am
- Status
- Aktion: **Protokoll starten / öffnen**

### Schnellaktionen

- Kunde suchen
- Anlage suchen
- Neues Wartungsprotokoll starten

### Unterer Bereich

- zuletzt bearbeitete Protokolle
- offene Mängel

## 4.3 Kundenliste

- Suche (Name, Kundennummer, Ort)
- Kundenstammdaten
- Zugeordnete Anlagen
- Aktion: neues Wartungsprotokoll für Kunde/Anlage starten

## 4.4 Anlagendetail

- Stammdaten der Anlage
- Wartungsintervall
- letzte reguläre Wartung
- nächste Wartung
- Status
- Dokumente/Fotos
- Historie (Protokolle, Mängel, letzte Aktivitäten)

## 4.5 Protokollmaske

- Header: Kunde, Anlage, Datum, Bearbeiter
- Abschnitt Checkliste
- Abschnitt Messwerte
- Abschnitt Mängel
- Abschnitt Fotos/Dokumente
- Abschluss mit Typ, Flag „reguläre Wartung“, Signatur, Speichern

UX-Ziel: Von Login bis „Protokoll starten“ in maximal zwei Klicks.

---

## 5) Entitäten für die technische Umsetzung

## Benutzer

- id
- name
- email
- passwort_hash
- rolle
- aktiv

## Kunde

- id
- kundennummer
- name
- adresse
- telefon
- email
- notizen

## Anlage

- id
- kunde_id
- anlagennummer
- typ
- hersteller
- modell
- inbetriebnahme
- wartungsintervall_monate
- letzte_regulaere_wartung_am
- naechste_wartung_am
- status

## Geplante_Wartung

- id
- anlage_id
- faellig_am
- status (`offen`, `begonnen`, `abgeschlossen`, `abgebrochen`)
- quelle (`automatisch`, `manuell`)
- erstellt_am
- abgeschlossen_am

## Wartungsprotokoll

- id
- anlage_id
- kunde_id
- geplante_wartung_id (nullable)
- benutzer_id
- protokoll_datum
- protokoll_typ
- regulaere_wartung_boolean
- bemerkungen
- zusammenfassung
- unterschrift
- erstellt_am

## Messwert

- id
- wartungsprotokoll_id
- bezeichnung
- wert
- einheit

## Mangel

- id
- wartungsprotokoll_id
- kategorie
- beschreibung
- schweregrad
- empfehlung

## Datei/Foto

- id
- wartungsprotokoll_id
- dateipfad
- typ
- hochgeladen_am

---

## 6) MVP-Umfang (Version 1)

Enthalten:

- Benutzer-Login
- Kundenverwaltung
- Anlagenverwaltung
- automatische Berechnung nächster Wartungen
- Dashboard mit heute fälligen Wartungen
- Kundensuche
- manuelles Starten von Wartungsprotokollen
- Wartungsprotokoll mit Checkliste, Messwerten, Mängeln, Fotos
- Protokollhistorie je Anlage
- PDF-Export des Protokolls

Nicht enthalten (später):

- Techniker-/Einsatzplanung
- 2-Faktor-Anmeldung
- Mehrmandantenfähigkeit
