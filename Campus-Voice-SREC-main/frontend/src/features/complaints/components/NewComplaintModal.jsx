// src/components/NewComplaintModal.jsx
import { useState } from "react";
import { Button, Select } from "../../../components/UI";
import { Upload, X } from "lucide-react";

export default function NewComplaintModal({ isOpen, onClose, onAdd }) {
  const [form, setForm] = useState({ title: "", desc: "", img: null });
  const [preview, setPreview] = useState("");

  if (!isOpen) return null;

  const handleImage = (e) => {
    const file = e.target.files[0];
    if (file) {
      setForm({ ...form, img: file });
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.title || !form.desc || !form.img) {
      return;
    }
    if (onAdd) {
      onAdd({
        ...form,
        img: preview,
        author: "You",
        id: Date.now(),
        status: "Pending",
        category: "Pending AI Analysis",
        upvotes: 0,
        submitted_at: new Date().toISOString()
      });
    }
    setForm({ title: "", desc: "", img: null });
    setPreview("");
    onClose();
  };

  const inputClass = "w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-srec-primary/20 focus:border-srec-primary transition-all";

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex justify-center items-end sm:items-center p-4 animate-fadeIn">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg border border-white/60 p-6 sm:p-8 transform transition-all scale-100 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">New Complaint</h2>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              className={inputClass}
              placeholder="Title of your grievance"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
            />
          </div>

          <div>
            <textarea
              className={inputClass}
              placeholder="Describe the issue in detail..."
              rows={4}
              value={form.desc}
              onChange={e => setForm({ ...form, desc: e.target.value })}
            ></textarea>
          </div>

          <div>
            {!preview ? (
              <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-gray-200 rounded-xl cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
                <Upload className="w-7 h-7 mb-1.5 text-gray-400" />
                <p className="text-xs text-gray-500">Click to upload evidence (optional)</p>
                <input type="file" className="hidden" accept="image/*" onChange={handleImage} />
              </label>
            ) : (
              <div className="relative h-32 w-full rounded-xl overflow-hidden border border-gray-200">
                <img src={preview} alt="preview" className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => { setForm({ ...form, img: null }); setPreview(""); }}
                  className="absolute top-2 right-2 p-1 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-1">
            <Button type="button" variant="ghost" onClick={onClose} className="flex-1">Cancel</Button>
            <button
              type="submit"
              className="flex-1 py-2.5 bg-srec-primary text-white font-semibold rounded-xl hover:bg-srec-primaryHover transition-all duration-200 text-sm"
            >
              Post Grievance
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
