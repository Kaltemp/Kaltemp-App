import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { useUser, UserProfile } from '../context/UserContext';
import { ModuleId } from '../types';
import { Shield, UserCheck, Lock, CheckCircle2, X, Plus, User, Key, Info, KeyRound, Trash2, Pencil } from 'lucide-react';
import { AvatarBadge } from './AvatarBadge';
import { AvatarPickerModal } from './AvatarPickerModal';

interface UserManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
}

const ALL_MODULE_LIST: { id: ModuleId; label: string; cat: string }[] = [
  { id: 'principal', label: 'Principal', cat: 'General' },
  { id: 'cumplimiento_ventas', label: 'Cumplimiento Ventas (25-24)', cat: 'General' },
  { id: 'ventas_sku', label: 'Ventas por SKU', cat: 'General' },
  { id: 'stock', label: 'Stock & Bodega', cat: 'Bsale ERP' },
  { id: 'pendientes_despacho', label: 'Pendientes por Despachar', cat: 'Bsale ERP' },
  { id: 'notas_credito', label: 'Notas de Crédito', cat: 'Bsale ERP' },
  { id: 'fulfillment', label: 'Detalle Fulfillment', cat: 'Logística' },
  { id: 'control_logistico', label: 'Control Logístico', cat: 'Logística' },
  { id: 'leads', label: 'CRM Leads', cat: 'Marketing & CRM' },
  { id: 'carros_abandonados', label: 'Carros Abandonados', cat: 'Marketing & CRM' },
  { id: 'campanas_mkt', label: 'Campañas de Marketing', cat: 'Marketing & CRM' },
  { id: 'indicadores_d2c', label: 'Indicadores D2C', cat: 'Canales & Analítica' },
  { id: 'distribuidores', label: 'Indicadores Distribuidores', cat: 'Canales & Analítica' },
  { id: 'ventas_temperatura', label: 'Ventas vs Temperatura', cat: 'Canales & Analítica' },
];

export const UserManagementModal: React.FC<UserManagementModalProps> = ({ isOpen, onClose, isDark }) => {
  const { users, currentUser, impersonate, addUser, resetUserPassword, removeUser, updateUser, uploadAvatarImage, removeAvatarImage } = useUser();
  const [showAddForm, setShowAddForm] = useState(false);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);

  const [newEmail, setNewEmail] = useState('');
  const [newNombre, setNewNombre] = useState('');
  const [newRol, setNewRol] = useState<'Administrador' | 'Ejecutivo Comercial' | 'Marketing' | 'Logística'>('Ejecutivo Comercial');
  const [newPassword, setNewPassword] = useState('');
  const [selectedBlocked, setSelectedBlocked] = useState<ModuleId[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [resettingUserId, setResettingUserId] = useState<string | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState('');
  const [resetError, setResetError] = useState<string | null>(null);

  if (!isOpen || !currentUser) return null;

  const isAdmin = currentUser.rol === 'Administrador';

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!isAdmin) return;
    if (!newEmail.trim() || !newNombre.trim()) return;
    if (newPassword.length < 8) {
      setCreateError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }

    setIsSubmitting(true);
    try {
      await addUser({
        email: newEmail.trim().toLowerCase(),
        nombre: newNombre.trim(),
        rol: newRol,
        password: newPassword,
        blockedModules: selectedBlocked,
      });
      setNewEmail('');
      setNewNombre('');
      setNewPassword('');
      setSelectedBlocked([]);
      setShowAddForm(false);
    } catch (err: any) {
      setCreateError(err?.message || 'No se pudo crear el usuario.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleImpersonate = async (usr: UserProfile) => {
    try {
      await impersonate(usr.id);
      onClose();
    } catch (err: any) {
      // Silencioso a propósito: si falla, el usuario simplemente sigue en
      // su sesión actual -- no hay nada roto que mostrar en pantalla.
      console.error('No se pudo simular la sesión:', err);
    }
  };

  const handleStartReset = (usr: UserProfile) => {
    setResettingUserId(usr.id);
    setResetPasswordValue('');
    setResetError(null);
  };

  const handleConfirmReset = async (usr: UserProfile) => {
    setResetError(null);
    if (resetPasswordValue.length < 8) {
      setResetError('Mínimo 8 caracteres.');
      return;
    }
    try {
      await resetUserPassword(usr.id, resetPasswordValue);
      setResettingUserId(null);
      setResetPasswordValue('');
    } catch (err: any) {
      setResetError(err?.message || 'No se pudo cambiar la contraseña.');
    }
  };

  const handleDelete = async (usr: UserProfile) => {
    if (usr.id === currentUser.id) return;
    if (!window.confirm(`¿Eliminar a ${usr.nombre} (${usr.email})? Esta acción no se puede deshacer.`)) return;
    try {
      await removeUser(usr.id);
    } catch (err: any) {
      console.error('No se pudo eliminar el usuario:', err);
    }
  };

  const handleChangeAvatar = async (avatarColor: string, avatarIcon: string | null) => {
    if (!currentUser) return;
    // '' (string vacío) le indica al backend "borra el ícono, vuelve a
    // solo iniciales" -- ver auth.py / api.ts.
    await updateUser(currentUser.id, { avatarColor, avatarIcon: avatarIcon ?? '' });
  };

  const handleUploadAvatarImage = async (file: File) => {
    if (!currentUser) return;
    await uploadAvatarImage(currentUser.id, file);
  };

  const handleRemoveAvatarImage = async () => {
    if (!currentUser) return;
    await removeAvatarImage(currentUser.id);
  };

  const toggleBlockedModule = (modId: ModuleId) => {
    setSelectedBlocked((prev) =>
      prev.includes(modId) ? prev.filter((m) => m !== modId) : [...prev, modId]
    );
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div
        className={`w-full max-w-4xl max-h-[90vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden ${
          isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-200 text-slate-900'
        }`}
      >
        {/* Modal Header */}
        <div className={`p-5 border-b flex items-center justify-between ${
          isDark ? 'border-[#2C2C2E] bg-[#141416]' : 'border-slate-200 bg-slate-50'
        }`}>
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-xl bg-blue-500/10 text-blue-500 border border-blue-500/20">
              <Shield className="w-5 h-5" />
            </span>
            <div>
              <h2 className="text-base font-black tracking-tight">
                Gestión de Usuarios y Roles (RBAC)
              </h2>
              <p className="text-xs text-slate-400 font-medium">
                Matriz de permisos de acceso por usuario y módulo
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-500/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Active User Switcher Header Banner */}
          <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
            isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowAvatarPicker(true)}
                title="Cambiar mi avatar"
                className="relative group shrink-0"
              >
                <AvatarBadge
                  nombre={currentUser.nombre}
                  avatarColor={currentUser.avatarColor}
                  avatarIcon={currentUser.avatarIcon}
                  avatarImageUrl={currentUser.avatarImageUrl}
                  size="md"
                />
                <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-blue-600 group-hover:bg-blue-500 flex items-center justify-center border-2 border-white dark:border-[#121214] transition-colors">
                  <Pencil className="w-2.5 h-2.5 text-white" />
                </span>
              </button>
              <div>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Usuario en sesión actual:</p>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-black">{currentUser.nombre}</span>
                  <span className="text-xs font-mono text-slate-400">({currentUser.email})</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-blue-500/15 text-blue-500 border border-blue-500/30">
                    {currentUser.rol}
                  </span>
                </div>
              </div>
            </div>

            {isAdmin ? (
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-extrabold text-xs flex items-center gap-1.5 transition-all shadow"
              >
                <Plus className="w-4 h-4" />
                {showAddForm ? 'Cancelar' : 'Crear Nuevo Usuario'}
              </button>
            ) : (
              <div
                title="Solo un usuario con rol Administrador puede crear nuevos usuarios."
                className="px-3 py-1.5 rounded-xl bg-slate-500/10 border border-slate-500/20 text-slate-400 font-bold text-xs flex items-center gap-1.5 cursor-not-allowed"
              >
                <Lock className="w-3.5 h-3.5 text-amber-500" />
                <span>Creación restringida a Administradores</span>
              </div>
            )}
          </div>

          {/* Add User Form */}
          {showAddForm && (
            <form onSubmit={handleCreateUser} className={`p-4 rounded-xl border space-y-4 ${
              isDark ? 'bg-[#232328] border-[#383840]' : 'bg-slate-100 border-slate-300'
            }`}>
              <h3 className="text-xs font-black uppercase tracking-wider text-blue-500 flex items-center gap-1.5">
                <User className="w-4 h-4" /> Registrar Nuevo Usuario
              </h3>

              {createError && (
                <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs font-semibold">
                  {createError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Nombre Completo:</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej. Roberto Gómez"
                    value={newNombre}
                    onChange={(e) => setNewNombre(e.target.value)}
                    className={`w-full px-3 py-1.5 text-xs font-bold rounded-lg border outline-none ${
                      isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                    }`}
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Correo Electrónico:</label>
                  <input
                    type="email"
                    required
                    placeholder="rgomez@kaltemp.cl"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    className={`w-full px-3 py-1.5 text-xs font-bold rounded-lg border outline-none ${
                      isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                    }`}
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Contraseña Inicial:</label>
                  <input
                    type="text"
                    required
                    minLength={8}
                    placeholder="Mínimo 8 caracteres"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className={`w-full px-3 py-1.5 text-xs font-bold rounded-lg border outline-none ${
                      isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                    }`}
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-400 block mb-1">Rol Asignado:</label>
                  <select
                    value={newRol}
                    onChange={(e) => setNewRol(e.target.value as any)}
                    className={`w-full px-3 py-1.5 text-xs font-bold rounded-lg border outline-none ${
                      isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                    }`}
                  >
                    <option value="Ejecutivo Comercial">Ejecutivo Comercial</option>
                    <option value="Administrador">Administrador</option>
                    <option value="Marketing">Marketing</option>
                    <option value="Logística">Logística</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-400 block mb-2">
                  Selecciona Módulos a Bloquear para este Usuario:
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                  {ALL_MODULE_LIST.map((mod) => {
                    const isBlocked = selectedBlocked.includes(mod.id);
                    return (
                      <button
                        type="button"
                        key={mod.id}
                        onClick={() => toggleBlockedModule(mod.id)}
                        className={`px-2.5 py-1.5 rounded-lg border text-xs font-bold flex items-center justify-between transition-all ${
                          isBlocked
                            ? 'bg-rose-500/15 border-rose-500/40 text-rose-400'
                            : isDark
                            ? 'bg-[#1C1C1E] border-[#383840] text-slate-400'
                            : 'bg-white border-slate-300 text-slate-600'
                        }`}
                      >
                        <span className="truncate">{mod.label}</span>
                        {isBlocked ? <Lock className="w-3 h-3 text-rose-500 shrink-0 ml-1" /> : <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0 ml-1" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-extrabold shadow disabled:opacity-60"
                >
                  {isSubmitting ? 'Guardando...' : 'Guardar Usuario'}
                </button>
              </div>
            </form>
          )}

          {/* User Table Matrix */}
          <div className="space-y-3">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>Usuarios Registrados ({users.length})</span>
              <span className="text-[11px] font-normal text-slate-500">Haz clic en "Simular Sesión" para probar accesos</span>
            </h3>

            <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-[#2C2C2E]">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className={`border-b text-[11px] font-black uppercase tracking-wider ${
                    isDark ? 'border-[#333339] text-[#8E8E93] bg-[#17171A]' : 'border-slate-200 text-slate-400 bg-slate-50'
                  }`}>
                    <th className="py-2.5 px-3">USUARIO / EMAIL</th>
                    <th className="py-2.5 px-3">ROL</th>
                    <th className="py-2.5 px-3">ACCESO & MÓDULOS PERMITIDOS</th>
                    <th className="py-2.5 px-3 text-center">ACCIONES</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/60 dark:divide-[#2C2C2E]">
                  {users.map((usr) => {
                    const isCurrent = currentUser.email.toLowerCase() === usr.email.toLowerCase();
                    const isTotalAccess = (!usr.blockedModules || usr.blockedModules.length === 0) && !usr.allowedModulesOnly;

                    return (
                      <tr
                        key={usr.email}
                        className={`transition-colors ${
                          isCurrent
                            ? isDark
                              ? 'bg-blue-500/10'
                              : 'bg-blue-50'
                            : isDark
                            ? 'hover:bg-[#232328]'
                            : 'hover:bg-slate-50'
                        }`}
                      >
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2.5">
                            <AvatarBadge
                              nombre={usr.nombre}
                              avatarColor={usr.avatarColor}
                              avatarIcon={usr.avatarIcon}
                              avatarImageUrl={usr.avatarImageUrl}
                              size="sm"
                            />
                            <div>
                              <div className="font-extrabold flex items-center gap-1.5">
                                {usr.nombre}
                                {isCurrent && (
                                  <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-blue-500 text-white">
                                    En Uso
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-400 font-mono">{usr.email}</div>
                            </div>
                          </div>
                        </td>

                        <td className="py-3 px-3 font-mono font-bold text-amber-500 text-[11px]">
                          {resettingUserId === usr.id ? (
                            <div className="flex flex-col gap-1.5 min-w-[160px]">
                              <input
                                type="text"
                                autoFocus
                                placeholder="Nueva contraseña"
                                value={resetPasswordValue}
                                onChange={(e) => setResetPasswordValue(e.target.value)}
                                className={`px-2 py-1 text-[11px] font-bold rounded border outline-none ${
                                  isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                                }`}
                              />
                              {resetError && <span className="text-rose-500 text-[10px] font-semibold">{resetError}</span>}
                              <div className="flex gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleConfirmReset(usr)}
                                  className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-extrabold"
                                >
                                  Guardar
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setResettingUserId(null)}
                                  className="px-2 py-1 rounded bg-slate-500/20 hover:bg-slate-500/30 text-[10px] font-extrabold"
                                >
                                  Cancelar
                                </button>
                              </div>
                            </div>
                          ) : (
                            isAdmin && (
                              <button
                                type="button"
                                onClick={() => handleStartReset(usr)}
                                className="px-2 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 font-bold text-[11px] flex items-center gap-1 border border-amber-500/20"
                              >
                                <KeyRound className="w-3 h-3" /> Resetear Contraseña
                              </button>
                            )
                          )}
                        </td>

                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${
                            usr.rol === 'Administrador'
                              ? 'bg-blue-500/15 text-blue-500 border border-blue-500/30'
                              : usr.rol === 'Ejecutivo Comercial'
                              ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                              : usr.rol === 'Marketing'
                              ? 'bg-purple-500/15 text-purple-500 border border-purple-500/30'
                              : 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                          }`}>
                            {usr.rol}
                          </span>
                        </td>

                        <td className="py-3 px-3">
                          {isTotalAccess ? (
                            <span className="inline-flex items-center gap-1 text-emerald-500 font-bold">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Acceso Total a todos los módulos
                            </span>
                          ) : usr.allowedModulesOnly ? (
                            <div className="space-y-1">
                              <span className="inline-flex items-center gap-1 text-amber-500 font-bold text-[11px]">
                                <Lock className="w-3.5 h-3.5" /> Acceso Restringido ÚNICAMENTE a:
                              </span>
                              <div className="flex flex-wrap gap-1">
                                {usr.allowedModulesOnly.map((m) => {
                                  const info = ALL_MODULE_LIST.find((x) => x.id === m);
                                  return (
                                    <span key={m} className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-bold text-[10px]">
                                      {info?.label || m}
                                    </span>
                                  );
                                })}
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              <span className="text-slate-400 font-semibold text-[11px] block">
                                Bloqueados ({usr.blockedModules.length}):
                              </span>
                              <div className="flex flex-wrap gap-1">
                                {usr.blockedModules.map((m) => {
                                  const info = ALL_MODULE_LIST.find((x) => x.id === m);
                                  return (
                                    <span key={m} className="px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/20 font-bold text-[10px] flex items-center gap-1">
                                      <Lock className="w-2.5 h-2.5" /> {info?.label || m}
                                    </span>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </td>

                        <td className="py-3 px-3 text-center">
                          {isCurrent ? (
                            <span className="text-[11px] font-bold text-emerald-500 flex items-center justify-center gap-1">
                              <UserCheck className="w-4 h-4" /> Activo
                            </span>
                          ) : (
                            <div className="flex items-center justify-center gap-1.5">
                              {isAdmin && (
                                <button
                                  onClick={() => handleImpersonate(usr)}
                                  className="px-3 py-1 rounded-lg bg-blue-500/10 hover:bg-blue-500 text-blue-500 hover:text-white font-extrabold text-xs transition-all border border-blue-500/20"
                                >
                                  Simular Sesión
                                </button>
                              )}
                              {isAdmin && (
                                <button
                                  onClick={() => handleDelete(usr)}
                                  title="Eliminar usuario"
                                  className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white transition-all border border-rose-500/20"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className={`p-4 border-t flex justify-end ${
          isDark ? 'border-[#2C2C2E] bg-[#141416]' : 'border-slate-200 bg-slate-50'
        }`}>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-200 dark:bg-[#2C2C32] hover:bg-slate-300 dark:hover:bg-[#383840] font-bold text-xs transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>

      <AvatarPickerModal
        isOpen={showAvatarPicker}
        onClose={() => setShowAvatarPicker(false)}
        isDark={isDark}
        nombre={currentUser.nombre}
        currentColor={currentUser.avatarColor}
        currentIcon={currentUser.avatarIcon}
        currentImageUrl={currentUser.avatarImageUrl}
        onSelect={handleChangeAvatar}
        onUploadImage={handleUploadAvatarImage}
        onRemoveImage={handleRemoveAvatarImage}
      />
    </div>,
    document.body
  );
};