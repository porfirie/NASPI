import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Share2, Clock, Link as LinkIcon, Check, Loader, AlertCircle, Users, Globe } from 'lucide-react';
import axios from 'axios';

const ShareModal = ({ isOpen, onClose, selectedFiles, API_URL }) => {
  // Starea pentru Tab-uri ('internal' sau 'external')
  const [activeTab, setActiveTab] = useState('internal');

  // Stări pentru Public Link (Extern)
  const [loadingExt, setLoadingExt] = useState(false);
  const [generatedLink, setGeneratedLink] = useState(null);
  const [copied, setCopied] = useState(false);

  // Stări pentru Aether Share (Intern)
  const [targetUsername, setTargetUsername] = useState('');
  const [expirationInt, setExpirationInt] = useState(24); // ore
  const [loadingInt, setLoadingInt] = useState(false);
  const [internalSuccess, setInternalSuccess] = useState(false);

  if (!isOpen) return null;

  // --- LOGICA PENTRU PUBLIC LINK (FILEBIN) ---
  const handlePublicShare = async () => {
    setLoadingExt(true);
    setGeneratedLink(null);
    setCopied(false);

    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${API_URL}/share-multiple`, {
        file_paths: selectedFiles,
        expiration: '24h' // Filebin ignoră oricum, dar trimitem pt compatibilitate
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGeneratedLink(res.data.link);
    } catch (err) {
      alert("Eroare la generarea link-ului: " + (err.response?.data?.detail || "Eroare server"));
    } finally {
      setLoadingExt(false);
    }
  };

  const copyToClipboard = async () => {
    if (!generatedLink) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(generatedLink);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = generatedLink;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      alert("Browserul a blocat copierea automată. Te rog selectează manual link-ul!");
    }
  };

  // --- LOGICA PENTRU AETHER SHARE (INTERN) ---
  const handleInternalShare = async () => {
    if (!targetUsername.trim()) {
      alert("Introdu numele utilizatorului!");
      return;
    }

    setLoadingInt(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/share-internal`, {
        file_paths: selectedFiles,
        target_username: targetUsername.trim(),
        expiration_hours: expirationInt
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setInternalSuccess(true);
      setTimeout(() => {
        closeModal();
      }, 2500); // Se închide singur după succes

    } catch (err) {
      alert("Eroare: " + (err.response?.data?.detail || "Nu am putut partaja."));
    } finally {
      setLoadingInt(false);
    }
  };

  const closeModal = () => {
    setGeneratedLink(null);
    setInternalSuccess(false);
    setTargetUsername('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-md bg-[#0d1117] border border-white/10 rounded-3xl overflow-hidden shadow-2xl relative"
      >
        {/* Header cu selector de Tab-uri */}
        <div className="border-b border-white/5 bg-gradient-to-r from-indigo-500/10 to-transparent">
          <div className="flex justify-between items-center p-6 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl">
                <Share2 size={20} />
              </div>
              <h2 className="text-sm font-bold text-white uppercase tracking-widest">Share Hub</h2>
            </div>
            <button onClick={closeModal} className="text-slate-500 hover:text-white transition-colors">
              <X size={20} />
            </button>
          </div>

          {/* TAB BUTTONS */}
          <div className="flex px-6 gap-4">
            <button 
              onClick={() => setActiveTab('internal')}
              className={`pb-3 text-xs font-bold uppercase tracking-widest transition-all border-b-2 flex items-center gap-2 ${activeTab === 'internal' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
            >
              <Users size={14} /> Aether Share
            </button>
            <button 
              onClick={() => setActiveTab('external')}
              className={`pb-3 text-xs font-bold uppercase tracking-widest transition-all border-b-2 flex items-center gap-2 ${activeTab === 'external' ? 'border-teal-500 text-teal-400' : 'border-transparent text-slate-500 hover:text-slate-300'}`}
            >
              <Globe size={14} /> Public Link
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Status Selecție (comun pentru ambele tab-uri) */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-white/5 border border-white/5">
            <AlertCircle size={18} className="text-indigo-400 mt-0.5" />
            <div>
              <p className="text-sm text-white">Ai selectat {selectedFiles.length} {selectedFiles.length === 1 ? 'fișier' : 'fișiere'}.</p>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {/* ================= TAB-UL INTERN ================= */}
            {activeTab === 'internal' && (
              <motion.div key="internal" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-4">
                
                {internalSuccess ? (
                  <div className="p-6 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-center space-y-2">
                    <Check size={32} className="text-indigo-400 mx-auto mb-2" />
                    <p className="text-indigo-400 font-bold text-sm">Trimis cu succes!</p>
                    <p className="text-[10px] text-indigo-400/70 uppercase tracking-widest">Utilizatorul va vedea fișierele instant.</p>
                  </div>
                ) : (
                  <>
                    <div className="space-y-2">
                      <label className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Către cine trimiți?</label>
                      <input 
                        type="text" 
                        placeholder="Ex: george"
                        value={targetUsername}
                        onChange={(e) => setTargetUsername(e.target.value)}
                        className="w-full bg-black/50 border border-white/10 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-2">
                        <Clock size={14} /> Valabilitate acces:
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {[1, 24, 168].map((hours) => (
                          <button
                            key={hours}
                            onClick={() => setExpirationInt(hours)}
                            className={`p-3 rounded-xl border text-xs font-bold transition-all uppercase tracking-widest ${
                              expirationInt === hours 
                                ? 'bg-indigo-500/20 border-indigo-500 text-indigo-400' 
                                : 'bg-transparent border-white/10 text-slate-400 hover:border-white/30'
                            }`}
                          >
                            {hours === 1 ? '1 Oră' : hours === 24 ? '24 Ore' : '7 Zile'}
                          </button>
                        ))}
                      </div>
                    </div>

                    <button 
                      onClick={handleInternalShare}
                      disabled={loadingInt || selectedFiles.length === 0 || !targetUsername.trim()}
                      className="w-full p-4 mt-4 rounded-xl bg-indigo-500 text-white font-bold uppercase tracking-widest text-xs hover:bg-indigo-400 transition-colors flex justify-center items-center gap-2 disabled:opacity-50"
                    >
                      {loadingInt ? <Loader className="animate-spin" size={16} /> : <Share2 size={16} />}
                      {loadingInt ? 'Se trimite...' : 'Oferă Acces'}
                    </button>
                  </>
                )}
              </motion.div>
            )}

            {/* ================= TAB-UL EXTERN ================= */}
            {activeTab === 'external' && (
              <motion.div key="external" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="space-y-4">
                {!generatedLink ? (
                  <>
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500/80 text-[11px] leading-relaxed">
                      Fișierele vor fi încărcate pe un server public (Filebin) și vor părăsi rețeaua sigură Aether. 
                      <br/><br/>
                      <strong className="text-amber-500">Link-ul se va șterge ireversibil după 6 zile.</strong>
                    </div>

                    <button 
                      onClick={handlePublicShare}
                      disabled={loadingExt || selectedFiles.length === 0}
                      className="w-full p-4 mt-2 rounded-xl bg-teal-500 text-black font-bold uppercase tracking-widest text-xs hover:bg-teal-400 transition-colors flex justify-center items-center gap-2 disabled:opacity-50"
                    >
                      {loadingExt ? <Loader className="animate-spin" size={16} /> : <Globe size={16} />}
                      {loadingExt ? 'Se generează...' : 'Generează Link Public'}
                    </button>
                  </>
                ) : (
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-teal-500/10 border border-teal-500/30 text-center space-y-2">
                      <Check size={32} className="text-teal-400 mx-auto mb-2" />
                      <p className="text-teal-400 font-bold text-sm">Link generat cu succes!</p>
                    </div>

                    <div className="flex gap-2">
                      <div className="flex-1 p-3 bg-black/50 border border-white/10 rounded-xl flex items-center overflow-hidden">
                        <LinkIcon size={14} className="text-slate-500 mr-2 shrink-0" />
                        <span className="text-xs text-white truncate" style={{ userSelect: 'all' }}>{generatedLink}</span>
                      </div>
                      <button 
                        onClick={copyToClipboard}
                        className={`px-4 rounded-xl font-bold text-xs uppercase tracking-widest transition-all ${copied ? 'bg-teal-500 text-black' : 'bg-white/10 text-white hover:bg-white/20'}`}
                      >
                        {copied ? 'Copiat!' : 'Copy'}
                      </button>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};

export default ShareModal;