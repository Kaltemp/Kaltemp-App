import React from 'react';

interface KaltempLogoKProps {
  isSyncing?: boolean; // Pásalo en true cuando el sync_master esté activo
  onClick?: () => void;
}

export const KaltempLogoK: React.FC<KaltempLogoKProps> = ({ isSyncing = false, onClick }) => {
  return (
    <button
      onClick={onClick}
      title="Kaltemp Dashboard"
      className="relative group flex items-center justify-center p-1 rounded-full outline-none focus:ring-2 focus:ring-[#CC0000]/50 transition-transform active:scale-95"
    >
      {/* 1. ANILLO CÓNICO ANIMADO (Ajustado para Fondo Blanco y Oscuro) */}
      <div
        className={`absolute -inset-[3px] rounded-full opacity-90 group-hover:opacity-100 transition-all duration-500 ${
          isSyncing ? 'animate-spin duration-700' : 'animate-spin'
        }`}
        style={{
          animationDuration: isSyncing ? '1.5s' : '8s',
          background: 'conic-gradient(from 0deg, #CC0000 0%, #0284C7 35%, #38BDF8 50%, #1E293B 75%, #CC0000 100%)',
          filter: 'drop-shadow(0px 2px 4px rgba(0, 0, 0, 0.15))' // Le da borde oscuro sobre fondo blanco
        }}
      />

      {/* 2. AURA LUMINOSA (Para Fondo Oscuro) */}
      <div 
        className="absolute -inset-[2px] rounded-full bg-[#00F0FF]/30 dark:bg-[#00F0FF]/40 blur-[4px] group-hover:blur-[8px] transition-all duration-300 opacity-60 group-hover:opacity-100"
      />

      {/* 3. CÍRCULO PRINCIPAL ROJO (Con relieve Glassmorphism) */}
      <div className="relative w-10 h-10 rounded-full bg-gradient-to-b from-[#E60000] via-[#CC0000] to-[#990000] flex items-center justify-center shadow-[0_3px_8px_rgba(0,0,0,0.25)] border border-white/30 overflow-hidden">
        
        {/* Reflejo Curvo Superior (Efecto Cristal) */}
        <div className="absolute top-0 left-0 right-0 h-[45%] bg-gradient-to-b from-white/35 to-transparent rounded-t-full pointer-events-none" />

        {/* BARRIDO METÁLICO INTERACTIVO (WOW Effect al hacer Hover / Sync) */}
        <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full bg-gradient-to-r from-transparent via-white/50 to-transparent transition-transform duration-1000 ease-in-out pointer-events-none" />

        {/* 4. LETRA 'K' CON SOMBRA TIPOGRÁFICA DEFINIDA */}
        <span className="relative z-10 text-white font-black text-xl tracking-wider select-none drop-shadow-[0_2px_3px_rgba(0,0,0,0.4)]">
          K
        </span>
      </div>

      {/* 5. INDICADOR PULSANTE DE SINCRONIZACIÓN (Badge KPI Activo) */}
      {isSyncing && (
        <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-sky-500 border-2 border-white"></span>
        </span>
      )}
    </button>
  );
};