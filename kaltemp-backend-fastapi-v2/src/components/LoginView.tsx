import React, { useState } from 'react';
import { Lock, User, Eye, EyeOff, ShieldCheck, ArrowRight, Sun, Moon } from 'lucide-react';
import { ThemeMode } from '../types';
import { useUser } from '../context/UserContext';

// Logos reales de Kaltemp (07-ago-2026) -- reemplazan el ícono "K" en caja
// roja y el texto "kaltemp" que se dibujaban a mano con CSS.
const KALTEMP_LOGO_CONDENSADO = 'https://cdn.shopify.com/s/files/1/0656/1605/2459/files/Logo_Kaltemp_Condensado.png?v=1786109942';

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
    <div className={`min-h-screen w-full flex flex-col justify-between transition-colors duration-200 ${
      isDark ? 'bg-[#0F0F12] text-[#EDEDED]' : 'bg-slate-50 text-slate-800'
    }`}>
      {/* Top Bar -- solo el toggle de tema. El logo grande ya vive dentro
          de la tarjeta (más abajo); tenerlo duplicado acá diluía la marca
          en vez de reforzarla (07-ago-2026, a pedido de William). */}
      <header className="w-full px-6 py-4 flex items-center justify-end">
        <button
          onClick={onThemeToggle}
          className={`p-2 rounded-xl border transition-all ${
            isDark
              ? 'bg-[#1C1C1E] border-[#2C2C2E] text-amber-400 hover:bg-[#2C2C2E]'
              : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-100'
          }`}
          title={isDark ? 'Modo claro' : 'Modo oscuro'}
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </header>

      {/* Main Login Card Centered */}
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <div className={`w-full max-w-md p-8 rounded-2xl border shadow-xl transition-all ${
          isDark 
            ? 'bg-[#17171A] border-[#2C2C2E] shadow-black/40' 
            : 'bg-white border-slate-200/80 shadow-slate-200/60'
        }`}>
          {/* Header section inside card */}
          <div className="text-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-[#CC0000]/10 border border-[#CC0000]/20 flex items-center justify-center mx-auto mb-3 overflow-hidden">
              <img
                src={KALTEMP_LOGO_CONDENSADO}
                alt="Kaltemp"
                className="w-9 h-9 object-contain"
              />
            </div>
            <h1 className="text-2xl font-black tracking-tight mb-1">
              Acceso a Analítica
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
              Plataforma de Business Intelligence & Control Operativo
            </p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-xs font-semibold animate-shake">
                {error}
              </div>
            )}

            {/* Email / Username field */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider mb-1.5 text-slate-600 dark:text-slate-400">
                Usuario / Correo
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ejemplo@kaltemp.cl"
                  autoComplete="username"
                  className={`w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border font-medium outline-none transition-all ${
                    isDark
                      ? 'bg-[#121214] border-[#2C2C2E] text-white focus:border-[#CC0000] focus:ring-1 focus:ring-[#CC0000]'
                      : 'bg-slate-50 border-slate-200 text-slate-900 focus:border-[#CC0000] focus:ring-1 focus:ring-[#CC0000]'
                  }`}
                />
              </div>
            </div>

            {/* Password field */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider mb-1.5 text-slate-600 dark:text-slate-400">
                Contraseña
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className={`w-full pl-10 pr-10 py-2.5 text-sm rounded-xl border font-medium outline-none transition-all ${
                    isDark
                      ? 'bg-[#121214] border-[#2C2C2E] text-white focus:border-[#CC0000] focus:ring-1 focus:ring-[#CC0000]'
                      : 'bg-slate-50 border-slate-200 text-slate-900 focus:border-[#CC0000] focus:ring-1 focus:ring-[#CC0000]'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 cursor-pointer font-medium select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-300 text-[#CC0000] focus:ring-[#CC0000]"
                />
                <span className="text-slate-600 dark:text-slate-400">Recordar sesión</span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-4 py-3 px-4 rounded-xl bg-[#CC0000] hover:bg-[#B30000] active:scale-[0.99] text-white font-bold text-sm transition-all shadow-lg shadow-[#CC0000]/25 flex items-center justify-center gap-2 disabled:opacity-70"
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
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full py-4 text-center text-xs text-slate-400 font-medium">
        <div className="flex items-center justify-center gap-1.5 mb-1">
          <ShieldCheck className="w-3.5 h-3.5 text-[#CC0000]" />
          <span>Kaltemp S.A. — Sistema Protegido de Gestión Operativa</span>
        </div>
      </footer>
    </div>
  );
};
