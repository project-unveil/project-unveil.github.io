/* ════════════════════════════════════════════════════════════
   UNVEIL Code Browser — UI logic
   - Fetches manifest.json, renders the file tree.
   - Routes file selection via location.hash (#file=path/to/file).
   - Loads file content from ./src/<urlencoded path>, renders as
     either highlight.js code or marked markdown.
═══════════════════════════════════════════════════════════════ */

(() => {
  'use strict';

  const MANIFEST_URL = './manifest.json';
  const SRC_PREFIX = './src/';
  const STORAGE_KEY = 'unveil-code-browser-folders';

  const state = {
    manifest: null,
    fileIndex: new Map(),   // path → file entry
    dirIndex: new Map(),    // path → dir entry
    current: null,          // {type: 'file'|'dir', path}
    openFolders: new Set(),
  };

  // ── DOM refs ──────────────────────────────────────────────
  const $tree = document.getElementById('cb-tree');
  const $breadcrumb = document.getElementById('cb-breadcrumb');
  const $fileName = document.getElementById('cb-file-name');
  const $langBadge = document.getElementById('cb-lang-badge');
  const $fileSize = document.getElementById('cb-file-size');
  const $emptyState = document.getElementById('cb-empty-state');
  const $markdown = document.getElementById('cb-markdown');
  const $codeWrap = document.getElementById('cb-code-wrap');
  const $code = document.getElementById('cb-code');
  const $lineNumbers = document.getElementById('cb-line-numbers');
  const $copyBtn = document.getElementById('cb-copy-btn');
  const $rawBtn = document.getElementById('cb-raw-btn');
  const $collapseAll = document.getElementById('cb-collapse-all');

  // ── Persistence for folder expansion state ───────────────
  const loadOpenFolders = () => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        state.openFolders = new Set(JSON.parse(stored));
      }
    } catch (e) { /* ignore */ }
  };
  const saveOpenFolders = () => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...state.openFolders]));
    } catch (e) { /* ignore */ }
  };

  // ── Helpers ──────────────────────────────────────────────
  const encodePath = (p) => p.split('/').map(encodeURIComponent).join('/');

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const indexFiles = (entries) => {
    for (const e of entries) {
      if (e.type === 'file') {
        state.fileIndex.set(e.path, e);
      } else if (e.type === 'dir') {
        indexFiles(e.children);
      }
    }
  };

  const getParentFolders = (filePath) => {
    const parts = filePath.split('/').slice(0, -1);
    const folders = [];
    for (let i = 0; i < parts.length; i++) {
      folders.push(parts.slice(0, i + 1).join('/'));
    }
    return folders;
  };

  // ── Tree rendering ───────────────────────────────────────
  const svgFolder = `<svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14" aria-hidden="true"><path d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3h-6.5a.25.25 0 0 1-.2-.1L6.06 1.4A1.75 1.75 0 0 0 4.66 1z"/></svg>`;
  const svgFile = `<svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13" aria-hidden="true"><path d="M2 1.75C2 .784 2.784 0 3.75 0h5.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0 1 12.25 16h-8.5A1.75 1.75 0 0 1 2 14.25zm10.5 5.379V14.25a.25.25 0 0 1-.25.25h-8.5a.25.25 0 0 1-.25-.25V1.75a.25.25 0 0 1 .25-.25H8V4.75c0 .967.784 1.75 1.75 1.75z"/></svg>`;
  const svgChevron = `<svg viewBox="0 0 16 16" fill="currentColor" width="10" height="10" aria-hidden="true"><path d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 1 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06z"/></svg>`;

  const renderNode = (entry, depth) => {
    if (entry.type === 'dir') {
      const wrapper = document.createElement('div');
      wrapper.className = 'cb-dir-wrapper';

      const isOpen = state.openFolders.has(entry.path);

      const node = document.createElement('div');
      node.className = 'cb-node cb-dir' + (isOpen ? ' cb-open' : '');
      node.style.paddingLeft = `${0.5 + depth * 0.9}rem`;
      node.dataset.path = entry.path;
      node.setAttribute('role', 'treeitem');
      node.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      node.innerHTML =
        `<span class="cb-node-chevron">${svgChevron}</span>` +
        `<span class="cb-node-icon">${svgFolder}</span>` +
        `<span class="cb-node-name"></span>`;
      node.querySelector('.cb-node-name').textContent = entry.name;

      const childContainer = document.createElement('div');
      childContainer.className = 'cb-children' + (isOpen ? ' cb-open' : '');
      childContainer.setAttribute('role', 'group');
      for (const child of entry.children) {
        childContainer.appendChild(renderNode(child, depth + 1));
      }

      node.addEventListener('click', () => {
        const willOpen = !node.classList.contains('cb-open');
        node.classList.toggle('cb-open', willOpen);
        childContainer.classList.toggle('cb-open', willOpen);
        node.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        if (willOpen) {
          state.openFolders.add(entry.path);
        } else {
          state.openFolders.delete(entry.path);
        }
        saveOpenFolders();
      });

      wrapper.appendChild(node);
      wrapper.appendChild(childContainer);
      return wrapper;
    }

    // File node
    const node = document.createElement('div');
    node.className = 'cb-node cb-file';
    node.style.paddingLeft = `${0.5 + depth * 0.9 + 0.85}rem`;
    node.dataset.path = entry.path;
    node.setAttribute('role', 'treeitem');
    node.innerHTML =
      `<span class="cb-node-icon">${svgFile}</span>` +
      `<span class="cb-node-name"></span>`;
    node.querySelector('.cb-node-name').textContent = entry.name;
    node.addEventListener('click', () => navigateTo(entry.path));
    return node;
  };

  const renderTree = () => {
    $tree.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (const entry of state.manifest.tree) {
      frag.appendChild(renderNode(entry, 0));
    }
    $tree.appendChild(frag);
  };

  const updateTreeSelection = (path) => {
    $tree.querySelectorAll('.cb-node.cb-file.cb-selected').forEach(n => {
      n.classList.remove('cb-selected');
    });
    if (!path) return;
    const node = $tree.querySelector(`.cb-node.cb-file[data-path="${CSS.escape(path)}"]`);
    if (node) {
      node.classList.add('cb-selected');
      node.scrollIntoView({ block: 'nearest' });
    }
  };

  const expandAncestors = (filePath) => {
    const folders = getParentFolders(filePath);
    for (const folder of folders) {
      state.openFolders.add(folder);
      const node = $tree.querySelector(`.cb-node.cb-dir[data-path="${CSS.escape(folder)}"]`);
      if (node) {
        node.classList.add('cb-open');
        node.setAttribute('aria-expanded', 'true');
        const children = node.parentElement.querySelector(':scope > .cb-children');
        if (children) children.classList.add('cb-open');
      }
    }
    saveOpenFolders();
  };

  // ── Breadcrumb ───────────────────────────────────────────
  const updateBreadcrumb = (path) => {
    $breadcrumb.innerHTML = '';
    if (!path) return;
    const parts = path.split('/');
    for (let i = 0; i < parts.length; i++) {
      if (i > 0) {
        const sep = document.createElement('span');
        sep.className = 'cb-crumb-sep';
        sep.textContent = '/';
        $breadcrumb.appendChild(sep);
      }
      const crumb = document.createElement('span');
      crumb.className = 'cb-crumb' + (i === parts.length - 1 ? ' cb-crumb-active' : '');
      crumb.textContent = parts[i];
      $breadcrumb.appendChild(crumb);
    }
  };

  // ── File loading & rendering ─────────────────────────────
  const showEmpty = () => {
    $emptyState.hidden = false;
    $markdown.hidden = true;
    $codeWrap.hidden = true;
    $fileName.textContent = '—';
    $langBadge.textContent = '';
    $fileSize.textContent = '';
  };

  const showMarkdown = (text, entry) => {
    $emptyState.hidden = true;
    $codeWrap.hidden = true;
    $markdown.hidden = false;
    const rendered = window.marked
      ? window.marked.parse(text, { mangle: false, headerIds: false })
      : `<pre>${escapeHtml(text)}</pre>`;
    $markdown.innerHTML = rendered;
    // Syntax-highlight any fenced code blocks inside the markdown.
    if (window.hljs) {
      $markdown.querySelectorAll('pre code').forEach(block => {
        window.hljs.highlightElement(block);
      });
    }
    $fileName.textContent = entry.path;
    $langBadge.textContent = entry.lang || '';
    $fileSize.textContent = formatSize(entry.size);
  };

  const showCode = (text, entry) => {
    $emptyState.hidden = true;
    $markdown.hidden = true;
    $codeWrap.hidden = false;

    $code.className = '';
    if (entry.lang && entry.lang !== 'plaintext') {
      $code.classList.add(`language-${entry.lang}`);
    }
    $code.textContent = text;

    const lineCount = text.length === 0 ? 1 : (text.match(/\n/g) || []).length + 1;
    const nums = new Array(lineCount);
    for (let i = 0; i < lineCount; i++) nums[i] = (i + 1).toString();
    $lineNumbers.textContent = nums.join('\n');

    if (window.hljs && entry.lang && entry.lang !== 'plaintext') {
      try { window.hljs.highlightElement($code); }
      catch (e) { /* fall back to plain */ }
    }

    $fileName.textContent = entry.path;
    $langBadge.textContent = entry.lang || '';
    $fileSize.textContent = formatSize(entry.size);
  };

  const escapeHtml = (s) => s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const loadFile = async (entry) => {
    const url = SRC_PREFIX + encodePath(entry.path);
    $rawBtn.onclick = () => window.open(url, '_blank', 'noopener');
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const text = await res.text();
      if (entry.lang === 'markdown') {
        showMarkdown(text, entry);
      } else {
        showCode(text, entry);
      }
    } catch (err) {
      $emptyState.hidden = true;
      $markdown.hidden = true;
      $codeWrap.hidden = false;
      $code.className = '';
      $code.textContent = `Failed to load ${entry.path}\n\n${err.message}`;
      $lineNumbers.textContent = '1\n2\n3';
    }
  };

  // ── Routing ──────────────────────────────────────────────
  const parseHash = () => {
    const h = location.hash.replace(/^#/, '');
    if (!h) return null;
    const m = h.match(/(?:^|&)file=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  };

  const navigateTo = (path) => {
    const target = `#file=${encodeURIComponent(path).replace(/%2F/g, '/')}`;
    if (location.hash !== target) {
      location.hash = target;
    } else {
      applyHash();
    }
  };

  const applyHash = () => {
    const path = parseHash() || state.manifest.default_file;
    const entry = state.fileIndex.get(path);
    if (!entry) {
      showEmpty();
      updateBreadcrumb('');
      updateTreeSelection(null);
      state.currentPath = null;
      return;
    }
    state.currentPath = path;
    expandAncestors(path);
    updateTreeSelection(path);
    updateBreadcrumb(path);
    loadFile(entry);
  };

  // ── Copy button ──────────────────────────────────────────
  const wireCopyButton = () => {
    $copyBtn.addEventListener('click', async () => {
      let text = '';
      if (!$codeWrap.hidden) {
        text = $code.textContent || '';
      } else if (!$markdown.hidden) {
        // Copy raw markdown by re-fetching (cheap; already cached).
        if (state.currentPath) {
          try {
            const r = await fetch(SRC_PREFIX + encodePath(state.currentPath));
            text = await r.text();
          } catch (e) { /* ignore */ }
        }
      }
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        const label = $copyBtn.querySelector('.cb-action-label');
        const original = label ? label.textContent : '';
        $copyBtn.classList.add('cb-action-success');
        if (label) label.textContent = 'Copied';
        setTimeout(() => {
          $copyBtn.classList.remove('cb-action-success');
          if (label) label.textContent = original;
        }, 1400);
      } catch (e) { /* clipboard blocked */ }
    });
  };

  // ── Collapse-all ────────────────────────────────────────
  const wireCollapseAll = () => {
    $collapseAll.addEventListener('click', () => {
      state.openFolders.clear();
      saveOpenFolders();
      $tree.querySelectorAll('.cb-node.cb-dir.cb-open').forEach(n => {
        n.classList.remove('cb-open');
        n.setAttribute('aria-expanded', 'false');
      });
      $tree.querySelectorAll('.cb-children.cb-open').forEach(c => {
        c.classList.remove('cb-open');
      });
    });
  };

  // ── Boot ─────────────────────────────────────────────────
  const boot = async () => {
    loadOpenFolders();
    try {
      const res = await fetch(MANIFEST_URL);
      if (!res.ok) throw new Error(`manifest HTTP ${res.status}`);
      state.manifest = await res.json();
    } catch (err) {
      $tree.innerHTML = `<div class="cb-tree-loading">Failed to load manifest: ${escapeHtml(err.message)}</div>`;
      return;
    }
    indexFiles(state.manifest.tree);
    renderTree();
    wireCopyButton();
    wireCollapseAll();
    window.addEventListener('hashchange', applyHash);
    applyHash();
  };

  boot();
})();
