import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Folder, ChevronRight } from 'lucide-react';

const FolderSelector = ({ isOpen, onClose, folders, onConfirm, title = 'Mută în...' }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="bg-[#161b22] border border-white/10 w-full max-w-sm rounded-3xl overflow-hidden shadow-2xl"
      >
        <div className="p-6 border-b border-white/5 flex justify-between items-center">
          <h3 className="text-[10px] uppercase tracking-[0.2em] font-bold text-teal-400">{title}</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white"><X size={20} /></button>
        </div>
        
        <div className="max-h-60 overflow-y-auto p-2">
          {/* Opțiunea HOME */}
          <button 
            onClick={() => onConfirm("")}
            className="w-full p-4 flex items-center gap-3 hover:bg-white/5 rounded-2xl transition-all text-slate-300 group"
          >
            <Folder size={18} className="text-teal-500" />
            <span className="text-xs font-bold uppercase tracking-widest">Root (Aether Home)</span>
            <ChevronRight size={14} className="ml-auto opacity-0 group-hover:opacity-100 transition-all" />
          </button>

          {/* Listă subfoldere */}
          {folders.map((f) => (
            <button 
              key={f.path}
              onClick={() => onConfirm(f.path)}
              className="w-full p-4 flex items-center gap-3 hover:bg-white/5 rounded-2xl transition-all text-slate-300 group"
            >
              <Folder size={18} className="text-teal-500/60" />
              <span className="text-xs font-bold uppercase tracking-widest truncate">{f.name}</span>
              <ChevronRight size={14} className="ml-auto opacity-0 group-hover:opacity-100 transition-all" />
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default FolderSelector;