// ============================================================
// ARCHIVO: Sidebar.tsx
// RUTA: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\components\Sidebar.tsx
// ============================================================

import React, { useState, useEffect } from 'react';
import { useGlobalFilter, ALL_CATEGORIES, ALL_CHANNELS, ALL_REPS, ALL_WAREHOUSES } from '../context/FilterContext';
import { useUser } from '../context/UserContext';
import { MultiSelectDropdown } from './MultiSelectDropdown';
import { DateRangePicker } from './DateRangePicker';
import { downloadVentasExcel, fetchCategoriasPendientes, fetchCampanasPendientes, fetchPesoPendientes, fetchSyncStatus } from '../services/api';
import { UserManagementModal } from './UserManagementModal';
import { CategoriaAlertaModal } from './CategoriaAlertaModal';
import { CampanaCategoriaAlertaModal } from './CampanaCategoriaAlertaModal';
import { PesoAlertaModal } from './PesoAlertaModal';
import { DataSyncModal } from './DataSyncModal';
import { DatosManualesModal } from './DatosManualesModal';
import {
  Home,
  LayoutDashboard,
  Package,
  Boxes,
  ClipboardList,
  FileSpreadsheet,
  Truck,
  Send,
  Target,
  Award,
  ShoppingCart,
  Megaphone,
  TrendingUp,
  Building2,
  Building,
  Thermometer,
  LogOut,
  Sun,
  Moon,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Weight,
  Database,
  Shield,
  UserCheck,
  Wallet,
  Clock
} from 'lucide-react';
import { ModuleId, ThemeMode, BrandMode } from '../types';
import { getBrandTokens } from '../theme/brandTokens';

interface SidebarProps {
  activeModule: ModuleId;
  onSelectModule: (m: ModuleId) => void;
  theme: ThemeMode;
  onThemeToggle?: () => void;
  brandMode: BrandMode;
  onBrandModeChange?: (m: BrandMode) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (d: string) => void;
  onEndDateChange: (d: string) => void;
  selectedCategory?: string;
  onCategoryChange?: (cat: string) => void;
  onOpenKpiReview: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  userEmail?: string;
  userName?: string;
  onLogout?: () => void;
}

interface NavGroup {
  category: string;
  items: {
    id: ModuleId;
    label: string;
    icon: React.ElementType;
    badge?: string;
  }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    category: '📊 Resumen',
    items: [
      { id: 'resumen', label: 'Resumen', icon: LayoutDashboard }
    ]
  },
  {
    category: '🏠 General',
    items: [
      { id: 'principal', label: 'Principal', icon: Home },
      { id: 'cumplimiento_ventas', label: 'Cumplimiento Ventas (25-24)', icon: Award },
      { id: 'ventas_sku', label: 'Ventas por SKU', icon: Package }
    ]
  },
  {
    category: '🗃️ Bsale',
    items: [
      { id: 'stock', label: 'Stock', icon: Boxes },
      { id: 'pendientes_despacho', label: 'Pendientes por Despachar', icon: ClipboardList, badge: '4' },
      { id: 'notas_credito', label: 'Notas de Crédito', icon: FileSpreadsheet, badge: '3' }
    ]
  },
  {
    category: '🚚 Logística',
    items: [
      { id: 'fulfillment', label: 'Detalle Fulfillment', icon: Truck },
      { id: 'control_logistico', label: 'Control Logístico', icon: Send, badge: '2' }
    ]
  },
  {
    category: '📣 Marketing & CRM',
    items: [
      { id: 'leads', label: 'Leads', icon: Target },
      { id: 'carros_abandonados', label: 'Carros Abandonados', icon: ShoppingCart },
      { id: 'campanas_mkt', label: 'Campañas de Marketing', icon: Megaphone }
    ]
  },
  {
    category: '🌐 Canales & Analítica',
    items: [
      { id: 'indicadores_d2c', label: 'Indicadores D2C', icon: TrendingUp },
      { id: 'distribuidores', label: 'Indicadores Distribuidores', icon: Building2 },
      { id: 'inmobiliaria', label: 'Indicadores Inmobiliaria', icon: Building },
      { id: 'ventas_temperatura', label: 'Ventas Vs Temperatura', icon: Thermometer }
    ]
  }
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeModule,
  onSelectModule,
  theme,
  onThemeToggle,
  brandMode,
  onBrandModeChange,
  isCollapsed,
  onToggleCollapse,
  userEmail: propEmail,
  userName: propName,
  onLogout
}) => {
  const isDark = theme === 'dark';
  const brandTokens = getBrandTokens(brandMode, isDark);
  const {
    selectedCategories,
    setSelectedCategories,
    selectedChannels,
    setSelectedChannels,
    selectedReps,
    setSelectedReps,
    selectedWarehouses,
    setSelectedWarehouses,
    startDate,
    setStartDate,
    endDate,
    setEndDate
  } = useGlobalFilter();

  const { currentUser, isModuleAllowed, users, impersonate } = useUser();
  const userName = currentUser?.nombre || propName || 'William Garrido';
  const userEmail = currentUser?.email || propEmail || 'william@kaltemp.cl';
  const isWilliam = currentUser?.email.toLowerCase() === 'william@kaltemp.cl';
  const isManuel = currentUser?.email.toLowerCase() === 'manuel@kaltemp.cl';
  const puedeBajarExcel = isWilliam || isManuel;

  const [downloading, setDownloading] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showDataSyncModal, setShowDataSyncModal] = useState(false);
  const [showCategoriaModal, setShowCategoriaModal] = useState(false);
  const [categoriasPendientesCount, setCategoriasPendientesCount] = useState(0);
  const [showCampanaCategoriaModal, setShowCampanaCategoriaModal] = useState(false);
  const [campanasPendientesCount, setCampanasPendientesCount] = useState(0);
  const [showPesoModal, setShowPesoModal] = useState(false);
  const [pesoPendientesCount, setPesoPendientesCount] = useState(0);
  const [showDatosManualesModal, setShowDatosManualesModal] = useState(false);
  const [showFiltrosGlobales, setShowFiltrosGlobales] = useState(false);
  const [ultimaActualizacion, setUltimaActualizacion] = useState<string | null | undefined>(undefined);

  const cargarUltimaActualizacion = () => {
    fetchSyncStatus()
      .then((res) => setUltimaActualizacion(res.terminado_en))
      .catch(() => setUltimaActualizacion(null));
  };

  const formatUltimaActualizacion = (iso: string | null | undefined): string => {
    if (ultimaActualizacion === undefined) return 'Cargando...';
    if (!iso) return 'Sin datos';
    const fecha = new Date(iso);
    if (isNaN(fecha.getTime())) return 'Sin datos';
    const diffMin = Math.floor((Date.now() - fecha.getTime()) / 60000);
    if (diffMin < 1) return 'hace instantes';
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffHoras = Math.floor(diffMin / 60);
    if (diffHoras < 24) return `hace ${diffHoras} h`;
    return fecha.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit' }) +
      ' ' + fecha.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
  };

  const cargarCategoriasPendientes = () => {
    fetchCategoriasPendientes()
      .then((res) => setCategoriasPendientesCount(res.total))
      .catch(() => {});
  };

  const cargarCampanasPendientes = () => {
    fetchCampanasPendientes()
      .then((res) => setCampanasPendientesCount(res.total))
      .catch(() => {});
  };

  const cargarPesoPendientes = () => {
    fetchPesoPendientes()
      .then((res) => setPesoPendientesCount(res.total))
      .catch(() => {});
  };

  useEffect(() => {
    cargarCategoriasPendientes();
    cargarCampanasPendientes();
    cargarPesoPendientes();
    cargarUltimaActualizacion();
    const intervalo = setInterval(cargarUltimaActualizacion, 5 * 60 * 1000);
    return () => clearInterval(intervalo);
  }, []);

  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>({});

  const toggleGroup = (category: string) => {
    setOpenGroups((prev) => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  const handleExportExcel = async () => {
    setDownloading(true);
    try {
      const catParam = selectedCategories.length === 1 ? selectedCategories[0] : undefined;
      const chanParam = selectedChannels.length === 1 ? selectedChannels[0] : undefined;
      await downloadVentasExcel(startDate, endDate, chanParam, catParam);
    } catch (err) {
      console.error('Error al exportar Excel:', err);
      alert('Hubo un problema al generar el archivo Excel.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <>
      <aside
        className={`shrink-0 border-r flex flex-col justify-between select-none overflow-x-hidden transition-[width] duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
          isCollapsed ? 'w-[70px]' : 'w-64'
        } ${
          isDark 
            ? 'bg-[#121214] border-[#2C2C2E] text-[#F5F5F7]' 
            : 'bg-[#EAEBED] border-slate-300/80 text-[#1D1D1F]'
        }`}
      >
        {/* Filete superior de marca -- responde al modo de marca global (ver theme/brandTokens.ts) */}
        <div
          className="h-[3px] w-full shrink-0"
          style={{ background: brandTokens.hairline }}
        />

        {/* Top Header / Branding */}
        <div className={`p-3.5 border-b flex items-center gap-2.5 ${
          isDark ? 'border-[#2C2C2E]' : 'border-slate-300/70'
        }`}>
          <div
            onClick={onToggleCollapse}
            className="w-9 h-9 rounded-[13px] flex items-center justify-center shrink-0 cursor-pointer border transition-transform active:scale-90 duration-150"
            style={{
              background: isDark ? '#2A2A32' : '#1a1a1e',
              borderColor: isDark ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.1)',
              boxShadow:
                'inset 0 1px 0 rgba(255,255,255,0.14), 0 5px 14px rgba(196,64,14,0.3), 0 5px 14px rgba(15,76,129,0.24)',
            }}
            title={isCollapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
          >
            <svg width="20" height="20" viewBox="0 0 100 100" fill="none">
              <defs>
                <linearGradient id="sbStrokeWarm" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F2954A" />
                  <stop offset="100%" stopColor="#C4400E" />
                </linearGradient>
                <linearGradient id="sbStrokeCool" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4FA8DE" />
                  <stop offset="100%" stopColor="#0F4C81" />
                </linearGradient>
                <linearGradient id="sbStrokeBar" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#E8791A" />
                  <stop offset="100%" stopColor="#1D6FA5" />
                </linearGradient>
              </defs>
              <path d="M50 12 L20 88" stroke="url(#sbStrokeWarm)" strokeWidth="14" strokeLinecap="round" />
              <path d="M50 12 L80 88" stroke="url(#sbStrokeCool)" strokeWidth="14" strokeLinecap="round" />
              <path d="M33 63 L67 63" stroke="url(#sbStrokeBar)" strokeWidth="11" strokeLinecap="round" />
            </svg>
          </div>

          <div className={`overflow-hidden transition-all duration-300 ease-out whitespace-nowrap ${
            isCollapsed ? 'w-0 opacity-0 pointer-events-none' : 'w-auto opacity-100'
          }`}>
            <span className={`font-extrabold text-lg tracking-tight block leading-none ${
              isDark ? 'text-white' : 'text-[#1D1D1F]'
            }`}>
              Analítica
            </span>
          </div>
        </div>

        {/* Main Scrollable Content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-3 py-2">
          <div className="px-2 space-y-2.5">
            {NAV_GROUPS.map((group) => {
              const allowedItems = group.items.filter((item) => isModuleAllowed(item.id));
              if (allowedItems.length === 0) return null;

              const isOpen = openGroups[group.category] ?? false;
              const groupBadges = allowedItems.reduce((acc, item) => acc + (Number(item.badge) || 0), 0);
              const hasActiveItem = allowedItems.some((item) => item.id === activeModule);

              return (
                <div key={group.category} className="space-y-0.5">
                  {/* Encabezado del grupo (solo se muestra o expande texto en full) */}
                  <button
                    onClick={() => toggleGroup(group.category)}
                    className={`w-full flex items-center justify-between px-2 py-1 rounded-lg text-[10px] font-extrabold uppercase tracking-wider transition-colors overflow-hidden ${
                      isCollapsed ? 'hidden' : 'flex'
                    } ${
                      hasActiveItem && !isOpen
                        ? 'text-[#CC0000] font-black'
                        : isDark
                        ? 'text-[#8E8E93] hover:text-white hover:bg-[#2C2C2E]/60'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-300/50'
                    }`}
                  >
                    <span className="truncate">{group.category}</span>
                    <div className="flex items-center gap-1 shrink-0">
                      {!isOpen && groupBadges > 0 && (
                        <span className="px-1.5 py-0.2 text-[9px] font-bold rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30">
                          {groupBadges}
                        </span>
                      )}
                      <div className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
                        <ChevronDown className="w-3.5 h-3.5 opacity-60" />
                      </div>
                    </div>
                  </button>

                  {/* Contenedor de Items con animación CSS Grid */}
                  <div className={`grid transition-all duration-200 ease-in-out ${
                    isOpen || isCollapsed ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                  }`}>
                    <div className="overflow-hidden space-y-0.5">
                      {allowedItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeModule === item.id;

                        return (
                          <button
                            key={item.id}
                            onClick={() => onSelectModule(item.id)}
                            title={isCollapsed ? item.label : undefined}
                            className={`w-full flex items-center rounded-xl text-xs font-semibold transition-all duration-150 relative h-9 ${
                              isCollapsed ? 'justify-center px-0' : 'justify-between px-2.5'
                            } ${
                              isActive
                                ? isDark
                                  ? 'bg-white/[0.08] text-white font-bold shadow-sm'
                                  : 'bg-white text-slate-900 font-bold shadow-sm'
                                : isDark
                                ? 'text-[#F5F5F7] hover:bg-[#2C2C2E]'
                                : 'text-slate-700 hover:bg-slate-300/60'
                            }`}
                          >
                            {/* Barra activa -- color según el modo de marca */}
                            {isActive && (
                              <div
                                className={`absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full transition-all duration-200 ${
                                  isCollapsed ? 'hidden' : 'block'
                                }`}
                                style={{ background: brandTokens.activeBar }}
                              />
                            )}

                            <div className="flex items-center gap-2.5 min-w-0">
                              <Icon
                                className="w-4 h-4 shrink-0 transition-colors duration-150"
                                style={{ color: brandTokens.accent }}
                              />
                              <div className={`overflow-hidden transition-all duration-200 whitespace-nowrap text-left ${
                                isCollapsed ? 'w-0 opacity-0 pointer-events-none' : 'w-auto opacity-100'
                              }`}>
                                <span className="truncate">{item.label}</span>
                              </div>
                            </div>

                            {/* Badge */}
                            {!isCollapsed && item.badge && (
                              <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shrink-0">
                                {item.badge}
                              </span>
                            )}
                            {isCollapsed && item.badge && (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 absolute top-1.5 right-1.5" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Grupo "Herramientas" (Solo William) */}
            {isWilliam && (() => {
              const TOOLS_KEY = '🛠️ Herramientas';
              const isToolsOpen = openGroups[TOOLS_KEY] ?? false;
              const toolsBadges = categoriasPendientesCount + campanasPendientesCount + pesoPendientesCount;
              const toolItems = [
                {
                  id: 'categorias',
                  label: 'Categorías Pendientes',
                  icon: AlertTriangle,
                  badge: categoriasPendientesCount > 0 ? String(categoriasPendientesCount) : undefined,
                  onClick: () => setShowCategoriaModal(true),
                },
                {
                  id: 'campanas',
                  label: 'Campañas Pendientes',
                  icon: Megaphone,
                  badge: campanasPendientesCount > 0 ? String(campanasPendientesCount) : undefined,
                  onClick: () => setShowCampanaCategoriaModal(true),
                },
                {
                  id: 'peso',
                  label: 'Peso/Medidas Pendientes',
                  icon: Weight,
                  badge: pesoPendientesCount > 0 ? String(pesoPendientesCount) : undefined,
                  onClick: () => setShowPesoModal(true),
                },
                {
                  id: 'duckdb',
                  label: 'DuckDB / Drive',
                  icon: Database,
                  onClick: () => setShowDataSyncModal(true),
                },
                {
                  id: 'datos_manuales',
                  label: 'Datos Manuales',
                  icon: Wallet,
                  onClick: () => setShowDatosManualesModal(true),
                },
              ];

              return (
                <div className="space-y-0.5">
                  <button
                    onClick={() => toggleGroup(TOOLS_KEY)}
                    className={`w-full flex items-center justify-between px-2 py-1 rounded-lg text-[10px] font-extrabold uppercase tracking-wider transition-colors overflow-hidden ${
                      isCollapsed ? 'hidden' : 'flex'
                    } ${
                      isDark
                        ? 'text-[#8E8E93] hover:text-white hover:bg-[#2C2C2E]/60'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-300/50'
                    }`}
                  >
                    <span className="truncate">{TOOLS_KEY}</span>
                    <div className="flex items-center gap-1 shrink-0">
                      {!isToolsOpen && toolsBadges > 0 && (
                        <span className="px-1.5 py-0.2 text-[9px] font-bold rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30">
                          {toolsBadges}
                        </span>
                      )}
                      <div className={`transition-transform duration-200 ${isToolsOpen ? 'rotate-180' : ''}`}>
                        <ChevronDown className="w-3.5 h-3.5 opacity-60" />
                      </div>
                    </div>
                  </button>

                  <div className={`grid transition-all duration-200 ease-in-out ${
                    isToolsOpen || isCollapsed ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                  }`}>
                    <div className="overflow-hidden space-y-0.5">
                      {toolItems.map((item) => {
                        const Icon = item.icon;
                        return (
                          <button
                            key={item.id}
                            onClick={item.onClick}
                            title={isCollapsed ? item.label : undefined}
                            className={`w-full flex items-center rounded-xl text-xs font-semibold transition-all duration-150 relative h-9 ${
                              isCollapsed ? 'justify-center px-0' : 'justify-between px-2.5'
                            } ${
                              isDark
                                ? 'text-[#F5F5F7] hover:bg-[#2C2C2E]'
                                : 'text-slate-700 hover:bg-slate-300/60'
                            }`}
                          >
                            <div className="flex items-center gap-2.5 min-w-0">
                              <Icon className="w-4 h-4 shrink-0 text-[#CC0000]" />
                              <div className={`overflow-hidden transition-all duration-200 whitespace-nowrap text-left ${
                                isCollapsed ? 'w-0 opacity-0 pointer-events-none' : 'w-auto opacity-100'
                              }`}>
                                <span className="truncate">{item.label}</span>
                              </div>
                            </div>

                            {!isCollapsed && item.badge && (
                              <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shrink-0">
                                {item.badge}
                              </span>
                            )}
                            {isCollapsed && item.badge && (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 absolute top-1.5 right-1.5" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Panel de Filtros Globales (con transición de opacidad y visibilidad) */}
          <div className={`mx-2.5 space-y-2 transition-all duration-200 ${
            isCollapsed ? 'opacity-0 pointer-events-none h-0 overflow-hidden' : 'opacity-100 h-auto'
          }`}>
            <div className={`rounded-2xl border overflow-hidden transition-all ${
              isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-300/80 shadow-sm'
            }`}>
              <button
                onClick={() => setShowFiltrosGlobales((prev) => !prev)}
                className="w-full flex items-center justify-between p-3 cursor-pointer"
              >
                <span className={`text-[11px] font-extrabold uppercase tracking-wider ${
                  isDark ? 'text-[#8E8E93]' : 'text-slate-600'
                }`}>
                  ⚙️ Filtros Globales
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-red-500/10 text-[#CC0000]">
                    Filtros
                  </span>
                  <div className={`transition-transform duration-200 ${showFiltrosGlobales ? 'rotate-180' : ''}`}>
                    <ChevronDown className="w-3.5 h-3.5 opacity-60" />
                  </div>
                </div>
              </button>

              <div className={`grid transition-all duration-200 ease-in-out ${
                showFiltrosGlobales ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
              }`}>
                <div className="overflow-hidden px-3 pb-3 space-y-1.5">
                  <DateRangePicker
                    startDate={startDate}
                    endDate={endDate}
                    onSelectRange={(start, end) => {
                      setStartDate(start);
                      setEndDate(end);
                    }}
                    theme={theme}
                  />

                  <MultiSelectDropdown
                    label="🏷️ Categoría SKU"
                    options={ALL_CATEGORIES}
                    selectedValues={selectedCategories}
                    onChange={setSelectedCategories}
                    placeholder="Todas las Categorías"
                    theme={theme}
                  />

                  <MultiSelectDropdown
                    label="🏬 Canal de Venta"
                    options={ALL_CHANNELS}
                    selectedValues={selectedChannels}
                    onChange={setSelectedChannels}
                    placeholder="Todos los Canales"
                    theme={theme}
                  />

                  <MultiSelectDropdown
                    label="👤 Vendedor"
                    options={ALL_REPS}
                    selectedValues={selectedReps}
                    onChange={setSelectedReps}
                    placeholder="Todos los Vendedores"
                    theme={theme}
                  />

                  <MultiSelectDropdown
                    label="🏭 Bodega"
                    options={ALL_WAREHOUSES}
                    selectedValues={selectedWarehouses}
                    onChange={setSelectedWarehouses}
                    placeholder="Todas las Bodegas"
                    theme={theme}
                  />
                </div>
              </div>
            </div>

            {onBrandModeChange && (
              <div className="grid grid-cols-3 gap-1">
                {(['standard', 'kaltemp', 'tompalmer'] as const).map((modo) => {
                  const activo = brandMode === modo;
                  const tokensBoton = getBrandTokens(modo, isDark);
                  const etiqueta = modo === 'standard' ? 'Standard' : modo === 'kaltemp' ? 'Kaltemp' : 'Tom Palmer';
                  return (
                    <button
                      key={modo}
                      onClick={() => onBrandModeChange(modo)}
                      title={`Modo ${etiqueta}`}
                      className={`py-1.5 px-1 rounded-lg text-[9.5px] font-bold border transition-all truncate ${
                        activo
                          ? isDark ? 'text-white' : 'text-white'
                          : isDark
                          ? 'bg-[#1C1C1E] border-[#2C2C2E] text-[#8E8E93] hover:text-white'
                          : 'bg-white border-slate-300/80 text-slate-500 hover:text-slate-800'
                      }`}
                      style={activo ? { background: tokensBoton.hairline, borderColor: 'transparent' } : undefined}
                    >
                      {etiqueta}
                    </button>
                  );
                })}
              </div>
            )}

            {onThemeToggle && (
              <button
                onClick={onThemeToggle}
                className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                  isDark
                    ? 'bg-[#1C1C1E] border-[#2C2C2E] text-amber-400 hover:bg-[#2C2C2E]'
                    : 'bg-white border-slate-300/80 text-amber-700 hover:bg-slate-100 shadow-sm'
                }`}
                title={isDark ? 'Modo Claro' : 'Modo Oscuro'}
              >
                {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                <span>{isDark ? 'Modo Claro' : 'Modo Oscuro'}</span>
              </button>
            )}

            {/* Última actualización */}
            <button
              onClick={cargarUltimaActualizacion}
              title="Haz clic para refrescar el estado de sincronización"
              className={`w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-xl text-[10.5px] font-medium transition-colors cursor-pointer ${
                isDark ? 'text-[#8E8E93] hover:text-white' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Clock className="w-3 h-3 shrink-0" />
              <span className="truncate">Actualizado {formatUltimaActualizacion(ultimaActualizacion)}</span>
            </button>
          </div>
        </div>

        {/* Footer / Bajar Excel & Sesión */}
        <div
          className={`p-2.5 border-t text-xs space-y-2 transition-all ${
            isDark ? 'border-[#2C2C2E] bg-[#1C1C1E]' : 'border-slate-300/80 bg-[#E2E5EA]'
          }`}
        >
          {puedeBajarExcel && (
            <div className="pb-1 border-b border-slate-300/70 dark:border-[#2C2C2E]">
              <button
                onClick={handleExportExcel}
                disabled={downloading}
                className={`w-full flex items-center justify-center gap-1.5 rounded-xl text-[11px] font-bold border transition-all cursor-pointer disabled:opacity-50 h-8 ${
                  isDark
                    ? 'bg-[#121214] border-[#2C2C2E] text-[#F5F5F7] hover:border-red-500 hover:text-[#CC0000]'
                    : 'bg-white border-slate-300 text-slate-800 hover:border-red-500 hover:text-[#CC0000] shadow-sm'
                }`}
                title="Bajar Excel Consolidado"
              >
                {downloading ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#CC0000]" />
                ) : (
                  <Download className="w-3.5 h-3.5 text-[#CC0000]" />
                )}
                <div className={`overflow-hidden transition-all duration-200 whitespace-nowrap ${
                  isCollapsed ? 'w-0 opacity-0 pointer-events-none' : 'w-auto opacity-100'
                }`}>
                  <span>Bajar Excel</span>
                </div>
              </button>
            </div>
          )}

          {/* Sección de Usuario */}
          <div className="relative">
            <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
              <button
                onClick={() => {
                  if (isWilliam) setShowUserDropdown(!showUserDropdown);
                }}
                className={`flex items-center gap-2 min-w-0 text-left rounded-xl p-1 transition-colors ${
                  isWilliam ? 'hover:bg-slate-300/50 dark:hover:bg-slate-500/10 cursor-pointer' : ''
                }`}
                title={isWilliam ? 'Cambiar sesión de usuario' : undefined}
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs text-white shrink-0 shadow"
                  style={{ backgroundColor: currentUser?.avatarColor || '#CC0000' }}
                >
                  {userName.charAt(0)}
                </div>
                <div className={`overflow-hidden transition-all duration-200 whitespace-nowrap min-w-0 ${
                  isCollapsed ? 'w-0 opacity-0 pointer-events-none' : 'w-auto opacity-100'
                }`}>
                  <p className="font-bold text-xs truncate flex items-center gap-1">
                    {userName}
                    {isWilliam && <ChevronDown className="w-3 h-3 text-slate-500 shrink-0" />}
                  </p>
                  <p className={`text-[10px] truncate ${isDark ? 'text-[#8E8E93]' : 'text-slate-600'}`}>
                    {currentUser?.rol || userEmail}
                  </p>
                </div>
              </button>

              {!isCollapsed && onLogout && (
                <button
                  onClick={onLogout}
                  className={`p-1.5 rounded-lg border transition-all shrink-0 cursor-pointer ${
                    isDark 
                      ? 'bg-[#1C1C1E] border-[#2C2C2E] text-slate-400 hover:text-red-400 hover:border-red-500/30' 
                      : 'bg-white border-slate-300 text-slate-600 hover:text-red-600 hover:border-red-300 shadow-sm'
                  }`}
                  title="Cerrar sesión"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Dropdown Menu de Cambio de Usuario (Solo William) */}
            {isWilliam && showUserDropdown && (
              <div
                className={`absolute bottom-full ${
                  isCollapsed ? 'left-full ml-2' : 'left-0 mb-2'
                } w-64 rounded-2xl border shadow-2xl overflow-hidden z-50 p-1.5 ${
                  isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-300 text-slate-900'
                }`}
              >
                <div className="px-3 py-2 border-b border-slate-200 dark:border-[#2C2C2E] mb-1">
                  <p className="text-[10px] font-black uppercase tracking-wider text-[#CC0000]">
                    Cambiar Sesión de Usuario (RBAC)
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Selecciona un usuario para verificar sus permisos:
                  </p>
                </div>

                <div className="max-h-60 overflow-y-auto space-y-0.5">
                  {users.map((usr) => {
                    const isSelected = usr.email.toLowerCase() === currentUser?.email.toLowerCase();
                    return (
                      <button
                        key={usr.email}
                        onClick={() => {
                          impersonate(usr.id).catch((err) => console.error('No se pudo simular la sesión:', err));
                          setShowUserDropdown(false);
                        }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-xl text-xs flex items-center justify-between transition-colors ${
                          isSelected
                            ? 'bg-[#CC0000] text-white font-black'
                            : isDark
                            ? 'hover:bg-[#2C2C2E] text-slate-200 font-medium'
                            : 'hover:bg-slate-100 text-slate-800 font-medium'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <div
                            className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-black text-white shrink-0"
                            style={{ backgroundColor: usr.avatarColor }}
                          >
                            {usr.nombre.charAt(0)}
                          </div>
                          <div className="truncate">
                            <p className="text-[11px] leading-tight truncate font-bold">{usr.nombre}</p>
                            <p className={`text-[9px] font-mono leading-tight ${isSelected ? 'text-red-100' : 'text-slate-500'}`}>
                              {usr.rol}
                            </p>
                          </div>
                        </div>
                        {isSelected && <UserCheck className="w-3.5 h-3.5 shrink-0" />}
                      </button>
                    );
                  })}
                </div>

                <div className="p-1.5 border-t border-slate-200 dark:border-[#2C2C2E] mt-1">
                  <button
                    onClick={() => {
                      setShowUserDropdown(false);
                      setShowModal(true);
                    }}
                    className="w-full py-1.5 px-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-[#CC0000] font-extrabold text-[11px] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Shield className="w-3.5 h-3.5" /> Ver Matriz de Permisos
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Modales */}
      <UserManagementModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        isDark={isDark}
      />

      <DataSyncModal
        isOpen={showDataSyncModal}
        onClose={() => setShowDataSyncModal(false)}
        isDark={isDark}
      />

      <CategoriaAlertaModal
        isOpen={showCategoriaModal}
        onClose={() => { setShowCategoriaModal(false); cargarCategoriasPendientes(); }}
        isDark={isDark}
        onCambiosGuardados={cargarCategoriasPendientes}
      />

      <CampanaCategoriaAlertaModal
        isOpen={showCampanaCategoriaModal}
        onClose={() => { setShowCampanaCategoriaModal(false); cargarCampanasPendientes(); }}
        isDark={isDark}
        onCambiosGuardados={cargarCampanasPendientes}
      />

      <PesoAlertaModal
        isOpen={showPesoModal}
        onClose={() => { setShowPesoModal(false); cargarPesoPendientes(); }}
        isDark={isDark}
        onCambiosGuardados={cargarPesoPendientes}
      />

      <DatosManualesModal
        isOpen={showDatosManualesModal}
        onClose={() => setShowDatosManualesModal(false)}
        isDark={isDark}
      />
    </>
  );
};