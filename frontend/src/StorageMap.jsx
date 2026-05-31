import React from 'react';
import { motion } from 'framer-motion';

const planetVariants = {
  animate: (speed) => ({
    rotate: [0, 360],
    transition: { duration: speed, ease: "linear", repeat: Infinity },
  }),
};

const StorageMap = ({ freeGb, totalGb, percentUsed }) => {
  return (
    // AM TĂIAT DIN PY-16 ȘI MB-12 PENTRU A ADUCE CONȚINUTUL MAI SUS
    <div className="relative flex justify-center pt-4 pb-2 mb-2">
      <motion.div
        initial={{ scale: 0, rotate: -180, opacity: 0 }}
        animate={{ scale: 1.005, rotate: 0, opacity: 1 }}
        transition={{ duration: 1.8, ease: [0.19, 1, 0.22, 1] }}
        // AM MICȘORAT PUȚIN SFERA PE TELEFON CA SĂ OCUPE MAI PUȚIN SPAȚIU
        className="relative w-64 h-64 md:w-72 md:h-72 flex flex-col items-center justify-center text-center transform-gpu preserve-3d"
        style={{ WebkitBackfaceVisibility: 'hidden', backfaceVisibility: 'hidden' }}
      >
        {/* FUNDAL NEBULA SUBTIL */}
        <div className="absolute inset-4 rounded-full bg-[radial-gradient(circle_at_center,theme(colors.teal.500/3%)_0%,theme(colors.rose.500/2%)_50%,transparent_100%)] blur-2xl pointer-events-none" />
        
        {/* ORBITE GEOMETRICE FIXE */}
        <div className="absolute w-[98%] h-[98%] rounded-full border border-white/[0.03] transform-gpu translate-z-0" />
        <div className="absolute w-[80%] h-[80%] rounded-full border border-teal-500/[0.03] transform-gpu translate-z-0" />
        <div className="absolute w-[60%] h-[60%] rounded-full border border-lavender-500/[0.03] transform-gpu translate-z-0" />
        <div className="absolute w-[40%] h-[40%] rounded-full border border-white/5" />
        <div className="absolute w-[20%] h-[20%] rounded-full border border-white/10" />
        
        {/* Linii constelație (SVG) */}
        <svg className="absolute inset-0 w-full h-full text-white/30" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <g transform="translate(15, 15) scale(0.7)">
            <g stroke="currentColor" strokeWidth="0.4">
              <line x1="38" y1="46" x2="65" y2="65" />
              <line x1="65" y1="65" x2="71" y2="50" />
              <line x1="38" y1="46" x2="55" y2="39" />
              <line x1="55" y1="39" x2="71" y2="50" />
              <line x1="55" y1="39" x2="72" y2="36" />
              <line x1="71" y1="50" x2="72" y2="36" />
              <line x1="72" y1="36" x2="82" y2="25" />
              <line x1="65" y1="65" x2="79" y2="54" />
              <line x1="71" y1="50" x2="79" y2="54" />
              <line x1="79" y1="54" x2="92" y2="48" />
              <line x1="65" y1="65" x2="68" y2="76" />
              <line x1="55" y1="39" x2="45" y2="34" />
              <line x1="38" y1="46" x2="38" y2="38" />
              <line x1="38" y1="38" x2="45" y2="34" />
              <line x1="38" y1="38" x2="13" y2="38" />
              <line x1="45" y1="34" x2="45" y2="20" />
              <line x1="45" y1="20" x2="40" y2="21" />
              <line x1="40" y1="21" x2="23" y2="10" />
              <line x1="23" y1="10" x2="16" y2="6" />
              <line x1="14" y1="38" x2="4" y2="47" />
              <line x1="4" y1="47" x2="5" y2="68" />
              <line x1="5" y1="68" x2="9" y2="87" />
              <line x1="9" y1="87" x2="25" y2="85" />
              <line x1="9" y1="87" x2="15" y2="98" />
            </g>
            <g fill="currentColor">
              <circle cx="38" cy="46" r="0.8" />
              <circle cx="65" cy="65" r="1.2" fill="white" className="animate-pulse" />
              <circle cx="71" cy="50" r="0.8" />
              <circle cx="55" cy="39" r="0.8" />
              <circle cx="72" cy="36" r="0.8" />
              <circle cx="82" cy="25" r="0.7" />
              <circle cx="79" cy="54" r="0.8" />
              <circle cx="92" cy="48" r="0.7" />
              <circle cx="68" cy="76" r="0.7" />
              <circle cx="45" cy="34" r="0.8" />
              <circle cx="38" cy="38" r="0.7" />
              <circle cx="45" cy="20" r="0.6" />
              <circle cx="23" cy="10" r="0.7" />
              <circle cx="4" cy="47" r="0.6" />
              <circle cx="9" cy="87" r="0.7" />
              <circle cx="25" cy="85" r="0.6" />
              <circle cx="15" cy="98" r="0.6" />
            </g>
          </g>
        </svg>

        {/* SATELIȚI */}
        <motion.div variants={planetVariants} animate="animate" custom={30} className="absolute w-[80%] h-[80%]">
          <div className="w-1.5 h-1.5 rounded-full bg-rose-300 shadow-[0_0_8px_theme(colors.rose.300)]" style={{ top: '20%', left: '80%', position: 'absolute' }} />
        </motion.div>
        <motion.div variants={planetVariants} animate="animate" custom={15} className="absolute w-[60%] h-[60%]">
          <div className="w-1 h-1 rounded-full bg-teal-300 shadow-[0_0_8px_theme(colors.teal.300)]" style={{ top: '60%', left: '5%', position: 'absolute' }} />
        </motion.div>

        {/* PROGRES CIRCULAR (Inelul de cotă) */}
        <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="0.5" fill="transparent" className="text-white/5" />
          <motion.circle
            cx="50" cy="50" r="45" stroke="currentColor" strokeWidth="0.50" fill="transparent" strokeLinecap="round"
            strokeDasharray="282.7"
            initial={{ strokeDashoffset: 282.7 }}
            animate={{ strokeDashoffset: 282.7 - (282.7 * percentUsed) / 100 }}
            transition={{ duration: 2, ease: "easeOut", delay: 1 }}
            className="text-teal-500/40 shadow-[0_0_10px_theme(colors.teal.500/20%)]"
          />
        </svg>

        {/* DATELE TEXTUALE */}
        <div className="z-10 mt-2">
          <span className="block text-[10px] uppercase tracking-[0.4em] text-teal-400 mb-2">Liber</span>
          {/* AM FĂCUT TEXTUL O IDEE MAI MIC (de la text-5xl la text-4xl) */}
          <span className="text-4xl font-extralight text-white tracking-tighter shadow-none">{freeGb}</span>
          <span className="block text-lg font-extralight text-white/70">GB</span>
          <span className="block text-[10px] text-slate-500 mt-2 uppercase tracking-[0.2em]">din {totalGb} GB</span>
        </div>
      </motion.div>
    </div>
  );
};

export default StorageMap;