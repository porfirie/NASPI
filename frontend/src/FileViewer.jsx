import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, Download, Maximize, FileText } from 'lucide-react';

const FileViewer = ({ isOpen, onClose, currentFile, allFiles, apiUrl }) => {
  const [index, setIndex] = useState(0);
  const [standaloneFile, setStandaloneFile] = useState(null); // PENTRU SEARCH

  // Sincronizăm indexul intern cu fișierul pe care s-a dat click
  useEffect(() => {
    if (currentFile) {
      const newIndex = allFiles.findIndex(f => f.name === currentFile.name);
      if (newIndex !== -1) {
        setIndex(newIndex);
        setStandaloneFile(null); // E în folderul curent
      } else {
        // Fișierul vine din SEARCH și nu e în folderul curent!
        setStandaloneFile(currentFile);
      }
    }
  }, [currentFile, allFiles]);

  if (!isOpen || (!allFiles[index] && !standaloneFile)) return null;

  // Dacă e din Search folosim standalone, altfel folosim lista normală
  const file = standaloneFile || allFiles[index];

  const isImage = file.name.match(/\.(jpg|jpeg|png|gif|webp)$/i);
  const isVideo = file.name.match(/\.(mp4|mov|avi|webm)$/i);

  // REPARAȚIE CRITICĂ: Folosim calea completă, nu doar numele!
  // Dacă fișierul vine din Dashboard, .path este deja calea completă.
  // Dacă vine din Search, ne asigurăm că îl construim corect.
  const filePath = (file.path && file.path !== "Root" && !file.path.includes(file.name))
      ? `${file.path}/${file.name}`
      : (file.path && file.path !== "Root" ? file.path : file.name);

  // NOU: endpoint-ul /media e acum protejat de autentificare.
  // Tag-urile <img>/<video>/<a download> nu pot trimite header Authorization,
  // așa că atașăm token-ul ca query param. Codăm fiecare segment al căii ca să
  // funcționeze și cu nume de fișiere cu spații / diacritice.
  const token = localStorage.getItem('token');
  const encodedPath = filePath.split('/').map(encodeURIComponent).join('/');
  const fileUrl = `${apiUrl}/media/${file.owner_id}/${encodedPath}?token=${encodeURIComponent(token || '')}`;

  // Navigarea stânga/dreapta merge doar dacă NU suntem în modul "Standalone / Search"
  const nextFile = () => {
    if (!standaloneFile) setIndex((prev) => (prev + 1) % allFiles.length);
  };
  const prevFile = () => {
    if (!standaloneFile) setIndex((prev) => (prev - 1 + allFiles.length) % allFiles.length);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-3xl flex flex-col items-center justify-center p-4"
    >
      {/* HEADER PREVIEW */}
      <div className="absolute top-0 left-0 right-0 p-6 flex justify-between items-center z-[110] bg-gradient-to-b from-black/50 to-transparent">
        <div className="flex flex-col">
          <span className="text-[10px] text-teal-500 font-black tracking-[0.3em] uppercase">
            {standaloneFile ? "Search Preview" : "Preview Mode"}
          </span>
          <span className="text-white/70 text-xs truncate max-w-[200px] font-light uppercase tracking-widest">{file.name}</span>
        </div>
        <div className="flex gap-4">
           <a href={fileUrl} download className="p-3 bg-white/5 rounded-full text-white/50 hover:text-white transition-colors">
            <Download size={20} />
          </a>
          <button onClick={onClose} className="p-3 bg-white/5 rounded-full text-white/50 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
      </div>

      {/* NAVIGARE STÂNGA/DREAPTA (Ascunse dacă fișierul e deschis din Search) */}
      {!standaloneFile && allFiles.length > 1 && (
        <>
          <button onClick={prevFile} className="absolute left-4 z-[110] p-4 text-white/20 hover:text-teal-500 transition-all hover:scale-125">
            <ChevronLeft size={40} />
          </button>
          <button onClick={nextFile} className="absolute right-4 z-[110] p-4 text-white/20 hover:text-teal-500 transition-all hover:scale-125">
            <ChevronRight size={40} />
          </button>
        </>
      )}

      {/* ZONA DE CONȚINUT */}
      <div className="w-full h-full flex items-center justify-center pointer-events-none">
        <AnimatePresence mode="wait">
          <motion.div
            key={file.name}
            initial={{ opacity: 0, scale: 0.9, x: 20 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 1.1, x: -20 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="max-w-5xl max-h-[80vh] flex items-center justify-center pointer-events-auto"
          >
            {isImage && (
              <img
                src={fileUrl}
                alt={file.name}
                className="max-w-full max-h-[85vh] md:max-h-[80vh] w-auto h-auto object-contain rounded-lg shadow-2xl"
              />
            )}

            {isVideo && (
              <video
                src={fileUrl}
                controls
                autoPlay
                className="max-w-full max-h-[85vh] md:max-h-[80vh] w-auto h-auto rounded-lg shadow-2xl outline-none"
              />
            )}

            {!isImage && !isVideo && (
              <div className="flex flex-col items-center gap-6 opacity-40">
                <FileText size={100} strokeWidth={1} />
                <span className="text-[10px] tracking-[0.5em] uppercase">Previzualizare indisponibilă</span>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* INDICATOR PAGINAȚIE JOS */}
      {!standaloneFile && (
        <div className="absolute bottom-10 text-[9px] text-white/20 tracking-[0.5em] uppercase font-bold">
          {index + 1} / {allFiles.length}
        </div>
      )}
    </motion.div>
  );
};

export default FileViewer;