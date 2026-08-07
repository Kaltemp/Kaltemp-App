import React, { useState, useEffect } from 'react';
import { useGlobalFilter, ALL_CATEGORIES, ALL_CHANNELS, ALL_REPS, ALL_WAREHOUSES } from '../context/FilterContext';
import { useUser } from '../context/UserContext';
import { MultiSelectDropdown } from './MultiSelectDropdown';
import { DateRangePicker } from './DateRangePicker';
import { downloadVentasExcel, fetchCategoriasPendientes, fetchCampanasPendientes } from '../services/api';

// Logos reales de Kaltemp (07-ago-2026) -- mismos que LoginView.tsx.
const KALTEMP_LOGO_CONDENSADO = 'https://cdn.shopify.com/s/files/1/0656/1605/2459/files/Logo_Kaltemp_Condensado.png?v=1786109942';
const KALTEMP_LOGO_HORIZONTAL = 'https://kaltemp.cl/cdn/shop/files/Logo_Horizontal-01_PNG.png?height=96&v=1659535251';
import { CategoriaAlertaModal } from './CategoriaAlertaModal';
import { CampanaCategoriaAlertaModal } from './CampanaCategoriaAlertaModal';
import { DataSyncModal } from './DataSyncModal';
import {
  Home,
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
  Sun,
  Moon,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Database
} from 'lucide-react';
import { ModuleId, ThemeMode } from '../types';

interface SidebarProps {
  activeModule: ModuleId;
  onSelectModule: (m: ModuleId) => void;
  theme: ThemeMode;
  onThemeToggle?: () => void;
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
    category: '🏠 General',
    items: [
      { id: 'principal', label: 'Principal', icon: Home },
      { id: 'cumplimiento_ventas', label: 'Cumplimiento Ventas (25-24)', icon: Award },
      { id: 'ventas_sku', label: 'Ventas por SKU', icon: Package }
    ]
  },
  {
    // Antes eran 2 grupos separados ("🗃️ Bsale" y "🚚 Logística") --
    // fusionados (07-ago-2026) porque Fulfillment y Pendientes por
    // Despachar son la misma familia funcional (qué está por salir/salió
    // del centro de distribución, solo que por canales distintos), y
    // "Bsale" como nombre de categoría no decía nada de negocio al que lo
    // mira -- es el nombre interno del ERP, no una función.
    category: '📦 Inventario & Despacho',
    items: [
      { id: 'stock', label: 'Stock', icon: Boxes },
      { id: 'pendientes_despacho', label: 'Pendientes por Despachar', icon: ClipboardList, badge: '4' },
      { id: 'fulfillment', label: 'Detalle Fulfillment', icon: Truck },
      { id: 'control_logistico', label: 'Control Logístico', icon: Send, badge: '2' },
      { id: 'notas_credito', label: 'Notas de Crédito', icon: FileSpreadsheet, badge: '3' }
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
  isCollapsed,
  onToggleCollapse
}) => {
  const isDark = theme === 'dark';
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

  const { currentUser, isModuleAllowed } = useUser();
  const isWilliam = currentUser?.email.toLowerCase() === 'william@kaltemp.cl';

  const [downloading, setDownloading] = useState(false);
  const [showDataSyncModal, setShowDataSyncModal] = useState(false);
  const [showCategoriaModal, setShowCategoriaModal] = useState(false);
  const [categoriasPendientesCount, setCategoriasPendientesCount] = useState(0);
  const [showCampanaCategoriaModal, setShowCampanaCategoriaModal] = useState(false);
  const [campanasPendientesCount, setCampanasPendientesCount] = useState(0);

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

  useEffect(() => {
    cargarCategoriasPendientes();
    cargarCampanasPendientes();
  }, []);

  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    NAV_GROUPS.forEach((group) => {
      initial[group.category] = group.items.some((item) => item.id === activeModule);
    });
    return initial;
  });

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
        className={`shrink-0 border-r flex flex-col justify-between transition-all duration-300 select-none ${
          isCollapsed ? 'w-16' : 'w-64'
        } ${
          isDark ? 'bg-[#121214] border-[#2C2C2E] text-[#F5F5F7]' : 'bg-[#F2F2F7] border-slate-200/80 text-[#1D1D1F]'
        }`}
      >
        {/* Top Header / Branding */}
        <div className={`border-b flex items-center gap-2 transition-all ${
          isCollapsed ? 'justify-center px-2 py-3.5' : 'justify-between p-3.5'
        } ${
          isDark ? 'border-[#2C2C2E]' : 'border-slate-200/80'
        }`}>
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              onClick={onToggleCollapse}
              className="relative p-[2px] rounded-2xl overflow-hidden shrink-0 group cursor-pointer shadow-lg transition-transform active:scale-95"
              title={isCollapsed ? 'Haz clic para expandir la barra lateral' : 'Haz clic para colapsar la barra lateral'}
            >
              {/* Glow: -1000% (el valor original) es innecesariamente
                  enorme y puede generar imprecisión de render en algunos
                  navegadores en los bordes del recorte -- 75% ya es de
                  sobra para que las esquinas del cuadrado girando nunca
                  entren al área visible, y el overflow-hidden + rounded-2xl
                  del wrapper sigue recortando todo en forma de cuadrado
                  con esquinas redondeadas (no círculo) (07-ago-2026) */}
              <div className="absolute inset-[-75%] bg-[conic-gradient(from_90deg_at_50%_50%,#CC0000_0%,#58C6E5_33%,#800404_66%,#CC0000_100%)] animate-[spin_8s_linear_infinite]" />
              <div className="relative w-9 h-9 rounded-[14px] bg-white flex items-center justify-center shadow-inner overflow-hidden">
                <img
                  src={KALTEMP_LOGO_CONDENSADO}
                  alt="Kaltemp"
                  className="w-full h-full object-contain p-0.5"
                />
              </div>
            </div>

            {!isCollapsed && (
              <div className="flex items-center min-w-0">
                <img
                  src={KALTEMP_LOGO_HORIZONTAL}
                  alt="Kaltemp"
                  className="h-7 object-contain"
                />
              </div>
            )}
          </div>
        </div>

        {/* Main Scrollable Content */}
        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          <div className="px-2 space-y-3">
            {NAV_GROUPS.map((group) => {
              const allowedItems = group.items.filter((item) => isModuleAllowed(item.id));
              if (allowedItems.length === 0) return null;

              const isOpen = openGroups[group.category] ?? true;
              const groupBadges = allowedItems.reduce((acc, item) => acc + (Number(item.badge) || 0), 0);
              const hasActiveItem = allowedItems.some((item) => item.id === activeModule);

              return (
                <div key={group.category} className="space-y-1">
                  {!isCollapsed && (
                    <button
                      onClick={() => toggleGroup(group.category)}
                      className={`w-full flex items-center justify-between px-2 py-1 rounded-lg text-[10px] font-extrabold uppercase tracking-wider transition-colors ${
                        hasActiveItem && !isOpen
                          ? 'text-[#CC0000] font-black'
                          : isDark
                          ? 'text-[#8E8E93] hover:text-white hover:bg-[#2C2C2E]/60'
                          : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/60'
                      }`}
                    >
                      <span className="truncate">{group.category}</span>
                      <div className="flex items-center gap-1 shrink-0">
                        {!isOpen && groupBadges > 0 && (
                          <span className="px-1.5 py-0.2 text-[9px] font-bold rounded-full bg-amber-500/20 text-amber-500 border border-amber-500/30">
                            {groupBadges}
                          </span>
                        )}
                        {isOpen ? (
                          <ChevronDown className="w-3.5 h-3.5 opacity-60" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                        )}
                      </div>
                    </button>
                  )}

                  {(isOpen || isCollapsed) && (
                    <div className="space-y-0.5">
                      {allowedItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeModule === item.id;

                        return (
                          <button
                            key={item.id}
                            onClick={() => onSelectModule(item.id)}
                            title={isCollapsed ? item.label : undefined}
                            className={`w-full flex items-center ${
                              isCollapsed ? 'justify-center py-2.5 px-0' : 'justify-between px-2.5 py-2'
                            } rounded-xl text-xs font-semibold transition-all relative ${
                              isActive
                                ? 'bg-[#CC0000] text-white shadow-md shadow-red-500/20'
                                : isDark
                                ? 'text-[#F5F5F7] hover:bg-[#2C2C2E]'
                                : 'text-slate-700 hover:bg-slate-200/70'
                            }`}
                          >
                            <div className="flex items-center gap-2.5 truncate">
                              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-[#CC0000]'}`} />
                              {!isCollapsed && <span className="truncate">{item.label}</span>}
                            </div>

                            {!isCollapsed && item.badge && (
                              <span
                                className={`px-1.5 py-0.5 text-[10px] font-bold rounded-full ${
                                  isActive
                                    ? 'bg-white/20 text-white'
                                    : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                                }`}
                              >
                                {item.badge}
                              </span>
                            )}
                            {isCollapsed && item.badge && (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 absolute top-1 right-1" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Panel de Filtros Globales */}
          {!isCollapsed ? (
            <div className="mx-2.5 space-y-2">
              <div className={`p-3 rounded-2xl border space-y-2 ${
                isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200/80 shadow-sm'
              }`}>
                <div className="flex items-center justify-between">
                  <span className={`text-[11px] font-extrabold uppercase tracking-wider ${
                    isDark ? 'text-[#8E8E93]' : 'text-slate-400'
                  }`}>
                    ⚙️ Filtros Globales
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-red-500/10 text-[#CC0000]">
                    Filtros
                  </span>
                </div>

                <div className="space-y-1">
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

              {onThemeToggle && (
                <button
                  onClick={onThemeToggle}
                  className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                    isDark
                      ? 'bg-[#1C1C1E] border-[#2C2C2E] text-amber-400 hover:bg-[#2C2C2E]'
                      : 'bg-[#1C1C1E] bg-white border-slate-200 text-amber-600 hover:bg-slate-100 shadow-sm'
                  }`}
                  title={isDark ? 'Modo Claro' : 'Modo Oscuro'}
                >
                  {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                  <span>{isDark ? 'Modo Claro' : 'Modo Oscuro'}</span>
                </button>
              )}
            </div>
          ) : null}
        </div>

        {/* Herramientas Especiales / Admin */}
        <div className={`p-2.5 border-t text-xs space-y-2 ${
          isDark ? 'border-[#2C2C2E] bg-[#121214]' : 'border-slate-200 bg-slate-50'
        }`}>
          {/* Botón de Categorías Pendientes (SKUs) */}
          {categoriasPendientesCount > 0 && (
            <button
              onClick={() => setShowCategoriaModal(true)}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                isDark
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20'
                  : 'bg-amber-50 border-amber-200 text-amber-600 hover:bg-amber-100'
              }`}
              title="SKUs vendidos sin categoría asignada"
            >
              <div className="flex items-center gap-2 truncate">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {!isCollapsed && <span className="truncate">Categorías</span>}
              </div>
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-black shrink-0 ${
                isDark ? 'bg-amber-500/20' : 'bg-amber-200'
              }`}>
                {categoriasPendientesCount}
              </span>
            </button>
          )}

          {/* Botón de Campañas de Marketing Pendientes (06-ago-2026) */}
          {campanasPendientesCount > 0 && (
            <button
              onClick={() => setShowCampanaCategoriaModal(true)}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                isDark
                  ? 'bg-purple-500/10 border-purple-500/30 text-purple-400 hover:bg-purple-500/20'
                  : 'bg-purple-50 border-purple-200 text-purple-600 hover:bg-purple-100'
              }`}
              title="Campañas de marketing sin categoría asignada"
            >
              <div className="flex items-center gap-2 truncate">
                <Megaphone className="w-4 h-4 shrink-0" />
                {!isCollapsed && <span className="truncate">Campañas</span>}
              </div>
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-black shrink-0 ${
                isDark ? 'bg-purple-500/20' : 'bg-purple-200'
              }`}>
                {campanasPendientesCount}
              </span>
            </button>
          )}

          {/* Botón Sincronización DuckDB / Drive (Solo William Garrido) */}
          {isWilliam && (
            <button
              onClick={() => setShowDataSyncModal(true)}
              className={`w-full flex items-center gap-2 ${
                isCollapsed ? 'justify-center py-2 px-0' : 'justify-start px-2.5 py-1.5'
              } rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                isDark
                  ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                  : 'bg-red-50 border-red-200 text-[#CC0000] hover:bg-red-100'
              }`}
              title="Sincronización de Base de Datos kaltemp_matrix.duckdb"
            >
              <Database className="w-4 h-4 text-[#CC0000] shrink-0" />
              {!isCollapsed && <span className="truncate">DuckDB / Drive</span>}
            </button>
          )}
        </div>

        {/* Footer / Bajar Excel & Sesión */}
        <div
          className={`p-2.5 border-t text-xs space-y-2.5 ${
            isDark ? 'border-[#2C2C2E] bg-[#1C1C1E]' : 'border-slate-200 bg-white'
          }`}
        >
          {!isCollapsed ? (
            <div className="pb-1 border-b border-slate-200/60 dark:border-[#2C2C2E]">
              <button
                onClick={handleExportExcel}
                disabled={downloading}
                className={`w-full flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-xl text-[11px] font-bold border transition-all cursor-pointer disabled:opacity-50 ${
                  isDark
                    ? 'bg-[#121214] border-[#2C2C2E] text-[#F5F5F7] hover:border-red-500 hover:text-[#CC0000]'
                    : 'bg-slate-50 border-slate-200 text-slate-700 hover:border-red-500 hover:text-[#CC0000]'
                }`}
              >
                {downloading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#CC0000]" />
                    <span>Generando Excel...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5 text-[#CC0000]" />
                    <span>Bajar Excel Consolidado</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 pb-1 border-b border-slate-200/60 dark:border-[#2C2C2E]">
              <button
                onClick={handleExportExcel}
                disabled={downloading}
                className={`p-2 rounded-xl border transition-all cursor-pointer disabled:opacity-50 ${
                  isDark ? 'bg-[#121214] border-[#2C2C2E] text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
                }`}
                title="Bajar Excel Consolidado"
              >
                {downloading ? (
                  <RefreshCw className="w-4 h-4 animate-spin text-[#CC0000]" />
                ) : (
                  <Download className="w-4 h-4 text-[#CC0000]" />
                )}
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Modales trasladados a la Sidebar */}
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
    </>
  );
};