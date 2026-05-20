import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Sparkles, FileText, Image as ImageIcon, Video, Folder, RefreshCw } from 'lucide-react';
import axios from 'axios';

// ATENȚIE: Am adăugat prop-ul 'onFileSelect' pe care trebuie să îl trimiți din Dashboard!
const SearchModal = ({ isOpen, onClose, API_URL, onFileSelect }) => {
  const [query, setQuery] = useState('');
  const [useAI, setUseAI] = useState(false);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false); // Pentru butonul de Sincronizare

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setResults([]);
      setUseAI(false);
    }
  }, [isOpen]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (query.trim() !== '') {
        performSearch();
      } else {
        setResults([]);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [query, useAI]);

  const performSearch = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_URL}/search?q=${encodeURIComponent(query)}&use_ai=${useAI}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResults(res.data);
    } catch (err) {
      console.error("Eroare la căutare:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${API_URL}/sync-db`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Sincronizare reușită! Adăugate: ${res.data.added}, Șterse: ${res.data.removed}`);
      if (query.trim() !== '') performSearch();
    } catch (err) {
      console.error("Eroare la sincronizare:", err);
      alert("Sincronizarea a eșuat.");
    } finally {
      setSyncing(false);
    }
  };

  const handleResultClick = (file) => {
    if (onFileSelect) {
      onFileSelect(file); // Trimitem fișierul către Dashboard pentru File Viewer
    }
    onClose(); // Închidem modalul de căutare
  };

  if (!isOpen) return null;

  return (
    // Am schimbat blur-ul aici (backdrop-blur-sm și bg-black/60)
    <div className="fixed inset-0 z-[120] flex items-start justify-center pt-[10vh] px-4 bg-black/60 backdrop-blur-sm">
      <motion.div 
        initial={{ opacity: 0, y: -50, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        className="w-full max-w-2xl bg-[#0d1117] border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)]"
      >
        {/* BARA DE CĂUTARE */}
        <div className="relative flex items-center p-2 border-b border-white/10">
          <div className="pl-6 text-slate-500">
            <Search size={24} />
          </div>
          <input 
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            // Am actualizat placeholder-ul pentru a reflecta funcțiile noi
            placeholder={useAI ? "Descrie o imagine (ex: plajă, câine)..." : "Caută după nume"}
            className="w-full bg-transparent p-6 text-xl text-white focus:outline-none placeholder:text-slate-600 font-light"
          />
          <button onClick={onClose} className="pr-6 text-slate-500 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* CONTROALE (Filtre / AI Toggle / Sync) */}
        <div className="bg-[#161b22] px-8 py-4 flex justify-between items-center border-b border-white/5">
          <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">
            {results.length} rezultate
          </span>
          
          <div className="flex gap-3">
            <button 
              onClick={handleSync}
              disabled={syncing}
              className={`flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 text-slate-500 hover:text-white transition-all text-[10px] font-bold uppercase tracking-widest ${syncing ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
              {syncing ? "Sincronizare..." : "Sync DB"}
            </button>

            <button 
              onClick={() => setUseAI(!useAI)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all text-[10px] font-bold uppercase tracking-widest ${
                useAI 
                  ? 'bg-indigo-500/20 border-indigo-500 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.3)]' 
                  : 'bg-white/5 border-white/10 text-slate-500 hover:text-white'
              }`}
            >
              <Sparkles size={14} className={useAI ? "animate-pulse" : ""} />
              AI Vision
            </button>
          </div>
        </div>

        {/* ZONA DE REZULTATE */}
        <div className="max-h-[50vh] overflow-y-auto p-4 space-y-2">
          {loading && <p className="text-center text-slate-500 text-xs tracking-widest uppercase my-8">Se caută în Aether...</p>}
          
          {!loading && results.length === 0 && query !== '' && (
            <p className="text-center text-rose-500/50 text-xs tracking-widest uppercase my-8">Nu am găsit nimic.</p>
          )}

          {!loading && results.map((file) => {
            const isImage = file.name.match(/\.(jpg|jpeg|png|webp|gif)$/i);
            
            // 1. REPARAȚIE WINDOWS: Transformăm backslash-urile '\' în '/' ca să nu dea eroare în link
            const safePath = file.path ? file.path.replace(/\\/g, '/') : "";
            
            // 2. Formatăm corect calea (scoatem "Root")
            const folderPath = (safePath === "Root" || safePath === "") ? "" : `${safePath}/`;
            
            // 3. Luăm token-ul și extragem username-ul pentru a ști în ce folder căutăm poza
            const token = localStorage.getItem('token'); 
            let username = "admin"; // Fallback
            if (token) {
              try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                if (payload.sub) username = payload.sub;
              } catch (e) {}
            }

            // 4. Construim link-ul corect pentru endpoint-ul tău de /media
            const baseUrl = API_URL.endsWith('/') ? API_URL.slice(0, -1) : API_URL;
            const mediaUrl = `${baseUrl}/media/${username}/${folderPath}${file.name}`;
            
            return (
              <div 
                key={file.id} 
                // ACTUALIZAT: Trimitem și username-ul către funcția de click!
                onClick={() => handleResultClick(file, username)} 
                className="flex items-center gap-4 p-4 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group"
              >
                {/* MINIATURĂ SAU ICONIȚĂ */}
                <div className="w-12 h-12 rounded-lg bg-black/40 flex items-center justify-center border border-white/5 overflow-hidden shrink-0">
                  {isImage ? (
                    <img 
                      src={mediaUrl} 
                      alt={file.name}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.style.display = 'none'; }} 
                    />
                  ) : (
                    <FileText size={20} className="text-slate-500" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{file.name}</p>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest truncate flex items-center gap-2">
                    <Folder size={10} /> {safePath === "" ? "Root" : safePath}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-slate-400 font-mono">{file.size} KB</p>
                  <p className="text-[9px] text-slate-600">{file.date}</p>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
};

export default SearchModal;