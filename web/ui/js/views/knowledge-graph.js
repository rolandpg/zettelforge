window.KnowledgeGraphView = {
  _nodes: [],
  _edges: [],
  _filteredIds: null,
  _selectedNode: null,
  _simulation: null,

  render: function() {
    var container = document.createElement('div');
    container.id = 'knowledge-graph-view';
    container.style.cssText = 'max-width:960px;';

    var heading = document.createElement('h2');
    heading.textContent = 'Knowledge Graph';
    heading.style.cssText = 'margin:0 0 var(--sp-4,16px);font-size:var(--text-xl,20px);font-weight:var(--fw-semibold,600);color:var(--fg-1,#C9D1D9);';
    container.appendChild(heading);

    var note = document.createElement('div');
    note.style.cssText = 'background:var(--bg-surface,#161B22);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);padding:8px 12px;font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);font-family:var(--font-mono);margin-bottom:var(--sp-4,16px);';
    note.textContent = '3D rendering with Three.js coming in v2.6.0 - 2D force graph shown here';
    container.appendChild(note);

    // Search bar
    var searchWrap = document.createElement('div');
    searchWrap.style.cssText = 'display:flex;gap:var(--sp-2,8px);margin-bottom:var(--sp-4,16px);';

    var searchInput = document.createElement('input');
    searchInput.id = 'kg-search';
    searchInput.type = 'text';
    searchInput.placeholder = 'Filter nodes by label...';
    searchInput.style.cssText = 'flex:1;padding:8px 12px;background:var(--bg-input,#0D1117);border:1px solid var(--border,#30363D);border-radius:var(--r-sm,6px);color:var(--fg-1,#C9D1D9);font-size:var(--text-sm,12px);font-family:var(--font-sans);outline:none;transition:border-color 120ms;';
    searchInput.addEventListener('focus', function() { searchInput.style.borderColor = 'var(--border-focus,#58A6FF)'; });
    searchInput.addEventListener('blur', function() { searchInput.style.borderColor = ''; });
    searchInput.addEventListener('input', function() {
      window.KnowledgeGraphView.filterNodes(this.value);
    });
    searchWrap.appendChild(searchInput);

    var statsSpan = document.createElement('span');
    statsSpan.id = 'kg-stats';
    statsSpan.style.cssText = 'padding:8px 12px;font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);font-family:var(--font-mono);white-space:nowrap;display:flex;align-items:center;';
    statsSpan.textContent = 'loading...';
    searchWrap.appendChild(statsSpan);

    container.appendChild(searchWrap);

    // Graph canvas
    var graphWrap = document.createElement('div');
    graphWrap.id = 'kg-graph';
    graphWrap.style.cssText = 'position:relative;background:var(--bg-surface,#161B22);border:1px solid var(--border,#30363D);border-radius:var(--r-md,8px);overflow:hidden;min-height:500px;';

    var loading = document.createElement('div');
    loading.id = 'kg-loading';
    loading.style.cssText = 'display:flex;align-items:center;justify-content:center;height:500px;gap:8px;color:var(--fg-2,#8B949E);font-size:var(--text-sm,12px);';
    loading.innerHTML = '<div class="pulse" style="width:16px;height:16px;border-radius:50%;border:2px solid var(--border,#30363D);border-top-color:var(--signal-neon,#00FFA3);"></div> Loading graph data...';
    graphWrap.appendChild(loading);

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.id = 'kg-svg';
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '500');
    svg.style.cssText = 'display:none;';

    var defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    // Arrow marker
    var marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', 'kg-arrow');
    marker.setAttribute('viewBox', '0 0 10 10');
    marker.setAttribute('refX', '10');
    marker.setAttribute('refY', '5');
    marker.setAttribute('markerWidth', '6');
    marker.setAttribute('markerHeight', '6');
    marker.setAttribute('orient', 'auto');
    var arrowPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    arrowPath.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
    arrowPath.setAttribute('fill', 'var(--border,#30363D)');
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    svg.appendChild(defs);

    var edgesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    edgesGroup.id = 'kg-edges';
    svg.appendChild(edgesGroup);

    var nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    nodesGroup.id = 'kg-nodes';
    svg.appendChild(nodesGroup);

    graphWrap.appendChild(svg);

    // Detail panel
    var detailPanel = document.createElement('div');
    detailPanel.id = 'kg-detail';
    detailPanel.style.cssText = 'display:none;position:absolute;top:12px;right:12px;width:280px;background:var(--bg-input,#0D1117);border:1px solid var(--border,#30363D);border-radius:var(--r-md,8px);padding:var(--sp-4,16px);z-index:10;max-height:400px;overflow-y:auto;';
    graphWrap.appendChild(detailPanel);

    container.appendChild(graphWrap);

    // Empty state (hidden by default)
    var emptyState = document.createElement('div');
    emptyState.id = 'kg-empty';
    emptyState.style.cssText = 'display:none;text-align:center;padding:var(--sp-12,48px);color:var(--fg-3,#484F58);';
    var emptyTitle = document.createElement('h3');
    emptyTitle.textContent = 'No graph data';
    emptyTitle.style.cssText = 'font-size:var(--text-lg,18px);margin-bottom:var(--sp-2,8px);color:var(--fg-2,#8B949E);font-weight:500;';
    emptyState.appendChild(emptyTitle);
    var emptySub = document.createElement('p');
    emptySub.textContent = 'Ingest threat intelligence to build the knowledge graph.';
    emptySub.style.cssText = 'margin:0;font-size:var(--text-base,14px);';
    emptyState.appendChild(emptySub);
    container.appendChild(emptyState);

    this.load();
    return container;
  },

  load: function() {
    var self = this;
    var loading = document.getElementById('kg-loading');
    var svg = document.getElementById('kg-svg');
    var empty = document.getElementById('kg-empty');
    var statsSpan = document.getElementById('kg-stats');

    Promise.all([
      window.API.get('/api/graph/nodes').catch(function() { return { nodes: [] }; }),
      window.API.get('/api/graph/edges').catch(function() { return { edges: [] }; })
    ]).then(function(results) {
      var nodeData = results[0];
      var edgeData = results[1];

      self._nodes = nodeData.nodes || [];
      self._edges = edgeData.edges || [];

      if (loading) loading.style.display = 'none';

      if (self._nodes.length === 0) {
        svg.style.display = 'none';
        empty.style.display = 'block';
        if (statsSpan) statsSpan.textContent = '0 nodes, 0 edges';
        return;
      }

      svg.style.display = 'block';
      empty.style.display = 'none';
      if (statsSpan) statsSpan.textContent = self._nodes.length + ' nodes, ' + self._edges.length + ' edges';

      self.renderGraph();
    }).catch(function(err) {
      if (loading) loading.style.display = 'none';
      if (statsSpan) statsSpan.textContent = 'error loading graph';
      var svg = document.getElementById('kg-svg');
      if (svg) {
        svg.style.display = 'block';
        svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="var(--danger,#F85149)" font-size="12" font-family="var(--font-mono)">Failed to load: ' + (err.message || 'unknown error') + '</text>';
      }
    });
  },

  filterNodes: function(query) {
    if (!query.trim()) {
      this._filteredIds = null;
    } else {
      var q = query.toLowerCase();
      var matchingIds = {};
      this._nodes.forEach(function(n) {
        if ((n.label || '').toLowerCase().indexOf(q) !== -1 ||
            (n.id || '').toLowerCase().indexOf(q) !== -1 ||
            (n.type || '').toLowerCase().indexOf(q) !== -1) {
          matchingIds[n.id] = true;
        }
      });
      this._filteredIds = matchingIds;
    }
    this.renderGraph();
  },

  getNodeColor: function(type) {
    var map = {
      actor: '#58A6FF',
      cve: '#F85149',
      tool: '#A371F7',
      campaign: '#D29922'
    };
    return map[type] || '#8B949E';
  },

  renderGraph: function() {
    var svg = document.getElementById('kg-svg');
    if (!svg) return;

    var w = svg.clientWidth || 800;
    var h = svg.clientHeight || 500;

    var edgeGroup = document.getElementById('kg-edges');
    var nodeGroup = document.getElementById('kg-nodes');
    if (!edgeGroup || !nodeGroup) return;

    edgeGroup.innerHTML = '';
    nodeGroup.innerHTML = '';

    var nodes = this._nodes;
    var edges = this._edges;

    if (nodes.length === 0) return;

    // Initialize positions if needed
    var hasPositions = true;
    nodes.forEach(function(n) {
      if (n.x === undefined || n.y === undefined) hasPositions = false;
    });

    if (!hasPositions) {
      // Place nodes in a circle
      var centerX = w / 2;
      var centerY = h / 2;
      var radius = Math.min(w, h) * 0.35;
      nodes.forEach(function(n, i) {
        var angle = (2 * Math.PI * i) / nodes.length;
        n.x = centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 40;
        n.y = centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 40;
      });
    }

    var self = this;
    var nodeMap = {};
    nodes.forEach(function(n) { nodeMap[n.id] = n; });

    // Render edges
    edges.forEach(function(e) {
      var source = nodeMap[e.source];
      var target = nodeMap[e.target];
      if (!source || !target) return;

      // Highlight if filtering
      var visible = true;
      if (self._filteredIds) {
        visible = self._filteredIds[e.source] && self._filteredIds[e.target];
      }

      var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', source.x);
      line.setAttribute('y1', source.y);
      line.setAttribute('x2', target.x);
      line.setAttribute('y2', target.y);
      var edgeColor = 'var(--border,#30363D)';
      if (e.relationship === 'uses') edgeColor = '#A371F7';
      else if (e.relationship === 'targets') edgeColor = '#F85149';
      else if (e.relationship === 'related_to') edgeColor = '#58A6FF';
      else if (e.relationship === 'attributed_to') edgeColor = '#D29922';
      line.style.cssText = 'stroke:' + edgeColor + ';stroke-width:1.5;stroke-opacity:' + (visible ? '0.6' : '0.08') + ';';
      line.setAttribute('data-edge', 'true');
      edgeGroup.appendChild(line);
    });

    // Render nodes
    nodes.forEach(function(n) {
      var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('data-node-id', n.id);
      g.style.cursor = 'pointer';

      var visible = true;
      if (self._filteredIds) {
        visible = !!self._filteredIds[n.id];
      }

      var r = 6 + Math.min(n.confidence || 0.5, 1) * 8;
      r = Math.max(6, Math.min(14, r));

      var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', n.x);
      circle.setAttribute('cy', n.y);
      circle.setAttribute('r', r);
      var color = self.getNodeColor(n.type);
      circle.setAttribute('fill', color);
      circle.setAttribute('stroke', visible ? 'rgba(255,255,255,0.15)' : 'transparent');
      circle.setAttribute('stroke-width', '1');
      circle.style.cssText = 'transition:fill 120ms;opacity:' + (visible ? '0.9' : '0.12') + ';';
      g.appendChild(circle);

      // Label
      var label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', n.x);
      label.setAttribute('y', n.y + r + 12);
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('fill', 'var(--fg-2,#8B949E)');
      label.setAttribute('font-size', '10');
      label.setAttribute('font-family', 'var(--font-mono)');
      label.textContent = n.label || n.id;
      label.style.cssText = 'pointer-events:none;opacity:' + (visible ? '0.85' : '0');
      g.appendChild(label);

      // Click handler
      g.addEventListener('click', function(e) {
        e.stopPropagation();
        self.selectNode(n.id);
      });

      nodeGroup.appendChild(g);
    });

    // Click background to deselect
    svg.addEventListener('click', function() {
      self.deselectNode();
    });
  },

  selectNode: function(nodeId) {
    this._selectedNode = nodeId;
    var panel = document.getElementById('kg-detail');
    if (!panel) return;

    var node = null;
    for (var i = 0; i < this._nodes.length; i++) {
      if (this._nodes[i].id === nodeId) {
        node = this._nodes[i];
        break;
      }
    }

    if (!node) return;

    var html = '';
    html += '<div style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px;">Node Detail</div>';
    html += '<div style="font-size:var(--text-base,14px);font-weight:600;color:var(--fg-1,#C9D1D9);margin-bottom:8px;">' + (node.label || node.id) + '</div>';

    html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);">ID:</span> <span style="font-size:var(--text-xs,11px);color:var(--intent-factual,#58A6FF);font-family:var(--font-mono);">' + node.id + '</span></div>';

    html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);">Type:</span> <span style="display:inline-block;padding:2px 8px;border-radius:var(--r-pill,9999px);font-size:var(--text-xs,11px);font-family:var(--font-mono);background:var(--bg-surface-hi,#21262D);color:' + this.getNodeColor(node.type) + ';">' + (node.type || 'unknown') + '</span></div>';

    if (node.confidence !== undefined) {
      html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);">Confidence:</span> <span style="font-size:var(--text-xs,11px);color:var(--fg-1,#C9D1D9);font-family:var(--font-mono);">' + (typeof node.confidence === 'number' ? (node.confidence * 100).toFixed(0) + '%' : node.confidence) + '</span></div>';
    }

    if (node.tier) {
      var tierColor = node.tier === 'a' ? 'var(--tier-a-fg,#3FB950)' : node.tier === 'b' ? 'var(--tier-b-fg,#A371F7)' : 'var(--tier-c-fg,#D29922)';
      html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);">Tier:</span> <span style="display:inline-block;padding:1px 6px;border-radius:var(--r-pill,9999px);font-size:var(--text-xs,11px);font-family:var(--font-mono);color:' + tierColor + ';background:var(--bg-surface-hi,#21262D);">' + node.tier.toUpperCase() + '</span></div>';
    }

    if (node.aliases && node.aliases.length) {
      html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);">Aliases:</span> <span style="font-size:var(--text-xs,11px);color:var(--fg-1,#C9D1D9);font-family:var(--font-mono);">' + node.aliases.join(', ') + '</span></div>';
    }

    if (node.created_at) {
      html += '<div style="margin-bottom:6px;"><span style="font-size:var(--text-xs,11px);color:var(--fg-2,#8B949E);">Created:</span> <span style="font-size:var(--text-xs,11px);color:var(--fg-1,#C9D1D9);font-family:var(--font-mono);">' + node.created_at + '</span></div>';
    }

    panel.innerHTML = html;
    panel.style.display = 'block';

    // Highlight node
    var allNodes = document.getElementById('kg-nodes');
    if (allNodes) {
      var groups = allNodes.querySelectorAll('g');
      groups.forEach(function(g) {
        var id = g.getAttribute('data-node-id');
        var circle = g.querySelector('circle');
        if (!circle) return;
        if (id === nodeId) {
          circle.setAttribute('stroke', 'var(--signal-neon,#00FFA3)');
          circle.setAttribute('stroke-width', '3');
        } else {
          circle.setAttribute('stroke', 'rgba(255,255,255,0.1)');
          circle.setAttribute('stroke-width', '1');
          circle.style.opacity = '0.3';
        }
      });
    }
  },

  deselectNode: function() {
    this._selectedNode = null;
    var panel = document.getElementById('kg-detail');
    if (panel) panel.style.display = 'none';

    var allNodes = document.getElementById('kg-nodes');
    if (allNodes) {
      var groups = allNodes.querySelectorAll('g');
      groups.forEach(function(g) {
        var circle = g.querySelector('circle');
        if (circle) {
          circle.setAttribute('stroke', 'rgba(255,255,255,0.15)');
          circle.setAttribute('stroke-width', '1');
          circle.style.opacity = '';
        }
      });
    }
  }
};
