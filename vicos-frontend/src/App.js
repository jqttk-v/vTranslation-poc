import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Monitor, Server, Database, Globe, Zap, Copy, CheckCircle, AlertCircle, RefreshCw, Upload, FileText, X } from 'lucide-react';
import './App.css';

/**
 * VICOSMinimalTranslator Component
 * 
 * Enterprise-grade React component for the VICOS Translation Service web interface.
 * Provides a user-friendly interface for translating monitoring messages into multiple languages.
 * 
 * @component
 * @author Joshua Quattek - VIRTIMO AG
 * @version 2.0.0
 * @created 2025-07-07
 * 
 * Features:
 * - Real-time API status monitoring
 * - Multi-language selection with visual feedback
 * - Automatic category detection display
 * - Copy-to-clipboard functionality
 * - Responsive design for mobile and desktop
 * - Keyboard shortcuts (Ctrl+Enter to translate)
 * - Error handling with user feedback
 * 
 * State Management:
 * - Uses React hooks for local state management
 * - Could be enhanced with Context API or Redux for larger applications
 * 
 * Performance Optimizations:
 * - useCallback for memoized functions
 * - Debounced API status checks
 * - Lazy loading of language models via backend
 */
const VICOSMinimalTranslator = () => {
  // ==============================================================================
  // STATE MANAGEMENT
  // ==============================================================================
  
  // User input and interaction state
  const [inputText, setInputText] = useState('');
  const [selectedLanguages, setSelectedLanguages] = useState(['de', 'es', 'fr']);
  const [translationResult, setTranslationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  
  // System status and configuration state
  const [status, setStatus] = useState(null);
  const [apiStatus, setApiStatus] = useState(null);
  const [supportedLanguages, setSupportedLanguages] = useState({});
  const [copiedJson, setCopiedJson] = useState(false);
  
  // Refs for managing timers and preventing memory leaks
  const statusTimeoutRef = useRef(null);
  const copyTimeoutRef = useRef(null);

  // ==============================================================================
  // CONFIGURATION
  // ==============================================================================
  
  // API base URL - can be configured via environment variable in production
  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000/api';
  
  // Maximum input text length to prevent performance issues
  const MAX_INPUT_LENGTH = 1000;
  
  // Status check interval (30 seconds)
  const STATUS_CHECK_INTERVAL = 30000;
  
  // Category styling configuration
  const categoryStyles = {
    error: { 
      icon: '❌', 
      color: '#dc2626', 
      bg: '#fee2e2',
      description: 'Critical error requiring immediate attention'
    },
    warning: { 
      icon: '⚠️', 
      color: '#d97706', 
      bg: '#fef3c7',
      description: 'Warning that may require action'
    },
    info: { 
      icon: '✅', 
      color: '#059669', 
      bg: '#dcfce7',
      description: 'Informational message'
    },
    security: { 
      icon: '🔒', 
      color: '#7c3aed', 
      bg: '#f3e8ff',
      description: 'Security-related alert'
    },
    general: { 
      icon: '📋', 
      color: '#6b7280', 
      bg: '#f3f4f6',
      description: 'General monitoring message'
    }
  };

  // ==============================================================================
  // API COMMUNICATION FUNCTIONS
  // ==============================================================================
  
  /**
   * Check API health status
   * Verifies backend availability and model loading status
   */
  const checkApiStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/status-minimal`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        // Add timeout to prevent hanging requests
        signal: AbortSignal.timeout(5000)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setApiStatus(data);
      
      // Log status to console in development
      if (process.env.NODE_ENV === 'development') {
        console.log('API Status:', data);
      }
    } catch (error) {
      console.error('API health check failed:', error);
      setApiStatus({ 
        status: 'ERROR', 
        error: error.message || 'Backend not reachable',
        timestamp: new Date().toISOString()
      });
    }
  }, [API_BASE]);

  /**
   * Load supported languages from backend
   * Fetches available translation models and their metadata
   */
  const loadSupportedLanguages = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/languages`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: AbortSignal.timeout(5000)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setSupportedLanguages(data.supported_languages || {});
      
      // Update selected languages if defaults are provided
      if (data.default_languages && data.default_languages.length > 0) {
        setSelectedLanguages(data.default_languages);
      }
    } catch (error) {
      console.error('Failed to load supported languages:', error);
      // Set a minimal fallback configuration
      setSupportedLanguages({
        'de': { name: 'Deutsch' },
        'es': { name: 'Español' },
        'fr': { name: 'Français' }
      });
    }
  }, [API_BASE]);

  /**
   * Perform translation request
   * Sends text to backend for multi-language translation
   */
  const performTranslation = useCallback(async () => {
    // Validation checks
    if (!inputText.trim()) {
      setStatus({ 
        type: 'warning', 
        message: 'Please enter text to translate' 
      });
      return;
    }
    
    if (selectedLanguages.length === 0) {
      setStatus({ 
        type: 'warning', 
        message: 'Please select at least one target language' 
      });
      return;
    }
    
    if (inputText.length > MAX_INPUT_LENGTH) {
      setStatus({ 
        type: 'error', 
        message: `Text exceeds maximum length of ${MAX_INPUT_LENGTH} characters` 
      });
      return;
    }
    
    // Clear previous results and start loading
    setLoading(true);
    setTranslationResult(null);
    setStatus({ 
      type: 'info', 
      message: `Translating to ${selectedLanguages.length} languages...` 
    });
    
    try {
      const response = await fetch(`${API_BASE}/translate-minimal`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          text: inputText,
          languages: selectedLanguages
        }),
        // Longer timeout for translation requests
        signal: AbortSignal.timeout(30000)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      
      if (data.success) {
        setTranslationResult(data);
        setStatus({ 
          type: 'success', 
          message: `Successfully translated to ${Object.keys(data.translations).length - 1} languages!` 
        });
        
        // Log success metrics in development
        if (process.env.NODE_ENV === 'development') {
          console.log('Translation successful:', {
            originalLength: inputText.length,
            languages: selectedLanguages,
            category: data.detected_category
          });
        }
      } else {
        throw new Error(data.error || 'Translation failed');
      }
    } catch (error) {
      console.error('Translation error:', error);
      
      // Provide user-friendly error messages
      if (error.name === 'AbortError') {
        setStatus({ 
          type: 'error', 
          message: 'Translation request timed out. Please try again.' 
        });
      } else if (error.message.includes('NetworkError')) {
        setStatus({ 
          type: 'error', 
          message: 'Network error. Please check your connection.' 
        });
      } else {
        setStatus({ 
          type: 'error', 
          message: error.message || 'Translation failed. Please try again.' 
        });
      }
    } finally {
      setLoading(false);
    }
  }, [inputText, selectedLanguages, API_BASE]);

  /**
   * Copy JSON output to clipboard
   * Provides visual feedback on successful copy
   */
  const copyJsonToClipboard = useCallback(async () => {
    if (!translationResult?.json_output) return;
    
    try {
      // Use modern clipboard API with fallback
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(translationResult.json_output);
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = translationResult.json_output;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      
      setCopiedJson(true);
      setStatus({ 
        type: 'success', 
        message: 'JSON copied to clipboard!' 
      });
      
      // Clear copied state after 2 seconds
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
      copyTimeoutRef.current = setTimeout(() => {
        setCopiedJson(false);
      }, 2000);
      
    } catch (error) {
      console.error('Copy to clipboard failed:', error);
      setStatus({ 
        type: 'error', 
        message: 'Failed to copy to clipboard. Please try selecting and copying manually.' 
      });
    }
  }, [translationResult]);

  // ==============================================================================
  // UI INTERACTION HANDLERS
  // ==============================================================================
  
  /**
   * Handle file upload
   * Reads .txt and .json files and extracts content
   */
  const handleFileUpload = useCallback(async (file) => {
    if (!file) return;
    
    // Validate file type
    const validExtensions = ['.txt', '.json'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
      setStatus({
        type: 'error',
        message: 'Please upload a .txt or .json file'
      });
      return;
    }
    
    // Validate file size (max 1MB)
    if (file.size > 1024 * 1024) {
      setStatus({
        type: 'error',
        message: 'File size must be less than 1MB'
      });
      return;
    }
    
    try {
      const text = await file.text();
      let extractedText = text;
      
      // If JSON file, try to extract message field or stringify content
      if (fileExtension === '.json') {
        try {
          const jsonData = JSON.parse(text);
          
          // Try to find common message fields
          extractedText = jsonData.message || 
                         jsonData.text || 
                         jsonData.alert || 
                         jsonData.error || 
                         jsonData.warning ||
                         jsonData.content ||
                         JSON.stringify(jsonData, null, 2);
          
          // If extracted text is still JSON, stringify it nicely
          if (typeof extractedText === 'object') {
            extractedText = JSON.stringify(extractedText, null, 2);
          }
        } catch (e) {
          console.error('Invalid JSON file:', e);
          setStatus({
            type: 'error',
            message: 'Invalid JSON file format'
          });
          return;
        }
      }
      
      if (extractedText.length > MAX_INPUT_LENGTH) {
        setStatus({
          type: 'error',
          message: `File content exceeds maximum length of ${MAX_INPUT_LENGTH} characters`
        });
        return;
      }
      
      setInputText(extractedText);
      setUploadedFile(file);
      setStatus({
        type: 'success',
        message: `Loaded ${file.name} successfully`
      });
      
      // Auto-hide success message
      if (statusTimeoutRef.current) {
        clearTimeout(statusTimeoutRef.current);
      }
      statusTimeoutRef.current = setTimeout(() => {
        setStatus(null);
      }, 3000);
    } catch (error) {
      console.error('File reading error:', error);
      setStatus({
        type: 'error',
        message: 'Failed to read file. Please try again.'
      });
    }
  }, []);
  
  /**
   * Handle drag and drop events
   */
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);
  
  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);
  
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);
  
  /**
   * Handle file input change
   */
  const handleFileInputChange = useCallback((e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);
  
  /**
   * Clear uploaded file and reset input
   */
  const clearUploadedFile = useCallback(() => {
    setUploadedFile(null);
    setInputText('');
    setTranslationResult(null);
  }, []);
  
  /**
   * Toggle language selection
   * Adds or removes a language from the selected list
   */
  const toggleLanguage = useCallback((langCode) => {
    setSelectedLanguages(prev => {
      if (prev.includes(langCode)) {
        // Remove language
        return prev.filter(l => l !== langCode);
      } else {
        // Add language
        return [...prev, langCode];
      }
    });
  }, []);

  /**
   * Handle keyboard shortcuts
   * Ctrl+Enter: Perform translation
   * Escape: Clear input
   */
  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      performTranslation();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setInputText('');
      setTranslationResult(null);
    }
  }, [performTranslation]);

  /**
   * Auto-hide status messages after delay
   */
  const setStatusWithTimeout = useCallback((statusObj, timeout = 5000) => {
    setStatus(statusObj);
    
    if (statusTimeoutRef.current) {
      clearTimeout(statusTimeoutRef.current);
    }
    
    if (statusObj.type !== 'error') {
      statusTimeoutRef.current = setTimeout(() => {
        setStatus(null);
      }, timeout);
    }
  }, []);

  // ==============================================================================
  // LIFECYCLE EFFECTS
  // ==============================================================================
  
  /**
   * Initial setup effect
   * Loads configuration and checks API status
   */
  useEffect(() => {
    checkApiStatus();
    loadSupportedLanguages();
  }, [checkApiStatus, loadSupportedLanguages]);

  /**
   * Periodic API status check
   * Monitors backend health every 30 seconds
   */
  useEffect(() => {
    const interval = setInterval(checkApiStatus, STATUS_CHECK_INTERVAL);
    
    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, [checkApiStatus]);

  /**
   * Cleanup effect for timeouts
   * Prevents memory leaks from pending timeouts
   */
  useEffect(() => {
    return () => {
      if (statusTimeoutRef.current) {
        clearTimeout(statusTimeoutRef.current);
      }
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  // ==============================================================================
  // RENDER
  // ==============================================================================
  
  return (
    <div className="minimal-app">
      {/* Header Section */}
      <header className="minimal-header">
        <div className="header-container">
          <div className="header-left">
            <div className="logo-icon">
              <Monitor size={32} />
            </div>
            <div className="header-text">
              <h1>VICOS Translation</h1>
              <p>Monitoring Messages → Multi-Language JSON</p>
            </div>
          </div>
          
          {/* Status Indicators */}
          <div className="status-indicators">
            {/* Backend Status */}
            <div 
              className={`status-dot ${apiStatus?.status === 'OK' ? 'online' : 'offline'}`}
              title={apiStatus?.status === 'OK' ? 'Backend is online' : 'Backend is offline'}
            >
              <Server size={16} />
              <span>{apiStatus?.status === 'OK' ? 'Online' : 'Offline'}</span>
            </div>
            
            {/* Model Status */}
            <div 
              className={`status-dot ${apiStatus?.models_loaded > 0 ? 'loaded' : 'loading'}`}
              title={`${apiStatus?.models_loaded || 0} translation models loaded`}
            >
              <Database size={16} />
              <span>{apiStatus?.models_loaded || 0} Models</span>
            </div>
            
            {/* Language Support */}
            <div 
              className="status-dot info"
              title={`${Object.keys(supportedLanguages).length} languages supported`}
            >
              <Globe size={16} />
              <span>{Object.keys(supportedLanguages).length} Languages</span>
            </div>
          </div>
        </div>
      </header>

      {/* Status Message Display */}
      {status && (
        <div className={`status-message ${status.type} fade-in`}>
          {status.type === 'error' ? <AlertCircle size={16} /> :
           status.type === 'success' ? <CheckCircle size={16} /> :
           <RefreshCw size={16} className={status.type === 'info' ? 'spin' : ''} />}
          <span>{status.message}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="main-content">
        <div className="content-container">
          
          {/* Input Section */}
          <section className="input-section" aria-label="Translation Input">
            <div className="section-header">
              <Zap size={24} aria-hidden="true" />
              <h2>Input</h2>
            </div>
            
            <div className="input-form">
              {/* Text Input */}
              <div className="form-group">
                <label htmlFor="monitoring-message" className="form-label">
                  Monitoring Message
                  <span className="character-count">
                    {inputText.length}/{MAX_INPUT_LENGTH}
                  </span>
                </label>
                <textarea
                  id="monitoring-message"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="e.g., Database connection failed&#10;&#10;Tip: Press Ctrl+Enter to translate"
                  className={`input-textarea ${inputText.length > MAX_INPUT_LENGTH ? 'error' : ''}`}
                  rows="6"
                  maxLength={MAX_INPUT_LENGTH + 100} // Allow slight overflow for visual feedback
                  aria-describedby="input-help"
                  disabled={loading}
                />
                <small id="input-help" className="sr-only">
                  Enter a monitoring message to translate. Press Ctrl+Enter to start translation.
                </small>
              </div>
              
              {/* File Upload Area */}
              <div className="form-group">
                <label className="form-label">
                  Or Upload a Text File
                </label>
                <div
                  className={`file-upload-area ${dragOver ? 'drag-over' : ''} ${loading ? 'disabled' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('file-input').click()}
                  role="button"
                  tabIndex={0}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      document.getElementById('file-input').click();
                    }
                  }}
                  aria-label="Upload text or JSON file"
                >
                  <Upload size={32} className="file-upload-icon" />
                  <p className="file-upload-text">
                    Drop a .txt or .json file here or click to browse
                  </p>
                  <p className="file-upload-hint">
                    Maximum file size: 1MB • Supported: TXT, JSON
                  </p>
                  <input
                    id="file-input"
                    type="file"
                    accept=".txt,.json"
                    onChange={handleFileInputChange}
                    className="sr-only"
                    disabled={loading}
                  />
                </div>
                
                {uploadedFile && (
                  <div className="file-name-display">
                    <FileText size={16} />
                    <span>{uploadedFile.name}</span>
                    <button
                      onClick={clearUploadedFile}
                      className="clear-file-button"
                      aria-label="Clear uploaded file"
                      title="Clear file"
                    >
                      <X size={16} />
                    </button>
                  </div>
                )}
              </div>
              
              {/* Language Selection */}
              <div className="form-group">
                <label className="form-label">
                  Target Languages
                </label>
                <div className="language-grid" role="group" aria-label="Select target languages">
                  {Object.entries(supportedLanguages).map(([code, lang]) => {
                    const isSelected = selectedLanguages.includes(code);
                    const isPriority = ['de', 'es', 'fr'].includes(code);
                    
                    return (
                      <button
                        key={code}
                        onClick={() => toggleLanguage(code)}
                        className={`language-button ${isSelected ? 'selected' : ''} ${isPriority ? 'priority' : ''}`}
                        aria-pressed={isSelected}
                        aria-label={`${lang.name} (${code.toUpperCase()}) - ${isSelected ? 'Selected' : 'Not selected'}`}
                        disabled={loading}
                      >
                        <span className="lang-code">{code.toUpperCase()}</span>
                        <span className="lang-name">{lang.name}</span>
                      </button>
                    );
                  })}
                </div>
                <div className="selected-count" aria-live="polite">
                  {selectedLanguages.length} {selectedLanguages.length === 1 ? 'language' : 'languages'} selected
                </div>
              </div>
              
              {/* Translate Button */}
              <button
                onClick={performTranslation}
                disabled={loading || !inputText.trim() || selectedLanguages.length === 0}
                className="translate-button"
                aria-label={loading ? 'Translation in progress' : 'Start translation'}
              >
                {loading ? (
                  <>
                    <RefreshCw size={20} className="spin" aria-hidden="true" />
                    <span>Translating...</span>
                  </>
                ) : (
                  <>
                    <Globe size={20} aria-hidden="true" />
                    <span>Generate JSON</span>
                  </>
                )}
              </button>
            </div>
          </section>

          {/* Output Section */}
          <section className="output-section" aria-label="Translation Output">
            <div className="section-header">
              <Database size={24} aria-hidden="true" />
              <h2>Output</h2>
            </div>
            
            {translationResult ? (
              <div className="output-content fade-in">
                {/* Category Display */}
                <div className="category-display">
                  <div 
                    className="category-badge"
                    style={{
                      color: categoryStyles[translationResult.detected_category]?.color,
                      backgroundColor: categoryStyles[translationResult.detected_category]?.bg
                    }}
                    title={categoryStyles[translationResult.detected_category]?.description}
                  >
                    <span className="category-icon" aria-hidden="true">
                      {categoryStyles[translationResult.detected_category]?.icon}
                    </span>
                    <span className="category-name">
                      {translationResult.detected_category.charAt(0).toUpperCase() + 
                       translationResult.detected_category.slice(1)}
                    </span>
                  </div>
                </div>

                {/* JSON Output */}
                <div className="json-output">
                  <div className="json-header">
                    <h3>Production-Ready JSON</h3>
                    <button
                      onClick={copyJsonToClipboard}
                      className="copy-button"
                      aria-label={copiedJson ? 'JSON copied!' : 'Copy JSON to clipboard'}
                    >
                      <Copy size={16} aria-hidden="true" />
                      <span>{copiedJson ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  
                  <div className="json-display">
                    <pre className="json-code">
                      <code>{translationResult.json_output}</code>
                    </pre>
                  </div>
                </div>

                {/* Usage Example */}
                <details className="usage-preview">
                  <summary>
                    <h4 style={{ display: 'inline', cursor: 'pointer' }}>Usage Example</h4>
                  </summary>
                  <pre className="usage-code">
                    <code>{`// In your monitoring system:
const messages = ${JSON.stringify(translationResult.translations, null, 2)};

// With VICOS Translation Formatter:
logger.${translationResult.detected_category}(
  VicosTranslation.format(messages, userLocale)
);

// Example output for German user:
// "${translationResult.translations.de || translationResult.translations.en}"

// Example for integration:
if (alert.severity === '${translationResult.detected_category}') {
  notificationService.send({
    title: messages[userLanguage] || messages.en,
    severity: '${translationResult.detected_category}',
    timestamp: new Date().toISOString()
  });
}`}</code>
                  </pre>
                </details>

                {/* Metadata */}
                <div className="metadata">
                  <div className="metadata-item">
                    <span className="metadata-label">Languages:</span>
                    <span className="metadata-value">
                      {Object.keys(translationResult.translations).join(', ').toUpperCase()}
                    </span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-label">Generated:</span>
                    <span className="metadata-value">
                      <time dateTime={translationResult.timestamp}>
                        {new Date(translationResult.timestamp).toLocaleString('de-DE')}
                      </time>
                    </span>
                  </div>
                  {translationResult.metadata?.version && (
                    <div className="metadata-item">
                      <span className="metadata-label">API Version:</span>
                      <span className="metadata-value">
                        {translationResult.metadata.version}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="output-placeholder">
                <Globe size={64} className="placeholder-icon" aria-hidden="true" />
                <h3>Waiting for Input</h3>
                <p>
                  Enter a monitoring message and select target languages.
                  The JSON output will be generated automatically.
                </p>
                {apiStatus?.status !== 'OK' && (
                  <p className="warning-text">
                    ⚠️ Backend service is currently offline. Please ensure the API is running.
                  </p>
                )}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

export default VICOSMinimalTranslator;