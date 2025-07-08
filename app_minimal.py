#!/usr/bin/env python3
"""
VICOS Translation Service - Minimal Multilingual Translation API

Author: Joshua Quattek
Organization: VIRTIMO AG
Version: 2.0.0-minimal
Created: 2025-07-07
Last Modified: 2025-07-08

Description:
    Flask API service for real-time translation of system monitoring
    messages into multiple languages. Leverages local Helsinki-NLP OPUS models for
    complete data sovereignty without cloud dependencies.

Architecture:
    - Microservice-ready Flask REST API with standardized JSON responses
    - On-demand model loading for memory optimization (lazy loading pattern)
    - Intelligent category detection using keyword-based classification
    - Support for 10+ languages with priority loading strategy
    - JSON-first output format for seamless system integration

Performance Characteristics:
    - Cold start: 30-60 seconds (priority model loading)
    - First translation: 2-5 seconds (model loading)
    - Subsequent translations: <1 second (cached models)
    - Memory usage: ~1-2GB per loaded language model
    - Concurrent processing: Sequential (can be enhanced with threading/async)

Security Considerations:
    - Local processing ensures data privacy (GDPR compliant)
    - No external API calls or cloud dependencies
    - Input validation and sanitization implemented
    - CORS enabled for web interface integration
    - Rate limiting ready (can be added via Flask-Limiter)

Dependencies:
    - transformers>=4.21.0: HuggingFace model loading and inference
    - torch>=1.12.0: PyTorch backend for model execution
    - flask>=2.2.0: Web framework for REST API
    - flask-cors>=3.0.10: Cross-origin resource sharing support

Usage:
    python app_minimal.py
    
    API Endpoints:
    - POST /api/translate-minimal: Core translation service
    - GET /api/status-minimal: Service health and status
    - GET /api/languages: Available language configurations

Environment Variables:
    - VICOS_DEBUG: Enable debug logging (default: False)
    - VICOS_PORT: Service port (default: 5000)
    - VICOS_HOST: Service host (default: 127.0.0.1)
    - VICOS_MODEL_CACHE_DIR: Model storage directory (default: ./models)
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from transformers import pipeline
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import flask

# ==============================================================================
# CONFIGURATION AND CONSTANTS
# ==============================================================================

# Logging configuration
LOG_LEVEL = logging.DEBUG if os.getenv('VICOS_DEBUG', 'False').lower() == 'true' else logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Flask application initialization
app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])  # Restrict CORS for security

# Global model storage
translation_models: Dict[str, any] = {}
category_classifier = None  # Reserved for future ML-based classification

# Language configuration with model mappings
# Note: Models are from Helsinki-NLP's OPUS-MT project (open source)
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    # ---- A – C ----
   # 'af': {'name': 'Afrikaans',       'model': 'Helsinki-NLP/opus-mt-en-af'},
   # 'am': {'name': 'Amharic',         'model': 'Helsinki-NLP/opus-mt-en-am'},
   # 'ar': {'name': 'Arabic',          'model': 'Helsinki-NLP/opus-mt-en-ar'},
   # 'az': {'name': 'Azerbaijani',     'model': 'Helsinki-NLP/opus-mt-en-az'},
   # 'be': {'name': 'Belarusian',      'model': 'Helsinki-NLP/opus-mt-en-be'},
   # 'bg': {'name': 'Bulgarian',       'model': 'Helsinki-NLP/opus-mt-en-bg'},
   # 'bn': {'name': 'Bengali',         'model': 'Helsinki-NLP/opus-mt-en-bn'},
   # 'bs': {'name': 'Bosnian',         'model': 'Helsinki-NLP/opus-mt-en-bs'},
   # 'ca': {'name': 'Catalan',         'model': 'Helsinki-NLP/opus-mt-en-ca'},
   # 'cs': {'name': 'Czech',           'model': 'Helsinki-NLP/opus-mt-en-cs'},
   # 'cy': {'name': 'Welsh',           'model': 'Helsinki-NLP/opus-mt-en-cy'},

    # ---- D – H ----
    'da': {'name': 'Danish',          'model': 'Helsinki-NLP/opus-mt-en-da'},
    'de': {'name': 'Deutsch',         'model': 'Helsinki-NLP/opus-mt-en-de'},
    'el': {'name': 'Greek',           'model': 'Helsinki-NLP/opus-mt-en-el'},
    'es': {'name': 'Español',         'model': 'Helsinki-NLP/opus-mt-en-es'},
   # 'et': {'name': 'Estonian',        'model': 'Helsinki-NLP/opus-mt-en-et'},
   #  'fa': {'name': 'Persian',         'model': 'Helsinki-NLP/opus-mt-en-fa'},
   #  'fi': {'name': 'Finnish',         'model': 'Helsinki-NLP/opus-mt-en-fi'},
    'fr': {'name': 'Français',        'model': 'Helsinki-NLP/opus-mt-en-fr'},
   #  'ga': {'name': 'Irish',           'model': 'Helsinki-NLP/opus-mt-en-ga'},
   #  'gl': {'name': 'Galician',        'model': 'Helsinki-NLP/opus-mt-en-gl'},
   # 'gu': {'name': 'Gujarati',        'model': 'Helsinki-NLP/opus-mt-en-gu'},
   #  'he': {'name': 'Hebrew',          'model': 'Helsinki-NLP/opus-mt-en-he'},
   #   'hi': {'name': 'Hindi',           'model': 'Helsinki-NLP/opus-mt-en-hi'},
    'hr': {'name': 'Croatian',        'model': 'Helsinki-NLP/opus-mt-en-hr'},
   #   'ht': {'name': 'Haitian Creole',  'model': 'Helsinki-NLP/opus-mt-en-ht'},
   #   'hu': {'name': 'Hungarian',       'model': 'Helsinki-NLP/opus-mt-en-hu'},
   #   'hy': {'name': 'Armenian',        'model': 'Helsinki-NLP/opus-mt-en-hy'},

    # ---- I – L ----
   #  'id': {'name': 'Indonesian',      'model': 'Helsinki-NLP/opus-mt-en-id'},
   #  'is': {'name': 'Icelandic',       'model': 'Helsinki-NLP/opus-mt-en-is'},
    'it': {'name': 'Italiano',        'model': 'Helsinki-NLP/opus-mt-en-it'},
   #  'ja': {'name': '日本語',           'model': 'Helsinki-NLP/opus-mt-en-ja'},
   #  'ka': {'name': 'Georgian',        'model': 'Helsinki-NLP/opus-mt-en-ka'},
   #  'kk': {'name': 'Kazakh',          'model': 'Helsinki-NLP/opus-mt-en-kk'},
   #  'km': {'name': 'Khmer',           'model': 'Helsinki-NLP/opus-mt-en-km'},
   #  'kn': {'name': 'Kannada',         'model': 'Helsinki-NLP/opus-mt-en-kn'},
   #  'ko': {'name': '한국어',           'model': 'Helsinki-NLP/opus-mt-tc-big-en-ko'},
   #  'ku': {'name': 'Kurdish',         'model': 'Helsinki-NLP/opus-mt-en-ku'},
   #  'ky': {'name': 'Kyrgyz',          'model': 'Helsinki-NLP/opus-mt-en-ky'},
   #  'lt': {'name': 'Lithuanian',      'model': 'Helsinki-NLP/opus-mt-en-lt'},
   #  'lv': {'name': 'Latvian',         'model': 'Helsinki-NLP/opus-mt-en-lv'},

    # ---- M – N ----
   #  'mk': {'name': 'Macedonian',      'model': 'Helsinki-NLP/opus-mt-en-mk'},
   #  'ml': {'name': 'Malayalam',       'model': 'Helsinki-NLP/opus-mt-en-ml'},
   #  'mn': {'name': 'Mongolian',       'model': 'Helsinki-NLP/opus-mt-en-mn'},
   #  'mr': {'name': 'Marathi',         'model': 'Helsinki-NLP/opus-mt-en-mr'},
   #  'ms': {'name': 'Malay',           'model': 'Helsinki-NLP/opus-mt-en-ms'},
   #  'mt': {'name': 'Maltese',         'model': 'Helsinki-NLP/opus-mt-en-mt'},
   #  'my': {'name': 'Burmese',         'model': 'Helsinki-NLP/opus-mt-en-my'},
   #  'ne': {'name': 'Nepali',          'model': 'Helsinki-NLP/opus-mt-en-ne'},
   #  'nl': {'name': 'Nederlands',      'model': 'Helsinki-NLP/opus-mt-en-nl'},
   #  'no': {'name': 'Norwegian',       'model': 'Helsinki-NLP/opus-mt-en-no'},

    # ---- O – R ----
   #  'or': {'name': 'Odia',            'model': 'Helsinki-NLP/opus-mt-en-or'},
   #   'pa': {'name': 'Punjabi',         'model': 'Helsinki-NLP/opus-mt-en-pa'},
   #  'pl': {'name': 'Polish',          'model': 'Helsinki-NLP/opus-mt-en-pl'},
   #   'ps': {'name': 'Pashto',          'model': 'Helsinki-NLP/opus-mt-en-ps'},
    'pt': {'name': 'Português',       'model': 'Helsinki-NLP/opus-mt-tc-big-en-pt'},
   #   'ro': {'name': 'Romanian',        'model': 'Helsinki-NLP/opus-mt-en-ro'},
   #   'ru': {'name': 'Русский',         'model': 'Helsinki-NLP/opus-mt-en-ru'},

    # ---- S ----
 #   'si': {'name': 'Sinhala',         'model': 'Helsinki-NLP/opus-mt-en-si'},
 #   'sk': {'name': 'Slovak',          'model': 'Helsinki-NLP/opus-mt-en-sk'},
 #   'sl': {'name': 'Slovenian',       'model': 'Helsinki-NLP/opus-mt-en-sl'},
 #   'sq': {'name': 'Albanian',        'model': 'Helsinki-NLP/opus-mt-en-sq'},
 #   'sr': {'name': 'Serbian',         'model': 'Helsinki-NLP/opus-mt-en-sr'},
 #   'sv': {'name': 'Swedish',         'model': 'Helsinki-NLP/opus-mt-en-sv'},
 #   'sw': {'name': 'Swahili',         'model': 'Helsinki-NLP/opus-mt-en-sw'},
 #   'ta': {'name': 'Tamil',           'model': 'Helsinki-NLP/opus-mt-en-ta'},
 #   'te': {'name': 'Telugu',          'model': 'Helsinki-NLP/opus-mt-en-te'},
 #  'th': {'name': 'Thai',            'model': 'Helsinki-NLP/opus-mt-en-th'},
 #  'tl': {'name': 'Tagalog',         'model': 'Helsinki-NLP/opus-mt-en-tl'},
 #  'tr': {'name': 'Turkish',         'model': 'Helsinki-NLP/opus-mt-en-tr'},

    # ---- U – Z ----
     'uk': {'name': 'Ukrainian',       'model': 'Helsinki-NLP/opus-mt-en-uk'},
 #   'ur': {'name': 'Urdu',            'model': 'Helsinki-NLP/opus-mt-en-ur'},
 #   'uz': {'name': 'Uzbek',           'model': 'Helsinki-NLP/opus-mt-en-uz'},
 #   'vi': {'name': 'Vietnamese',      'model': 'Helsinki-NLP/opus-mt-en-vi'},
 #   'zh': {'name': '中文',             'model': 'Helsinki-NLP/opus-mt-en-zh'}
}


# Priority languages loaded at startup for performance
PRIORITY_LANGUAGES: List[str] = ['de', 'es', 'fr']

# Maximum text length for translation (prevent memory issues)
MAX_TEXT_LENGTH: int = 1000

# ==============================================================================
# KEYWORD DEFINITIONS FOR CATEGORY DETECTION
# ==============================================================================

# Comprehensive keyword lists for accurate category detection
# These can be extended based on your monitoring system's vocabulary
CATEGORY_KEYWORDS = {
    'error': [
        'error', 'failed', 'failure', 'exception', 'crash', 'critical',
        'timeout', 'connection refused', 'unavailable', 'unreachable',
        'fatal', 'abort', 'panic', 'segfault', 'core dump', 'stack trace'
    ],
    'warning': [
        'warning', 'warn', 'high', 'low', 'threshold', 'exceeded',
        'approaching', 'usage', 'memory', 'cpu', 'disk', 'performance',
        'degraded', 'slow', 'latency', 'queue', 'buffer', 'limit'
    ],
    'security': [
        'security', 'unauthorized', 'authentication', 'permission',
        'denied', 'blocked', 'suspicious', 'breach', 'attack',
        'intrusion', 'malware', 'virus', 'exploit', 'vulnerability',
        'firewall', 'access denied', 'forbidden', 'ssl', 'certificate'
    ],
    'info': [
        'started', 'completed', 'finished', 'success', 'healthy',
        'backup', 'maintenance', 'update', 'restart', 'loaded',
        'initialized', 'ready', 'online', 'connected', 'synced',
        'deployed', 'created', 'deleted', 'modified'
    ]
}

# ==============================================================================
# MODEL MANAGEMENT FUNCTIONS
# ==============================================================================

def init_models() -> None:
    """
    Initialize translation models for priority languages.
    
    This function loads the most commonly used language models at startup
    to reduce latency for initial translations. Additional models are loaded
    on-demand to optimize memory usage.
    
    Raises:
        Exception: If critical models fail to load
    """
    global translation_models
    
    logger.info("🚀 Initializing VICOS Translation Service...")
    logger.info(f"📊 Priority languages: {', '.join(PRIORITY_LANGUAGES)}")
    
    successful_loads = 0
    failed_loads = []
    
    for lang in PRIORITY_LANGUAGES:
        try:
            logger.info(f"📥 Loading {SUPPORTED_LANGUAGES[lang]['name']} model...")
            
            # Load model with optimized settings
            translation_models[lang] = pipeline(
                "translation",
                model=SUPPORTED_LANGUAGES[lang]['model'],
                device=-1  # Force CPU usage for consistency
            )
            
            logger.info(f"✅ {lang.upper()} model loaded successfully")
            successful_loads += 1
            
        except Exception as e:
            logger.error(f"❌ Failed to load {lang} model: {str(e)}")
            failed_loads.append(lang)
    
    # Log initialization summary
    logger.info(f"✅ Initialization complete: {successful_loads} models loaded")
    if failed_loads:
        logger.warning(f"⚠️  Failed to load: {', '.join(failed_loads)}")

def load_model_for_language(lang: str) -> bool:
    """
    Load a translation model on-demand for a specific language.
    
    This implements lazy loading to optimize memory usage. Models are only
    loaded when first requested and then cached for subsequent use.
    
    Args:
        lang: ISO 639-1 language code (e.g., 'de', 'es')
        
    Returns:
        bool: True if model loaded successfully, False otherwise
        
    Example:
        >>> load_model_for_language('it')
        True
    """
    # Check if model already loaded
    if lang in translation_models:
        logger.debug(f"Model for {lang} already loaded")
        return True
    
    # Validate language code
    if lang not in SUPPORTED_LANGUAGES:
        logger.error(f"Unsupported language code: {lang}")
        return False
    
    try:
        logger.info(f"📥 Loading {SUPPORTED_LANGUAGES[lang]['name']} model on-demand...")
        
        # Load model with error handling
        translation_models[lang] = pipeline(
            "translation",
            model=SUPPORTED_LANGUAGES[lang]['model'],
            device=-1
        )
        
        logger.info(f"✅ {lang.upper()} model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error loading {lang} model: {str(e)}")
        return False

# ==============================================================================
# CORE TRANSLATION FUNCTIONS
# ==============================================================================

def classify_monitoring_category(text: str) -> str:
    """
    Classify monitoring message into predefined categories using keyword analysis.
    
    This function implements a rule-based classification system that analyzes
    the input text for specific keywords associated with different monitoring
    categories. The classification is case-insensitive and uses a priority
    system (error > security > warning > info > general).
    
    Args:
        text: The monitoring message to classify
        
    Returns:
        str: Category name ('error', 'security', 'warning', 'info', 'general')
        
    Example:
        >>> classify_monitoring_category("Database connection failed")
        'error'
        >>> classify_monitoring_category("CPU usage exceeded 80%")
        'warning'
    """
    text_lower = text.lower()
    
    # Priority-based classification (most critical first)
    for category, keywords in [
        ('error', CATEGORY_KEYWORDS['error']),
        ('security', CATEGORY_KEYWORDS['security']),
        ('warning', CATEGORY_KEYWORDS['warning']),
        ('info', CATEGORY_KEYWORDS['info'])
    ]:
        if any(keyword in text_lower for keyword in keywords):
            logger.debug(f"Text classified as '{category}' based on keywords")
            return category
    
    # Default category if no keywords match
    logger.debug("Text classified as 'general' (no keyword matches)")
    return 'general'

def translate_to_languages(
    text: str,
    target_languages: List[str],
    source_lang: str = 'en'
) -> Dict[str, str]:
    """
    Translate text into multiple target languages with monitoring context.
    
    This function handles the core translation logic, including:
    - Adding monitoring context to improve translation quality
    - Loading models on-demand for requested languages
    - Graceful error handling with fallbacks
    - Performance logging for monitoring
    
    Args:
        text: Source text to translate (English)
        target_languages: List of ISO 639-1 language codes
        source_lang: Source language code (default: 'en')
        
    Returns:
        Dict[str, str]: Dictionary mapping language codes to translations
        
    Example:
        >>> translate_to_languages("Server is down", ['de', 'es'])
        {'en': 'Server is down', 'de': 'Server ist ausgefallen', 'es': 'El servidor está caído'}
    """
    # Add monitoring context for better technical translations
    monitoring_context = ""
    contextualized_text = text
    
    # Initialize with source text
    translations = {source_lang: text}
    
    # Track performance metrics
    translation_times = {}
    start_time = datetime.now()
    
    for lang in target_languages:
        # Skip if same as source language
        if lang == source_lang:
            continue
        
        # Track individual translation time
        lang_start = datetime.now()
        
        # Attempt to load model if not already loaded
        if not load_model_for_language(lang):
            logger.warning(f"Model unavailable for {lang}, using fallback")
            translations[lang] = f"[Translation unavailable for {lang}]"
            continue
        
        try:
            logger.info(f"🔄 Translating to {lang.upper()}...")
            
            # Perform translation with length limit
            result = translation_models[lang](
                contextualized_text[:MAX_TEXT_LENGTH],
                max_length=512,
                truncation=True
            )
            
            # Extract translated text
            translated_text = result[0]['translation_text']
            
            # Remove context prefix from translation - check multiple variations
            # Some models translate the context prefix differently
            context_variations = [
                f"{monitoring_context} ",
                "System monitoring alert: ",
                "Systemüberwachungsalarm: ",  # German
                "Alerta de monitoreo del sistema: ",  # Spanish
                "Alerte de surveillance du système : ",  # French
                "Avviso di monitoraggio del sistema: ",  # Italian
                "Alerta de monitoramento do sistema: ",  # Portuguese
                "Systeembewakingswaarschuwing: ",  # Dutch
                "Системное предупреждение мониторинга: ",  # Russian
                "系统监控警报：",  # Chinese
                "システム監視アラート：",  # Japanese
                "시스템 모니터링 경고: ",  # Korean
            ]
            
            for variation in context_variations:
                if translated_text.startswith(variation):
                    translated_text = translated_text[len(variation):]
                    break
            
            translations[lang] = translated_text.strip()
            
            # Log translation time
            translation_time = (datetime.now() - lang_start).total_seconds()
            translation_times[lang] = translation_time
            logger.info(f"✅ {lang.upper()}: {translated_text} (took {translation_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ Translation error for {lang}: {str(e)}")
            translations[lang] = text  # Fallback to original text
    
    # Log total translation time
    total_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"📊 Total translation time: {total_time:.2f}s for {len(target_languages)} languages")
    
    return translations

# ------------------------------------------------------------------
# JSON-Helfer: übersetzt rekursiv alle Strings in einem JSON-Objekt
# ------------------------------------------------------------------
def translate_json(obj, target_langs):
    if isinstance(obj, dict):
        return {k: translate_json(v, target_langs) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [translate_json(x, target_langs) for x in obj]
    elif isinstance(obj, str):
        # ← komplette Sprach-Map zurückgeben
        return translate_to_languages(obj, target_langs)
    else:
        return obj



# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route('/api/translate-minimal', methods=['POST'])
def translate_minimal() -> Tuple[Response, int]:
    """
    Core translation endpoint for monitoring messages.
    
    This endpoint accepts a monitoring message and target languages, performs
    automatic category detection, translates to all requested languages, and
    returns a comprehensive JSON response.
    
    Request JSON Schema:
        {
            "text": "string (required) - The monitoring message to translate",
            "languages": ["array of language codes (optional) - defaults to ['de', 'es']"]
        }
        
    Response JSON Schema:
        {
            "success": "boolean - Operation success status",
            "original_text": "string - Input text",
            "detected_category": "string - Detected message category",
            "translations": {
                "language_code": "translated text"
            },
            "json_output": "string - Pretty-printed JSON of translations",
            "target_languages": ["array - Requested languages"],
            "timestamp": "ISO 8601 timestamp"
        }
        
    Status Codes:
        200: Success
        400: Bad request (missing/invalid input)
        500: Internal server error
    """
    try:
        # Parse and validate request data
        data = request.get_json()

        # Kein Body? → 400
        if not data:
            logger.warning("Request with no JSON body")
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
    
    # JSON-Modus
        if isinstance(data.get('text'), dict):
            json_payload = data['text']
            target_languages = data.get('languages', list(SUPPORTED_LANGUAGES.keys()))
            translations = translate_json(json_payload, target_languages)

            return jsonify({
                'success': True,
                'original_json': json_payload,
                'translations': translations,
                'target_languages': target_languages,
                'timestamp': datetime.now().isoformat()
            }), 200
    
        if not data:
            logger.warning("Request with no JSON body")
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Extract and validate text input
        text = data.get('text', '').strip()
        
        if not text:
            logger.warning("Request with empty text field")
            return jsonify({
                'success': False,
                'error': 'No text provided for translation'
            }), 400
        
        # Validate text length
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(f"Text too long: {len(text)} characters")
            return jsonify({
                'success': False,
                'error': f'Text exceeds maximum length of {MAX_TEXT_LENGTH} characters'
            }), 400
        
        # Extract target languages with defaults
        target_languages = data.get('languages', list(SUPPORTED_LANGUAGES.keys()))
        
        # Validate language codes
        invalid_languages = [lang for lang in target_languages if lang not in SUPPORTED_LANGUAGES]
        if invalid_languages:
            logger.warning(f"Invalid language codes: {invalid_languages}")
            return jsonify({
                'success': False,
                'error': f'Invalid language codes: {", ".join(invalid_languages)}'
            }), 400
        
        logger.info(f"🎯 Translation request: '{text[:50]}...' to {target_languages}")
        
        # Perform category detection
        detected_category = classify_monitoring_category(text)
        logger.info(f"📂 Detected category: {detected_category}")
        
        # Perform translations
        translations = translate_to_languages(text, target_languages)
        
        # Generate pretty-printed JSON output
        json_output = json.dumps(translations, ensure_ascii=False, indent=2)
        
        # Build successful response
        response = {
            'success': True,
            'original_text': text,
            'detected_category': detected_category,
            'translations': translations,
            'json_output': json_output,
            'target_languages': target_languages,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'version': '2.0.0-minimal',
                'models_loaded': len(translation_models),
                'processing_language': 'en'
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in translate_minimal: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/languages', methods=['GET'])
def get_supported_languages() -> Tuple[Response, int]:
    """
    Get all supported languages and their current status.
    
    This endpoint provides information about available languages, which models
    are currently loaded, and default language configurations.
    
    Response JSON Schema:
        {
            "supported_languages": {
                "language_code": {
                    "name": "Language name",
                    "model": "Model identifier"
                }
            },
            "loaded_models": ["array of loaded language codes"],
            "default_languages": ["array of default language codes"]
        }
    """
    try:
        response = {
            'supported_languages': SUPPORTED_LANGUAGES,
            'loaded_models': list(translation_models.keys()),
            'default_languages': ['de', 'es', 'fr'],
            'priority_languages': PRIORITY_LANGUAGES,
            'total_available': len(SUPPORTED_LANGUAGES),
            'total_loaded': len(translation_models)
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in get_supported_languages: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve language information'
        }), 500

@app.route('/api/status-minimal', methods=['GET'])
def status_minimal() -> Tuple[Response, int]:
    """
    Service health check and status endpoint.
    
    Provides real-time information about service health, loaded models,
    and system capabilities. Useful for monitoring and debugging.
    
    Response JSON Schema:
        {
            "status": "string - Service status (OK/ERROR)",
            "version": "string - Service version",
            "models_loaded": "integer - Number of loaded models",
            "supported_languages": "integer - Total supported languages",
            "available_models": ["array - Currently loaded language codes"],
            "auto_category_detection": "boolean - Category detection status",
            "json_format": "boolean - JSON output capability",
            "uptime": "string - Service uptime"
        }
    """
    try:
        # Calculate service uptime (if tracking start time)
        uptime = "N/A"  # Could be implemented with a global start_time variable
        
        response = {
            'status': 'OK',
            'version': '2.0.0-minimal',
            'models_loaded': len(translation_models),
            'supported_languages': len(SUPPORTED_LANGUAGES),
            'available_models': list(translation_models.keys()),
            'auto_category_detection': True,
            'json_format': True,
            'system_info': {
                'python_version': os.sys.version.split()[0],
                'flask_version': flask.__version__,
                'debug_mode': app.debug
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in status_minimal: {str(e)}")
        return jsonify({
            'status': 'ERROR',
            'error': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def status():                           # Alias für alte Clients
    return status_minimal()

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors with JSON response."""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 404
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with JSON response."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'status': 500
    }), 500

# ==============================================================================
# APPLICATION ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    """
    Main entry point for the VICOS Translation Service.
    
    Initializes the service, loads priority models, and starts the Flask
    development server. For production deployment, use a WSGI server like
    Gunicorn or uWSGI instead of the Flask development server.
    """
    print("=" * 60)
    print("🌍 VICOS Translation Service - Enterprise Edition")
    print("   Automatic Category Detection + Multi-Language Support")
    print("=" * 60)
    print(f"Version: 2.0.0-minimal")
    print(f"Author: Joshua Quattek @ VIRTIMO AG")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    logger.info("🚀 Starting VICOS Translation Service...")
    
    # Initialize priority models
    init_models()
    
    # Get configuration from environment
    host = os.getenv('VICOS_HOST', '127.0.0.1')
    port = int(os.getenv('VICOS_PORT', '5000'))
    debug = os.getenv('VICOS_DEBUG', 'False').lower() == 'true'
    
    # Display service information
    print("\n🌐 VICOS Translation Service is ready!")
    print(f"📍 Backend API: http://{host}:{port}")
    print(f"📊 Status: http://{host}:{port}/api/status-minimal")
    print(f"🎮 Frontend: http://localhost:3000")
    print(f"🔧 Debug Mode: {'Enabled' if debug else 'Disabled'}")
    print(f"🤖 Category Detection: Automatic (Keyword-based)")
    print(f"📦 Models Loaded: {len(translation_models)}/{len(SUPPORTED_LANGUAGES)}")
    print("\n💡 Press Ctrl+C to stop the service")
    print("=" * 60)
    
    # Start Flask application
    app.run(host=host, port=port, debug=debug)
