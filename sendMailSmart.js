(function (global) {
  'use strict';

  // Configuration: backend endpoints (do not change API paths)
  const LOCAL_ENDPOINT = 'http://127.0.0.1:5500/send-mail';

  // Default timeout for fetch (ms) — reduced for snappier feedback
  const DEFAULT_TIMEOUT_MS = 5000;

  // Minimal set of required payload keys (must match backend)
  const REQUIRED_KEYS = ['name', 'email', 'phone', 'message', 'source'];

  // Utility: determine whether current page is running on localhost
  function isLocalhostEnvironment() {
    if (typeof window === 'undefined' || !window.location) return false;
    const host = window.location.hostname;
    return (
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host === '::1' ||
      /^\s*127\.\d+\.\d+\.\d+\s*$/.test(host)
    );
  }

  // Helper: perform a POST JSON fetch with timeout and robust error handling.
  // Returns an object: { ok: boolean, status?: number, data?: any, error?: string }
  async function sendToEndpoint(endpointUrl, payload, timeoutMs = DEFAULT_TIMEOUT_MS) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(endpointUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(id);

      const status = res.status;

      if (!res.ok) {
        // Non-2xx response
        return {
          ok: false,
          status,
          error: `Non-OK HTTP status: ${status} ${res.statusText || ''}`.trim()
        };
      }

      // Try to parse JSON; handle parse errors
      let parsed;
      try {
        parsed = await res.json();
      } catch (jsonErr) {
        return {
          ok: false,
          status,
          error: `Failed to parse JSON response: ${jsonErr && jsonErr.message ? jsonErr.message : String(jsonErr)}`
        };
      }

      // Success
      return { ok: true, status, data: parsed };
    } catch (err) {
      clearTimeout(id);
      // Distinguish abort/timeout vs network errors
      if (err && err.name === 'AbortError') {
        return { ok: false, error: `Request timed out after ${timeoutMs}ms` };
      }
      return { ok: false, error: err && err.message ? err.message : String(err) };
    }
  }

  // Validate payload has required keys (do not change keys)
  function validatePayload(payload) {
    if (!payload || typeof payload !== 'object') {
      return 'Payload must be an object with required keys';
    }
    for (const key of REQUIRED_KEYS) {
      if (!(key in payload)) {
        return `Missing required payload key: ${key}`;
      }
    }
    return null;
  }

  // Main exported function:
  // Sends to a single chosen endpoint (local when on localhost, otherwise primary).
  // Returns a standardized result: { success: true/false, status?, data?, error? }
  async function sendMailSmart(payload, options = {}) {
    const timeoutMs = typeof options.timeoutMs === 'number' ? options.timeoutMs : DEFAULT_TIMEOUT_MS;

    const validationError = validatePayload(payload);
    if (validationError) {
      return { success: false, error: validationError };
    }

    // Try multiple candidates so the client works regardless of which port the page is served on.
    const candidates = [];

    if (typeof window !== 'undefined' && window.location && /^https?:/.test(window.location.protocol)) {
      // 1) same-origin (useful if backend is reverse-proxied or served from same host)
      candidates.push(window.location.origin + '/send-mail');
      // 2) same hostname but backend default port 5000
      if (window.location.hostname) {
        candidates.push(window.location.protocol + '//' + window.location.hostname + ':5000/send-mail');
      }
    }

    // 3) explicit localhost addresses (common developer setups)
    candidates.push('http://127.0.0.1:5000/send-mail');
    candidates.push('http://localhost:5000/send-mail');
    candidates.push(LOCAL_ENDPOINT);

    let lastError = null;
    for (const endpoint of candidates) {
      const res = await sendToEndpoint(endpoint, payload, timeoutMs);
      if (res && res.ok) {
        try { console.info('sendMailSmart: succeeded via', endpoint); } catch (e) { }
        return { success: true, status: res.status ?? null, data: res.data, backend: endpoint };
      }
      lastError = res && res.error ? res.error : 'Unknown error';
    }

    return { success: false, error: lastError ?? 'All endpoints failed' };
  }

  // Sample handler function:
  // Usage:
  //  - Provide `payload` object with exact keys: name,email,phone,message,source
  //  - Provide optional callbacks in `opts`: onSuccess(result), onError(errorMessage)
  //  - This handler ensures user only sees final success/failure; intermediate errors are not shown.
  async function handleSend(payload, opts = {}) {
    const onSuccess = typeof opts.onSuccess === 'function' ? opts.onSuccess : () => { };
    const onError = typeof opts.onError === 'function' ? opts.onError : () => { };
    const timeoutMs = typeof opts.timeoutMs === 'number' ? opts.timeoutMs : DEFAULT_TIMEOUT_MS;

    try {
      const result = await sendMailSmart(payload, { timeoutMs });

      if (result && result.success) {
        // Only final success shown to user
        onSuccess({
          message: 'Message sent successfully.',
          backend: result.backend,
          data: result.data
        });
        return { success: true, backend: result.backend, data: result.data };
      } else {
        // Only final failure shown to user
        // Create a user-friendly error message (without exposing intermediate details)
        onError('Failed to send message. Please try again later.');
        return { success: false, error: result && result.error ? result.error : 'Unknown error', attempts: result && result.attempts ? result.attempts : [] };
      }
    } catch (err) {
      // Catch any unexpected errors; do not expose intermediate details to end user
      try { console.error('handleSend: unexpected error', err); } catch (e) { }
      onError('Failed to send message. Please try again later.');
      return { success: false, error: err && err.message ? err.message : String(err) };
    }
  }

  // Expose functions to global scope for use in plain JS projects
  global.sendMailSmart = sendMailSmart;
  global.handleSend = handleSend;

})(typeof window !== 'undefined' ? window : this);
