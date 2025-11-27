# 🐳 Docker-basiertes Python Dependency Management für Teams

Ein modernes, Docker-basiertes System für Python Dependency Management, das lokale Installationen von Python, pip, PDM und Poetry überflüssig macht.

## 🎯 Hauptvorteile

**Keine lokale Installation mehr erforderlich:**
- ✅ Kein Python, pip, PDM, Poetry oder pipx auf lokalen Entwicklungsrechnern nötig
- ✅ Nur Docker erforderlich - einheitliche Entwicklungsumgebung für alle Teammitglieder
- ✅ Konsistente Python 3.13 Umgebung unabhängig vom Betriebssystem
- ✅ Nahtloser Übergang: Package Management → Backend-Start mit `docker-compose up`

## 🚀 Schnellstart

### 1. Einmalige Einrichtung
```bash
# Aus dem Projekt-Root-Verzeichnis:
./manage-python-project-dependencies.sh
```

Das Script führt automatisch folgende Schritte aus:
- Erstellt `config.env` aus `config.env.example` (falls nicht vorhanden)
- Zeigt aktuelle Konfiguration an
- Baut Docker Image mit Python 3.13 + PDM + Poetry + uv
- Generiert/aktualisiert `pdm.lock` und `poetry.lock`
- Startet interaktive Shell mit allen Tools

### 2. Dependencies verwalten
```bash
# Im Container:
pdm add requests fastapi        # Pakete hinzufügen
pdm add pytest --dev          # Development Dependencies
pdm remove old-package        # Pakete entfernen
pdm list                       # Installierte Pakete anzeigen
pdm update                     # Alle Dependencies aktualisieren
```

### 3. Backend starten
```bash
# Container verlassen:
exit

# Backend mit aktualisierten Dependencies starten:
docker-compose up --build
```

## 🛠️ Technische Features

### **Moderne Tools integriert:**
- **PDM** mit **uv-Backend** für blitzschnelle Dependency-Resolution
- **Poetry** als Alternative verfügbar
- **uv** für ultraschnelle Package-Installation
- Alle Tools über **pipx** isoliert installiert

### **Automatisierte Konfiguration:**
- `config.env` für teamweite Einstellungen
- PDM nutzt uv-Backend standardmäßig (konfigurierbar)
- Parallel-Installation und Caching aktiviert
- Alle Änderungen persistent in Projektdateien

## 📁 Verzeichnisstruktur

```
python-dependency-management/
├── Dockerfile              # Python 3.13 + PDM + Poetry + uv
├── docker-compose.yml      # Service-Definition
├── dev-setup.sh           # Initialisierung + Konfiguration
├── config.env.example     # Konfigurationsvorlage
├── config.env             # Lokale Konfiguration (gitignored)
└── README.md              # Diese Dokumentation
```

## ⚙️ Konfiguration

### **config.env Optionen:**
```bash
# uv als PDM Backend verwenden (empfohlen)
USE_UV_BACKEND=true

# PDM Install Cache aktivieren
PDM_INSTALL_CACHE=true

# Parallele Installation aktivieren
PDM_PARALLEL_INSTALL=true

# Python Version (muss mit Dockerfile übereinstimmen)
PYTHON_VERSION=3.13
```

## 💡 Häufige PDM-Kommandos

### **📦 Basis Package Management:**
```bash
pdm add requests                    # Paket hinzufügen
pdm add "requests>=2.28.0"         # Mit Versionsbeschränkung
pdm add pytest --dev               # Development Dependency
pdm remove requests                 # Paket entfernen
pdm install                         # Alle Dependencies installieren
pdm list                            # Installierte Pakete anzeigen
```

### **🔄 Dependency Management:**
```bash
pdm update                          # Alle Dependencies aktualisieren
pdm update requests                 # Spezifisches Paket aktualisieren
pdm lock                            # Lock-Datei aktualisieren
pdm lock --check                    # Lock-Datei auf Aktualität prüfen
pdm sync                            # Umgebung mit Lock-Datei synchronisieren
```

### **🔧 Troubleshooting & Konflikte:**
```bash
pdm lock --update-reuse             # Lock-Update mit Konfliktlösung
pdm install --no-lock               # Installation ohne Lock-Update
pdm cache clear                     # Package Cache leeren
pdm info                            # Projekt-Informationen anzeigen
pdm info requests                   # Paket-Details anzeigen
```

### **🐍 Python Version Management:**
```bash
pdm python list                     # Verfügbare Python-Versionen
pdm python install 3.12             # Spezifische Python-Version installieren
pdm use 3.12                        # Zu Python 3.12 wechseln
```

### **🚀 Scripts ausführen:**
```bash
pdm run python script.py            # Script mit Projekt-Dependencies
pdm run pytest                      # Tests ausführen
pdm run --list                      # Verfügbare Scripts anzeigen
```

### **🔍 Debugging Dependency Issues:**
```bash
pdm show --graph                    # Dependency-Baum anzeigen
pdm show --reverse requests         # Was hängt von requests ab?
pdm export -f requirements          # Export zu requirements.txt
pdm import requirements.txt         # Import aus requirements.txt
```

### **⚡ Quick Fixes für häufige Probleme:**
```bash
# Dependency-Konflikt-Lösung:
pdm lock --update-reuse --resolution=highest

# Alle Pakete neu installieren:
pdm sync --reinstall

# Frische Lock-Datei erstellen:
rm pdm.lock && pdm lock && pdm install
```

## 👥 Vorteile für Teams

### **Konsistenz:**
- Identische Python-Umgebung für alle Entwickler
- Keine "works on my machine"-Probleme
- Einheitliche Tool-Versionen (PDM, Poetry, uv)

### **Onboarding:**
- Neue Teammitglieder brauchen nur Docker
- Ein Befehl für komplette Einrichtung
- Integrierte Dokumentation und Hilfe

### **Wartung:**
- Zentrale Konfiguration in `config.env.example`
- Einfache Updates durch Docker Image Rebuild
- Keine Konflikte mit lokalen Python-Installationen

## 🔧 Workflow für Entwickler

### **Typischer Entwicklungsworkflow:**
1. **Dependencies verwalten:** `./manage-python-project-dependencies.sh`
2. **Pakete hinzufügen/entfernen** im interaktiven Container
3. **Container verlassen:** `exit`
4. **Backend testen:** `docker-compose up --build`
5. **Deployment:** Dockerfile nutzt PDM für Produktionsumgebung

### **Dateien werden automatisch aktualisiert:**
- `pyproject.toml` - Dependency-Definitionen
- `pdm.lock` - Exakte Versionen für Reproduzierbarkeit
- `poetry.lock` - Falls Poetry parallel genutzt wird

## 🚨 Troubleshooting

### **Container startet nicht:**
```bash
# Docker Image neu bauen:
cd python-dependency-management
docker-compose build --no-cache
```

### **Konfiguration ändern:**
```bash
# config.env bearbeiten:
nano python-dependency-management/config.env

# Script erneut ausführen:
./manage-python-project-dependencies.sh
```

### **PDM-Kommando nicht gefunden:**
```bash
# Überprüfen ob uv-Backend aktiviert ist:
pdm config use_uv

# PATH-Probleme debuggen:
echo $PATH
which pdm
```

## 🎉 Fazit

**Ein Befehl ersetzt komplette lokale Python-Infrastruktur:**
- Kein manuelles Setup von Python-Umgebungen
- Moderne, schnelle Tools (PDM + uv) out-of-the-box
- Nahtlose Integration in Docker-basierte Entwicklung
- Teamweite Konsistenz und einfaches Onboarding

**Perfekt für moderne Python-Teams, die auf Docker setzen!** 🐳

---

## 📝 Weitere Informationen

- **Hauptprojekt README:** `../README.md`
- **PDM Dokumentation:** https://pdm.fming.dev/
- **uv Dokumentation:** https://docs.astral.sh/uv/
- **Docker Compose Referenz:** https://docs.docker.com/compose/ 