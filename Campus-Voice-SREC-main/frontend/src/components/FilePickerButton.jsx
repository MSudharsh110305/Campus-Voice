import React, { useRef } from 'react';
import { Paperclip } from 'lucide-react';

/**
 * FilePickerButton — uses the File System Access API (showOpenFilePicker) when
 * available, falling back gracefully to a hidden <input type="file">.
 *
 * Props:
 *   onFileSelected(file: File)  — called with the chosen File object
 *   accept          string      — MIME type hint for the fallback input (e.g. "image/*", ".pdf")
 *   label           string      — Button label text
 *   className       string      — Extra Tailwind classes for the button
 */
export default function FilePickerButton({
  onFileSelected,
  accept = '*/*',
  label = 'Attach File',
  className = '',
}) {
  const inputRef = useRef(null);

  const handleClick = async () => {
    // Try File System Access API first (Chrome 86+, Edge 86+)
    if ('showOpenFilePicker' in window) {
      try {
        // Build MIME-type accept map for the picker
        let acceptMap;
        if (accept.includes('pdf')) {
          acceptMap = { 'application/pdf': ['.pdf'] };
        } else if (accept.startsWith('image')) {
          acceptMap = { 'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.webp'] };
        } else {
          // Generic fallback — no type filter
          acceptMap = { '*/*': [] };
        }

        const [fileHandle] = await window.showOpenFilePicker({
          types: [{ description: 'Files', accept: acceptMap }],
          multiple: false,
        });
        const file = await fileHandle.getFile();
        onFileSelected(file);
        return;
      } catch (err) {
        if (err.name === 'AbortError') return; // user cancelled — do nothing
        // Any other error (e.g. SecurityError in some browsers) — fall through to input
      }
    }

    // Fallback: trigger the hidden <input type="file">
    inputRef.current?.click();
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className={`inline-flex items-center gap-2 ${className}`}
      >
        <Paperclip size={16} />
        {label}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelected(file);
          // Reset so the same file can be re-selected if needed
          e.target.value = '';
        }}
      />
    </>
  );
}
