import os
import re
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any

import httpx
import dateparser
from dateparser.search import search_dates
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from ics import Calendar, Event

app = FastAPI()

AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT", "").rstrip("/")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY", "")
AZURE_API_VERSION = "2024-11-30"
AZURE_MODEL = "prebuilt-layout"


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DateLift — Bulk Date Extractor</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --blue-50:  #eff6ff;
      --blue-100: #dbeafe;
      --blue-500: #3b82f6;
      --blue-600: #2563eb;
      --blue-700: #1d4ed8;
      --slate-50:  #f8fafc;
      --slate-100: #f1f5f9;
      --slate-200: #e2e8f0;
      --slate-300: #cbd5e1;
      --slate-400: #94a3b8;
      --slate-500: #64748b;
      --slate-600: #475569;
      --slate-700: #334155;
      --slate-800: #1e293b;
      --slate-900: #0f172a;
      --green-100: #dcfce7;
      --green-600: #16a34a;
      --amber-100: #fef3c7;
      --amber-600: #d97706;
      --red-100:   #fee2e2;
      --red-600:   #dc2626;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --radius-xl: 24px;
      --shadow-sm: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05);
      --shadow-md: 0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
      --shadow-lg: 0 10px 30px rgba(0,0,0,.10), 0 4px 8px rgba(0,0,0,.05);
    }

    html { scroll-behavior: smooth; }

    body {
      font-family: 'Figtree', sans-serif;
      background: var(--slate-50);
      color: var(--slate-800);
      min-height: 100vh;
    }

    /* ── NAV ── */
    nav {
      background: white;
      border-bottom: 1px solid var(--slate-200);
      padding: 0 32px;
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .nav-logo {
      font-weight: 700;
      font-size: 18px;
      color: var(--slate-900);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .nav-logo svg {
      color: var(--blue-600);
    }

    .nav-badge {
      font-size: 11px;
      font-weight: 600;
      color: var(--blue-600);
      background: var(--blue-50);
      border: 1px solid var(--blue-100);
      padding: 2px 8px;
      border-radius: 999px;
      letter-spacing: .03em;
    }

    /* ── MAIN LAYOUT ── */
    .page {
      max-width: 1120px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }

    /* ── HERO ── */
    .hero {
      text-align: center;
      padding: 48px 0 40px;
      animation: fadeUp .5s ease both;
    }

    .hero h1 {
      font-size: clamp(28px, 4vw, 42px);
      font-weight: 700;
      color: var(--slate-900);
      line-height: 1.2;
      letter-spacing: -.02em;
      margin-bottom: 14px;
    }

    .hero p {
      font-size: 16px;
      color: var(--slate-500);
      max-width: 520px;
      margin: 0 auto;
      line-height: 1.6;
    }

    /* ── UPLOAD CARD ── */
    .card {
      background: white;
      border-radius: var(--radius-xl);
      border: 1px solid var(--slate-200);
      box-shadow: var(--shadow-md);
      padding: 32px;
      animation: fadeUp .5s .1s ease both;
    }

    .upload-zone {
      border: 2px dashed var(--slate-300);
      border-radius: var(--radius-lg);
      padding: 48px 32px;
      text-align: center;
      cursor: pointer;
      transition: border-color .2s, background .2s;
      position: relative;
    }

    .upload-zone:hover, .upload-zone.drag-over {
      border-color: var(--blue-500);
      background: var(--blue-50);
    }

    .upload-zone input[type=file] {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
      width: 100%;
      height: 100%;
    }

    .upload-icon {
      width: 48px;
      height: 48px;
      background: var(--blue-50);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px;
    }

    .upload-icon svg { color: var(--blue-600); }

    .upload-zone h3 {
      font-size: 16px;
      font-weight: 600;
      color: var(--slate-700);
      margin-bottom: 6px;
    }

    .upload-zone p {
      font-size: 13px;
      color: var(--slate-400);
    }

    .file-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }

    .chip {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--slate-100);
      border: 1px solid var(--slate-200);
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      color: var(--slate-600);
      animation: chipIn .2s ease both;
    }

    .chip svg { color: var(--blue-500); }

    /* ── ACTIONS ROW ── */
    .actions {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 24px;
      flex-wrap: wrap;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 10px 20px;
      border-radius: var(--radius-md);
      font-family: inherit;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all .15s ease;
      white-space: nowrap;
    }

    .btn:disabled { opacity: .5; cursor: not-allowed; pointer-events: none; }

    .btn-primary {
      background: var(--blue-600);
      color: white;
      box-shadow: 0 1px 3px rgba(37,99,235,.3);
    }
    .btn-primary:hover { background: var(--blue-700); box-shadow: 0 4px 12px rgba(37,99,235,.35); transform: translateY(-1px); }
    .btn-primary:active { transform: translateY(0); }

    .btn-outline {
      background: white;
      color: var(--slate-700);
      border: 1px solid var(--slate-200);
      box-shadow: var(--shadow-sm);
    }
    .btn-outline:hover { background: var(--slate-50); border-color: var(--slate-300); }

    .btn-ghost {
      background: transparent;
      color: var(--slate-500);
      padding: 10px 14px;
    }
    .btn-ghost:hover { background: var(--slate-100); color: var(--slate-700); }

    .btn-export {
      background: var(--slate-900);
      color: white;
      margin-left: auto;
    }
    .btn-export:hover { background: var(--slate-700); transform: translateY(-1px); }

    /* ── STATUS ── */
    .status-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      font-size: 13px;
      font-weight: 500;
      margin-top: 16px;
      transition: all .3s ease;
    }

    .status-bar.hidden { display: none; }
    .status-bar.info    { background: var(--blue-50);  color: var(--blue-600);  border: 1px solid var(--blue-100); }
    .status-bar.success { background: var(--green-100); color: var(--green-600); border: 1px solid #bbf7d0; }
    .status-bar.error   { background: var(--red-100);  color: var(--red-600);   border: 1px solid #fecaca; }

    .spinner {
      width: 14px; height: 14px;
      border: 2px solid currentColor;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin .7s linear infinite;
      flex-shrink: 0;
    }

    /* ── RESULTS SECTION ── */
    .results-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin: 36px 0 16px;
      animation: fadeUp .4s ease both;
    }

    .results-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--slate-900);
    }

    .results-count {
      font-size: 13px;
      color: var(--slate-400);
      font-weight: 500;
    }

    .results-actions {
      display: flex;
      gap: 8px;
    }

    /* ── TABLE ── */
    .table-wrap {
      background: white;
      border-radius: var(--radius-xl);
      border: 1px solid var(--slate-200);
      box-shadow: var(--shadow-md);
      overflow: hidden;
      animation: fadeUp .4s .05s ease both;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13.5px;
    }

    thead tr {
      background: var(--slate-50);
      border-bottom: 1px solid var(--slate-200);
    }

    th {
      padding: 12px 16px;
      text-align: left;
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--slate-400);
    }

    th:first-child { padding-left: 20px; }

    tbody tr {
      border-bottom: 1px solid var(--slate-100);
      transition: background .12s;
    }

    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: var(--slate-50); }

    td {
      padding: 14px 16px;
      vertical-align: middle;
      color: var(--slate-700);
    }

    td:first-child { padding-left: 20px; }

    .cb-wrap {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    input[type=checkbox] {
      width: 16px;
      height: 16px;
      accent-color: var(--blue-600);
      cursor: pointer;
      border-radius: 4px;
    }

    .lawyer-cell {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 11.5px;
      font-weight: 600;
    }

    .badge-hearing    { background: #ede9fe; color: #6d28d9; }
    .badge-summons    { background: #fce7f3; color: #be185d; }
    .badge-deadline   { background: #ffedd5; color: #c2410c; }
    .badge-appointment{ background: #dcfce7; color: #15803d; }
    .badge-unknown    { background: var(--slate-100); color: var(--slate-500); }

    /* ── COLOR SWATCH PICKER ── */
    .color-picker-wrap {
      position: relative;
    }

    .color-swatch-btn {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 0 0 1.5px var(--slate-300);
      cursor: pointer;
      transition: box-shadow .15s, transform .15s;
      flex-shrink: 0;
    }

    .color-swatch-btn:hover {
      transform: scale(1.12);
      box-shadow: 0 0 0 2px var(--blue-400);
    }

    .color-dropdown {
      display: none;
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      background: white;
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-lg);
      padding: 10px;
      z-index: 200;
      width: 300px;
    }

    .color-dropdown.open { display: block; animation: fadeUp .15s ease both; }

    .color-dropdown-label {
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .07em;
      color: var(--slate-400);
      margin-bottom: 8px;
    }

    .color-grid {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 6px;
    }

    .color-dot {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      cursor: pointer;
      border: 2px solid transparent;
      transition: transform .12s, border-color .12s;
    }

    .color-dot:hover { transform: scale(1.2); }
    .color-dot.active { border-color: var(--slate-700); }

    .inline-input {
      font-family: inherit;
      font-size: 13.5px;
      color: var(--slate-700);
      background: var(--slate-50);
      border: 1px solid var(--slate-200);
      border-radius: var(--radius-sm);
      padding: 5px 9px;
      width: 130px;
      transition: border-color .15s, box-shadow .15s;
      outline: none;
    }

    .inline-input:focus {
      border-color: var(--blue-500);
      box-shadow: 0 0 0 3px rgba(59,130,246,.15);
      background: white;
    }

    .snippet-cell {
      max-width: 300px;
      color: var(--slate-500);
      font-size: 12.5px;
      line-height: 1.5;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .empty-state {
      padding: 64px 32px;
      text-align: center;
    }

    .empty-icon {
      width: 56px; height: 56px;
      background: var(--slate-100);
      border-radius: var(--radius-lg);
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 16px;
    }

    .empty-icon svg { color: var(--slate-400); }

    .empty-state h3 { font-size: 15px; font-weight: 600; color: var(--slate-600); margin-bottom: 6px; }
    .empty-state p  { font-size: 13px; color: var(--slate-400); }

    /* ── EXPORT FOOTER ── */
    .export-bar {
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: white;
      border-top: 1px solid var(--slate-200);
      padding: 14px 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      box-shadow: 0 -4px 20px rgba(0,0,0,.07);
      z-index: 50;
      transform: translateY(100%);
      transition: transform .3s cubic-bezier(.34,1.56,.64,1);
    }

    .export-bar.visible { transform: translateY(0); }

    .export-bar-info { font-size: 14px; color: var(--slate-600); }
    .export-bar-info strong { color: var(--slate-900); }

    /* ── ANIMATIONS ── */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(16px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    @keyframes chipIn {
      from { opacity: 0; transform: scale(.85); }
      to   { opacity: 1; transform: scale(1); }
    }

    /* ── RESPONSIVE ── */
    @media (max-width: 640px) {
      nav { padding: 0 16px; }
      .page { padding: 24px 14px 100px; }
      .card { padding: 20px; }
      .actions { gap: 8px; }
      .btn-export { margin-left: 0; }
      .export-bar { padding: 14px 20px; }
    }
  </style>
</head>
<body>

  <!-- NAV -->
  <nav>
    <div class="nav-logo">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
      DateLift
    </div>
    <span class="nav-badge">BETA</span>
  </nav>

  <div class="page">

    <!-- HERO -->
    <div class="hero">
      <h1>Extract dates from any document</h1>
      <p>Upload scanned PDFs or images. We'll find hearings, deadlines, and appointments — then export them straight to your calendar.</p>
    </div>

    <!-- UPLOAD CARD -->
    <div class="card">
      <div class="upload-zone" id="dropzone">
        <input type="file" id="files" multiple accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
               onchange="handleFiles(this.files)" />
        <div class="upload-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <h3>Drop files here or click to browse</h3>
        <p>PDF, PNG, JPG, TIFF supported</p>
      </div>

      <div id="fileChips" class="file-chips"></div>

      <div class="actions">
        <button class="btn btn-primary" id="extractBtn" onclick="extract()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          Extract Dates
        </button>
      </div>

      <div id="statusBar" class="status-bar hidden">
        <span id="statusIcon"></span>
        <span id="statusText"></span>
      </div>
    </div>

    <!-- RESULTS -->
    <div id="resultsSection" style="display:none;">
      <div class="results-header">
        <div>
          <div class="results-title">Extracted Events</div>
          <div class="results-count" id="resultsCount"></div>
        </div>
        <div class="results-actions">
          <button class="btn btn-ghost" onclick="selectAll()">Select all</button>
          <button class="btn btn-ghost" onclick="clearAll()">Clear all</button>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width:44px"></th>
              <th>Type</th>
              <th>Date</th>
              <th>Time</th>
              <th>Lawyer</th>
              <th>Context</th>
            </tr>
          </thead>
          <tbody id="resultsBody"></tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- EXPORT BAR -->
  <div class="export-bar" id="exportBar">
    <div class="export-bar-info">
      <strong id="selectedCount">0</strong> event(s) selected for export
    </div>
    <button class="btn btn-export" onclick="downloadICS()">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      Download .ics
    </button>
  </div>

<script>
let results = [];
let chosenFiles = [];

// ── Drag & drop ──────────────────────────────────────────────
const dropzone = document.getElementById('dropzone');
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  handleFiles(e.dataTransfer.files);
});

function handleFiles(files) {
  chosenFiles = Array.from(files);
  renderChips();
}

function renderChips() {
  const el = document.getElementById('fileChips');
  el.innerHTML = '';
  chosenFiles.forEach(f => {
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      ${escapeHtml(f.name)}
    `;
    el.appendChild(chip);
  });
}

// ── Status helpers ────────────────────────────────────────────
function setStatus(type, text, spinner) {
  const bar  = document.getElementById('statusBar');
  const icon = document.getElementById('statusIcon');
  const msg  = document.getElementById('statusText');
  bar.className = `status-bar ${type}`;
  msg.textContent = text;
  icon.innerHTML = spinner
    ? '<div class="spinner"></div>'
    : type === 'success'
      ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>'
      : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
}

function clearStatus() {
  document.getElementById('statusBar').className = 'status-bar hidden';
}

// ── Extract ───────────────────────────────────────────────────
async function extract() {
  if (!chosenFiles.length) {
    setStatus('error', 'Choose at least one file first.');
    return;
  }

  const btn = document.getElementById('extractBtn');
  btn.disabled = true;
  setStatus('info', 'Processing files… this may take a moment for scanned PDFs.', true);

  const fd = new FormData();
  chosenFiles.forEach(f => fd.append('files', f));

  try {
    const res  = await fetch('/extract', { method: 'POST', body: fd });
    const data = await res.json();

    if (!res.ok) {
      setStatus('error', data.detail || 'Extraction failed.');
      return;
    }

    results = data.results.map(r => ({ ...r, selected: true }));
    renderTable();
    setStatus('success', `Found ${results.length} candidate event(s).`);
    document.getElementById('resultsSection').style.display = '';
    updateExportBar();
  } catch (err) {
    setStatus('error', 'Request failed: ' + err);
  } finally {
    btn.disabled = false;
  }
}

// ── Render table ──────────────────────────────────────────────
const COLORS = [
  '#ef4444','#f97316','#f59e0b','#eab308','#84cc16','#22c55e','#10b981',
  '#14b8a6','#06b6d4','#0ea5e9','#3b82f6','#6366f1','#8b5cf6','#a855f7',
  '#d946ef','#ec4899','#f43f5e','#64748b','#0f172a','#78716c','#7c3aed',
];

function badgeClass(type) {
  const map = { Hearing:'badge-hearing', 'Summons/Appearance':'badge-summons', Deadline:'badge-deadline', Appointment:'badge-appointment' };
  return 'badge ' + (map[type] || 'badge-unknown');
}

function renderTable() {
  const body = document.getElementById('resultsBody');
  body.innerHTML = '';

  if (!results.length) {
    body.innerHTML = `
      <tr><td colspan="6">
        <div class="empty-state">
          <div class="empty-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </div>
          <h3>No events found</h3>
          <p>Try uploading a different document.</p>
        </div>
      </td></tr>`;
    return;
  }

  document.getElementById('resultsCount').textContent = `${results.length} event${results.length !== 1 ? 's' : ''} found`;

  results.forEach((row, i) => {
    const color = row.lawyer_color || COLORS[i % COLORS.length];
    if (!row.lawyer_color) row.lawyer_color = color;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="cb-wrap">
          <input type="checkbox" ${row.selected ? 'checked' : ''}
            onchange="toggleRow(${i}, this.checked)" />
        </div>
      </td>
      <td><span class="${badgeClass(row.event_type)}">${escapeHtml(row.event_type)}</span></td>
      <td><input class="inline-input" value="${escapeHtml(row.event_date || '')}" onchange="updateField(${i}, 'event_date', this.value)" placeholder="YYYY-MM-DD" /></td>
      <td><input class="inline-input" value="${escapeHtml(row.event_time || '')}" onchange="updateField(${i}, 'event_time', this.value)" placeholder="—" style="width:110px" /></td>
      <td>
        <div class="lawyer-cell">
          <input class="inline-input" value="${escapeHtml(row.lawyer_name || '')}"
            onchange="updateField(${i}, 'lawyer_name', this.value)"
            placeholder="Lawyer name" style="width:140px" />
          <div class="color-picker-wrap" id="cpwrap-${i}">
            <div class="color-swatch-btn" id="swatch-${i}"
              style="background:${color}"
              onclick="toggleColorPicker(${i}, event)"></div>
            <div class="color-dropdown" id="cdrop-${i}">
              <div class="color-dropdown-label">Colour</div>
              <div class="color-grid" id="cgrid-${i}"></div>
            </div>
          </div>
        </div>
      </td>
      <td class="snippet-cell" title="${escapeHtml(row.snippet || '')}">${escapeHtml(row.snippet || '')}</td>
    `;
    body.appendChild(tr);

    // Build color grid
    const grid = document.getElementById(`cgrid-${i}`);
    COLORS.forEach(c => {
      const dot = document.createElement('div');
      dot.className = 'color-dot' + (c === color ? ' active' : '');
      dot.style.background = c;
      dot.title = c;
      dot.onclick = (e) => { e.stopPropagation(); pickColor(i, c); };
      grid.appendChild(dot);
    });
  });
}

function toggleColorPicker(i, e) {
  e.stopPropagation();
  document.querySelectorAll('.color-dropdown.open').forEach(d => {
    if (d.id !== `cdrop-${i}`) d.classList.remove('open');
  });
  document.getElementById(`cdrop-${i}`).classList.toggle('open');
}

function pickColor(i, color) {
  results[i].lawyer_color = color;
  document.getElementById(`swatch-${i}`).style.background = color;
  document.getElementById(`cdrop-${i}`).classList.remove('open');
  document.querySelectorAll(`#cgrid-${i} .color-dot`).forEach(d => {
    d.classList.toggle('active', d.title === color);
  });
}

// Close pickers on outside click
document.addEventListener('click', () => {
  document.querySelectorAll('.color-dropdown.open').forEach(d => d.classList.remove('open'));
});

// ── Selection helpers ─────────────────────────────────────────
function toggleRow(i, checked) {
  results[i].selected = checked;
  updateExportBar();
}

function updateField(i, field, value) { results[i][field] = value; }

function selectAll() {
  results = results.map(r => ({ ...r, selected: true }));
  renderTable(); updateExportBar();
}

function clearAll() {
  results = results.map(r => ({ ...r, selected: false }));
  renderTable(); updateExportBar();
}

function updateExportBar() {
  const n   = results.filter(r => r.selected).length;
  const bar = document.getElementById('exportBar');
  document.getElementById('selectedCount').textContent = n;
  bar.classList.toggle('visible', n > 0);
}

// ── Export ────────────────────────────────────────────────────
async function downloadICS() {
  const selected = results.filter(r => r.selected);
  if (!selected.length) return;

  const res = await fetch('/download-ics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(selected)
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    setStatus('error', data.detail || 'Export failed.');
    return;
  }

  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'calendar_events.ics'; a.click();
  URL.revokeObjectURL(url);
}

// ── Utils ─────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str ?? '')
    .replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HTML)


def classify_event(snippet: str) -> str:
    s = (snippet or "").lower()

    if any(word in s for word in ["hearing", "conference", "calendar call"]):
        return "Hearing"
    if any(word in s for word in ["summons", "summoned", "appear before", "you are hereby summoned", "must appear"]):
        return "Summons/Appearance"
    if "appointment" in s:
        return "Appointment"
    if any(word in s for word in ["deadline", "due", "respond within", "response due", "must file by"]):
        return "Deadline"
    return "Unknown"


def confidence_for(snippet: str, event_type: str, parsed_dt: datetime) -> str:
    score = 0
    s = (snippet or "").lower()

    if event_type != "Unknown":
        score += 2
    if parsed_dt.hour != 0 or parsed_dt.minute != 0:
        score += 1
    if any(k in s for k in ["court", "judge", "hearing", "summons", "appointment", "deadline"]):
        score += 1

    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def normalize_time(dt: datetime) -> str:
    if dt.hour == 0 and dt.minute == 0:
        return ""
    return dt.strftime("%I:%M %p").lstrip("0")


def extract_candidates_from_text(text: str, filename: str) -> List[Dict[str, Any]]:
    results = []
    seen = set()

    found = search_dates(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    ) or []

    for match_text, parsed_dt in found:
        if not parsed_dt:
            continue

        if parsed_dt.year < 2020 or parsed_dt.year > 2035:
            continue

        idx = text.lower().find(match_text.lower())
        if idx == -1:
            idx = 0

        start = max(0, idx - 80)
        end = min(len(text), idx + len(match_text) + 80)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()

        event_type = classify_event(snippet)
        confidence = confidence_for(snippet, event_type, parsed_dt)

        key = (filename, parsed_dt.isoformat(), event_type, snippet[:50])
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "filename": filename,
            "event_type": event_type,
            "event_date": parsed_dt.strftime("%Y-%m-%d"),
            "event_time": normalize_time(parsed_dt),
            "confidence": confidence,
            "snippet": snippet,
        })

    return results


async def azure_ocr_bytes(file_bytes: bytes, filename: str) -> str:
    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise HTTPException(
            status_code=500,
            detail="Set AZURE_DI_ENDPOINT and AZURE_DI_KEY first."
        )

    post_url = (
        f"{AZURE_DI_ENDPOINT}/documentintelligence/documentModels/"
        f"{AZURE_MODEL}:analyze?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_DI_KEY,
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        post_resp = await client.post(post_url, headers=headers, content=file_bytes)

        if post_resp.status_code not in (200, 202):
            raise HTTPException(
                status_code=500,
                detail=f"Azure analyze start failed for {filename}: {post_resp.text}"
            )

        operation_location = post_resp.headers.get("operation-location")
        if not operation_location:
            data = post_resp.json()
            return data.get("analyzeResult", {}).get("content", "")

        for _ in range(60):
            poll_resp = await client.get(
                operation_location,
                headers={"Ocp-Apim-Subscription-Key": AZURE_DI_KEY}
            )

            if poll_resp.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Azure polling failed for {filename}: {poll_resp.text}"
                )

            data = poll_resp.json()
            status = data.get("status")

            if status == "succeeded":
                return data.get("analyzeResult", {}).get("content", "")
            if status == "failed":
                raise HTTPException(
                    status_code=500,
                    detail=f"Azure OCR failed for {filename}: {json.dumps(data)}"
                )

            await sleep_async(1.5)

    raise HTTPException(status_code=500, detail=f"Azure OCR timed out for {filename}.")


async def sleep_async(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


@app.post("/extract")
async def extract(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    all_results = []

    for file in files:
        content = await file.read()
        text = await azure_ocr_bytes(content, file.filename)
        candidates = extract_candidates_from_text(text, file.filename)
        all_results.extend(candidates)

    return {"results": all_results}


@app.post("/download-ics")
async def download_ics(events: List[Dict[str, Any]]):
    if not events:
        raise HTTPException(status_code=400, detail="No events selected.")

    cal = Calendar()

    for row in events:
        event_date = (row.get("event_date") or "").strip()
        event_time = (row.get("event_time") or "").strip()
        event_type = (row.get("event_type") or "Event").strip()
        filename = (row.get("filename") or "Document").strip()
        snippet = (row.get("snippet") or "").strip()

        if not event_date:
            continue

        dt_text = event_date if not event_time else f"{event_date} {event_time}"
        parsed = dateparser.parse(dt_text)

        if not parsed:
            continue

        e = Event()
        e.name = f"{event_type} — {filename}"
        e.begin = parsed
        e.description = snippet
        cal.events.add(e)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ics") as tmp:
        tmp.write(str(cal).encode("utf-8"))
        tmp_path = tmp.name

    return FileResponse(tmp_path, filename="calendar_events.ics", media_type="text/calendar")