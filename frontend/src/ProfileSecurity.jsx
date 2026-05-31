import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User, Lock, Check, AlertCircle, Shield, Users, HardDrive, Edit2, Trash2, ArrowLeft } from 'lucide-react';
import axios from 'axios';

const ProfileSecurity = ({ showProfile, setShowProfile, userRole, apiUrl, username: currentUsername }) => {
  // Views: 'main', 'password', 'username', 'usermgmt'
  const [activeView, setActiveView] = useState('main'); 
  const [status, setStatus] = useState({ type: "", msg: "" });
  const [loading, setLoading] = useState(false);

  // Password State
  const [passData, setPassData] = useState({ old: "", new: "", confirm: "" });
  
  // Username State
  const [newUsername, setNewUsername] = useState("");

  // Admin User Management State
  const [users, setUsers] = useState([]);
  const [editingUserId, setEditingUserId] = useState(null);
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'user', storage_quota_mb: 5000 });

  // Reset everything when modal closes
  const handleClose = () => {
    setShowProfile(false);
    setTimeout(() => {
      setActiveView('main');
      setPassData({ old: "", new: "", confirm: "" });
      setNewUsername("");
      setStatus({ type: "", msg: "" });
      setEditingUserId(null);
    }, 300);
  };

  // --- ACTIONS: SELF ---

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (passData.new !== passData.confirm) return setStatus({ type: "error", msg: "PAROLELE NOI NU COINCID" });
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${apiUrl}/change-password`, 
        { old_password: passData.old, new_password: passData.new }, 
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStatus({ type: "success", msg: "PAROLA A FOST ACTUALIZATĂ" });
      setTimeout(() => setActiveView('main'), 2000);
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "EROARE SERVER" });
    } finally {
      setLoading(false);
    }
  };

  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${apiUrl}/change-username`, 
        { new_username: newUsername }, 
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // Important: Update token so subsequent requests don't fail
      localStorage.setItem('token', res.data.new_token);
      setStatus({ type: "success", msg: "NUMELE A FOST ACTUALIZAT. Vă rugăm să dați refresh paginii." });
      setTimeout(() => window.location.reload(), 2000);
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "EROARE SERVER" });
    } finally {
      setLoading(false);
    }
  };

  // --- ACTIONS: ADMIN USER MGMT ---

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${apiUrl}/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
      setUsers(res.data);
    } catch (err) { setStatus({ type: "error", msg: "Eroare la încărcarea listei" }); }
  };

  // Fetch users automatically when entering the usermgmt view
  useEffect(() => {
    if (activeView === 'usermgmt') fetchUsers();
  }, [activeView]);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${apiUrl}/admin/users`, newUser, { headers: { Authorization: `Bearer ${token}` } });
      setNewUser({ username: '', password: '', role: 'user', storage_quota_mb: 5000 });
      fetchUsers();
    } catch (err) { setStatus({ type: "error", msg: err.response?.data?.detail || "Eroare la creare" }); }
  };

  const handleUpdateUser = async (userId, updatedData) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${apiUrl}/admin/users/${userId}`, updatedData, { headers: { Authorization: `Bearer ${token}` } });
      setEditingUserId(null);
      fetchUsers();
    } catch (err) { alert(err.response?.data?.detail || "Eroare la actualizare"); }
  };

  const handleDeleteUser = async (id) => {
    if (!window.confirm("Ștergi acest utilizator și TOT folderul lui?")) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${apiUrl}/admin/users/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      fetchUsers();
    } catch (err) { alert(err.response?.data?.detail); }
  };

  // --- RENDERING HELPERS ---

  const slideVariants = {
    enter: (direction) => ({ x: direction > 0 ? 50 : -50, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (direction) => ({ x: direction < 0 ? 50 : -50, opacity: 0 })
  };

  if (!showProfile) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] bg-[#0d1117]/98 backdrop-blur-2xl p-4 md:p-8 flex flex-col items-center justify-center overflow-y-auto"
      >
        <button onClick={handleClose} className="absolute top-8 right-8 text-white/30 hover:text-white transition-colors z-10">
          <X size={30} />
        </button>
        
        <div className="w-full max-w-md flex flex-col items-center relative">
          
          {/* TOP ICON (Dynamic based on view) */}
          <motion.div layout className="w-20 h-20 md:w-24 md:h-24 rounded-full border border-teal-500/10 bg-teal-500/5 mb-6 flex items-center justify-center shadow-[0_0_20px_theme(colors.teal.500/10%)] relative overflow-hidden">
             <AnimatePresence mode="wait">
                {activeView === 'main' && <motion.div key="main" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}><User size={32} className="text-teal-500/50" /></motion.div>}
                {activeView === 'password' && <motion.div key="pass" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}><Shield size={32} className="text-rose-500/50" /></motion.div>}
                {activeView === 'username' && <motion.div key="user" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}><Edit2 size={32} className="text-indigo-500/50" /></motion.div>}
                {activeView === 'usermgmt' && <motion.div key="mgmt" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}><Users size={32} className="text-teal-500/50" /></motion.div>}
             </AnimatePresence>
          </motion.div>
          
          <h3 className="text-white/60 tracking-[0.3em] md:tracking-[0.5em] mb-8 uppercase text-[10px] md:text-xs font-bold text-center">
            {activeView === 'main' && "PROFIL UTILIZATOR"}
            {activeView === 'password' && "SCHIMBARE PAROLĂ"}
            {activeView === 'username' && "SCHIMBARE NUME"}
            {activeView === 'usermgmt' && "MANAGEMENT UTILIZATORI"}
          </h3>

          <div className="w-full relative min-h-[300px]">
            <AnimatePresence mode="wait" custom={1}>

              {/* ======================= MAIN MENU VIEW ======================= */}
              {activeView === 'main' && (
                <motion.div key="view-main" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.2 }} className="w-full flex flex-col gap-3">
                  <div className="text-center mb-4">
                    <p className="text-white text-xl">{currentUsername}</p>
                    <p className="text-teal-500 text-[10px] uppercase tracking-widest">{userRole}</p>
                  </div>

                  <button onClick={() => { setActiveView('username'); setStatus({type:"", msg:""}); }} className="w-full py-4 rounded-2xl border border-white/5 bg-white/5 text-[10px] tracking-[0.2em] uppercase text-white hover:bg-white/10 transition-all flex items-center justify-center gap-3">
                    <Edit2 size={14} className="text-indigo-400" /> SCHIMBĂ NUMELE
                  </button>

                  <button onClick={() => { setActiveView('password'); setStatus({type:"", msg:""}); }} className="w-full py-4 rounded-2xl border border-white/5 bg-white/5 text-[10px] tracking-[0.2em] uppercase text-white hover:bg-white/10 transition-all flex items-center justify-center gap-3">
                    <Lock size={14} className="text-rose-400" /> SCHIMBĂ PAROLA
                  </button>
                  
                  {userRole === 'admin' && (
                    <button onClick={() => { setActiveView('usermgmt'); setStatus({type:"", msg:""}); }} className="w-full mt-4 py-4 rounded-2xl border border-teal-500/20 bg-teal-500/5 text-[10px] tracking-[0.2em] uppercase text-teal-400 hover:bg-teal-500/10 transition-all shadow-[0_0_20px_rgba(20,184,166,0.05)] flex items-center justify-center gap-3">
                      <Users size={14} /> GESTIONARE UTILIZATORI
                    </button>
                  )}
                </motion.div>
              )}

              {/* ======================= CHANGE PASSWORD VIEW ======================= */}
              {activeView === 'password' && (
                <motion.form key="view-pass" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.2 }} onSubmit={handlePasswordSubmit} className="w-full space-y-4">
                  <input type="password" placeholder="PAROLA ACTUALĂ" className="w-full bg-white/5 border border-white/5 p-4 rounded-2xl text-[10px] tracking-[0.2em] text-white focus:outline-none focus:border-rose-500/30"
                    value={passData.old} onChange={(e) => setPassData({...passData, old: e.target.value})} required />
                  <div className="h-px w-full bg-gradient-to-r from-transparent via-white/5 to-transparent my-4" />
                  <input type="password" placeholder="PAROLA NOUĂ" className="w-full bg-white/5 border border-white/5 p-4 rounded-2xl text-[10px] tracking-[0.2em] text-white focus:outline-none focus:border-rose-500/30"
                    value={passData.new} onChange={(e) => setPassData({...passData, new: e.target.value})} required />
                  <input type="password" placeholder="CONFIRMĂ PAROLA" className="w-full bg-white/5 border border-white/5 p-4 rounded-2xl text-[10px] tracking-[0.2em] text-white focus:outline-none focus:border-rose-500/30"
                    value={passData.confirm} onChange={(e) => setPassData({...passData, confirm: e.target.value})} required />

                  {status.msg && (
                    <div className={`flex items-center gap-2 p-3 rounded-xl text-[9px] tracking-[0.1em] uppercase font-bold ${status.type === 'error' ? 'bg-rose-500/10 text-rose-400' : 'bg-teal-500/10 text-teal-400'}`}>
                      {status.type === 'error' ? <AlertCircle size={14} /> : <Check size={14} />} {status.msg}
                    </div>
                  )}

                  <div className="flex gap-3 pt-4">
                     <button type="button" onClick={() => setActiveView('main')} className="flex-1 py-4 rounded-2xl bg-white/5 text-white text-[10px] tracking-[0.2em] uppercase font-bold hover:bg-white/10">ÎNAPOI</button>
                     <button type="submit" disabled={loading} className="flex-[2] py-4 rounded-2xl bg-rose-500 text-white text-[10px] tracking-[0.2em] uppercase font-black hover:bg-rose-600">ACTUALIZEAZĂ</button>
                  </div>
                </motion.form>
              )}

              {/* ======================= CHANGE USERNAME VIEW ======================= */}
              {activeView === 'username' && (
                <motion.form key="view-user" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.2 }} onSubmit={handleUsernameSubmit} className="w-full space-y-4">
                  <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 mb-4">
                    <p className="text-[10px] text-indigo-300 leading-relaxed text-center">Modificarea numelui de utilizator va necesita o reautentificare automată a sesiunii.</p>
                  </div>

                  <input type="text" placeholder="NUME DE UTILIZATOR NOU" className="w-full bg-white/5 border border-white/5 p-4 rounded-2xl text-[10px] tracking-[0.2em] text-white focus:outline-none focus:border-indigo-500/30"
                    value={newUsername} onChange={(e) => setNewUsername(e.target.value)} required />

                  {status.msg && (
                    <div className={`flex items-center gap-2 p-3 rounded-xl text-[9px] tracking-[0.1em] uppercase font-bold ${status.type === 'error' ? 'bg-rose-500/10 text-rose-400' : 'bg-indigo-500/10 text-indigo-400'}`}>
                      {status.type === 'error' ? <AlertCircle size={14} /> : <Check size={14} />} {status.msg}
                    </div>
                  )}

                  <div className="flex gap-3 pt-4">
                     <button type="button" onClick={() => setActiveView('main')} className="flex-1 py-4 rounded-2xl bg-white/5 text-white text-[10px] tracking-[0.2em] uppercase font-bold hover:bg-white/10">ÎNAPOI</button>
                     <button type="submit" disabled={loading} className="flex-[2] py-4 rounded-2xl bg-indigo-500 text-white text-[10px] tracking-[0.2em] uppercase font-black hover:bg-indigo-600">SCHIMBĂ NUMELE</button>
                  </div>
                </motion.form>
              )}

              {/* ======================= USER MANAGEMENT VIEW ======================= */}
              {activeView === 'usermgmt' && (
                <motion.div key="view-mgmt" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.2 }} className="w-full flex flex-col gap-6 w-[90vw] max-w-2xl">
                  
                  <button onClick={() => setActiveView('main')} className="flex items-center gap-2 text-slate-500 hover:text-white text-xs tracking-widest uppercase transition-colors self-start mb-2">
                    <ArrowLeft size={16} /> Înapoi la Profil
                  </button>

                  {status.msg && (
                    <div className="p-3 rounded-xl bg-rose-500/10 text-rose-400 text-[10px] text-center border border-rose-500/20">{status.msg}</div>
                  )}

                  {/* CREATE NEW USER FORM */}
                  <form onSubmit={handleCreateUser} className="bg-white/5 p-4 md:p-6 rounded-3xl border border-white/5">
                    <h4 className="text-[10px] text-teal-500 tracking-widest uppercase mb-4 font-bold">Adaugă Utilizator</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <input type="text" placeholder="USERNAME" className="bg-black/40 border border-white/5 p-3 rounded-xl text-xs text-white outline-none focus:border-teal-500/30"
                        value={newUser.username} onChange={e => setNewUser({...newUser, username: e.target.value})} required />
                      <input type="password" placeholder="PAROLĂ INITIALĂ" className="bg-black/40 border border-white/5 p-3 rounded-xl text-xs text-white outline-none focus:border-teal-500/30"
                        value={newUser.password} onChange={e => setNewUser({...newUser, password: e.target.value})} required />
                      
                      <select className="bg-black/40 border border-white/5 p-3 rounded-xl text-[10px] uppercase text-white outline-none"
                        value={newUser.role} onChange={e => setNewUser({...newUser, role: e.target.value})}>
                        <option value="user">USER NORMAL</option>
                        <option value="admin">ADMIN</option>
                      </select>

                      <select className="bg-black/40 border border-white/5 p-3 rounded-xl text-[10px] uppercase text-teal-400 outline-none"
                        value={newUser.storage_quota_mb} onChange={e => setNewUser({...newUser, storage_quota_mb: parseInt(e.target.value)})}>
                        <option value="2000">2 GB</option>
                        <option value="5000">5 GB (Standard)</option>
                        <option value="15000">15 GB</option>
                        <option value="50000">50 GB</option>
                        <option value="999999">Nelimitat</option>
                      </select>
                    </div>
                    <button type="submit" className="w-full py-3 mt-4 bg-teal-500/20 text-teal-400 hover:bg-teal-500 hover:text-black transition-all rounded-xl text-[10px] font-black uppercase tracking-widest">
                      Crează Cont
                    </button>
                  </form>

                  {/* USER LIST & EDITING */}
                  <div className="space-y-3 overflow-y-auto max-h-[40vh] pr-2 no-scrollbar">
                    {users.map(u => (
                      <div key={u.id} className="flex flex-col p-4 bg-black/40 border border-white/5 rounded-2xl gap-3">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-3">
                            {u.role === 'admin' ? <Shield size={16} className="text-teal-500" /> : <User size={16} className="text-slate-500" />}
                            <span className="text-xs font-bold text-white uppercase tracking-wide">{u.username}</span>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            {editingUserId !== u.id && (
                              <button onClick={() => setEditingUserId(u.id)} className="p-2 bg-white/5 rounded-lg text-slate-400 hover:text-white transition-all"><Edit2 size={14}/></button>
                            )}
                            <button onClick={() => handleDeleteUser(u.id)} className="p-2 bg-rose-500/10 rounded-lg text-rose-500 hover:bg-rose-600 hover:text-white transition-all"><Trash2 size={14}/></button>
                          </div>
                        </div>

                        {/* EDIT MODE EXPANDED */}
                        <AnimatePresence>
                          {editingUserId === u.id ? (
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="pt-2 border-t border-white/5 overflow-hidden">
                               <div className="flex flex-col md:flex-row gap-2">
                                  <select 
                                    className="flex-1 bg-black/60 border border-white/5 p-2 rounded-lg text-[10px] uppercase text-slate-300 outline-none"
                                    defaultValue={u.role}
                                    onChange={(e) => handleUpdateUser(u.id, { role: e.target.value, storage_quota_mb: u.storage_quota_mb })}
                                  >
                                    <option value="user">Rol: USER</option>
                                    <option value="admin">Rol: ADMIN</option>
                                  </select>
                                  <select 
                                    className="flex-1 bg-black/60 border border-white/5 p-2 rounded-lg text-[10px] uppercase text-teal-400 outline-none"
                                    defaultValue={u.storage_quota_mb}
                                    onChange={(e) => handleUpdateUser(u.id, { role: u.role, storage_quota_mb: parseInt(e.target.value) })}
                                  >
                                    <option value="500">Spațiu: 500 MB</option>
                                    <option value="2000">Spațiu: 2 GB</option>
                                    <option value="5000">Spațiu: 5 GB</option>
                                    <option value="15000">Spațiu: 15 GB</option>
                                    <option value="999999">Spațiu: Nelimitat</option>
                                  </select>
                               </div>
                               <button onClick={() => setEditingUserId(null)} className="w-full mt-2 py-2 text-[10px] uppercase tracking-widest text-slate-500 hover:text-white">Închide Editarea</button>
                            </motion.div>
                          ) : (
                            /* NORMAL MODE DETAILS */
                            <div className="flex items-center gap-4 text-[9px] uppercase tracking-wider text-slate-500 ml-7">
                              <span>Rol: {u.role}</span>
                              <div className="flex items-center gap-1"><HardDrive size={10} /> {u.storage_quota_mb > 100000 ? 'Nelimitat' : `${(u.storage_quota_mb / 1024).toFixed(1)} GB`}</div>
                            </div>
                          )}
                        </AnimatePresence>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

            </AnimatePresence>
          </div>

          <p className="text-[9px] text-slate-700 uppercase tracking-[0.2em] mt-8 text-center absolute -bottom-12">Aether Pi NAS Server</p>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ProfileSecurity;