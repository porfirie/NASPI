import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, FileText, Image as ImageIcon, HardDrive, UploadCloud, FolderPlus, Sparkles, Grip, Search } from 'lucide-react';

const PulseMenu = ({ showFabMenu, setShowFabMenu, setActiveTab, handleCreateFolder, handleUpload, isSelectionMode, isUploadDisabled, setShowSearch }) => {
  return (
    <AnimatePresence>
      {!isSelectionMode && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className="fixed z-[100] right-6"
          style={{ bottom: 'calc(2rem + env(safe-area-inset-bottom))' }}
        >
          <div className="relative w-14 h-14">
            <AnimatePresence>
              {showFabMenu && (
                <>
                  {/* ORBITE */}
                  <motion.div initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 200, damping: 25 }} className="absolute border border-white/10 rounded-full pointer-events-none" style={{ width: '150px', height: '150px', top: '50%', left: '50%', marginTop: '-75px', marginLeft: '-75px', zIndex: 2 }} />
                  <motion.div initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 200, damping: 25, delay: 0.05 }} className="absolute border border-white/5 rounded-full pointer-events-none" style={{ width: '260px', height: '260px', top: '50%', left: '50%', marginTop: '-130px', marginLeft: '-130px', zIndex: 2 }} />

                  {/* INEL INTERIOR */}
                  <motion.button initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: 19, y: -72, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20 }} onClick={() => { setActiveTab('rpi'); setShowFabMenu(false); }} className="absolute w-10 h-10 bg-[#161b22] border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-teal-400 transition-colors shadow-xl z-10"><Cpu size={16} /></motion.button>
                  <motion.button initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: -32, y: -68, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.02 }} onClick={() => { setActiveTab('documents'); setShowFabMenu(false); }} className="absolute w-10 h-10 bg-[#161b22] border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-teal-400 transition-colors shadow-xl z-10"><FileText size={16} /></motion.button>
                  <motion.button initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: -68, y: -32, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.04 }} onClick={() => { setActiveTab('media'); setShowFabMenu(false); }} className="absolute w-10 h-10 bg-[#161b22] border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-teal-400 transition-colors shadow-xl z-10"><ImageIcon size={16} /></motion.button>
                  <motion.button initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: -72, y: 19, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.06 }} onClick={() => { setActiveTab('all'); setShowFabMenu(false); }} className="absolute w-10 h-10 bg-[#161b22] border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-teal-400 transition-colors shadow-xl z-10"><HardDrive size={16} /></motion.button>

                  {/* INEL EXTERIOR */}
                  <motion.label initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: 0, y: -130, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.1 }} className={`absolute w-12 h-12 rounded-full flex items-center justify-center text-white transition-colors shadow-[0_0_15px_rgba(20,184,166,0.5)] z-10 ${isUploadDisabled ? 'bg-white/10 cursor-not-allowed opacity-60' : 'bg-teal-500 hover:bg-teal-400 cursor-pointer'}`}>
                    <UploadCloud size={20} />
                    <input type="file" multiple disabled={isUploadDisabled} className="hidden" onChange={(e) => { setShowFabMenu(false); handleUpload(e); }} />
                  </motion.label>
                  <motion.button initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: -65, y: -113, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.12 }} onClick={handleCreateFolder} className="absolute w-12 h-12 bg-[#161b22] border border-white/10 rounded-full flex items-center justify-center text-teal-400 hover:bg-white/5 transition-colors shadow-xl z-10"><FolderPlus size={20} /></motion.button>
                  
                  {/* LUPA + SPARKLES (FARA SHARE) */}
                  <motion.button initial={{ scale: 0, x: 0, y: 0, opacity: 0 }} animate={{ scale: 1, x: -113, y: -65, opacity: 1 }} exit={{ scale: 0, x: 0, y: 0, opacity: 0 }} transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.14 }} onClick={() => { setShowFabMenu(false); setShowSearch(true); }} className="absolute w-12 h-12 bg-[#161b22] border border-indigo-500/30 rounded-full flex items-center justify-center text-indigo-400 hover:bg-indigo-500/10 transition-colors shadow-[0_0_15px_rgba(99,102,241,0.2)] z-10">
                    <div className="relative flex items-center justify-center">
                      <Search size={18} className="text-white" />
                      <Sparkles size={10} className="absolute -top-1 -right-1 text-purple-400" />
                    </div>
                  </motion.button>
                </>
              )}
            </AnimatePresence>

            <motion.button
              onClick={() => setShowFabMenu(!showFabMenu)}
              animate={{ rotate: showFabMenu ? 45 : 0 }}
              className={`absolute inset-0 w-14 h-14 rounded-full flex items-center justify-center z-20 transition-all duration-300 border border-white/10 ${showFabMenu ? 'bg-[#161b22] text-teal-400 shadow-[0_0_30px_rgba(20,184,166,0.2)]' : 'bg-teal-500 text-white shadow-[0_0_20px_rgba(20,184,166,0.3)]'}`}
            >
              <Grip size={26} strokeWidth={2} />
            </motion.button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PulseMenu;