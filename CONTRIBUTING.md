# Beitragen zu MapDrawer

Danke für dein Interesse! Hier steht alles, was du wissen musst um mitzumachen.

---

## Issues

Bugs, Ideen, Fragen – einfach ein **Issue** aufmachen.
Jeder darf Issues erstellen, kein Account-Level nötig.

Bitte beim Erstellen kurz angeben:
- Was hast du erwartet?
- Was ist stattdessen passiert?
- Betriebssystem und Python-Version (falls relevant)

---

## Branches

```
main        ← stabile Releases (nur Maintainer)
  └── develop   ← Integrations-Branch (nur per Pull Request)
        └── feature/mein-feature   ← deine Arbeit
```

**Direkte Pushes auf `develop` und `main` sind gesperrt.**
Alle Änderungen kommen über einen Pull Request.

---

## Workflow Schritt für Schritt

```bash
# 1. Repo forken (einmalig, über GitHub-UI)

# 2. Lokal klonen
git clone https://github.com/DEIN-NAME/MapDrawer.git
cd MapDrawer

# 3. develop als Basis holen
git checkout develop
git pull origin develop

# 4. Feature-Branch erstellen
git checkout -b feature/mein-feature

# 5. Änderungen machen, committen
git add .
git commit -m "Kurze Beschreibung was sich geändert hat"

# 6. Branch pushen
git push origin feature/mein-feature
```

Dann auf GitHub einen **Pull Request** von `feature/mein-feature` → `develop` stellen.

---

## Branch-Naming

| Präfix | Wann |
|---|---|
| `feature/` | Neues Feature |
| `fix/` | Bugfix |
| `docs/` | Nur Dokumentation |
| `refactor/` | Umstrukturierung ohne neues Verhalten |

Beispiele: `feature/undo-history`, `fix/door-id-crash`, `docs/format-spec`

---

## Pull Requests

- Ziel-Branch ist immer **`develop`**, nie `main`
- Titel kurz und auf den Punkt: *"Add zoom keyboard shortcut"*
- Kurze Beschreibung was der PR macht und warum
- PRs werden mit **Squash and Merge** zusammengeführt
  → alle deine Commits landen als ein einzelner Commit in `develop`
  → dein Feature-Branch bleibt als Referenz erhalten

---

## Entwicklungsumgebung

```bash
pip install Pillow   # optional, für Icons

python main.py       # Editor starten
```

Benötigt Python 3.10+ mit Tkinter (in der Standard-Installation enthalten).
