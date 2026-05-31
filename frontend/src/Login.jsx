import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Lock, User, ArrowRight } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

const Login = ({ setToken }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await axios.post(`${API_URL}/login`, formData);
      const token = response.data.access_token;
      localStorage.setItem('token', token);
      setToken(token);
    } catch (err) {
      setError('Identitate necunoscută sau parolă invalidă.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d1117] px-4 overflow-hidden relative">
      
      {/* 1. FUNDAL DECORATIV (Stil Nebula / Star Map) */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-teal-500/5 rounded-full blur-[120px]" />
        <div className="absolute top-1/4 left-1/3 w-[300px] h-[300px] bg-rose-500/5 rounded-full blur-[100px]" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, ease: [0.19, 1, 0.22, 1] }}
        className="w-full max-w-sm relative z-10"
      >
        {/* 2. LOGO & TITLU */}
        <div className="flex flex-col items-center mb-12">
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.5, type: "spring", stiffness: 100 }}
            className="w-16 h-16 rounded-3xl border border-teal-500/20 bg-teal-500/5 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(20,184,166,0.1)]"
          >
            <Shield size={28} className="text-teal-500/70" />
          </motion.div>
          <h2 className="text-[10px] font-black text-white/30 tracking-[0.8em] uppercase">
            Aether NAS
          </h2>
        </div>

        {/* 3. CARDUL DE LOGIN */}
        <div className="p-8 rounded-[40px] bg-[#161b22]/50 backdrop-blur-3xl border border-white/5 shadow-2xl">
          <form onSubmit={handleLogin} className="space-y-5">
            
            <div className="space-y-1">
              <label className="text-[8px] uppercase tracking-[0.3em] text-slate-500 ml-4">Utilizator</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600" size={16} />
                <input 
                  type="text" 
                  required
                  className="w-full bg-white/5 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-white outline-none focus:border-teal-500/30 focus:bg-white/[0.07] transition-all"
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[8px] uppercase tracking-[0.3em] text-slate-500 ml-4">Parolă</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600" size={16} />
                <input 
                  type="password" 
                  required
                  className="w-full bg-white/5 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm text-white outline-none focus:border-teal-500/30 focus:bg-white/[0.07] transition-all"
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <AnimatePresence>
              {error && (
                <motion.p 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="text-rose-400/80 text-[10px] text-center uppercase tracking-widest"
                >
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            <button 
              type="submit"
              disabled={isSubmitting}
              className="w-full group relative bg-teal-500 hover:bg-teal-400 text-[#0d1117] font-bold py-4 rounded-2xl transition-all shadow-[0_0_20px_rgba(20,184,166,0.3)] active:scale-95 flex items-center justify-center overflow-hidden"
            >
              <span className="text-[10px] uppercase tracking-[0.2em] relative z-10">
                {isSubmitting ? 'Verificare...' : 'Autorizare'}
              </span>
              {!isSubmitting && (
                <ArrowRight size={16} className="ml-2 relative z-10 group-hover:translate-x-1 transition-transform" />
              )}
              
              {/* Efect de reflexie pe buton */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            </button>
          </form>
        </div>


      </motion.div>
    </div>
  );
};

export default Login;