/**
 * providers-sync.js — Synchronous provider sync via XHR (runs before React)
 * This script must be loaded as a regular <script> in <head>, BEFORE the deferred main bundle.
 */
(function() {
  var STORAGE_KEY = 'nexus-ai-providers';
  var DEFAULT_KEY = 'nexus-default-provider';

  // Use synchronous XHR so providers are in localStorage before React reads them
  try {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/providers', false); // false = synchronous
    xhr.send();
    if (xhr.status !== 200) return;
    var serverProviders = JSON.parse(xhr.responseText);

    var current = [];
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) current = JSON.parse(raw);
    } catch {}

    var changed = false;
    for (var i = 0; i < serverProviders.length; i++) {
      var sp = serverProviders[i];
      var existing = null;
      for (var j = 0; j < current.length; j++) {
        if (current[j].id === sp.id) { existing = current[j]; break; }
      }
      if (sp.id === 'ollama') {
        // Keep existing Ollama config, just sync models list
        if (existing) {
          var newModels = sp.models.map(function(m) { return m.id; });
          if (JSON.stringify(existing.models) !== JSON.stringify(newModels)) {
            existing.models = newModels;
            changed = true;
          }
        }
      } else {
        // Cloud/other: add or update
        var providerModels = sp.models.map(function(m) { return m.id; });
        if (existing) {
          if (JSON.stringify(existing.models) !== JSON.stringify(providerModels)) {
            existing.models = providerModels;
            existing.online = sp.online;
            changed = true;
          }
        } else {
          current.push({
            id: sp.id,
            name: sp.name,
            baseUrl: '',
            enabled: sp.online,
            free: true,
            online: sp.online,
            models: providerModels
          });
          changed = true;
        }
      }
    }

    if (changed) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
    }

    // Set opencode-zen as favorite if no favorite is set
    if (!localStorage.getItem(DEFAULT_KEY)) {
      for (var k = 0; k < current.length; k++) {
        if (current[k].id === 'opencode-zen' && current[k].models.length > 0) {
          current[k].favorite = true;
          localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
          localStorage.setItem(DEFAULT_KEY, current[k].id);
          break;
        }
      }
    }
  } catch (e) {
    // Silent fail — Ollama defaults will be used
  }
})();
