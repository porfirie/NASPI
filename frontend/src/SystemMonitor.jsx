import React, { useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Cpu, HardDrive, Network, BrainCircuit, Terminal, Pause, Play, Square, MemoryStick, Thermometer, ArrowUp, ArrowDown, Users } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL;

// --- COMPONENTA PRINCIPALĂ (Conectată la Backend) ---
const SystemMonitor = ({ stats }) => {
  const [activeTab, setActiveTab] = useState('hardware');

  // Funcție reală pentru a trimite comenzi la backend
  const sendAiCommand = async (action) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/ai/control`, { action }, {
        headers: { Authorization: `Bearer ${token}` }
      });
    } catch (err) {
      console.error("Eroare la controlul AI:", err);
    }
  };

  // Butoanele folosesc statusul real primit prin WebSocket
  const toggleAiPause = () => {
    if (stats?.ai_status === 'running') sendAiCommand('pause');
    else sendAiCommand('play');
  };
  
  const stopAi = () => sendAiCommand('stop');

  // Culori dinamice pentru log-uri
  const getLogColor = (level) => {
    if (level === 'success') return 'text-teal-400';
    if (level === 'warning') return 'text-amber-400';
    if (level === 'error') return 'text-rose-400';
    return 'text-sky-300'; // info
  };

  // Afișăm loading dacă datele lipsesc (inclusiv lipsa statisticilor initiale)
  if (!stats || stats.cpu === undefined) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-500 font-mono text-xs animate-pulse gap-4">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }} className="w-8 h-8 border-t border-teal-500 rounded-full" />
        <p className="text-[10px] tracking-[0.4em] uppercase text-teal-500">Se scanează hardware-ul...</p>
      </div>
    );
  }

  // Extragem starea reală a AI-ului din stats (cu fallback în caz că nu a venit încă nimic)
  const aiStatus = stats.ai_status || 'stopped';
  const aiQueue = stats.ai_queue || 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-5xl mx-auto w-full"
    >
      {/* HEADER & TABS - Stil Glassy */}
      <div className="flex items-center justify-between sm:justify-start gap-3 mb-6 pb-2 overflow-x-auto no-scrollbar border-b border-white/5">
        <TabButton active={activeTab === 'hardware'} onClick={() => setActiveTab('hardware')} icon={Activity} label="Hardware" />
        <TabButton active={activeTab === 'ai'} onClick={() => setActiveTab('ai')} icon={BrainCircuit} label="AI Engine" />
        <TabButton active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} icon={Terminal} label="Jurnal Live" />
      </div>

      {/* CONȚINUTUL TAB-URILOR */}
      <div className="relative min-h-[300px]">
        <AnimatePresence mode="wait">
          
          {/* TAB 1: HARDWARE */}
          {activeTab === 'hardware' && (
            <motion.div key="hardware" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: 0.2 }} className="flex flex-col gap-6">
              
              {/* RÂNDUL 1: Carduri Hardware Compacte (CPU, RAM, DISK, TEMP) */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard 
                  icon={Cpu} 
                  label="Procesor" 
                  value={`${stats.cpu}%`} 
                  sub={`Stabil`} 
                />
                <StatCard 
                  icon={MemoryStick} 
                  label="Memorie RAM" 
                  value={`${stats.ram_percent}%`} 
                  sub={`${stats.ram_used_gb} / ${stats.ram_total_gb} GB`} 
                />
                <StatCard 
                  icon={HardDrive} 
                  label="Stocare" 
                  value={`${stats.disk_percent}%`} 
                  sub={`${stats.disk_used_gb} / ${stats.disk_total_gb} GB`} 
                />
                <StatCard 
                  icon={Thermometer} 
                  label="Termal" 
                  value={stats.temp > 0 ? `${stats.temp}°C` : 'N/A'} 
                  sub="Temp. CPU" 
                />
              </div>

              {/* RÂNDUL 2: Carduri de Rețea & Conexiuni */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Trafic Rețea */}
                <div className="bg-black/40 backdrop-blur-xl border border-white/5 rounded-2xl p-6 flex items-center justify-between relative overflow-hidden group shadow-[0_8px_32px_rgba(0,0,0,0.3)]">
                  <div className="absolute right-[-10%] top-[-10%] opacity-5 group-hover:scale-110 transition-transform duration-700">
                    <Activity size={120} />
                  </div>
                  <div className="relative z-10 w-full">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-6 font-bold">Trafic Rețea Live</p>
                    <div className="flex justify-between md:justify-start gap-8">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white/5 border border-white/10 rounded-full">
                          <ArrowUp className="text-teal-400/80" size={16} />
                        </div>
                        <div>
                          <p className="text-xl text-slate-200 font-light">{stats.up_speed}</p>
                          <p className="text-[8px] text-teal-400/50 uppercase tracking-widest">KB/s OUT</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white/5 border border-white/10 rounded-full">
                          <ArrowDown className="text-indigo-400/80" size={16} />
                        </div>
                        <div>
                          <p className="text-xl text-slate-200 font-light">{stats.down_speed}</p>
                          <p className="text-[8px] text-indigo-400/50 uppercase tracking-widest">KB/s IN</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Conexiuni WebSocket */}
                <div className="bg-black/40 backdrop-blur-xl border border-white/5 rounded-2xl p-6 flex items-center justify-between relative overflow-hidden group shadow-[0_8px_32px_rgba(0,0,0,0.3)] hover:bg-black/50 transition-colors">
                  <div className="absolute right-[-5%] top-0 opacity-5 group-hover:scale-110 transition-transform duration-700">
                    <Users size={120} />
                  </div>
                  <div className="relative z-10">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-6 font-bold">Conexiuni Active</p>
                    <div className="flex items-center gap-4">
                      <span className="text-5xl text-slate-200 font-light tracking-tighter">
                        {stats.active_connections}
                      </span>
                      <div className="flex flex-col">
                        <span className="text-[10px] text-teal-400/80 uppercase tracking-widest font-bold">WebSocket</span>
                        <span className="text-[9px] text-slate-500 uppercase tracking-widest truncate">Teste Stres</span>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </motion.div>
          )}

          {/* TAB 2: AI ENGINE (Conectat real la backend) */}
          {activeTab === 'ai' && (
            <motion.div key="ai" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: 0.2 }} className="flex flex-col gap-4">
              {/* Status Header */}
              <div className="bg-black/40 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.3)] flex items-center justify-between hover:bg-black/50 transition-colors">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl bg-white/5 ${aiStatus === 'running' ? 'text-teal-400 animate-pulse' : aiStatus === 'paused' ? 'text-amber-400' : 'text-slate-500'}`}>
                    <BrainCircuit size={24} />
                  </div>
                  <div>
                    <h3 className="text-slate-200 text-xs sm:text-sm font-bold uppercase tracking-widest">Motor Inteligență Artificială</h3>
                    <p className="text-slate-400 text-[10px] sm:text-xs mt-1 font-mono">
                      Status: <span className={aiStatus === 'running' ? 'text-teal-400/80' : ''}>{aiStatus === 'running' ? 'Activ & Procesează' : aiStatus === 'paused' ? 'În Pauză' : 'Inactiv'}</span>
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Control Panel */}
                <div className="bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.3)] flex flex-col justify-center gap-5">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold text-center sm:text-left">Comenzi Sistem</span>
                  <div className="flex items-center justify-center sm:justify-start gap-4">
                    <button onClick={toggleAiPause} className={`w-14 h-14 flex items-center justify-center rounded-full transition-all border ${aiStatus === 'running' ? 'bg-white/5 border-white/10 text-amber-400 hover:bg-white/10' : 'bg-white/5 border-white/10 text-teal-400 hover:bg-white/10'}`}>
                      {aiStatus === 'running' ? <Pause fill="currentColor" size={20} /> : <Play fill="currentColor" size={20} className="ml-1" />}
                    </button>
                    <button onClick={stopAi} disabled={aiStatus === 'stopped'} className="w-12 h-12 flex items-center justify-center rounded-full bg-white/5 border border-white/10 text-rose-400/80 hover:bg-white/10 hover:text-rose-400 transition-all disabled:opacity-20 disabled:hover:bg-white/5">
                      <Square fill="currentColor" size={16} />
                    </button>
                  </div>
                </div>

                {/* Queue Card */}
                <div className="bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.3)] flex flex-col items-center justify-center">
                  <span className="text-5xl text-slate-200 font-light tracking-tighter">{aiQueue}</span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest mt-3">Fișiere în așteptare</span>
                </div>
              </div>
            </motion.div>
          )}

          {/* TAB 3: JURNAL LIVE (Terminal Real) */}
          {activeTab === 'logs' && (
            <motion.div key="logs" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: 0.2 }} className="bg-black/60 backdrop-blur-2xl border border-white/10 rounded-2xl p-5 h-[340px] overflow-y-auto font-mono text-[10px] sm:text-xs shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-col-reverse">
              {/* Flex col-reverse ține scroll-ul jos la mesajele noi! */}
              <div>
                <div className="text-slate-600 mb-5 border-b border-white/5 pb-3 uppercase tracking-widest text-[9px]">Aether NAS // Jurnal Sistem Live</div>
                
                {/* Iterăm prin array-ul de logs venit din Backend */}
                {stats.logs && stats.logs.length > 0 ? (
                  stats.logs.map((log, index) => (
                    <div key={index} className="flex items-start gap-3 mb-3">
                      <span className="text-slate-500 shrink-0">[{log.time}]</span>
                      <span className={getLogColor(log.level)}>{log.message}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic">Sistemul a fost pornit. Așteptare evenimente...</div>
                )}
                
                <div className="flex items-start gap-3 mt-4">
                  <span className="w-1.5 h-3.5 bg-slate-400 animate-pulse"></span>
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </motion.div>
  );
};

// --- COMPONENTE AJUTĂTOARE ---

const TabButton = ({ active, onClick, icon: Icon, label }) => (
  <button 
    onClick={onClick} 
    className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-[10px] sm:text-xs font-bold tracking-widest uppercase transition-all shrink-0 border ${
      active 
        ? 'bg-black/40 backdrop-blur-xl text-slate-200 border-white/10 shadow-[0_4px_15px_rgba(0,0,0,0.3)]' 
        : 'bg-transparent text-slate-500 border-transparent hover:text-slate-300'
    }`}
  >
    <Icon size={14} className={active ? "text-teal-400/80" : ""} />
    {label}
  </button>
);

const StatCard = ({ icon: Icon, label, value, sub }) => (
  <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl p-4 sm:p-5 flex flex-col shadow-[0_8px_32px_rgba(0,0,0,0.3)] hover:bg-black/50 transition-colors">
    <div className="p-2.5 rounded-xl bg-white/5 text-slate-400 w-fit mb-4">
      <Icon size={18} />
    </div>
    <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1.5">{label}</span>
    <span className="text-lg sm:text-2xl text-slate-200 font-light mb-1.5 tracking-tight">{value}</span>
    <span className="text-[9px] sm:text-[10px] text-slate-500 font-mono truncate">{sub}</span>
  </div>
);

export default SystemMonitor;