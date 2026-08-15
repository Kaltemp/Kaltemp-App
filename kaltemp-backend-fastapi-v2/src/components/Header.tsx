// ============================================================
// ARCHIVO: Header.tsx
// RUTA: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\components\Header.tsx
// ============================================================

import React, { useMemo } from 'react';
import { ModuleId, ThemeMode } from '../types';
import { useUser } from '../context/UserContext';
import { useGlobalFilter } from '../context/FilterContext';
import { Sparkles } from 'lucide-react';
import { UserMenu } from './UserMenu';

interface HeaderProps {
  theme: ThemeMode;
  activeModule: ModuleId;
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
  onThemeToggle?: () => void;
  startDate?: string;
  endDate?: string;
  lastSyncMin?: number;
  onSync?: () => void;
  isSyncing?: boolean;
}

interface ModuleInfo {
  category: string;
  name: string;
  desc: string;
}

const MODULE_MAP: Record<string, ModuleInfo> = {
  resumen: {
    category: 'General',
    name: 'Resumen Ejecutivo',
    desc: 'Centro de control ejecutivo, KPIs clave y estado general del negocio'
  },
  principal: {
    category: 'General',
    name: 'Vista Principal Ejecutiva',
    desc: 'Consolidado de ventas, cumplimiento de metas y margen frontal'
  },
  ventas_sku: {
    category: 'General',
    name: 'Ventas por SKU & Categorías',
    desc: 'Desglose jerárquico por categoría, familias de producto y rotación'
  },
  stock: {
    category: 'Bsale ERP',
    name: 'Consolidado de Stock & Bodega',
    desc: 'Inventario disponible en Casa Matriz y valoración total'
  },
  pendientes_despacho: {
    category: 'Bsale ERP',
    name: 'Auditoría Pendientes por Despachar',
    desc: 'Control de órdenes en preparación y despacho por tramos de atención'
  },
  notas_credito: {
    category: 'Bsale ERP',
    name: 'Notas de Crédito & Desfase RCOF',
    desc: 'Conciliación tributaria y devoluciones de clientes'
  },
  fulfillment: {
    category: 'Logística',
    name: 'Detalle Fulfillment',
    desc: 'Seguimiento FBF Falabella, FBM Mercado Libre, FBP Paris y FBR Ripley'
  },
  control_logistico: {
    category: 'Logística',
    name: 'Control Logístico',
    desc: 'Evaluación de couriers (BlueExpress, Chilexpress, Starken)'
  },
  leads: {
    category: 'Marketing & CRM',
    name: 'CRM Leads & Gestión Comercial',
    desc: 'Captación por canales (Cliengo, Web, Google Ads, Meta) y vendedores'
  },
  carros_abandonados: {
    category: 'Marketing & CRM',
    name: 'Carros Abandonados Shopify',
    desc: 'Checkouts no concretados y tasa de recuperación comercial'
  },
  campanas_mkt: {
    category: 'Marketing & CRM',
    name: 'Campañas de Marketing Digital',
    desc: 'Rendimiento de pauta en Meta Ads y Google Ads'
  },
  indicadores_d2c: {
    category: 'Canales & Analítica',
    name: 'Indicadores D2C & Funnel GA4',
    desc: 'Tasa de conversión e-commerce, ROAS y métricas web'
  },
  distribuidores: {
    category: 'Canales & Analítica',
    name: 'Canal Distribuidores (B2B)',
    desc: 'Ranking de clientes mayoristas y comparativo interanual'
  },
  inmobiliaria: {
    category: 'Canales & Analítica',
    name: 'Canal Inmobiliaria (Proyectos)',
    desc: 'Indicadores de venta B2B inmobiliarias, ranking de proyectos y categorías'
  },
  ventas_temperatura: {
    category: 'Canales & Analítica',
    name: 'Ventas vs. Temperatura Santiago',
    desc: 'Correlación clima - estufas y demanda estacional'
  },
  cumplimiento_ventas: {
    category: 'Gestión Comercial',
    name: 'Cumplimiento & Proyección de Ventas (Ciclo 25 - 24)',
    desc: 'Cumplimiento de metas comerciales por vendedor, brechas y proyección de cierre'
  }
};

const fmtDateCL = (isoStr?: string) => {
  if (!isoStr || !isoStr.includes('-')) return isoStr || '';
  const parts = isoStr.split('-');
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return isoStr;
};

export const Header: React.FC<HeaderProps> = ({
  theme,
  activeModule,
  startDate,
  endDate,
  isSyncing = false
}) => {
  const isDark = theme === 'dark';
  const currentInfo = MODULE_MAP[activeModule] || MODULE_MAP.resumen || MODULE_MAP.principal;
  const { currentUser } = useUser();

  // Lectura segura del contexto global de filtros
  let globalFilter: any = null;
  try {
    globalFilter = useGlobalFilter();
  } catch (e) {
    globalFilter = null;
  }

  // Rango de fechas formateado
  const fechaBadge = useMemo(() => {
    const s = startDate || globalFilter?.startDate || globalFilter?.dateRange?.startDate || globalFilter?.fechaInicio || globalFilter?.fecha_inicio;
    const e = endDate || globalFilter?.endDate || globalFilter?.dateRange?.endDate || globalFilter?.fechaFin || globalFilter?.fecha_fin;

    if (s && e) {
      return `${fmtDateCL(String(s).slice(0, 10))} ➔ ${fmtDateCL(String(e).slice(0, 10))}`;
    }

    const hoy = new Date();
    const hace30 = new Date(hoy.getTime() - 30 * 24 * 60 * 60 * 1000);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return `${fmtDateCL(iso(hace30))} ➔ ${fmtDateCL(iso(hoy))}`;
  }, [startDate, endDate, globalFilter]);

  if (!currentUser) return null;

  // VISIBILIDAD EXCLUSIVA: Solo en el módulo Resumen
  const isResumen = activeModule === 'resumen';

  return (
    <>
      <style>{`
        @keyframes kaltemp-brand-wave {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .kaltemp-brand-thinking-text {
          background: linear-gradient(
            90deg,
            #8E8E93 0%,
            #CC0000 35%,
            #58C6E5 70%,
            #8E8E93 100%
          );
          background-size: 200% 100%;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: kaltemp-brand-wave 4s linear infinite;
        }
      `}</style>

      {/* HEADER UNIFICADO: Mismo gris #EAEBED en modo claro para fusionarse con el Sidebar y el Lienzo */}
      <header
        className={`sticky top-0 z-30 border-b transition-all duration-200 backdrop-blur-md px-4 py-2.5 sm:px-6 ${
          isDark
            ? 'bg-[#0F0F12]/90 border-[#2C2C2E]'
            : 'bg-[#EAEBED]/95 border-slate-300/80'
        }`}
      >
        <div className="w-full mx-auto flex items-center justify-between min-h-[38px] gap-4">

          {/* LADO IZQUIERDO: TÍTULO DEL MÓDULO + BADGE SOLO EN RESUMEN */}
          <div className="flex items-center gap-3.5 min-w-0 flex-wrap">
            <h1
              className={`text-base sm:text-lg font-black tracking-tight truncate leading-none ${
                isDark ? 'text-white' : 'text-slate-900'
              }`}
            >
              {currentInfo.name}
            </h1>

            {/* CÁPSULA DE FECHA EXCLUSIVA PARA EL MÓDULO RESUMEN */}
            {isResumen && (
              <div
                className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border shadow-sm shrink-0 transition-all ${
                  isDark
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-white text-emerald-800 border-emerald-300'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                <span className="text-[11px] sm:text-xs font-black font-mono tracking-tight">
                  {fechaBadge}
                </span>
              </div>
            )}

            {isSyncing && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-red-500/30 shadow-inner shrink-0">
                <Sparkles className="w-3.5 h-3.5 text-[#CC0000] animate-spin" />
                <span className="text-xs font-bold kaltemp-brand-thinking-text">
                  Sincronizando datos...
                </span>
              </div>
            )}
          </div>

          {/* LADO DERECHO: MENÚ DE USUARIO */}
          <div className="shrink-0 flex items-center gap-2">
            <UserMenu isDark={isDark} />
          </div>
        </div>
      </header>
    </>
  );
};