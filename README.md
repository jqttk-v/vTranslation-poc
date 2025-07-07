# vTranslation Monitor via LLM

Ein POC (Proof of Concept) zur automatischen Übersetzung von System-Monitoring-Inhalten in mehrere Sprachen mit lokalen LLM-Modellen.

## Was macht das Programm?

Das System nimmt Monitoring-Nachrichten (z.B. Fehlermeldungen, Warnungen, Status-Updates) entgegen, kategorisiert sie automatisch und übersetzt sie in mehrere Sprachen. Die Übersetzungen werden als JSON ausgegeben, sodass sie einfach in bestehende Logging- und Alerting-Systeme integriert werden können.

**Beispiel:**

## Eingabe-Beispiel:

```
"Database connection timeout after 30 seconds"
```

## Ausgabe-Beispiel:

```
{
  "en": "Database connection timeout after 30 seconds",
  "de": "Datenbankverbindung nach 30 Sekunden abgebrochen",
  "es": "Tiempo de espera de conexión a la base de datos después de 30 segundos",
  "fr": "Délai d'attente de connexion à la base de données après 30 secondes"
}

Erkannte Kategorie: error

```

## Features

- **Lokale Übersetzung**: Nutzt Helsinki-NLP-Modelle lokal, keine Cloud-APIs nötig // Überlegung: Für maximale Präzision bei lokalem LLM: NLLB-200-3.3B ist deine beste Wahl. Es übertrifft Helsinki-NLP deutlich in Qualität und Sprachabdeckung, läuft komplett lokal, und ist speziell für technische Texte optimiert. Ist aber etwas Leistungsintensiver. 
- **Automatische Kategorisierung**: Erkennt Error/Warning/Info/Security/General basierend auf Keywords
- **10+ Sprachen**: DE, ES, FR, IT, PT, NL, RU, ZH, JA, KO
- **On-Demand Model Loading**: Lädt Übersetzungsmodelle nur bei Bedarf -> LazyLoading 
- **REST API**: Einfache Integration in bestehende Systeme // Kann bei Bedarf einfach umgebaut werden
- **Web Interface**: Benutzerfreundliche Oberfläche zum Testen // Nur für Tests, kann integriert werden
- **JSON Export**: Copy-to-Clipboard // Kann direkt in DB geschrieben werden

## Installation

### Voraussetzungen
- Python 3.8+
- Node.js 14+ (für Frontend)
- Mindestens 4GB RAM (für Übersetzungsmodelle)

### Backend Setup
```bash
Installation

# Repository klonen
git clone https://github.com/jqttk-v/vTranslation-poc.git
cd vTranslation-poc

# Backend-Setup
python -m venv venv

# Virtuelle Umgebung aktivieren
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Abhängigkeiten installieren
pip install flask flask-cors transformers sentencepiece torch
pip install -r requirements.txt

# Backend starten (Terminal 1)
python app_minimal.py

# Frontend-Setup (Terminal 2)
cd vicos-frontend
npm install
npm start
```


Das System ist dann erreichbar unter:
- Backend API: http://localhost:5000
- Web-Oberfläche: http://localhost:3000
- API-Status: http://localhost:5000/api/status-minimal
- API-Dokumentation: http://localhost:5000/api/languages

## Verwendung

### Testdaten


```
- Database connection timeout after 30 seconds

- Unable to establish connection to database server

- Failed to authenticate with database credentials

- Query execution took too long and was aborted

- Database is currently unavailable — please try again later

- Connection refused by database host

- Database connection pool exhausted — too many connections

- Invalid database schema detected
```

### Web Interface
1. System starten (siehe Installation)
2. Browser auf http://localhost:3000 öffnen
3. Monitoring-Nachricht eingeben
4. Zielsprachen auswählen
5. "JSON Generieren" klicken
6. Ergebnis kopieren oder verwenden

## 🌍 Sprachunterstützung

| Code | Sprache | Modell | Status |
|------|---------|--------|--------|
| `de` | Deutsch | Helsinki-NLP/opus-mt-en-de | ✅ Priorität |
| `es` | Español | Helsinki-NLP/opus-mt-en-es | ✅ Priorität |
| `fr` | Français | Helsinki-NLP/opus-mt-en-fr | ✅ Priorität |
| `it` | Italiano | Helsinki-NLP/opus-mt-en-it | 🔄 Bedarfsgesteuert |
| `pt` | Português | Helsinki-NLP/opus-mt-en-pt | 🔄 Bedarfsgesteuert |
| `nl` | Nederlands | Helsinki-NLP/opus-mt-en-nl | 🔄 Bedarfsgesteuert |
| `ru` | Русский | Helsinki-NLP/opus-mt-en-ru | 🔄 Bedarfsgesteuert |
| `zh` | 中文 | Helsinki-NLP/opus-mt-en-zh | 🔄 Bedarfsgesteuert |
| `ja` | 日本語 | Helsinki-NLP/opus-mt-en-jap | 🔄 Bedarfsgesteuert |
| `ko` | 한국어 | Helsinki-NLP/opus-mt-en-ko | 🔄 Bedarfsgesteuert |

Weitere können im Code auskommentiert werden. 

## 🔍 Kategorieerkennung

Das System kategorisiert Überwachungsmeldungen automatisch durch intelligente Schlüsselwortanalyse:

| Kategorie | Schlüsselwörter | Beispiel | Icon |
|-----------|-----------------|----------|------|
| **Error** | `error`, `failed`, `timeout`, `crash`, `critical` | "Database connection failed" | ❌ |
| **Warning** | `warning`, `high`, `threshold`, `exceeded`, `usage` | "Memory usage at 85%" | ⚠️ |
| **Security** | `unauthorized`, `authentication`, `blocked`, `breach` | "Unauthorized access attempt" | 🔒 |
| **Info** | `started`, `completed`, `success`, `healthy`, `backup` | "Backup completed successfully" | ✅ |
| **General** | Alle anderen Meldungen | "System maintenance scheduled" | 📋 |


### API Direkt verwenden
```bash
# Übersetzung anfordern
curl -X POST http://localhost:5000/api/translate-minimal \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Database connection failed",
    "languages": ["de", "es", "fr"]
  }'

# System Status prüfen
curl http://localhost:5000/api/status-minimal

# Verfügbare Sprachen anzeigen
curl http://localhost:5000/api/languages
```

## Architektur

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitoring    │───▶│  Translation     │───▶│   Multilingual  │
│   Messages      │    │  Service         │    │   JSON Output   │
│                 │    │                  │    │                 │
│ • Database logs │    │ • Category       │    │ • Structured    │
│ • Error alerts  │    │   Detection      │    │   Format        │
│ • System status │    │ • Local LLM      │    │ • Copy-ready    │
└─────────────────┘    │ • 10+ Languages   │    │ • API Response  │
                       └──────────────────┘    └─────────────────┘
```
## 📈 Leistungsmetriken

### Typische Leistung

| Metrik | Wert | Anmerkungen |
|--------|------|-------------|
| **Erste Übersetzung** | 2-5 Sekunden | Modellladezeit |
| **Folgende Übersetzungen** | <1 Sekunde | Zwischengespeicherte Modelle |
| **Speicher pro Modell** | ~1-2 GB | Variiert je nach Sprache |
| **Gleichzeitige Anfragen** | 1-3 | Sequenzielle Verarbeitung |
| **Startzeit** | 30-60 Sekunden | Prioritätsmodell-Laden |

### Optimierungsstrategien

```python
# Produktionskonfiguration
PRODUCTION_CONFIG = {
    'preload_languages': ['de', 'es', 'fr'],  # Häufigste
    'lazy_load_threshold': 5,  # Laden nach 5 Anfragen
    'model_cache_size': 8,     # 8 Modelle im Speicher behalten
    'request_timeout': 30,     # 30 Sekunden Timeout
    'batch_processing': True   # Batch-Modus aktivieren
}
```

## 🛠️ Entwicklung

### Lokale Entwicklungsumgebung

```bash
# Backend-Entwicklung (Hot Reload)
python app_minimal.py --debug

# Frontend-Entwicklung (Hot Reload)
cd vicos-frontend
npm run dev

# Tests ausführen
python -m pytest tests/
npm test
```

### Neue Sprachen hinzufügen

```python
# Zu SUPPORTED_LANGUAGES in app_minimal.py hinzufügen
SUPPORTED_LANGUAGES = {
    # ... bestehende Sprachen
    'sv': {'name': 'Svenska', 'model': 'Helsinki-NLP/opus-mt-en-sv'},
    'no': {'name': 'Norsk', 'model': 'Helsinki-NLP/opus-mt-en-no'}
}
```

### Benutzerdefinierte Kategorieerkennung

```python
def custom_category_classifier(text):
    """
    Unternehmensspezifische Kategorieerkennung
    Diese Funktion für domänenspezifische Kategorisierung erweitern
    """
    text_lower = text.lower()
    
    # Benutzerdefinierte Geschäftslogik
    if 'payment' in text_lower or 'transaction' in text_lower:
        return 'financial'
    elif 'user' in text_lower and ('login' in text_lower or 'signup' in text_lower):
        return 'user_activity'
    
    # Rückfall auf Standard-Kategorisierung
    return classify_monitoring_category(text)
```

### Komponenten

**Backend (Python Flask)**
- `vicos_translation_service.py`: Hauptservice mit REST API
- Helsinki-NLP/OPUS Übersetzungsmodelle
- Keyword-basierte Kategorisierung
- On-Demand Model Loading

**Frontend (React)**
- `VICOSMinimalTranslator.jsx`: Haupt-Komponente
- 2-Spalten Layout (Input/Output)
- Real-time API Status
- Sprachen-Auswahl Interface

**CSS**
- `App.css`: Responsive Design
- Clean 2-Column Layout
- Status Indicators
- Mobile-friendly


## Integration in bestehende Systeme

### Beispiel: Python Logging
```python
import requests
import json

def translate_log_message(message, languages=['de', 'es']):
    response = requests.post('http://localhost:5000/api/translate-minimal', 
                           json={'text': message, 'languages': languages})
    return response.json()

# In Ihrem Monitoring Code:
error_msg = "Database connection failed"
translations = translate_log_message(error_msg)
logger.error(f"Multilingual Alert: {json.dumps(translations['translations'])}")
```

### Beispiel: Slack Integration
```python
def send_multilingual_alert(message, severity):
    translations = translate_log_message(message, ['de', 'es', 'fr'])
    
    for lang, text in translations['translations'].items():
        channel = f"#alerts-{lang}"
        slack_client.chat_postMessage(
            channel=channel,
            text=f"🚨 {severity.upper()}: {text}"
        )
```

## Technische Details

### Model Loading Strategy
- **Startup**: Lädt DE, ES, FR Modelle (häufigste Nutzung)
- **On-Demand**: Andere Sprachen werden bei Bedarf geladen
- **Caching**: Einmal geladene Modelle bleiben im Speicher

### Performance
- **Erste Übersetzung**: 2-5 Sekunden (Model Loading)
- **Folgende Übersetzungen**: <1 Sekunde
- **Speicherverbrauch**: ~1-2GB pro geladenem Modell
- **CPU**: Nutzt verfügbare Kerne für Inferenz

### API Endpoints

```
POST /api/translate-minimal
GET  /api/status-minimal
GET  /api/languages
```

## Limitierungen

- **Nur Englisch → Andere Sprachen**: Derzeit nur EN als Quellsprache
- **Keyword-basierte Kategorisierung**: Einfache Regel-basierte Erkennung
- **Sequenzielle Verarbeitung**: Ein Request nach dem anderen
- **Lokale Installation**: Benötigt lokale Python/Node.js Setup

## Mögliche Erweiterungen

### Kurzfristig
- Automatische Spracherkennung für Input
- Batch-Verarbeitung mehrerer Nachrichten
- Docker Container für einfache Deployment
- Webhook Integration für automatische Alerts

### Langfristig
- ML-basierte Kategorisierung (statt Keywords)
- Mehr Quellsprachen (nicht nur Englisch)
- Message Queue Integration (Kafka, RabbitMQ)
- Dashboard für Übersetzungsstatistiken
- Fine-tuning der Modelle für Domain-spezifische Begriffe

## Entwicklung

### Lokale Entwicklung
```bash
# Backend Development
cd backend
python vicos_translation_service.py

# Frontend Development (Watch Mode)
cd frontend
npm run dev
```

### Debugging
- Backend Logs: Console Output mit detailliertem Logging
- Frontend: Browser Developer Tools
- API Testing: Nutzen Sie curl oder Postman

### Entwicklungsprozess

1. **Fork** des Repositories
2. **Erstellen** eines Feature-Branchs (`git checkout -b feature/amazing-feature`)
3. **Commits** durchführen (`git commit -m 'Add amazing feature'`)
4. **Push** zum Branch (`git push origin feature/amazing-feature`)
5. **Pull Request** öffnen

### Code-Standards

- **Python**: PEP 8, Type-Hints, umfassende Docstrings
- **JavaScript**: ESLint-Konfiguration, JSDoc-Kommentare
- **Testing**: Mindestens 80% Code-Coverage
- **Dokumentation**: README und API-Dokumentation aktualisieren

## 📄 Lizenz

© 2025 VIRTIMO AG. Alle Rechte vorbehalten.

**Autor**: Joshua Quattek  
**Organisation**: VIRTIMO AG  
**Projekttyp**: Proof of Concept (POC)

Diese Software ist Eigentum der VIRTIMO AG. Unbefugtes Kopieren, Verteilen oder Modifizieren ist untersagt.