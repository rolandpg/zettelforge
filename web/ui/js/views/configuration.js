window.ConfigurationView = {
  _config: null,
  _changes: {},
  _activeTab: 'flags',
  _editorContent: '',

  render: function() {
    var container = document.createElement('div');
    container.id = 'configuration-view';
    container.style.cssText = 'max-width:960px;';

    var heading = document.createElement('h2');
    heading.textContent = 'Configuration';
    heading.style.cssText = 'margin:0 0 var(--sp-4,16px);font-size:var(--text-xl,20px);font-weight:var(--fw-semibold,600);color:var(--fg-1,#C9D1D9);';
    container.appendChild(heading);

    // Tab bar
    var tabContainer = document.createElement('div');
    tabContainer.id = 'config-tabs';
    tabContainer.style.cssText = 'display:flex;gap:6px;margin-bottom:var(--sp-4,16px);';
    var tabs = ['flags', 'yaml'];
    var labels = { flags: 'Feature Flags', yaml: 'YAML Editor' };
    var self = this;

    tabs.forEach(function(t) {
      var active = self._activeTab === t;
      var btn = document.createElement('button');
      btn.textContent = labels[t] || t;
      btn.style.cssText = 'padding:8px 16px;background:' + (active ? 'var(--bg-surface-hi,#21262D)' : 'transparent') + ';border:1px solid ' + (active ? 'var(--border-focus,#58A6FF)' : 'var(--border,#30363D)') + ';border-radius:var(--r-sm,6px);color:' + (active ? 'var(--fg-1,#C9D1D9)' : 'var(--fg-2,#8B949E)') + ';cursor:pointer;font-size:var(--text-sm,12px);font-family:var(--font-sans);transition:color 120ms,background 120ms,border-color 120ms;';
      btn.addEventListener('mouseenter', function() { if (!active) btn.style.color = 'var(--fg-1,#C9D1D9)'; });
      btn.addEventListener('mouseleave', function() { if (!active) btn.style.color = 'var(--fg-2,#8B949E)'; });
      btn.addEventListener('click', function() {
        self._activeTab = t;
        container.innerHTML = '';
        container.appendChild(self.render().firstChild);
        // Re-render entire view
        var newContainer = self.render();
        container.parentNode.replaceChild(newContainer, container);
      });
      tabContainer.appendChild(btn);
    });

    container.appendChild(tabContainer);

    // Content area
    var content = document.createElement('div');
    content.id = 'config-content';
    container.appendChild(content);

    if (this._activeTab === 'flags') {
      content.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;padding:var(--sp-8,32px);gap:8px;color:var(--fg-2,#8B949E);font-size:var(--text-sm,12px);"><div class="pulse" style="width:16px;height:16px;border-radius:50%;border:2px solid var(--border,#30363D);border-top-color:var(--signal-neon,#00FFA3);"></div> Loading configuration...</div>';
      this.loadFlags(content);
    } else {
      this.loadYamlEditor(content);
    }

    return container;
  },

  loadFlags: function(contentEl) {
    var self = this;

    window.API.get('/api/config').then(function(config) {
      self._config = config;
      self._changes = {};
      self.renderFlags(contentEl, config);
    }).catch(function(err) {
      contentEl.innerHTML = '<div style="padding:var(--sp-4,16px);background:var(--bg-surface,#161B22);border:1px solid var(--danger,#F85149);border-radius:var(--r-md,8px);color:var(--danger,#F85149);font-size:var(--text-sm,12px);font-family:var(--font-mono);">Failed to load configuration: ' + (err.message || 'unknown error') + '</div>';
    });
  },

  renderFlags: function(container, config) {
    container.innerHTML = '';

    if (!config || Object.keys(config).length === 0) {
      container.innerHTML = '<div style="padding:var(--sp-6,24px);text-align:center;color:var(--fg-3,#484F58);font-size:var(--text-sm,12px);font-family:var(--font-mono);">No configuration data available</div>';
      return;
    }

    // Group config into sections
    var groups = {
      'Core': ['version', 'edition', 'data_dir', 'log_level', 'log_file', 'max_content_length', 'max_file_size'],
      'LLM': ['llm_provider', 'llm_model', 'llm_local_backend', 'llm_temperature', 'llm_max_tokens', 'llm_api_key'],
      'Embedding': ['embedding_provider', 'embedding_model', 'embedding_dimensions', 'embedding_api_key'],
      'Retrieval': ['top_k', 'min_score', 'recall_rerank', 'recall_hybrid_search'],
      'Synthesis': ['synthesis_enabled', 'synthesis_default_format', 'synthesis_max_sources'],
      'Governance': ['governance_enabled', 'governance_policy'],
      'Logging': ['log_level', 'log_file', 'log_format', 'telemetry_enabled']
    };

    var self = this;
    var matchedKeys = {};

    for (var groupName in groups) {
      if (!groups.hasOwnProperty(groupName)) continue;
      var keys = groups[groupName];
      var groupConfig = {};

      keys.forEach(function(k) {
        if (config[k] !== undefined) {
          groupConfig[k] = config[k];
          matchedKeys[k] = true;
        }
      });

      // Add any remaining unmapped keys
      if (Object.keys(groupConfig).length === 0) continue;

      var card = document.createElement('div');
      card.style.cssText = 'background:var(--bg-surface,#161B22);border:1px solid var(--border,#30363D);border-radius:var(--r-md,8px);padding:var(--sp-4,16px);margin-bottom:var(--sp-4,16px);';

      var cardTitle = document.createElement('h3');
      cardTitle.textContent = groupName;
      cardTitle.style.cssText = 'margin:0 0 var(--sp-3,12px);font-size:var(--text-base,14px);font-weight:var(--fw-semibold,600);color:var(--fg-1,#C9D1D9);';
      card.appendChild(cardTitle);

      for (var key in groupConfig) {
        if (!groupConfig.hasOwnProperty(key)) continue;
        var val = groupConfig[key];
        var row = document.createElement('div');
        row.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border,#30363D);';
        row.style.borderBottom = '1px solid var(--border,#30363D)';

        var labelDiv = document.createElement('div');
        labelDiv.style.cssText = 'flex:1;';

        var nameSpan = document.createElement('div');
        nameSpan.textContent = key;
        nameSpan.style.cssText = 'font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--fg-1,#C9D1D9);';
        labelDiv.appendChild(nameSpan);

        var descHint = document.createElement('div');
        descHint.style.cssText = 'font-size:10px;color:var(--fg-3,#484F58);margin-top:2px;';
        descHint.textContent = self.getDescriptionHint(key);
        labelDiv.appendChild(descHint);

        row.appendChild(labelDiv);

        var controlDiv = document.createElement('div');
        controlDiv.style.cssText = 'flex-shrink:0;margin-left:12px;';

        var isSecret = key.indexOf('api_key') !== -1 || key.indexOf('secret') !== -1 || key.indexOf('password') !== -1 || key.indexOf('token') !== -1;
        var isBool = typeof val === 'boolean';
        var isNum = typeof val === 'number';

        if (isSecret) {
          var secretSpan = document.createElement('span');
          secretSpan.textContent = '***';
          secretSpan.style.cssText = 'font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--fg-3,#484F58);padding:4px 8px;background:var(--bg-input,#0D1117);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);';
          secretSpan.setAttribute('readonly', 'true');
          controlDiv.appendChild(secretSpan);
        } else if (isBool) {
          var toggleLabel = document.createElement('label');
          toggleLabel.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;';
          var toggle = document.createElement('input');
          toggle.type = 'checkbox';
          toggle.checked = val;
          toggle.style.cssText = 'accent-color:var(--signal-neon,#00FFA3);';
          toggle.setAttribute('data-config-key', key);
          toggle.addEventListener('change', function() {
            var k = this.getAttribute('data-config-key');
            self._changes[k] = this.checked;
            self.updateApplyButton();
          });
          toggleLabel.appendChild(toggle);
          var toggleText = document.createElement('span');
          toggleText.textContent = val ? 'enabled' : 'disabled';
          toggleText.style.cssText = 'font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);font-family:var(--font-mono);';
          toggleLabel.appendChild(toggleText);

          // Update text on change
          toggle.addEventListener('change', function() {
            this.nextSibling.textContent = this.checked ? 'enabled' : 'disabled';
          });

          controlDiv.appendChild(toggleLabel);
        } else {
          var input = document.createElement('input');
          input.type = isNum ? 'number' : 'text';
          input.value = val !== null && val !== undefined ? String(val) : '';
          input.style.cssText = 'width:160px;padding:4px 8px;background:var(--bg-input,#0D1117);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);color:var(--fg-1,#C9D1D9);font-size:var(--text-xs,11px);font-family:var(--font-mono);outline:none;text-align:right;';
          input.setAttribute('data-config-key', key);
          input.addEventListener('change', function() {
            var k = this.getAttribute('data-config-key');
            var original = config[k];
            var newVal = this.value;
            if (typeof original === 'number') newVal = parseFloat(newVal) || 0;
            self._changes[k] = newVal;
            self.updateApplyButton();
          });
          controlDiv.appendChild(input);
        }

        row.appendChild(controlDiv);
        card.appendChild(row);
      }

      container.appendChild(card);
    }

    // Handle any remaining unmapped keys
    var unmapped = {};
    for (var k in config) {
      if (config.hasOwnProperty(k) && !matchedKeys[k]) {
        unmapped[k] = config[k];
      }
    }
    if (Object.keys(unmapped).length > 0) {
      var otherCard = document.createElement('div');
      otherCard.style.cssText = 'background:var(--bg-surface,#161B22);border:1px solid var(--border,#30363D);border-radius:var(--r-md,8px);padding:var(--sp-4,16px);margin-bottom:var(--sp-4,16px);';
      var otherTitle = document.createElement('h3');
      otherTitle.textContent = 'Other';
      otherTitle.style.cssText = 'margin:0 0 var(--sp-3,12px);font-size:var(--text-base,14px);font-weight:var(--fw-semibold,600);color:var(--fg-1,#C9D1D9);';
      otherCard.appendChild(otherTitle);

      for (var uk in unmapped) {
        if (!unmapped.hasOwnProperty(uk)) continue;
        var uv = unmapped[uk];
        var orow = document.createElement('div');
        orow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border,#30363D);';

        var olabel = document.createElement('span');
        olabel.textContent = uk;
        olabel.style.cssText = 'font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--fg-1,#C9D1D9);';
        orow.appendChild(olabel);

        var oval = document.createElement('span');
        oval.textContent = typeof uv === 'object' ? JSON.stringify(uv) : String(uv);
        oval.style.cssText = 'font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);font-family:var(--font-mono);';
        orow.appendChild(oval);

        otherCard.appendChild(orow);
      }

      container.appendChild(otherCard);
    }

    // Apply button
    var applyRow = document.createElement('div');
    applyRow.id = 'config-apply-row';
    applyRow.style.cssText = 'display:flex;gap:var(--sp-3,12px);align-items:center;margin-top:var(--sp-4,16px);';

    var applyBtn = document.createElement('button');
    applyBtn.id = 'config-apply-btn';
    applyBtn.textContent = 'Apply Changes';
    applyBtn.style.cssText = 'padding:8px 20px;background:#238636;border:none;border-radius:var(--r-sm,6px);color:#fff;cursor:pointer;font-size:var(--text-sm,12px);font-family:var(--font-sans);transition:background 120ms;';
    applyBtn.addEventListener('mouseenter', function() { applyBtn.style.background = '#2EA043'; });
    applyBtn.addEventListener('mouseleave', function() { applyBtn.style.background = '#238636'; });
    applyBtn.addEventListener('click', function() { window.ConfigurationView.applyChanges(); });

    var pendingCount = Object.keys(this._changes).length;
    if (pendingCount === 0) {
      applyBtn.disabled = true;
      applyBtn.style.opacity = '0.4';
      applyBtn.style.cursor = 'default';
    }

    applyRow.appendChild(applyBtn);

    var pendingSpan = document.createElement('span');
    pendingSpan.id = 'config-pending-count';
    pendingSpan.textContent = pendingCount > 0 ? pendingCount + ' pending change(s)' : '';
    pendingSpan.style.cssText = 'font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);font-family:var(--font-mono);';
    applyRow.appendChild(pendingSpan);

    container.appendChild(applyRow);

    // Result area
    var resultArea = document.createElement('div');
    resultArea.id = 'config-result';
    resultArea.style.cssText = 'margin-top:var(--sp-3,12px);';
    container.appendChild(resultArea);
  },

  updateApplyButton: function() {
    var btn = document.getElementById('config-apply-btn');
    var span = document.getElementById('config-pending-count');
    var count = Object.keys(this._changes).length;
    if (btn) {
      btn.disabled = count === 0;
      btn.style.opacity = count === 0 ? '0.4' : '1';
      btn.style.cursor = count === 0 ? 'default' : 'pointer';
    }
    if (span) {
      span.textContent = count > 0 ? count + ' pending change(s)' : '';
    }
  },

  applyChanges: function() {
    var self = this;
    var btn = document.getElementById('config-apply-btn');
    var resultArea = document.getElementById('config-result');
    if (!resultArea) return;

    var changes = this._changes;
    if (Object.keys(changes).length === 0) {
      window.ToastComponent.show('No changes to apply', 'info');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Applying...';
    }

    resultArea.innerHTML = '<div style="display:flex;align-items:center;gap:8px;padding:12px 0;color:var(--fg-2,#8B949E);font-size:var(--text-sm,12px);"><div class="pulse" style="width:16px;height:16px;border-radius:50%;border:2px solid var(--border,#30363D);border-top-color:var(--signal-neon,#00FFA3);"></div> Applying configuration changes...</div>';

    window.API.put('/api/config', changes).then(function(data) {
      self._changes = {};
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Apply Changes';
        btn.style.opacity = '0.4';
      }
      self.updateApplyButton();

      var html = '<div style="background:var(--bg-input,#0D1117);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);padding:var(--sp-3,12px);">';

      if (data.applied && data.applied.length) {
        html += '<div style="margin-bottom:8px;"><span style="font-size:var(--text-xs,11px);color:var(--success,#3FB950);font-family:var(--font-mono);font-weight:600;">Applied:</span></div>';
        data.applied.forEach(function(k) {
          html += '<div style="padding:2px 0;font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--success,#3FB950);">\u2713 ' + k + '</div>';
        });
      }

      if (data.pending_restart && data.pending_restart.length) {
        html += '<div style="margin-top:8px;margin-bottom:4px;">';
        html += '<span style="font-size:var(--text-xs,11px);color:var(--warning,#D29922);font-family:var(--font-mono);font-weight:600;">Pending Restart:</span>';
        html += '<span style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:var(--r-pill,9999px);font-size:10px;font-family:var(--font-mono);background:var(--tier-c-bg,#3A2A0F);color:var(--warning,#D29922);">Restart Required</span>';
        html += '</div>';
        data.pending_restart.forEach(function(k) {
          html += '<div style="padding:2px 0;font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--warning,#D29922);">\u26A0 ' + k + '</div>';
        });
      }

      html += '</div>';
      resultArea.innerHTML = html;

      window.ToastComponent.show('Configuration applied', 'success');
    }).catch(function(err) {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Apply Changes';
        btn.style.opacity = '1';
      }
      resultArea.innerHTML = '<div style="padding:12px;color:var(--danger,#F85149);font-size:var(--text-sm,12px);font-family:var(--font-mono);background:var(--bg-input,#0D1117);border:1px solid var(--danger,#F85149);border-radius:var(--r-sm,6px);">Failed to apply: ' + (err.message || 'unknown error') + '</div>';
      window.ToastComponent.show('Apply failed: ' + err.message, 'error');
    });
  },

  loadYamlEditor: function(contentEl) {
    var self = this;

    contentEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;padding:var(--sp-8,32px);gap:8px;color:var(--fg-2,#8B949E);font-size:var(--text-sm,12px);"><div class="pulse" style="width:16px;height:16px;border-radius:50%;border:2px solid var(--border,#30363D);border-top-color:var(--signal-neon,#00FFA3);"></div> Loading configuration...</div>';

    window.API.get('/api/config').then(function(config) {
      self._config = config;
      self._editorContent = self.configToYaml(config);
      self.renderYamlEditor(contentEl, config);
    }).catch(function(err) {
      contentEl.innerHTML = '<div style="padding:var(--sp-4,16px);background:var(--bg-surface,#161B22);border:1px solid var(--danger,#F85149);border-radius:var(--r-md,8px);color:var(--danger,#F85149);font-size:var(--text-sm,12px);font-family:var(--font-mono);">Failed to load configuration: ' + (err.message || 'unknown error') + '</div>';
    });
  },

  configToYaml: function(config, indent) {
    if (indent === undefined) indent = '';
    var yaml = '';
    for (var k in config) {
      if (!config.hasOwnProperty(k)) continue;
      var v = config[k];
      if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
        yaml += indent + k + ':\n';
        yaml += this.configToYaml(v, indent + '  ');
      } else if (Array.isArray(v)) {
        yaml += indent + k + ':\n';
        v.forEach(function(item) {
          yaml += indent + '  - ' + item + '\n';
        });
      } else if (typeof v === 'boolean') {
        yaml += indent + k + ': ' + (v ? 'true' : 'false') + '\n';
      } else if (typeof v === 'number') {
        yaml += indent + k + ': ' + v + '\n';
      } else if (v === null) {
        yaml += indent + k + ': null\n';
      } else {
        var strVal = String(v);
        var isSecret = k.indexOf('api_key') !== -1 || k.indexOf('secret') !== -1 || k.indexOf('password') !== -1 || k.indexOf('token') !== -1;
        if (isSecret) strVal = '***';
        if (strVal.indexOf('#') !== -1 || strVal.indexOf(':') !== -1 || strVal.indexOf('\n') !== -1 || strVal === '') {
          yaml += indent + k + ': "' + strVal.replace(/"/g, '\\"') + '"\n';
        } else {
          yaml += indent + k + ': ' + strVal + '\n';
        }
      }
    }
    return yaml;
  },

  renderYamlEditor: function(container, config) {
    container.innerHTML = '';

    // Warning banner
    var warning = document.createElement('div');
    warning.style.cssText = 'background:rgba(210,153,34,0.08);border:1px solid var(--warning,#D29922);border-radius:var(--r-sm,6px);padding:8px 12px;font-size:var(--text-xs,11px);color:var(--warning,#D29922);font-family:var(--font-mono);margin-bottom:var(--sp-3,12px);display:flex;align-items:center;gap:8px;';
    warning.innerHTML = '<span style="flex-shrink:0;">\u26A0</span> Some changes require a restart. API keys and secrets are shown as "***" and are not editable.';
    container.appendChild(warning);

    // Editor
    var editor = document.createElement('textarea');
    editor.id = 'config-yaml-editor';
    editor.value = this._editorContent;
    editor.style.cssText = 'width:100%;min-height:400px;padding:var(--sp-4,16px);background:#0D1117;border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);color:var(--fg-1,#C9D1D9);font-size:var(--text-xs,11px);font-family:var(--font-mono, "JetBrains Mono");resize:vertical;outline:none;box-sizing:border-box;tab-size:2;line-height:1.5;';
    editor.addEventListener('input', function() {
      window.ConfigurationView._editorContent = this.value;
    });
    container.appendChild(editor);

    // Action buttons
    var actionRow = document.createElement('div');
    actionRow.style.cssText = 'display:flex;gap:var(--sp-2,8px);margin-top:var(--sp-3,12px);';

    var applyYamlBtn = document.createElement('button');
    applyYamlBtn.textContent = 'Apply';
    applyYamlBtn.style.cssText = 'padding:8px 20px;background:#238636;border:none;border-radius:var(--r-sm,6px);color:#fff;cursor:pointer;font-size:var(--text-sm,12px);font-family:var(--font-sans);transition:background 120ms;';
    applyYamlBtn.addEventListener('mouseenter', function() { applyYamlBtn.style.background = '#2EA043'; });
    applyYamlBtn.addEventListener('mouseleave', function() { applyYamlBtn.style.background = '#238636'; });
    applyYamlBtn.addEventListener('click', function() { window.ConfigurationView.applyYaml(); });
    actionRow.appendChild(applyYamlBtn);

    var resetYamlBtn = document.createElement('button');
    resetYamlBtn.textContent = 'Reset to Default';
    resetYamlBtn.style.cssText = 'padding:8px 20px;background:var(--bg-surface,#161B22);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);color:var(--fg-2,#8B949E);cursor:pointer;font-size:var(--text-sm,12px);font-family:var(--font-sans);transition:border-color 120ms,color 120ms;';
    resetYamlBtn.addEventListener('mouseenter', function() { resetYamlBtn.style.borderColor = 'var(--danger,#F85149)'; resetYamlBtn.style.color = 'var(--fg-1,#C9D1D9)'; });
    resetYamlBtn.addEventListener('mouseleave', function() { resetYamlBtn.style.borderColor = 'var(--border,#30363D)'; resetYamlBtn.style.color = 'var(--fg-2,#8B949E)'; });
    resetYamlBtn.addEventListener('click', function() { window.ConfigurationView.resetYaml(); });
    actionRow.appendChild(resetYamlBtn);

    container.appendChild(actionRow);

    // Result area
    var resultArea = document.createElement('div');
    resultArea.id = 'config-yaml-result';
    resultArea.style.cssText = 'margin-top:var(--sp-3,12px);';
    container.appendChild(resultArea);
  },

  applyYaml: function() {
    var self = this;
    var btn = document.querySelector('#config-content button:first-child');
    var resultArea = document.getElementById('config-yaml-result');
    if (!resultArea) return;

    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Applying...';
    }

    resultArea.innerHTML = '<div style="display:flex;align-items:center;gap:8px;padding:12px 0;color:var(--fg-2,#8B949E);font-size:var(--text-sm,12px);"><div class="pulse" style="width:16px;height:16px;border-radius:50%;border:2px solid var(--border,#30363D);border-top-color:var(--signal-neon,#00FFA3);"></div> Applying YAML configuration...</div>';

    // Simple YAML parser for flat key: value pairs
    var yamlText = this._editorContent;
    var configObj = {};
    var lines = yamlText.split('\n');
    var currentKey = null;
    var currentIndent = 0;

    lines.forEach(function(line) {
      var trimmed = line.trim();
      if (!trimmed || trimmed.charAt(0) === '#') return;

      var indent = line.search(/\S/);
      if (indent === -1) return;

      // Check if it's a key: value pair
      var colonIdx = trimmed.indexOf(':');
      if (colonIdx === -1) return;

      var key = trimmed.slice(0, colonIdx).trim();
      var value = trimmed.slice(colonIdx + 1).trim();

      if (value === '') {
        // It's a parent key with children — skip for flat submission
        return;
      }

      // Parse YAML value types
      if (value === 'true') value = true;
      else if (value === 'false') value = false;
      else if (value === 'null' || value === '~') value = null;
      else if (value.match(/^-?\d+\.?\d*$/) && !isNaN(parseFloat(value))) {
        if (value.indexOf('.') !== -1) value = parseFloat(value);
        else value = parseInt(value, 10);
      } else if ((value.charAt(0) === '"' && value.charAt(value.length - 1) === '"') ||
                 (value.charAt(0) === "'" && value.charAt(value.length - 1) === "'")) {
        value = value.slice(1, -1);
      }

      configObj[key] = value;
    });

    window.API.put('/api/config', configObj).then(function(data) {
      if (btn) { btn.disabled = false; btn.textContent = 'Apply'; }

      var html = '<div style="background:var(--bg-input,#0D1117);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);padding:var(--sp-3,12px);">';

      if (data.applied && data.applied.length) {
        html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--success,#3FB950);font-family:var(--font-mono);font-weight:600;">Applied:</span></div>';
        data.applied.forEach(function(k) {
          html += '<div style="padding:2px 0;font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--success,#3FB950);">\u2713 ' + k + '</div>';
        });
      }

      if (data.pending_restart && data.pending_restart.length) {
        html += '<div style="margin-top:6px;margin-bottom:4px;">';
        html += '<span style="font-size:var(--text-xs,11px);color:var(--warning,#D29922);font-family:var(--font-mono);font-weight:600;">Pending Restart:</span>';
        html += '<span style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:var(--r-pill,9999px);font-size:10px;font-family:var(--font-mono);background:var(--tier-c-bg,#3A2A0F);color:var(--warning,#D29922);">Restart Required</span>';
        html += '</div>';
        data.pending_restart.forEach(function(k) {
          html += '<div style="padding:2px 0;font-size:var(--text-xs,11px);font-family:var(--font-mono);color:var(--warning,#D29922);">\u26A0 ' + k + '</div>';
        });
      }

      html += '</div>';
      resultArea.innerHTML = html;
      window.ToastComponent.show('YAML configuration applied', 'success');
    }).catch(function(err) {
      if (btn) { btn.disabled = false; btn.textContent = 'Apply'; }
      resultArea.innerHTML = '<div style="padding:12px;color:var(--danger,#F85149);font-size:var(--text-sm,12px);font-family:var(--font-mono);background:var(--bg-input,#0D1117);border:1px solid var(--danger,#F85149);border-radius:var(--r-sm,6px);">Failed to apply: ' + (err.message || 'unknown error') + '</div>';
      window.ToastComponent.show('Apply failed: ' + err.message, 'error');
    });
  },

  resetYaml: function() {
    var self = this;
    var resultArea = document.getElementById('config-yaml-result');
    var editor = document.getElementById('config-yaml-editor');

    if (editor) {
      editor.value = 'Loading configuration...';
    }

    window.API.get('/api/config').then(function(config) {
      self._config = config;
      self._editorContent = self.configToYaml(config);
      if (editor) {
        editor.value = self._editorContent;
      }
      if (resultArea) {
        resultArea.innerHTML = '<div style="padding:12px;color:var(--success,#3FB950);font-size:var(--text-xs,11px);font-family:var(--font-mono);">Configuration reset to current server state</div>';
      }
      window.ToastComponent.show('Configuration reset to server state', 'info');
    }).catch(function(err) {
      if (resultArea) {
        resultArea.innerHTML = '<div style="padding:12px;color:var(--danger,#F85149);font-size:var(--text-sm,12px);font-family:var(--font-mono);">Failed to fetch config: ' + (err.message || 'unknown error') + '</div>';
      }
    });
  },

  getDescriptionHint: function(key) {
    var hints = {
      log_level: 'Log verbosity (DEBUG, INFO, WARNING, ERROR)',
      log_file: 'Path to log output file',
      data_dir: 'Data storage directory path',
      top_k: 'Number of results to retrieve',
      min_score: 'Minimum relevance score threshold',
      llm_provider: 'LLM backend provider',
      llm_model: 'Model identifier string',
      llm_temperature: 'Response creativity (0.0 - 2.0)',
      llm_max_tokens: 'Maximum tokens per response',
      llm_api_key: 'API key for LLM provider',
      embedding_provider: 'Embedding service provider',
      embedding_model: 'Embedding model identifier',
      embedding_dimensions: 'Vector dimension count',
      embedding_api_key: 'API key for embedding service',
      synthesis_enabled: 'Enable synthesis pipeline',
      synthesis_default_format: 'Default synthesis output format',
      synthesis_max_sources: 'Maximum sources per synthesis',
      governance_enabled: 'Enforce governance policies',
      governance_policy: 'Governance policy ruleset',
      telemetry_enabled: 'Collect and report telemetry',
      recall_rerank: 'Enable reranking of results',
      recall_hybrid_search: 'Combine vector and keyword search',
      max_content_length: 'Maximum content body size',
      max_file_size: 'Maximum uploaded file size'
    };
    return hints[key] || '';
  }
};
