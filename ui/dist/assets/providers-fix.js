/**
 * providers-sync.js — Synchronous provider sync via XHR (runs before React)
 * Forces OpenCode Zen + deepseek-v4-flash-free as default on every load.
 */
(function() {
  var STORAGE_KEY = 'nexus-ai-providers';
  var DEFAULT_KEY = 'nexus-default-provider';
  var DEFAULT_MODEL_KEY = 'nexus-default-model';

  try {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/providers', false);
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
        if (existing) {
          var newModels = sp.models.map(function(m) { return m.id; });
          if (JSON.stringify(existing.models) !== JSON.stringify(newModels)) {
            existing.models = newModels;
            changed = true;
          }
        }
      } else {
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

    // ALWAYS force OpenCode Zen as default provider
    var zenExists = false;
    for (var k = 0; k < current.length; k++) {
      if (current[k].id === 'opencode-zen') {
        zenExists = true;
        current[k].favorite = true;
        break;
      }
    }
    if (zenExists) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
      localStorage.setItem(DEFAULT_KEY, 'opencode-zen');
      localStorage.setItem(DEFAULT_MODEL_KEY, 'deepseek-v4-flash-free');
    }
  } catch (e) {
    // Silent fail
  }
})();
