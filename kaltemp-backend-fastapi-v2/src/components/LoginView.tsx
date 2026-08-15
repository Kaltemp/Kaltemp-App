// GUARDAR EN: (misma ruta donde vive tu LoginView.tsx actual)
// Actualizado 13-ago-2026: nuevo diseño de login "Acceso a Analítica" con
// isotipo A (fusión Kaltemp/Tom Palmer) y doble marca al pie, aprobado a
// nivel gerencial. Reemplaza el look claro/oscuro anterior por una portada
// de marca fija con degradé cálido->frío (independiente del ThemeMode).

import React, { useState } from 'react';
import { Lock, User, Eye, EyeOff, ShieldCheck, ArrowRight, Sun, Moon } from 'lucide-react';
import { ThemeMode } from '../types';
import { useUser } from '../context/UserContext';

// Logo real de Kaltemp (07-ago-2026). Ya no se usa en esta pantalla -- el
// isotipo A vectorial de abajo reemplaza el ícono de marca en el login --
// pero se deja la constante por si se reutiliza en Sidebar/Header.
// const KALTEMP_LOGO_CONDENSADO = 'https://cdn.shopify.com/s/files/1/0656/1605/2459/files/Logo_Kaltemp_Condensado.png?v=1786109942';

interface LoginViewProps {
  theme: ThemeMode;
  onThemeToggle: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({
  theme,
  onThemeToggle,
}) => {
  const isDark = theme === 'dark';
  const { login } = useUser();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username.trim()) {
      setError('Por favor ingresa tu usuario o correo electrónico.');
      return;
    }
    if (!password) {
      setError('Por favor ingresa tu contraseña.');
      return;
    }

    setIsLoading(true);
    try {
      await login(username.trim().toLowerCase(), password);
      // No hay más que hacer acá: App.tsx re-renderiza automáticamente
      // apenas currentUser deja de ser null.
    } catch (err: any) {
      setError(err?.message || 'Correo o contraseña incorrectos.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center px-4 py-10 relative overflow-hidden"
      style={{
        background:
          'linear-gradient(135deg, #C4400E 0%, #E8791A 28%, #4b4650 50%, #1D6FA5 72%, #0F4C81 100%)',
      }}
    >
      {/* Resplandores decorativos cálido/frío en las esquinas */}
      <div
        className="absolute -top-32 -left-32 w-[420px] h-[420px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(255,140,60,0.45), transparent 70%)' }}
      />
      <div
        className="absolute -bottom-32 -right-32 w-[420px] h-[420px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(60,160,255,0.45), transparent 70%)' }}
      />

      {/* Toggle de tema -- se mantiene por consistencia con el resto de la
          app (afecta el tema una vez adentro); esta pantalla de portada no
          cambia de look con él, a pedido de William (13-ago-2026). */}
      <button
        onClick={onThemeToggle}
        className="absolute top-5 right-5 p-2 rounded-xl border border-white/20 bg-white/10 text-white hover:bg-white/20 transition-all backdrop-blur-sm"
        title={isDark ? 'Modo claro' : 'Modo oscuro'}
      >
        {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>

      {/* Tarjeta de vidrio */}
      <div
        className="relative w-full max-w-[400px] rounded-[22px] border border-white/[0.16] p-8 pb-7"
        style={{
          background: 'rgba(20,18,22,0.5)',
          backdropFilter: 'blur(18px)',
          WebkitBackdropFilter: 'blur(18px)',
          boxShadow: '0 30px 70px rgba(0,0,0,0.45)',
        }}
      >
        {/* Isotipo A -- trazo izquierdo Kaltemp, trazo derecho Tom Palmer */}
        <div className="flex justify-center mb-4">
          <div
            className="w-[68px] h-[68px] rounded-[18px] flex items-center justify-center border border-white/[0.18]"
            style={{
              background: 'rgba(255,255,255,0.07)',
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.15), 0 10px 24px rgba(0,0,0,0.35)',
            }}
          >
            <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
              <defs>
                <linearGradient id="loginStrokeWarm" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F2954A" />
                  <stop offset="100%" stopColor="#C4400E" />
                </linearGradient>
                <linearGradient id="loginStrokeCool" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4FA8DE" />
                  <stop offset="100%" stopColor="#0F4C81" />
                </linearGradient>
                <linearGradient id="loginStrokeBar" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#E8791A" />
                  <stop offset="100%" stopColor="#1D6FA5" />
                </linearGradient>
              </defs>
              <path d="M50 12 L20 88" stroke="url(#loginStrokeWarm)" strokeWidth="11" strokeLinecap="round" />
              <path d="M50 12 L80 88" stroke="url(#loginStrokeCool)" strokeWidth="11" strokeLinecap="round" />
              <path d="M33 63 L67 63" stroke="url(#loginStrokeBar)" strokeWidth="9" strokeLinecap="round" />
            </svg>
          </div>
        </div>

        <h1 className="text-center text-white text-[22px] font-extrabold tracking-tight">
          Acceso a Analítica
        </h1>
        <p className="text-center text-white/65 text-[11.5px] font-medium mt-1">
          Plataforma de Business Intelligence &amp; Control Operativo
        </p>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="mt-2">
          {error && (
            <div className="mt-5 p-3 rounded-xl bg-red-500/15 border border-red-400/30 text-red-100 text-xs font-semibold animate-shake">
              {error}
            </div>
          )}

          {/* Usuario / Correo */}
          <label className="block text-white/75 text-[10.5px] font-bold uppercase tracking-wider mt-5 mb-1.5">
            Usuario / Correo
          </label>
          <div className="flex items-center gap-2.5 bg-white/[0.08] border border-white/[0.18] rounded-xl px-3.5 py-2.5">
            <User className="w-[15px] h-[15px] text-white/60 flex-shrink-0" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ejemplo@kaltemp.cl"
              autoComplete="username"
              className="bg-transparent border-none outline-none text-white text-sm w-full placeholder:text-white/40"
            />
          </div>

          {/* Contraseña */}
          <label className="block text-white/75 text-[10.5px] font-bold uppercase tracking-wider mt-5 mb-1.5">
            Contraseña
          </label>
          <div className="flex items-center gap-2.5 bg-white/[0.08] border border-white/[0.18] rounded-xl px-3.5 py-2.5">
            <Lock className="w-[15px] h-[15px] text-white/60 flex-shrink-0" />
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              className="bg-transparent border-none outline-none text-white text-sm w-full placeholder:text-white/40"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="text-white/50 hover:text-white/80 flex-shrink-0"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {/* Recordar sesión */}
          <div className="flex items-center justify-between mt-4">
            <label className="flex items-center gap-2 cursor-pointer select-none text-white/70 text-[11.5px]">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-white/30 accent-[#E8791A]"
              />
              Recordar sesión
            </label>
          </div>

          {/* Botón submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-6 h-[46px] rounded-xl text-white font-bold text-[13.5px] flex items-center justify-center gap-2 transition-all active:scale-[0.99] disabled:opacity-70"
            style={{
              background: 'linear-gradient(90deg, #E8791A 0%, #C4400E 45%, #1D6FA5 100%)',
              boxShadow: '0 10px 24px rgba(196,64,14,0.35)',
            }}
          >
            {isLoading ? (
              <span>Validando credenciales...</span>
            ) : (
              <>
                <span>Iniciar Sesión</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Separador de marcas */}
        <div className="flex items-center gap-2.5 mt-6 mb-4">
          <div className="flex-1 h-px bg-white/15" />
          <span className="text-white/40 text-[9.5px] uppercase tracking-widest">
            Plataforma compartida por
          </span>
          <div className="flex-1 h-px bg-white/15" />
        </div>

        <div className="flex items-center justify-center gap-3.5">
          <div className="flex items-center gap-1.5">
            <span className="w-[7px] h-[7px] rounded-full" style={{ background: '#E8791A' }} />
            <span className="text-white/70 text-[10.5px] font-bold tracking-wide">KALTEMP</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-[7px] h-[7px] rounded-full" style={{ background: '#3E9FD8' }} />
            <span className="text-white/70 text-[10.5px] font-bold tracking-wide">TOM PALMER</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-5 left-0 right-0 text-center">
        <div className="flex items-center justify-center gap-1.5 text-white/35 text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Kaltemp Group — Sistema Protegido de Gestión Operativa</span>
        </div>
      </div>
    </div>
  );
};