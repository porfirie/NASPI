import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { HardDrive, LogOut, ChevronRight, User, MoveHorizontal, Download, Trash2, X, Loader, Share2, Copy, Edit3, CloudUpload } from 'lucide-react';


import FileViewer from './FileViewer';
import StorageMap from './StorageMap';
import SystemMonitor from './SystemMonitor';

// Componente
import ProfileSecurity from './ProfileSecurity';
import PulseMenu from './PulseMenu';
import FileBrowser from './FileBrowser';
import FolderSelector from './FolderSelector';
import SearchModal from './SearchModal';
import ShareModal from './ShareModal';

const API_URL = import.meta.env.VITE_API_URL;

const Dashboard = ({ setToken }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showProfile, setShowProfile] = useState(false);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isZipping, setIsZipping] = useState(false);

  const [selectedPreview, setSelectedPreview] = useState(null);
  const [showViewer, setShowViewer] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadLoaded, setUploadLoaded] = useState(0);
  const [uploadTotal, setUploadTotal] = useState(0);

  const [showFabMenu, setShowFabMenu] = useState(false);
  const [currentPath, setCurrentPath] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0); // <--- ADAUGĂ ASTA
  const [sysStats, setSysStats] = useState(null);
  const [showFolderSelector, setShowFolderSelector] = useState(false);
  const [folderActionMode, setFolderActionMode] = useState('move');

  const [showSearch, setShowSearch] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);

  const isSharedPath = currentPath.join('/').startsWith('Shared with me');

  useEffect(() => { fetchData(); }, [currentPath, refreshTrigger]);

  useEffect(() => {
    if (API_URL) {
      try {
        const baseUrl = API_URL.endsWith('/') ? API_URL.slice(0, -1) : API_URL;
        const WS_URL = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        const socket = new WebSocket(`${WS_URL}/ws`);

        socket.onopen = () => console.log("✅ Conectat la Live Server (Aether WS)");
        socket.onmessage = (event) => {
          try {
            const messageData = JSON.parse(event.data);
            if (messageData.type === "REFRESH_FILES") {
              // 🚨 AICI E MAGIA: Nu mai chemăm fetchData(), ci declanșăm refresh-ul sigur
              setRefreshTrigger(prev => prev + 1);
            }
            if (messageData.type === "SYSTEM_STATS") {
              setSysStats(messageData);
            }
          } catch (err) { console.error("Eroare WS:", err); }
        };
        return () => socket.close();
      } catch (err) { console.error("Eroare fatală la inițializarea WS:", err); }
    }
  }, []); // E foarte important ca array-ul de aici să rămână gol []!

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const folderPath = currentPath.join('/');
      const res = await axios.get(`${API_URL}/dashboard?path=${encodeURIComponent(folderPath)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(res.data);
      setLoading(false);
    } catch (err) { handleLogout(); }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 MB';
    const k = 1024 * 1024; // Convertim direct în MB
    return (bytes / k).toFixed(1) + ' MB';
  };

  const handleLogout = () => { localStorage.removeItem('token'); setToken(null); };

  const handleCreateFolder = async () => {
    setShowFabMenu(false);
    const folderName = window.prompt("Introdu numele noului folder:");
    if (!folderName || folderName.trim() === '') return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/create-folder`, {
        path: currentPath.join('/'),
        folder_name: folderName.trim()
      }, { headers: { Authorization: `Bearer ${token}` } });
      fetchData();
    } catch (err) { alert("Eroare: " + (err.response?.data?.detail || "Nu am putut crea folderul")); }
  };

  const handleUpload = async (event) => {
    const files = event.target.files;
    if (!files.length) return;

    const folderPath = currentPath.join('/');
    if (folderPath.startsWith('Shared with me')) {
      event.target.value = null;
      alert('Nu poți încărca fișiere direct în folderul "Shared with me". Navighează în propriul folder și încarcă de acolo.');
      return;
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append("files", files[i]);
    formData.append("target_path", folderPath);

    setUploading(true); setProgress(0);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          setProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
          setUploadLoaded(progressEvent.loaded); // <-- Salvăm cât s-a încărcat
          setUploadTotal(progressEvent.total);   // <-- Salvăm totalul
        }
      });
      await fetchData();
    } catch (err) {
      console.error('Upload error:', err);
      alert("Eroare la upload: " + (err.response?.data?.detail || err.message || "Nu am putut încărca fișierul"));
    } finally {
      event.target.value = null;
      setTimeout(() => { setUploading(false); setProgress(0); }, 1000);
    }
  };

  const toggleFileSelection = (filePath) => {
    setSelectedFiles(prev => prev.includes(filePath) ? prev.filter(f => f !== filePath) : [...prev, filePath]);
  };

  const handleBulkDelete = async () => {
    if (selectedFiles.length === 0) return;
    if (!window.confirm(`Ștergi definitiv ${selectedFiles.length} elemente?`)) return;

    const token = localStorage.getItem('token');
    try {
      await axios.post(`${API_URL}/delete-multiple`, { filenames: selectedFiles }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsSelectionMode(false);
      setSelectedFiles([]);
      fetchData();
    } catch (err) {
      alert("Eroare la ștergere: " + (err.response?.data?.detail || "Nu am putut șterge elementele"));
    }
  };

  const handleBulkDownload = async () => {
    if (selectedFiles.length === 0) return;

    // REPARATIE: Excludem directoarele din selecție dacă s-au strecurat
    const filesToDownload = selectedFiles.filter(f => !f.endsWith('/'));

    if (filesToDownload.length === 0) {
      alert("Ai selectat doar foldere. Deocamdată poți descărca doar fișiere.");
      return;
    }

    setIsZipping(true);
    try {
      const token = localStorage.getItem('token');
      // REPARATIE: Ne asigurăm că trimitem un array curat către Python
      const response = await axios.post(`${API_URL}/download-zip`, filesToDownload, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a'); link.href = url;
      link.setAttribute('download', 'Aether_Files.zip');
      document.body.appendChild(link); link.click(); link.remove();
      window.URL.revokeObjectURL(url);
      setIsSelectionMode(false); setSelectedFiles([]);
    } catch (err) {
      console.error("Eroare ZIP:", err);
      alert("Eroare la crearea arhivei. Verifică consola pentru detalii.");
    }
    finally { setIsZipping(false); }
  };

  const handleMoveFiles = async (destPath) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/move`, {
        source_paths: selectedFiles,
        destination_folder: destPath
      }, { headers: { Authorization: `Bearer ${token}` } });

      setIsSelectionMode(false);
      setSelectedFiles([]);
      setShowFolderSelector(false);
      fetchData();
    } catch (err) {
      alert("Eroare la mutare: " + (err.response?.data?.detail || "Eroare necunoscută"));
    }
  };

  const handleCopyFiles = async (destPath) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/copy-files`, {
        source_paths: selectedFiles,
        destination_folder: destPath
      }, { headers: { Authorization: `Bearer ${token}` } });

      setIsSelectionMode(false);
      setSelectedFiles([]);
      setShowFolderSelector(false);
      fetchData();
    } catch (err) {
      alert("Eroare la copiere: " + (err.response?.data?.detail || "Eroare necunoscută"));
    }
  };

  const selectedFolder = selectedFiles.length === 1 ? data?.categories?.folders?.find(folder => folder.path === selectedFiles[0] && !folder.is_virtual) : null;

  const handleRenameFolder = async () => {
    if (!selectedFolder) return;
    const newName = window.prompt("Numele nou al folderului:", selectedFolder.name);
    if (!newName || newName.trim() === "" || newName.trim() === selectedFolder.name) return;

    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/rename-folder`, {
        folder_path: selectedFolder.path,
        new_name: newName.trim()
      }, { headers: { Authorization: `Bearer ${token}` } });

      const currentPathString = currentPath.join('/');
      if (currentPathString === selectedFolder.path) {
        setCurrentPath(currentPath.slice(0, -1).concat(newName.trim()));
      } else if (currentPathString.startsWith(`${selectedFolder.path}/`)) {
        const suffix = currentPath.slice(selectedFolder.path.split('/').length);
        setCurrentPath([...selectedFolder.path.split('/').slice(0, -1), newName.trim(), ...suffix]);
      }

      setSelectedFiles([]);
      setIsSelectionMode(false);
      fetchData();
    } catch (err) {
      alert("Eroare la redenumire: " + (err.response?.data?.detail || "Nu am putut redenumi folderul"));
    }
  };

  const getFilesToRender = () => {
    if (!data || !data.categories) return [];
    if (activeTab === 'all') return [...(data.categories.media || []), ...(data.categories.documents || [])].filter(item => item.type !== 'folder');
    return data.categories[activeTab] || [];
  };

  const selectedHasSharedItems = data ? getFilesToRender().some(item => selectedFiles.includes(item.path) && item.is_shared) : false;

  if (loading) return (
    <div className="h-screen bg-[#0d1117] flex items-center justify-center">
      <motion.div animate={{ scale: [1, 1.2, 1], opacity: [0.3, 1, 0.3] }} transition={{ duration: 3, repeat: Infinity }} className="w-24 h-24 rounded-full border border-teal-500/30 flex items-center justify-center text-teal-500 font-light tracking-widest text-xs">
        AETHER
      </motion.div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0d1117] text-slate-300 font-light overflow-x-hidden">

      <header className="p-6 flex justify-between items-center relative z-40 border-b border-white/5 bg-[#0d1117]/80 backdrop-blur-sm sticky top-0">
        <motion.div whileTap={{ scale: 0.95 }} onClick={() => setShowProfile(!showProfile)} className="w-12 h-12 rounded-full border border-teal-500/10 bg-teal-500/5 flex items-center justify-center cursor-pointer hover:bg-teal-500/10 transition-all shadow-[0_0_15px_theme(colors.teal.500/5%)]">
          <User size={20} className="text-teal-400/70" />
        </motion.div>
        <h1 className="text-xs tracking-[0.5em] uppercase text-white/30">Aether NAS</h1>
        <button onClick={handleLogout} className="p-2 text-rose-400/30 hover:text-rose-400 transition-colors"><LogOut size={18} /></button>
      </header>

      <main className="px-6 pb-24 pt-8 max-w-7xl mx-auto">
        <StorageMap freeGb={data.storage_stats.free_gb} totalGb={data.storage_stats.total_gb} percentUsed={data.storage_stats.percent_used} />

        <AnimatePresence>
          {activeTab === 'all' && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="flex items-center gap-2 mb-6 px-2 text-[10px] uppercase font-bold tracking-widest text-slate-500 overflow-x-auto no-scrollbar">
              <button className="hover:text-teal-400 transition-colors flex items-center gap-2 shrink-0" onClick={() => setCurrentPath([])}>
                <HardDrive size={14} /> HOME
              </button>
              {currentPath.map((folder, index) => (
                <React.Fragment key={folder}>
                  <ChevronRight size={14} className="text-slate-700 shrink-0" />
                  <button className="hover:text-teal-400 transition-colors shrink-0" onClick={() => setCurrentPath(currentPath.slice(0, index + 1))}>
                    {folder}
                  </button>
                </React.Fragment>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <section className="mb-20 px-2 relative">
          <AnimatePresence mode="wait">
            {activeTab === 'rpi' ? (
              <SystemMonitor key="monitor" stats={sysStats} />
            ) : (
              <FileBrowser
                data={data} activeTab={activeTab} filesToRender={getFilesToRender()}
                currentPath={currentPath} setCurrentPath={setCurrentPath}
                isSelectionMode={isSelectionMode} setIsSelectionMode={setIsSelectionMode}
                showMenu={showMenu} setShowMenu={setShowMenu}
                selectedFiles={selectedFiles} toggleFileSelection={toggleFileSelection}
                setSelectedPreview={setSelectedPreview} setShowViewer={setShowViewer}
                API_URL={API_URL}
              />
            )}
          </AnimatePresence>
        </section>
      </main>

      {/* MENIUL RADIAL EXTERN */}
      <PulseMenu
        showFabMenu={showFabMenu}
        setShowFabMenu={setShowFabMenu}
        setActiveTab={setActiveTab}
        handleCreateFolder={handleCreateFolder}
        handleUpload={handleUpload}
        isSelectionMode={isSelectionMode}
        isUploadDisabled={isSharedPath}
        setShowSearch={setShowSearch}
      />

      <ProfileSecurity
        showProfile={showProfile}
        setShowProfile={setShowProfile}
        userRole={data?.storage_stats?.user_role}
        username={data?.categories?.folders ? currentPath.length === 0 ? localStorage.getItem('token') ? JSON.parse(atob(localStorage.getItem('token').split('.')[1])).sub : "User" : "User" : "User"} // A simple hack to decode username from JWT, or you can just pass the decoded token state if you have it.
        apiUrl={API_URL}
      />

      <FolderSelector
        isOpen={showFolderSelector}
        onClose={() => setShowFolderSelector(false)}
        folders={data?.categories?.folders || []}
        title={folderActionMode === 'copy' ? 'Copiază în...' : 'Mută în...'}
        onConfirm={folderActionMode === 'copy' ? handleCopyFiles : handleMoveFiles}
      />

      <SearchModal
        isOpen={showSearch}
        onClose={() => setShowSearch(false)}
        API_URL={API_URL}
        onFileSelect={(file, username) => {
          setSelectedPreview({
            ...file,
            username: username
          });
          setShowViewer(true);
        }}
      />

      {/* MODALUL NOU DE SHARE */}
      <AnimatePresence>
        {showShareModal && (
          <ShareModal
            isOpen={showShareModal}
            onClose={() => setShowShareModal(false)}
            selectedFiles={selectedFiles}
            API_URL={API_URL}
          />
        )}
      </AnimatePresence>

      {/* BARA DE ACȚIUNI (Dark Frosted Glass - Fără margini, Dark Mode) */}
      <AnimatePresence>
        {isSelectionMode && (
          <motion.div
            initial={{ y: 100, opacity: 0, scale: 0.95 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 100, opacity: 0, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[60] flex items-center p-1.5 bg-black/40 backdrop-blur-xl rounded-full shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
          >
            {/* Counter Badge - Subtil */}
            <div className="flex items-center justify-center h-9 px-4 bg-white/5 rounded-full text-slate-200 font-medium text-xs mx-1">
              {selectedFiles.length}
            </div>

            <div className="w-px h-5 bg-white/10 mx-2" />

            {/* Butoane Acțiuni Standard - Muted */}
            <div className="flex items-center gap-1">
              {[
                { icon: Share2, title: "Partajează", onClick: () => setShowShareModal(true), disabled: selectedFiles.length === 0 },
                { icon: Loader, title: "Descarcă ZIP", onClick: handleBulkDownload, disabled: isZipping || selectedFiles.length === 0, isLoader: true },
                { icon: Copy, title: "Copiază", onClick: () => { setFolderActionMode('copy'); setShowFolderSelector(true); }, disabled: selectedFiles.length === 0 || selectedHasSharedItems },
                { icon: MoveHorizontal, title: "Mută", onClick: () => { setFolderActionMode('move'); setShowFolderSelector(true); }, disabled: selectedFiles.length === 0 || selectedHasSharedItems },
                { icon: Edit3, title: "Redenumește Folder", onClick: handleRenameFolder, disabled: !selectedFolder },
              ].map((btn, index) => (
                <button
                  key={index}
                  onClick={btn.onClick}
                  disabled={btn.disabled}
                  title={btn.title}
                  className="w-10 h-10 flex items-center justify-center rounded-full text-slate-400 hover:bg-white/10 hover:text-white transition-all disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  {btn.isLoader && isZipping ? (
                    <Loader className="animate-spin" size={18} />
                  ) : btn.isLoader ? (
                    <Download size={18} />
                  ) : (
                    <btn.icon size={18} />
                  )}
                </button>
              ))}
            </div>

            <div className="w-px h-5 bg-white/10 mx-2" />

            {/* Ștergere - Roșu stins */}
            <button
              onClick={handleBulkDelete}
              disabled={selectedFiles.length === 0 || selectedHasSharedItems}
              className="w-10 h-10 flex items-center justify-center rounded-full text-rose-500/70 hover:bg-rose-500/20 hover:text-rose-400 transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
              title="Șterge"
            >
              <Trash2 size={18} />
            </button>

            <div className="w-px h-5 bg-white/10 mx-2" />

            {/* Anulare (X) */}
            <button
              onClick={() => { setIsSelectionMode(false); setSelectedFiles([]); }}
              className="w-10 h-10 flex items-center justify-center rounded-full bg-white/5 text-slate-400 hover:bg-white/20 hover:text-white transition-all mr-1"
              title="Anulează selecția"
            >
              <X size={18} />
            </button>

          </motion.div>
        )}
      </AnimatePresence>

     {/* BARA DE PROGRES PENTRU UPLOAD (Stil Dark Frosted Glass) */}
      <AnimatePresence>
        {uploading && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="fixed bottom-6 left-4 right-24 sm:bottom-8 sm:left-8 sm:right-auto z-[100] sm:w-72 bg-black/40 backdrop-blur-xl rounded-2xl p-3 sm:p-4 shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
          >
            <div className="flex items-center gap-3 mb-2 sm:mb-3">
              {/* Iconița muted, fără culori țipătoare */}
              <div className="p-2 bg-white/5 text-slate-300 rounded-xl animate-pulse shrink-0">
                <CloudUpload size={20} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-end mb-0.5">
                  <h4 className="text-[10px] sm:text-[11px] font-bold text-slate-200 tracking-widest uppercase truncate">Se încarcă</h4>
                  {uploadTotal > 0 && (
                     <span className="text-[8px] sm:text-[9px] text-slate-400 font-mono tracking-wider shrink-0 ml-2">
                       {formatBytes(uploadLoaded)} / {formatBytes(uploadTotal)}
                     </span>
                  )}
                </div>
                <p className="text-[9px] sm:text-[10px] text-slate-500 font-mono">{progress}% finalizat</p>
              </div>
            </div>
            
            {/* Bara de progres fină */}
            <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-slate-300 shadow-[0_0_10px_rgba(255,255,255,0.2)]"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.1, ease: "linear" }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>


      <AnimatePresence>{showViewer && <FileViewer isOpen={showViewer} onClose={() => setShowViewer(false)} currentFile={selectedPreview} allFiles={getFilesToRender()} apiUrl={API_URL} />}</AnimatePresence>

    </div>
  );
};

export default Dashboard;