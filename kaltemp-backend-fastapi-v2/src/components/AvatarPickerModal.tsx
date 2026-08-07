import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import * as LucideIcons from 'lucide-react';
import { X, Check, Upload, Trash2 } from 'lucide-react';
import { AVATAR_CATALOG, INITIALS_COLOR_PALETTE } from './avatarCatalog';
import { resolveAvatarImageUrl } from '../services/api';

interface AvatarPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
  nombre: string;
  currentColor: string;
  currentIcon?: string | null;
  currentImageUrl?: string | null;
  /** avatarIcon = null significa "sin ícono, solo iniciales". */
  onSelect: (avatarColor: string, avatarIcon: string | null) => Promise<void> | void;
  onUploadImage: (file: File) => Promise<void> | void;
  onRemoveImage: () => Promise<void> | void;
}

const MAX_AVATAR_BYTES = 2 * 1024 * 1024; // 2MB, debe calzar con el límite del backend
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export const AvatarPickerModal: React.FC<AvatarPickerModalProps> = ({
  isOpen,
  onClose,
  isDark,
  nombre,
  currentColor,
  currentIcon,
  currentImageUrl,
  onSelect,
  onUploadImage,
  onRemoveImage,
}) => {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handlePick = async (color: string, icon: string | null) => {
    setSaving(true);
    setError(null);
    try {
      await onSelect(color, icon);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'No se pudo guardar el avatar.');
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // permite volver a elegir el mismo archivo después
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Solo se permiten imágenes JPG, PNG o WEBP.');
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setError('La imagen no puede pesar más de 2MB.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onUploadImage(file);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'No se pudo subir la imagen.');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async () => {
    setSaving(true);
    setError(null);
    try {
      await onRemoveImage();
      onClose();
    } catch (err: any) {
      setError(err?.message || 'No se pudo quitar la imagen.');
    } finally {
      setSaving(false);
    }
  };

  const resolvedCurrentImage = resolveAvatarImageUrl(currentImageUrl);

  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div
        className={`w-full max-w-lg rounded-2xl border shadow-2xl ${
          isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-200 text-slate-900'
        }`}
      >
        <div className={`p-4 border-b flex items-center justify-between ${isDark ? 'border-[#2C2C2E]' : 'border-slate-200'}`}>
          <h3 className="text-sm font-black uppercase tracking-wider">Elegir Avatar</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-500/10">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs font-semibold">
              {error}
            </div>
          )}

          {/* Foto propia */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Tu propia foto
            </p>
            <div className="flex items-center gap-3">
              {resolvedCurrentImage ? (
                <img
                  src={resolvedCurrentImage}
                  alt={nombre}
                  className="w-14 h-14 rounded-full object-cover shadow border-2 border-blue-500"
                />
              ) : (
                <div
                  className={`w-14 h-14 rounded-full flex items-center justify-center border-2 border-dashed ${
                    isDark ? 'border-[#383840] text-slate-500' : 'border-slate-300 text-slate-400'
                  }`}
                >
                  <Upload className="w-5 h-5" />
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-extrabold flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Upload className="w-3.5 h-3.5" />
                  {resolvedCurrentImage ? 'Cambiar foto' : 'Subir foto'}
                </button>
                {resolvedCurrentImage && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={handleRemove}
                    className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 text-xs font-extrabold flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Quitar foto
                  </button>
                )}
                <p className={`text-[10px] ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                  JPG, PNG o WEBP -- máx. 2MB
                </p>
              </div>
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Catálogo de íconos
            </p>
            <div className="grid grid-cols-6 gap-2.5">
              {AVATAR_CATALOG.map((opt) => {
                const IconComp = (LucideIcons as unknown as Record<string, React.FC<any>>)[opt.icon];
                const isSelected = !resolvedCurrentImage && currentIcon === opt.icon && currentColor === opt.color;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    title={opt.label}
                    disabled={saving}
                    onClick={() => handlePick(opt.color, opt.icon)}
                    className={`relative w-11 h-11 rounded-full flex items-center justify-center transition-all hover:scale-105 disabled:opacity-50 ${
                      isSelected ? `ring-2 ring-offset-2 ring-blue-500 ${isDark ? 'ring-offset-[#1C1C1E]' : 'ring-offset-white'}` : ''
                    }`}
                    style={{ backgroundColor: opt.color }}
                  >
                    {IconComp && <IconComp className="w-5 h-5 text-white" />}
                    {isSelected && (
                      <span className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center border-2 ${isDark ? 'border-[#1C1C1E]' : 'border-white'}`}>
                        <Check className="w-2.5 h-2.5 text-white" />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Solo iniciales (sin ícono)
            </p>
            <div className="grid grid-cols-8 gap-2.5">
              {INITIALS_COLOR_PALETTE.map((color) => {
                const isSelected = !resolvedCurrentImage && !currentIcon && currentColor === color;
                return (
                  <button
                    key={color}
                    type="button"
                    disabled={saving}
                    onClick={() => handlePick(color, null)}
                    className={`relative w-9 h-9 rounded-full flex items-center justify-center font-black text-white text-xs transition-all hover:scale-105 disabled:opacity-50 ${
                      isSelected ? `ring-2 ring-offset-2 ring-blue-500 ${isDark ? 'ring-offset-[#1C1C1E]' : 'ring-offset-white'}` : ''
                    }`}
                    style={{ backgroundColor: color }}
                  >
                    {nombre.charAt(0).toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};