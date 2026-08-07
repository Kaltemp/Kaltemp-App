import React, { useState, useEffect, useMemo } from 'react';
import { ThemeMode } from '../types';
import { TrendingUp, DollarSign, Smartphone, ShoppingBag, Eye, Zap, ArrowUpRight, CheckCircle2, RefreshCw } from 'lucide-react';
import { useGlobalFilter, ALL_CATEGORIES, ALL_CHANNELS, ALL_REPS, ALL_WAREHOUSES } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import { fetchD2CPerformance } from '../services/api';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

// Logos reales por marca (mismos que usa sync_marketing.py como respaldo
// de imagen para campañas de Google sin creative propio) -- 07-ago-2026.
const BRANDS: { id: 'Kaltemp' | 'Tom Palmer'; label: string; logo: string; color: string }[] = [
  {
    id: 'Kaltemp',
    label: 'Kaltemp',
    logo: 'https://kaltemp.cl/cdn/shop/files/Logo_Horizontal-01_PNG.png?height=96&v=1659535251',
    color: '#CC0000',
  },
  {
    id: 'Tom Palmer',
    label: 'Tom Palmer',
    logo: 'https://www.tompalmer.cl/cdn/shop/files/Diseno_sin_titulo_3.png?v=1767198984&width=500',
    color: '#B45309',
  },
];

interface Props {
  theme: ThemeMode;
}

export const D2CPerformanceView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  
  const { 
    selectedCategories,
    selectedChannels,
    selectedReps,
    selectedWarehouses,
    startDate, 
    endDate 
  } = useGlobalFilter();

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedMarca, setSelectedMarca] = useState<'Kaltemp' | 'Tom Palmer'>('Kaltemp');
  const [ga4Disponible, setGa4Disponible] = useState(true);

  const [sortKey, setSortKey] = useState<string>('venta');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const [totalSessions, setTotalSessions] = useState(0);
  const [totalMktSpend, setTotalMktSpend] = useState(0);
  const [totalD2CSales, setTotalD2CSales] = useState(0);
  const [tacosGlobal, setTacosGlobal] = useState(0);
  const [conversionRate, setConversionRate] = useState(0);
  const [bounceRate, setBounceRate] = useState(0);

  const [sessionsYoy, setSessionsYoy] = useState(0);
  const [mktSpendYoy, setMktSpendYoy] = useState(0);
  const [d2cSalesYoy, setD2cSalesYoy] = useState(0);
  const [tacosYoy, setTacosYoy] = useState(0);

  const [weeklyData, setWeeklyData] = useState<{ week: string; sessions: number; spend: number }[]>([]);
  const [categoryPerf, setCategoryPerf] = useState<any[]>([]);
  
  const [mobileSessions, setMobileSessions] = useState(0);
  const [desktopSessions, setDesktopSessions] = useState(0);
  const [addToCart, setAddToCart] = useState(0);
  const [checkouts, setCheckouts] = useState(0);
  const [transactions, setTransactions] = useState(0);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);

    const catParam = (selectedCategories && selectedCategories.length < ALL_CATEGORIES.length) ? selectedCategories.join(',') : selectedCategory;
    const chanParam = (selectedChannels && selectedChannels.length < ALL_CHANNELS.length) ? selectedChannels.join(',') : null;
    const repParam = (selectedReps && selectedReps.length < ALL_REPS.length) ? selectedReps.join(',') : null;
    const whParam = (selectedWarehouses && selectedWarehouses.length < ALL_WAREHOUSES.length) ? selectedWarehouses.join(',') : null;

    fetchD2CPerformance(startDate, endDate, catParam, chanParam, repParam, whParam, selectedMarca)
      .then((data: any) => {
        if (!data || typeof data !== 'object') return;

        setGa4Disponible(data.ga4Disponible !== false);
        setTotalSessions(Number(data.totalSessions ?? data.sesiones ?? 0));
        setTotalMktSpend(Number(data.totalMktSpend ?? data.inversion ?? 0));
        setTotalD2CSales(Number(data.totalD2CSales ?? data.ventasD2C ?? 0));
        setTacosGlobal(Number(data.tacosGlobal ?? data.tacos ?? 0));
        setConversionRate(Number(data.conversionRate ?? data.tasaConversion ?? 0));
        setBounceRate(Number(data.bounceRate ?? data.tasaRebote ?? 0));

        setSessionsYoy(Number(data.sessionsYoy ?? 0));
        setMktSpendYoy(Number(data.mktSpendYoy ?? 0));
        setD2cSalesYoy(Number(data.d2cSalesYoy ?? 0));
        setTacosYoy(Number(data.tacosYoy ?? 0));

        setWeeklyData(Array.isArray(data.weeklyData) ? data.weeklyData : (Array.isArray(data.tendenciaSemanal) ? data.tendenciaSemanal : []));
        setCategoryPerf(Array.isArray(data.categoryPerf) ? data.categoryPerf : (Array.isArray(data.performanceCategoria) ? data.performanceCategoria : []));

        setMobileSessions(Number(data.mobileSessions ?? 0));
        setDesktopSessions(Number(data.desktopSessions ?? 0));
        setAddToCart(Number(data.addToCart ?? data.atc ?? 0));
        setCheckouts(Number(data.checkouts ?? 0));
        setTransactions(Number(data.transactions ?? data.transacciones ?? 0));
      })
      .catch((err) => {
        console.error("Error al cargar performance D2C:", err);
        setTotalSessions(0);
        setTotalMktSpend(0);
        setTotalD2CSales(0);
        setTacosGlobal(0);
        setConversionRate(0);
        setBounceRate(0);
        setWeeklyData([]);
        setCategoryPerf([]);
      })
      .finally(() => setLoading(false));
  }, [
    startDate, 
    endDate, 
    selectedCategory, 
    selectedMarca,
    JSON.stringify(selectedCategories), 
    JSON.stringify(selectedChannels), 
    JSON.stringify(selectedReps), 
    JSON.stringify(selectedWarehouses)
  ]);

  const filteredCategories = useMemo(() => {
    let list = Array.isArray(categoryPerf) ? categoryPerf : [];
    if (selectedCategory) {
      list = list.filter((c) => (c.categoria || c.name || "").toLowerCase().includes(selectedCategory.toLowerCase()));
    }

    return [...list].sort((a: any, b: any) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];
      if (aVal === undefined || aVal === null) aVal = '';
      if (bVal === undefined || bVal === null) bVal = '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [selectedCategory, sortKey, sortDir, categoryPerf]);

  const sessionsVarPct = sessionsYoy ? ((totalSessions - sessionsYoy) / sessionsYoy) * 100 : 0;
  const mktVarPct = mktSpendYoy ? ((totalMktSpend - mktSpendYoy) / mktSpendYoy) * 100 : 0;
  const salesVarPct = d2cSalesYoy ? ((totalD2CSales - d2cSalesYoy) / d2cSalesYoy) * 100 : 0;
  const tacosDiff = tacosGlobal - tacosYoy;

  const totalDevSessions = mobileSessions + desktopSessions || 1;
  const mobilePct = ((mobileSessions / totalDevSessions) * 100).toFixed(1);
  const desktopPct = ((desktopSessions / totalDevSessions) * 100).toFixed(1);

  const baseAtc = addToCart || 1;
  const checkoutPct = ((checkouts / baseAtc) * 100).toFixed(1);
  const purchasePct = ((transactions / baseAtc) * 100).toFixed(1);

  // Estilos de Apple HIG para Fondos y Títulos
  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titleAmber = isDark ? "text-amber-400" : "text-amber-800";
  const titlePurple = isDark ? "text-purple-400" : "text-purple-700";
  const titleRose = isDark ? "text-rose-400" : "text-rose-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600" />
        <span className={`text-sm font-semibold ${subtextColor}`}>Cargando Indicadores D2C Performance...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {/* Selector de marca (rediseñado 07-ago-2026 -- mismo lenguaje visual
          que las KPI cards: panelBg + bordes redondeados 2xl, en vez del
          pill genérico anterior) */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className={`flex items-center gap-1.5 p-1.5 rounded-2xl border w-fit ${panelBg}`}>
          {BRANDS.map((b) => {
            const isSelected = selectedMarca === b.id;
            return (
              <button
                key={b.id}
                onClick={() => setSelectedMarca(b.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl transition-all ${
                  isSelected
                    ? isDark
                      ? 'bg-[#2C2C2E] shadow-sm'
                      : 'bg-slate-100 shadow-sm'
                    : 'opacity-45 hover:opacity-80'
                }`}
                style={isSelected ? { boxShadow: `inset 0 -2px 0 0 ${b.color}` } : undefined}
              >
                <img src={b.logo} alt={b.label} className="h-5 w-auto max-w-[88px] object-contain" />
                <span
                  className="text-xs font-bold whitespace-nowrap"
                  style={{ color: isSelected ? b.color : undefined }}
                >
                  {b.label}
                </span>
              </button>
            );
          })}
        </div>

        {!ga4Disponible && (
          <span className="text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-600 border border-amber-500/30">
            Sesiones/Funnel de GA4 aún no disponibles para Tom Palmer -- pendiente conectar su propiedad de Analytics
          </span>
        )}
      </div>

      {/* Top KPI Cards Estilo Apple HIG */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        
        {/* Card 1: Sesiones GA4 */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between transition-all hover:shadow-md ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black uppercase tracking-wider ${titleBlue}`}>
                SESIONES (GA4)
              </span>
              <Eye className="w-4 h-4 text-blue-500 opacity-80" />
            </div>
            <div className={`text-3xl font-black mt-2 ${titleBlue}`}>
              {(totalSessions / 1000).toFixed(1)} K
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] space-y-1 text-xs">
            <div className="flex justify-between items-center font-semibold">
              <span className={subtextColor}>YoY: {(sessionsYoy / 1000).toFixed(1)}K</span>
              <span className={`font-black ${sessionsVarPct >= 0 ? titleEmerald : titleRose}`}>
                {sessionsVarPct >= 0 ? '+' : ''}{sessionsVarPct.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Inversión MKT */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between transition-all hover:shadow-md ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black uppercase tracking-wider ${titleAmber}`}>
                INVERSIÓN MKT
              </span>
              <DollarSign className="w-4 h-4 text-amber-500 opacity-80" />
            </div>
            <div className={`text-3xl font-black mt-2 ${titleAmber}`}>
              ${(totalMktSpend / 1000000).toFixed(1)} M
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] space-y-1 text-xs">
            <div className="flex justify-between items-center font-semibold">
              <span className={subtextColor}>YoY: ${(mktSpendYoy / 1000000).toFixed(1)}M</span>
              <span className={`font-black ${mktVarPct <= 0 ? titleEmerald : titleRose}`}>
                {mktVarPct >= 0 ? '+' : ''}{mktVarPct.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Ventas D2C */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between transition-all hover:shadow-md ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black uppercase tracking-wider ${titleEmerald}`}>
                VENTAS D2C
              </span>
              <Zap className="w-4 h-4 text-emerald-500 opacity-80" />
            </div>
            <div className={`text-3xl font-black mt-2 ${titleEmerald}`}>
              ${(totalD2CSales / 1000000).toFixed(1)} M
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] space-y-1 text-xs">
            <div className="flex justify-between items-center font-semibold">
              <span className={subtextColor}>YoY: ${(d2cSalesYoy / 1000000).toFixed(1)}M</span>
              <span className={`font-black ${salesVarPct >= 0 ? titleEmerald : titleRose}`}>
                {salesVarPct >= 0 ? '+' : ''}{salesVarPct.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: TACOS Global */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between transition-all hover:shadow-md ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black uppercase tracking-wider ${titlePurple}`}>
                TACOS GLOBAL
              </span>
              <ArrowUpRight className="w-4 h-4 text-purple-500 opacity-80" />
            </div>
            <div className={`text-3xl font-black mt-2 ${titlePurple}`}>
              {tacosGlobal.toFixed(1)}%
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] space-y-1 text-xs">
            <div className="flex justify-between items-center font-semibold">
              <span className={subtextColor}>YoY: {tacosYoy.toFixed(1)}%</span>
              <span className={`font-black ${tacosDiff <= 0 ? titleEmerald : titleRose}`}>
                {tacosDiff >= 0 ? '+' : ''}{tacosDiff.toFixed(1)} pp
              </span>
            </div>
          </div>
        </div>

        {/* Card 5: % Conversión */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between transition-all hover:shadow-md ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black uppercase tracking-wider ${titleBlue}`}>
                % CONVERSIÓN
              </span>
              <CheckCircle2 className="w-4 h-4 text-blue-500 opacity-80" />
            </div>
            <div className={`text-3xl font-black mt-2 ${titleBlue}`}>
              {conversionRate.toFixed(2)}%
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] space-y-1 text-xs">
            <div className="flex justify-between items-center font-semibold">
              <span className={subtextColor}>E-commerce GA4</span>
              <span className={`font-black ${titleEmerald}`}>Target &gt; 1.5%</span>
            </div>
          </div>
        </div>

        {/* Card 6: Tasa Rebote */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between transition-all hover:shadow-md ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-black uppercase tracking-wider ${titleRose}`}>
                TASA REBOTE
              </span>
              <TrendingUp className="w-4 h-4 text-rose-500 opacity-80" />
            </div>
            <div className={`text-3xl font-black mt-2 ${titleRose}`}>
              {bounceRate.toFixed(1)}%
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] space-y-1 text-xs">
            <div className="flex justify-between items-center font-semibold">
              <span className={subtextColor}>Tráfico Web GA4</span>
              <span className={`font-black ${titleEmerald}`}>&lt; 40% Target</span>
            </div>
          </div>
        </div>

      </div>

      {/* Gráfico de Tendencia Semanal */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
            <TrendingUp className="w-4 h-4" /> TENDENCIA SEMANAL DE SESIONES GA4 VS INVERSIÓN PUBLICITARIA ($)
          </h3>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={weeklyData} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
              <XAxis dataKey="week" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={11} />
              <YAxis yAxisId="left" hide />
              <YAxis yAxisId="right" orientation="right" hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: isDark ? '#1C1C1E' : '#ffffff',
                  borderColor: isDark ? '#2C2C2E' : '#e2e8f0',
                  color: isDark ? '#F5F5F7' : '#1e293b',
                  borderRadius: '12px'
                }}
              />
              <Bar yAxisId="left" dataKey="sessions" name="Sesiones GA4" fill="#0A84FF" radius={[6, 6, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="spend" name="Inversión ($)" stroke="#FF9F0A" strokeWidth={3} dot={{ r: 5, fill: '#FF9F0A' }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabla Performance & TACOS por Categoría */}
      <div className={`p-6 rounded-2xl border shadow-sm space-y-4 ${panelBg}`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
            <DollarSign className="w-4 h-4" /> PERFORMANCE &amp; TACOS POR CATEGORÍA
          </h3>
          <span className={`text-xs font-medium ${subtextColor}`}>Clic en fila para filtro cruzado</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse min-w-[1000px]">
            <thead>
              <tr className={`border-b text-[10px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="INVERSIÓN" sortKey="inversion" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="INVERSIÓN YOY" sortKey="inversionYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="VENTA ACTUAL" sortKey="venta" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={`${titleBlue} font-black`} />
                <SortableTh label="VENTA YOY" sortKey="ventaYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="TKP ACTUAL" sortKey="tkp" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="TACOS %" sortKey="tacos" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" className={`${titlePurple} font-black`} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
              {filteredCategories.map((cat: any, idx: number) => {
                const catNombre = cat.categoria || cat.name || "Categoría";
                const isSelected = selectedCategory?.toLowerCase() === catNombre.toLowerCase();
                const inv = Number(cat.inversion ?? 0);
                const invYoy = Number(cat.inversionYoy ?? 0);
                const vta = Number(cat.venta ?? 0);
                const vtaYoy = Number(cat.ventaYoy ?? 0);
                const tkp = Number(cat.tkp ?? 0);
                const catTacos = vta > 0 ? ((inv / vta) * 100) : 0;

                const rowBg = isSelected
                  ? (isDark ? 'bg-blue-600/30 font-bold border-l-4 border-l-blue-400' : 'bg-blue-50 font-bold border-l-4 border-l-blue-600')
                  : (isDark ? 'hover:bg-[#2C2C2E] text-[#F5F5F7]' : 'hover:bg-slate-50 text-slate-800');

                return (
                  <tr
                    key={catNombre + idx}
                    onClick={() => setSelectedCategory(isSelected ? null : catNombre)}
                    className={`cursor-pointer transition-colors ${rowBg}`}
                  >
                    <td className="p-3 font-extrabold">{catNombre}</td>
                    <td className="p-3 text-right font-bold">${inv.toLocaleString('es-CL')}</td>
                    <td className={`p-3 text-right ${subtextColor}`}>${invYoy.toLocaleString('es-CL')}</td>
                    <td className={`p-3 text-right font-black ${titleBlue}`}>${vta.toLocaleString('es-CL')}</td>
                    <td className={`p-3 text-right ${subtextColor}`}>${vtaYoy.toLocaleString('es-CL')}</td>
                    <td className="p-3 text-right font-bold">${Math.round(tkp).toLocaleString('es-CL')}</td>
                    <td className={`p-3 text-center font-black ${titlePurple}`}>{catTacos.toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Dispositivos & Embudo de Ventas (Funnel GA4) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        {/* Sesiones por Dispositivo */}
        <div className={`p-6 rounded-2xl border shadow-sm flex flex-col justify-between ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
                <Smartphone className="w-4 h-4" /> SESIONES POR DISPOSITIVO (GA4)
              </h3>
              <span className={`text-xs font-extrabold ${titleBlue}`}>Total: {(totalSessions / 1000).toFixed(1)}K</span>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center text-xs font-extrabold mb-1.5">
                  <span>📱 Mobile / Smartphone</span>
                  <span className={titleBlue}>{mobileSessions.toLocaleString('es-CL')} ses. ({mobilePct}%)</span>
                </div>
                <div className={`w-full h-3 rounded-full overflow-hidden ${isDark ? 'bg-[#333339]' : 'bg-slate-200'}`}>
                  <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${mobilePct}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center text-xs font-extrabold mb-1.5">
                  <span>💻 Desktop / Notebook</span>
                  <span className={titlePurple}>{desktopSessions.toLocaleString('es-CL')} ses. ({desktopPct}%)</span>
                </div>
                <div className={`w-full h-3 rounded-full overflow-hidden ${isDark ? 'bg-[#333339]' : 'bg-slate-200'}`}>
                  <div className="h-full bg-purple-500 rounded-full transition-all duration-500" style={{ width: `${desktopPct}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Embudo de Compra GA4 */}
        <div className={`p-6 rounded-2xl border shadow-sm flex flex-col justify-between ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
                <ShoppingBag className="w-4 h-4" /> PROCESO DE COMPRA (FUNNEL GA4)
              </h3>
              <span className={`text-xs font-extrabold bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 ${titleEmerald}`}>
                Conv. Carrito {purchasePct}%
              </span>
            </div>

            <div className="space-y-4 text-xs font-medium">
              <div>
                <div className="flex justify-between font-bold mb-1">
                  <span>1. Add to Cart (Agregar al Carrito)</span>
                  <span className={`font-black ${titleBlue}`}>{addToCart.toLocaleString('es-CL')} u. (100%)</span>
                </div>
                <div className={`w-full h-3 rounded-full overflow-hidden ${isDark ? 'bg-[#333339]' : 'bg-slate-200'}`}>
                  <div className="h-full bg-blue-500 rounded-full w-full" />
                </div>
              </div>

              <div>
                <div className="flex justify-between font-bold mb-1">
                  <span>2. Checkout Started (Inicio Checkout)</span>
                  <span className={`font-black ${titleAmber}`}>{checkouts.toLocaleString('es-CL')} u. ({checkoutPct}%)</span>
                </div>
                <div className={`w-full h-3 rounded-full overflow-hidden ${isDark ? 'bg-[#333339]' : 'bg-slate-200'}`}>
                  <div className="h-full bg-amber-500 rounded-full transition-all duration-500" style={{ width: `${checkoutPct}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between font-bold mb-1">
                  <span>3. Venta Concretada (Transacciones GA4)</span>
                  <span className={`font-black ${titleEmerald}`}>{transactions.toLocaleString('es-CL')} u. ({purchasePct}%)</span>
                </div>
                <div className={`w-full h-3 rounded-full overflow-hidden ${isDark ? 'bg-[#333339]' : 'bg-slate-200'}`}>
                  <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${purchasePct}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default D2CPerformanceView;