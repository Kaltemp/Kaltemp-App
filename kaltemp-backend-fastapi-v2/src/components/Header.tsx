import React from 'react';
import { ModuleId, ThemeMode } from '../types';
import { useUser } from '../context/UserContext';
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

const MODULE_MAP: Record<ModuleId, ModuleInfo> = {
  principal: {
    category: 'General',
    name: 'Vista Principal Ejecutiva',
    desc: 'Resumen consolidado de ventas, cumplimiento de metas y margen frontal'
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

export const Header: React.FC<HeaderProps> = ({
  theme,
  activeModule,
  isSyncing = false
}) => {
  const isDark = theme === 'dark';
  const currentInfo = MODULE_MAP[activeModule] || MODULE_MAP.principal;
  const { currentUser } = useUser();

  if (!currentUser) return null;

  return (
    <>
      {/* Estilo CSS exclusivo para cuando el sistema está sincronizando (Pensando) */}
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

      <header
        className={`sticky top-0 z-30 border-b transition-all duration-200 backdrop-blur-md px-4 py-3 sm:px-6 ${
          isDark
            ? 'bg-[#121214]/90 border-[#2C2C2E]'
            : 'bg-white/90 border-slate-200/80'
        }`}
      >
        <div className="w-full mx-auto flex items-center justify-between min-h-[36px] gap-3">

          {/* TÍTULO DEL MÓDULO -- todo lo demás (categorías, campañas,
              DuckDB/Drive, selector de usuario) vive en Sidebar.tsx */}
          <div className="flex items-center gap-3 truncate">
            <h1 className={`text-base sm:text-xl font-black tracking-tight truncate leading-none ${
              isDark ? 'text-white' : 'text-[#1D1D1F]'
            }`}>
              {currentInfo.name}
            </h1>

            {isSyncing && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-red-500/30 shadow-inner shrink-0">
                <Sparkles className="w-3.5 h-3.5 text-[#CC0000] animate-spin" />
                <span className="text-xs font-bold kaltemp-brand-thinking-text">
                  Sincronizando datos...
                </span>
              </div>
            )}
          </div>

          {/* Usuario (trasladado desde Sidebar.tsx 07-ago-2026) */}
          <UserMenu isDark={isDark} />
        </div>
      </header>
    </>
  );
};
