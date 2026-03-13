/**
 * ExportModal — zero-dependency export component.
 *
 * Supports CSV (opens in Excel/Sheets) and PDF (browser print dialog).
 * Pass `sections` array where each section is:
 *   { id, label, data: [{key, label, value}], tableRows: [{cols}] }
 *
 * Or pass shorthand `stats` object and `complaints` array for quick use.
 */
import React, { useState } from 'react';
import { X, Download, FileText, Table, CheckSquare, Square } from 'lucide-react';

// ── helpers ──────────────────────────────────────────────────────────────────

function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function escapeCsvCell(v) {
    if (v == null) return '';
    const s = String(v);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
}

function buildCsv(sections) {
    const rows = [];
    sections.forEach(s => {
        rows.push([s.label]);
        if (s.stats) {
            rows.push(['Metric', 'Value']);
            s.stats.forEach(item => rows.push([item.label, item.value ?? '—']));
            rows.push([]);
        }
        if (s.tableHeaders && s.tableRows?.length) {
            rows.push(s.tableHeaders);
            s.tableRows.forEach(r => rows.push(r));
            rows.push([]);
        }
    });
    return rows.map(r => r.map(escapeCsvCell).join(',')).join('\r\n');
}

function openPrintWindow(sections, title) {
    const html = `<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>${title}</title>
<style>
  body { font-family: Arial, sans-serif; font-size: 12px; color: #111; margin: 24px; }
  h1 { font-size: 18px; margin-bottom: 4px; color: #14532D; }
  .meta { color: #666; font-size: 11px; margin-bottom: 20px; }
  h2 { font-size: 14px; margin: 20px 0 6px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
  th { background: #f3f4f6; text-align: left; padding: 6px 8px; font-size: 11px; border: 1px solid #e5e7eb; }
  td { padding: 5px 8px; border: 1px solid #e5e7eb; font-size: 11px; vertical-align: top; }
  tr:nth-child(even) td { background: #f9fafb; }
  @media print { h2 { page-break-before: auto; } }
</style>
</head><body>
<h1>${title}</h1>
<p class="meta">Generated: ${new Date().toLocaleString()}</p>
${sections.map(s => `
<h2>${s.label}</h2>
${s.stats ? `<table><tr><th>Metric</th><th>Value</th></tr>
${s.stats.map(item => `<tr><td>${item.label}</td><td><strong>${item.value ?? '—'}</strong></td></tr>`).join('')}
</table>` : ''}
${s.tableHeaders && s.tableRows?.length ? `<table>
<tr>${s.tableHeaders.map(h => `<th>${h}</th>`).join('')}</tr>
${s.tableRows.map(r => `<tr>${r.map(c => `<td>${c ?? ''}</td>`).join('')}</tr>`).join('')}
</table>` : ''}
`).join('')}
</body></html>`;

    const w = window.open('', '_blank', 'width=900,height=700');
    w.document.write(html);
    w.document.close();
    w.focus();
    setTimeout(() => { w.print(); }, 400);
}

// ── component ─────────────────────────────────────────────────────────────────

export default function ExportModal({ isOpen, onClose, title = 'Export Report', sections = [] }) {
    const [selected, setSelected] = useState(() => Object.fromEntries(sections.map(s => [s.id, true])));
    const [format, setFormat] = useState('csv');

    if (!isOpen) return null;

    const toggle = (id) => setSelected(prev => ({ ...prev, [id]: !prev[id] }));
    const activeSections = sections.filter(s => selected[s.id]);

    const handleExport = () => {
        if (!activeSections.length) return;
        const safeTitle = title.replace(/[^a-zA-Z0-9\s_-]/g, '').replace(/\s+/g, '_');
        const date = new Date().toISOString().slice(0, 10);

        if (format === 'csv') {
            const csv = buildCsv(activeSections);
            downloadBlob(csv, `${safeTitle}_${date}.csv`, 'text/csv;charset=utf-8;');
            onClose();
        } else {
            openPrintWindow(activeSections, title);
            onClose();
        }
    };

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 w-full max-w-md">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                        <Download size={18} className="text-srec-primary" />
                        <h2 className="text-base font-bold text-gray-900">{title}</h2>
                    </div>
                    <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-50 transition-colors">
                        <X size={18} />
                    </button>
                </div>

                <div className="px-6 py-4 space-y-5">
                    {/* Format selection */}
                    <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Format</p>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={() => setFormat('csv')}
                                className={`flex items-center gap-2 border rounded-xl px-4 py-3 text-sm font-medium transition-all ${format === 'csv' ? 'border-srec-primary bg-srec-primary/5 text-srec-primary' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                            >
                                <Table size={16} /> Excel / CSV
                            </button>
                            <button
                                onClick={() => setFormat('pdf')}
                                className={`flex items-center gap-2 border rounded-xl px-4 py-3 text-sm font-medium transition-all ${format === 'pdf' ? 'border-srec-primary bg-srec-primary/5 text-srec-primary' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                            >
                                <FileText size={16} /> PDF / Print
                            </button>
                        </div>
                        <p className="text-xs text-gray-400 mt-1.5">
                            {format === 'csv' ? 'Downloads a .csv file (opens in Excel, Google Sheets)' : 'Opens browser print dialog — Save as PDF'}
                        </p>
                    </div>

                    {/* Section selection */}
                    <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Include Sections</p>
                        <div className="space-y-2">
                            {sections.map(s => (
                                <button
                                    key={s.id}
                                    onClick={() => toggle(s.id)}
                                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border border-gray-100 hover:border-gray-200 transition-colors text-left"
                                >
                                    {selected[s.id]
                                        ? <CheckSquare size={16} className="text-srec-primary flex-shrink-0" />
                                        : <Square size={16} className="text-gray-300 flex-shrink-0" />}
                                    <span className={`text-sm ${selected[s.id] ? 'text-gray-900 font-medium' : 'text-gray-400'}`}>
                                        {s.label}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-50 flex items-center justify-between gap-3">
                    <p className="text-xs text-gray-400">{activeSections.length} of {sections.length} sections selected</p>
                    <div className="flex gap-3">
                        <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                            Cancel
                        </button>
                        <button
                            onClick={handleExport}
                            disabled={!activeSections.length}
                            className="px-5 py-2 text-sm font-semibold bg-srec-primary text-white rounded-xl hover:bg-srec-primaryHover transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            <Download size={14} /> Export
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
