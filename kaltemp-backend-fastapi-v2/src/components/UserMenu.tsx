import React, { useState } from 'react';
import { ChevronDown, UserCheck, Shield, LogOut } from 'lucide-react';
import { useUser } from '../context/UserContext';
import { AvatarBadge } from './AvatarBadge';
import { UserManagementModal } from './UserManagementModal';

interface UserMenuProps {
  isDark: boolean;
}

/**
 * Bloque de usuario (avatar + nombre + rol), con:
 *  - Dropdown para "Simular Sesión" de otro usuario (solo William, mismo
 *    comportamiento que tenía en Sidebar.tsx).
 *  - Botón para cerrar sesión.
 *  - Acceso al modal "Gestión de Usuarios y Roles (RBAC)".
 *
 * Trasladado de Sidebar.tsx al Header.tsx (07-ago-2026) -- es autocontenido
 * (usa useUser() directamente) para poder vivir en cualquiera de los dos
 * sin pasar props extra por App.tsx.
 */
export const UserMenu: React.FC<UserMenuProps> = ({ isDark }) => {
  const { currentUser, users, impersonate, logout } = useUser();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showModal, setShowModal] = useState(false);

  if (!currentUser) return null;

  const isWilliam = currentUser.email.toLowerCase() === 'william@kaltemp.cl';

  const handleImpersonate = async (usrId: string) => {
    try {
      await impersonate(usrId);
      setShowDropdown(false);
    } catch (err) {
      // Silencioso a propósito: si falla, el usuario simplemente sigue en
      // su sesión actual -- no hay nada roto que mostrar en pantalla.
      console.error('No se pudo simular la sesión:', err);
    }
  };

  return (
    <div className="relative shrink-0">
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => {
            if (isWilliam) setShowDropdown(!showDropdown);
          }}
          className={`flex items-center gap-2 rounded-xl p-1 pr-1.5 transition-colors ${
            isWilliam ? 'hover:bg-slate-500/10 cursor-pointer' : ''
          }`}
          title={isWilliam ? 'Cambiar sesión de usuario' : undefined}
        >
          <div className="text-right hidden sm:block">
            <p className="font-bold text-xs flex items-center justify-end gap-1 leading-tight">
              {currentUser.nombre}
              {isWilliam && <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />}
            </p>
            <p className={`text-[10px] leading-tight ${isDark ? 'text-[#8E8E93]' : 'text-slate-400'}`}>
              {currentUser.rol}
            </p>
          </div>
          <AvatarBadge
            nombre={currentUser.nombre}
            avatarColor={currentUser.avatarColor}
            avatarIcon={currentUser.avatarIcon}
            avatarImageUrl={currentUser.avatarImageUrl}
            size="sm"
          />
        </button>

        <button
          onClick={logout}
          className={`p-1.5 rounded-lg border transition-all shrink-0 cursor-pointer ${
            isDark
              ? 'bg-[#1C1C1E] border-[#2C2C2E] text-slate-400 hover:text-red-400 hover:border-red-500/30'
              : 'bg-slate-100 border-slate-200 text-slate-500 hover:text-red-600 hover:border-red-200'
          }`}
          title="Cerrar sesión"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Dropdown Menu de Cambio de Usuario (Solo William) -- se abre hacia
          abajo y alineado a la derecha porque ahora vive en el Header. */}
      {isWilliam && showDropdown && (
        <div
          className={`absolute right-0 top-full mt-2 w-64 rounded-2xl border shadow-2xl overflow-hidden z-40 p-1.5 ${
            isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}
        >
          <div className="px-3 py-2 border-b border-slate-200/60 dark:border-[#2C2C2E] mb-1">
            <p className="text-[10px] font-black uppercase tracking-wider text-[#CC0000]">
              Cambiar Sesión de Usuario (RBAC)
            </p>
            <p className="text-[11px] text-slate-400">
              Selecciona un usuario para verificar sus permisos:
            </p>
          </div>

          <div className="max-h-60 overflow-y-auto space-y-0.5">
            {users.map((usr) => {
              const isSelected = usr.email.toLowerCase() === currentUser.email.toLowerCase();
              return (
                <button
                  key={usr.email}
                  onClick={() => handleImpersonate(usr.id)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-xl text-xs flex items-center justify-between transition-colors ${
                    isSelected
                      ? 'bg-[#CC0000] text-white font-black'
                      : isDark
                      ? 'hover:bg-[#2C2C2E] text-slate-200 font-medium'
                      : 'hover:bg-slate-100 text-slate-800 font-medium'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <AvatarBadge
                      nombre={usr.nombre}
                      avatarColor={usr.avatarColor}
                      avatarIcon={usr.avatarIcon}
                      avatarImageUrl={usr.avatarImageUrl}
                      size="xs"
                    />
                    <div className="truncate">
                      <p className="text-[11px] leading-tight truncate font-bold">{usr.nombre}</p>
                      <p className={`text-[9px] font-mono leading-tight ${isSelected ? 'text-red-100' : 'text-slate-400'}`}>
                        {usr.rol}
                      </p>
                    </div>
                  </div>
                  {isSelected && <UserCheck className="w-3.5 h-3.5 shrink-0" />}
                </button>
              );
            })}
          </div>

          <div className="p-1.5 border-t border-slate-200/60 dark:border-[#2C2C2E] mt-1">
            <button
              onClick={() => {
                setShowDropdown(false);
                setShowModal(true);
              }}
              className="w-full py-1.5 px-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-[#CC0000] font-extrabold text-[11px] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
            >
              <Shield className="w-3.5 h-3.5" /> Ver Matriz de Permisos
            </button>
          </div>
        </div>
      )}

      <UserManagementModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        isDark={isDark}
      />
    </div>
  );
};
