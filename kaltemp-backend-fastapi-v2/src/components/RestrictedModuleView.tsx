import React from 'react';
import { useUser } from '../context/UserContext';
import { ModuleId, ThemeMode } from '../types';
import { ShieldAlert, Lock, UserCheck, ArrowLeft, Key } from 'lucide-react';

interface RestrictedModuleViewProps {
  moduleId: ModuleId;
  theme: ThemeMode;
  onGoBack: () => void;
  onOpenUserModal: () => void;
}

const MODULE_NAMES: Record<ModuleId, string> = {
  principal: 'Vista Principal Ejecutiva',
  ventas_sku: 'Ventas por SKU & Categorías',
  stock: 'Consolidado de Stock & Bodega',
  pendientes_despacho: 'Auditoría Pendientes por Despachar',
  notas_credito: 'Notas de Crédito & Desfase RCOF',
  fulfillment: 'Detalle Fulfillment',
  control_logistico: 'Control Logístico',
  leads: 'CRM Leads & Gestión Comercial',
  carros_abandonados: 'Carros Abandonados Shopify',
  campanas_mkt: 'Campañas de Marketing Digital',
  indicadores_d2c: 'Indicadores D2C & Funnel GA4',
  distribuidores: 'Canal Distribuidores (B2B)',
  inmobiliaria: 'Indicadores Inmobiliaria',
  ventas_temperatura: 'Ventas vs. Temperatura Santiago',
  cumplimiento_ventas: 'Cumplimiento Ventas (25-24)'
};

export const RestrictedModuleView: React.FC<RestrictedModuleViewProps> = ({
  moduleId,
  theme,
  onGoBack,
  onOpenUserModal
}) => {
  const { currentUser } = useUser();
  const isDark = theme === 'dark';
  const moduleName = MODULE_NAMES[moduleId] || moduleId;

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-6">
      <div
        className={`w-full max-w-xl p-8 rounded-3xl border shadow-2xl text-center space-y-6 ${
          isDark
            ? 'bg-[#1C1C1E] border-[#333339] text-white'
            : 'bg-white border-slate-200 text-slate-800'
        }`}
      >
        {/* Icon Header */}
        <div className="mx-auto w-16 h-16 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-500 flex items-center justify-center shadow-lg">
          <Lock className="w-8 h-8" />
        </div>

        {/* Title & Description */}
        <div className="space-y-2">
          <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-500 border border-rose-500/20 inline-block">
            Acceso Bloqueado por Rol
          </span>
          <h2 className="text-xl font-black tracking-tight">
            Módulo Restringido: {moduleName}
          </h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Tu usuario actual <strong className="text-blue-500">{currentUser.nombre}</strong> (
            <span className="font-mono">{currentUser.email}</span>) con el rol de{' '}
            <strong className="text-amber-500">{currentUser.rol}</strong> no posee autorización de acceso a esta sección del sistema.
          </p>
        </div>

        {/* User Card */}
        <div className={`p-4 rounded-2xl border text-left flex items-center justify-between ${
          isDark ? 'bg-[#141416] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
        }`}>
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center font-black text-white text-sm shadow shrink-0"
              style={{ backgroundColor: currentUser.avatarColor }}
            >
              {currentUser.nombre.charAt(0)}
            </div>
            <div>
              <p className="text-xs font-black">{currentUser.nombre}</p>
              <p className="text-[11px] text-slate-400 font-mono">{currentUser.email}</p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase bg-blue-500/15 text-blue-500 border border-blue-500/30">
            {currentUser.rol}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={onGoBack}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-extrabold text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 transition-all"
          >
            <ArrowLeft className="w-4 h-4" /> Ir a Módulo Permitido
          </button>

          <button
            onClick={onOpenUserModal}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-300 dark:border-[#333339] hover:bg-slate-500/10 font-extrabold text-xs flex items-center justify-center gap-2 transition-all"
          >
            <Key className="w-4 h-4 text-amber-500" /> Cambiar Usuario / Ver Permisos
          </button>
        </div>
      </div>
    </div>
  );
};
