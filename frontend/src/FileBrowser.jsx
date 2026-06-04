import React, { useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MoreVertical, Check, Folder, Video, FileText, CheckSquare, Network, Sparkles } from 'lucide-react';

const FileBrowser = ({ 
  data, activeTab, filesToRender, currentPath, setCurrentPath, 
  isSelectionMode, setIsSelectionMode,
  showMenu, setShowMenu, selectedFiles, toggleFileSelection, 
  setSelectedPreview, setShowViewer, API_URL 
}) => {

  const timerRef = useRef(null);
  const isLongPressing = useRef(false);

  const handlePressStart = (path) => {
    isLongPressing.current = false;
    timerRef.current = setTimeout(() => {
      isLongPressing.current = true;
      if (!isSelectionMode) setIsSelectionMode(true);
      if (!selectedFiles.includes(path)) toggleFileSelection(path);
      
      if (navigator.vibrate) navigator.vibrate(50);
    }, 500);
  };

  const handlePressCancel = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  };

  // Funcție nouă: Selectează tot din tab-ul curent
  const handleSelectAll = () => {
    const allPaths = filesToRender.map(f => f.path || f.name);
    if (activeTab === 'all' && data?.categories?.folders) {
      const folderPaths = data.categories.folders.map(f => f.path);
      allPaths.push(...folderPaths);
    }
    
    // Dacă sunt toate selectate, le deselectăm. Dacă nu, le selectăm pe toate.
    if (selectedFiles.length === allPaths.length) {
      allPaths.forEach(path => toggleFileSelection(path)); // Deselect (le scoate din listă)
    } else {
      // Adăugăm doar ce lipsește
      allPaths.forEach(path => {
        if (!selectedFiles.includes(path)) toggleFileSelection(path);
      });
    }
    setShowMenu(false);
  };

  return (
    <motion.div key="files" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      
      <div className="flex justify-between items-end mb-8 border-b border-white/5 pb-2">
        <h2 className="text-[10px] uppercase tracking-[0.5em] text-white/40">
          {isSelectionMode ? `MOD SELECȚIE` : "FIȘIERE"}
        </h2>
        <div className="flex items-center gap-4">
          <p className="text-[10px] text-slate-600 tracking-widest uppercase">
            Total ({(data?.categories?.folders?.length || 0) + filesToRender.length})
          </p>

          <div className="relative">
            <button onClick={() => setShowMenu(!showMenu)} className="p-1 text-slate-500 hover:text-white transition-colors">
              <MoreVertical size={18} />
            </button>
            <AnimatePresence>
              {showMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
                  className="absolute right-0 mt-2 w-48 bg-[#161b22] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                >
                  <button onClick={() => { setIsSelectionMode(!isSelectionMode); setShowMenu(false); }} className="w-full px-4 py-3 text-left text-[10px] uppercase text-slate-300 hover:text-white hover:bg-white/5 flex items-center gap-2 font-bold">
                    <Check size={14} className="text-teal-500" /> {isSelectionMode ? 'Ieșire Selecție' : 'Selecție Manuală'}
                  </button>
                  
                  {isSelectionMode && (
                    <>
                      <div className="h-px w-full bg-white/5" />
                      <button onClick={handleSelectAll} className="w-full px-4 py-3 text-left text-[10px] uppercase text-indigo-400 hover:bg-white/5 flex items-center gap-2 font-bold">
                        <CheckSquare size={14} /> Selectează Tot
                      </button>
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        
        {/* FOLDERE */}
        {activeTab === 'all' && data?.categories?.folders?.map((folder, idx) => {
          // --- VERIFICĂM DACĂ E FOLDERUL VIRTUAL DE SHARE ---
          const isSharedFolder = folder.is_virtual; 

          return (
            <motion.div
              layout key={`folder-${idx}`}
              onTouchStart={() => handlePressStart(folder.path)}
              onTouchEnd={handlePressCancel}
              onTouchMove={handlePressCancel}
              onMouseDown={() => handlePressStart(folder.path)}
              onMouseUp={handlePressCancel}
              onMouseLeave={handlePressCancel}
              onClick={() => {
                if (isLongPressing.current) { isLongPressing.current = false; return; }
                if (isSelectionMode) toggleFileSelection(folder.path);
                else setCurrentPath([...currentPath, folder.name]); // Chiar dacă e "Shared with me", va merge perfect către server
              }}
              // Dacă e folder de share, îi dăm o strălucire mov/indigo. Altfel, rămâne teal/verde.
              className={`relative aspect-[1/1.1] rounded-2xl flex flex-col items-center justify-center cursor-pointer transition-all group shadow-lg select-none 
                ${isSharedFolder 
                    ? 'bg-indigo-500/10 border border-indigo-500/30 hover:border-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.15)]' 
                    : 'bg-[#161b22]/50 border border-white/5 hover:border-teal-500/30'
                }
                ${isSelectionMode && selectedFiles.includes(folder.path) ? 'border-rose-500 bg-rose-500/10' : ''}`}
            >
              <div 
                onClick={(e) => {
                  e.stopPropagation();
                  if (!isSelectionMode) setIsSelectionMode(true);
                  toggleFileSelection(folder.path);
                }}
                className={`absolute top-3 left-3 z-30 transition-all duration-300 ${isSelectionMode || selectedFiles.includes(folder.path) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
              >
                <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${selectedFiles.includes(folder.path) ? 'bg-rose-500 border-rose-500 scale-110' : 'bg-black/40 border-white/30 hover:bg-black/60'}`}>
                  {selectedFiles.includes(folder.path) && <Check size={14} className="text-white" />}
                </div>
              </div>

              {/* ICONIȚA (Network pt Share, Folder normal pt restul) */}
              <div className="relative pointer-events-none">
                  {isSharedFolder ? (
                      <>
                        <Network size={48} className="text-indigo-400 group-hover:scale-110 transition-transform duration-300" />
                        
                      </>
                  ) : (
                      <Folder size={48} className="text-teal-500/60 group-hover:scale-110 transition-transform duration-300" />
                  )}
              </div>
              
              <p className={`mt-4 text-[10px] font-bold uppercase tracking-widest pointer-events-none truncate w-full text-center px-4 ${isSharedFolder ? 'text-indigo-300' : 'text-slate-300'}`}>
                {folder.name}
              </p>
            </motion.div>
          )
        })}

        {/* FIȘIERE */}
        {filesToRender.map((file, idx) => {
          const filePath = file.path || file.name;
          // Verificăm dacă fișierul este împrumutat prin share (flag-ul pus în Python)
          const isSharedFile = file.is_shared;

          return (
            <motion.div
              layout key={filePath + idx}
              onTouchStart={() => handlePressStart(filePath)}
              onTouchEnd={handlePressCancel}
              onTouchMove={handlePressCancel}
              onMouseDown={() => handlePressStart(filePath)}
              onMouseUp={handlePressCancel}
              onMouseLeave={handlePressCancel}
              onClick={() => {
                if (isLongPressing.current) { isLongPressing.current = false; return; }
                if (isSelectionMode) toggleFileSelection(filePath);
                else { setSelectedPreview(file); setShowViewer(true); }
              }}
              // Dacă e fișier share-uit, îi punem un border mov fin la hover
              className={`relative group aspect-[1/1.1] rounded-2xl border transition-all cursor-pointer overflow-hidden flex flex-col select-none 
                ${isSelectionMode && selectedFiles.includes(filePath) 
                  ? 'border-teal-500 bg-teal-500/10 shadow-[0_0_15px_rgba(20,184,166,0.2)]' 
                  : `bg-white/5 border-white/5 ${isSharedFile ? 'hover:border-indigo-500/40' : 'hover:border-teal-500/20'}`
                }`}
            >
              <div 
                onClick={(e) => {
                  e.stopPropagation();
                  if (!isSelectionMode) setIsSelectionMode(true);
                  toggleFileSelection(filePath);
                }}
                className={`absolute top-3 left-3 z-30 transition-all duration-300 ${isSelectionMode || selectedFiles.includes(filePath) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
              >
                <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${selectedFiles.includes(filePath) ? 'bg-teal-500 border-teal-500 scale-110' : 'bg-black/40 border-white/30 hover:bg-black/60'}`}>
                  {selectedFiles.includes(filePath) && <Check size={14} className="text-white" />}
                </div>
              </div>

              <div className="flex-1 p-3 flex items-center justify-center relative pointer-events-none">
                {file.name.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
                  <img src={`${API_URL}/media/${file.owner_id}/${filePath}`} className={`absolute inset-0 w-full h-full object-cover transition-all ${isSelectionMode && selectedFiles.includes(filePath) ? 'opacity-100 grayscale-0' : 'opacity-60 grayscale-[40%]'}`} draggable="false" />
                ) : (
                  <div className={`transition-opacity ${selectedFiles.includes(filePath) ? 'opacity-100' : 'opacity-20'}`}>
                    {file.name.match(/\.(mp4|mov|avi)$/i) ? <Video size={36} /> : <FileText size={36} />}
                  </div>
                )}
              </div>

              <div className="p-3 bg-black/30 backdrop-blur-sm mt-auto border-t border-white/5 pointer-events-none flex flex-col">
                <p className={`text-[10px] truncate font-medium ${isSharedFile ? 'text-indigo-300' : 'text-slate-400'}`}>
                  {file.name}
                </p>
                <div className="flex justify-between items-center mt-1">
                  {isSharedFile ? (
                      <span className="text-[8px] text-indigo-400/60 uppercase tracking-widest flex items-center gap-1">
                          <Network size={8}/> De la: {file.username}
                      </span>
                  ) : (
                      <span className="text-[9px] text-slate-600 font-mono">{file.size} KB</span>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  );
};

export default FileBrowser;