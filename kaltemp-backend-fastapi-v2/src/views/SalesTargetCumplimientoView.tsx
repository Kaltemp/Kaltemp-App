import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode } from '../types';
import { 
  useGlobalFilter, 
  ALL_REPS, 
  ALL_CATEGORIES, 
  ALL_CHANNELS, 
  ALL_WAREHOUSES 
} from '../context/FilterContext';
import { fetchCumplimiento } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import {
  Target,
  TrendingUp,
  User,
  CheckCircle2,
  AlertCircle,
  BarChart2,
  Sliders,
  Award,
  ArrowUpRight,
  PieChart as PieChartIcon,
  Package,
  RotateCcw,
  Trash2
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
}

const SELLER_DEFAULT_TARGETS: Record<string, { ventaMeta: number; contriMeta: number }> = {
  'William Garrido': { ventaMeta: 99.0, contriMeta: 43.0 },
  'Carlos Silva': { ventaMeta: 85.0, contriMeta: 36.0 },
  'María José Pérez': { ventaMeta: 70.0, contriMeta: 30.0 },
  'Andrea Morales': { ventaMeta: 60.0, contriMeta: 25.0 },
  'Felipe Lagos': { ventaMeta: 50.0, contriMeta: 22.0 },
};

function obtenerCicloComercialActual(): { startDate: string; endDate: string; label: string } {
  const hoy = new Date();
  const year = hoy.getFullYear();
  const month = hoy.getMonth();
  const day = hoy.getDate();

  let startYear = year;
  let startMonth = month;
  let endYear = year;
  let endMonth = month;

  if (day >= 25) {
    startYear = year;
    startMonth = month;

    const proximoMes = new Date(year, month + 1, 1);
    endYear = proximoMes.getFullYear();
    endMonth = proximoMes.getMonth();
  } else {
    const mesAnterior = new Date(year, month - 1, 1);
    startYear = mesAnterior.getFullYear();
    startMonth = mesAnterior.getMonth();

    endYear = year;
    endMonth = month;
  }

  const startStr = `${startYear}-${String(startMonth + 1).padStart(2, '0')}-25`;
  const endStr = `${endYear}-${String(endMonth + 1).padStart(2, '0')}-24`;

  const startDateObj = new Date(startYear, startMonth, 25);
  const endDateObj = new Date(endYear, endMonth, 24);

  const label = `${startDateObj.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' })} - ${endDateObj.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' })}`;

  return { startDate: startStr, endDate: endStr, label };
}

export const SalesTargetCumplimientoView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';

  const { 
    selectedCategories, 
    selectedChannels, 
    selectedReps, 
    selectedWarehouses 
  } = useGlobalFilter();

  const cicloComercial = useMemo(() => obtenerCicloComercialActual(), []);

  const [cumplimientoData, setCumplimientoData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const currentYear = useMemo(() => new Date(cicloComercial.endDate).getFullYear() || 2026, [cicloComercial]);
  const prevYear = currentYear - 1;

  useEffect(() => {
    setLoading(true);

    const vendedoresFiltro = selectedReps.length < ALL_REPS.length ? selectedReps : [];
    const categoriasFiltro = selectedCategories.length < ALL_CATEGORIES.length ? selectedCategories : [];
    const canalesFiltro = selectedChannels.length < ALL_CHANNELS.length ? selectedChannels : [];
    const bodegasFiltro = selectedWarehouses.length < ALL_WAREHOUSES.length ? selectedWarehouses : [];

    fetchCumplimiento(
      cicloComercial.startDate,
      cicloComercial.endDate,
      vendedoresFiltro,
      categoriasFiltro,
      canalesFiltro,
      bodegasFiltro
    )
      .then(setCumplimientoData)
      .catch((err) => {
        console.error("Error al cargar datos de cumplimiento:", err);
        setCumplimientoData(null);
      })
      .finally(() => setLoading(false));
  }, [
    cicloComercial, 
    selectedReps, 
    selectedCategories, 
    selectedChannels, 
    selectedWarehouses
  ]);

  const activeSellerName = selectedReps.length === 1 ? selectedReps[0] : 'Todos los Vendedores';

  const initialVentaMeta = useMemo(() => {
    if (selectedReps.length === 1 && SELLER_DEFAULT_TARGETS[selectedReps[0]]) {
      return SELLER_DEFAULT_TARGETS[selectedReps[0]].ventaMeta;
    }
    return 150.0;
  }, [selectedReps]);

  const initialContriMeta = useMemo(() => {
    if (selectedReps.length === 1 && SELLER_DEFAULT_TARGETS[selectedReps[0]]) {
      return SELLER_DEFAULT_TARGETS[selectedReps[0]].contriMeta;
    }
    return 65.0;
  }, [selectedReps]);

  const [ventaMeta, setVentaMeta] = useState<number | string>(initialVentaMeta);
  const [contriMeta, setContriMeta] = useState<number | string>(initialContriMeta);

  useEffect(() => {
    setVentaMeta(initialVentaMeta);
    setContriMeta(initialContriMeta);
  }, [initialVentaMeta, initialContriMeta]);

  const numVentaMeta = Number(ventaMeta) || 0;
  const numContriMeta = Number(contriMeta) || 0;

  const ventaReal = cumplimientoData?.ventaReal ?? 0;
  const contriReal = cumplimientoData?.contriReal ?? 0;

  const pctVenta = Math.round((ventaReal / (numVentaMeta || 1)) * 100);
  const pctContri = Math.round((contriReal / (numContriMeta || 1)) * 100);

  const daysElapsed = cumplimientoData?.diasTranscurridos ?? 1;
  const totalDaysCycle = cumplimientoData?.diasTotalCiclo ?? 31;
  const runRateFactor = totalDaysCycle / (daysElapsed || 1);
  const ventaProyeccion = Number((ventaReal * runRateFactor).toFixed(1));
  const contriProyeccion = Number((contriReal * runRateFactor).toFixed(1));
  const pctProyeccionVenta = Math.round((ventaProyeccion / (numVentaMeta || 1)) * 100);

  const channelBreakdown = useMemo(() => {
    const canales = cumplimientoData?.canalBreakdown ?? [];
    const pctCumplimientoGlobal = numContriMeta ? Math.round((contriReal / numContriMeta) * 100) - 100 : 0;
    return canales.map((c: any) => ({
      canal: c.canal,
      contri: c.contri,
      proy: c.proy,
      meta: contriReal ? Number(((c.contri / contriReal) * numContriMeta).toFixed(1)) : 0,
      ventaDiaria: c.ventaDiaria,
      yoyPct: c.yoyPct,
      metaPct: pctCumplimientoGlobal,
    }));
  }, [cumplimientoData, contriReal, numContriMeta]);

  const targetMilestones = [70, 80, 90, 100, 110, 120, 130, 140];
  const thresholdCards = targetMilestones.map((pct) => {
    const requiredContri = (numContriMeta * pct) / 100;
    const diff = contriReal - requiredContri;
    return {
      pct,
      required: requiredContri.toFixed(1),
      diff: diff.toFixed(1),
      diffNum: diff,
    };
  });

  const historicalTrend = [
    { año: '2023', meta: 65.4, contribucion: 42.0, cumplimiento: 64.2 },
    { año: '2024', meta: 76.1, contribucion: 36.1, cumplimiento: 47.5 },
    { año: '2025', meta: 46.6, contribucion: 39.7, cumplimiento: 85.2 },
    { año: String(currentYear), meta: numContriMeta, contribucion: contriReal, cumplimiento: pctContri },
  ];

  const categorySales = useMemo(() => {
    return (cumplimientoData?.categorySales ?? []).map((c: any) => ({
      cat: c.cat,
      y2025: c.anterior,
      y2026: c.actual,
    }));
  }, [cumplimientoData]);

  const skuTargetMatrix = [
    { desc: 'Calefactor a Gas Eiger 6', u70: -1, v70: -0.1, u100: -1, v100: -0.1, u140: 1, v140: 0.1 },
    { desc: 'Calefactor a Gas Leger 12', u70: -1, v70: 0.0, u100: -1, v100: 0.0, u140: 1, v140: 0.1 },
    { desc: 'CALEFACTOR BIOSMART IR04', u70: -31, v70: -4.4, u100: -12, v100: -1.7, u140: 16, v140: 2.3 },
    { desc: 'Calefactor de Terraza Woody 20', u70: -9, v70: -1.7, u100: -4, v100: -0.8, u140: 5, v140: 0.9 },
    { desc: 'CALEFACTOR SECATOALLAS', u70: -6, v70: -0.4, u100: -3, v100: -0.2, u140: 3, v140: 0.2 },
    { desc: 'CONVECTOR APOLO 1500 INVERTER', u70: -27, v70: -3.8, u100: -11, v100: -1.5, u140: 11, v140: 1.6 },
  ];

  // Estilos de Apple HIG para Fondos y Títulos
  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titleAmber = isDark ? "text-amber-400" : "text-amber-800";
  const titlePurple = isDark ? "text-purple-400" : "text-purple-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  if (loading) {
    return (
      <div className={`p-12 text-center text-sm font-semibold rounded-2xl border ${panelBg}`}>
        <span className={subtextColor}>Cargando métricas de Cumplimiento de Ventas para el Ciclo {cicloComercial.label}...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-12">
      <CrossFilterBanner theme={theme} />

      {/* --- PANEL DE AJUSTE DINÁMICO DE METAS Y CICLO AUTOMÁTICO --- */}
      <div className={`p-5 rounded-2xl border ${panelBg}`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-xl bg-blue-500/10 text-blue-500 border border-blue-500/20">
              <Sliders className="w-5 h-5" />
            </span>
            <div>
              <span className={`text-xs font-black uppercase tracking-wider block ${titleBlue}`}>
                AJUSTE DE META COMERCIAL ({activeSellerName})
              </span>
              <p className={`text-[11px] font-medium ${subtextColor}`}>
                Ciclo Automático Activo: <strong className={isDark ? "text-white" : "text-slate-900"}>{cicloComercial.label}</strong> (Día {daysElapsed} de {totalDaysCycle})
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <label className={`text-xs font-bold ${subtextColor}`}>Meta Venta ($M):</label>
              <input
                type="text"
                placeholder="0.0"
                value={ventaMeta}
                onChange={(e) => setVentaMeta(e.target.value)}
                className={`w-24 px-3 py-1.5 text-xs font-extrabold rounded-xl border outline-none text-right transition-colors focus:border-blue-500 ${
                  isDark ? 'bg-[#17171A] border-[#333339] text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                }`}
              />
            </div>

            <div className="flex items-center gap-2">
              <label className={`text-xs font-bold ${subtextColor}`}>Meta Contribución ($M):</label>
              <input
                type="text"
                placeholder="0.0"
                value={contriMeta}
                onChange={(e) => setContriMeta(e.target.value)}
                className={`w-24 px-3 py-1.5 text-xs font-extrabold rounded-xl border outline-none text-right transition-colors focus:border-blue-500 ${
                  isDark ? 'bg-[#17171A] border-[#333339] text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                }`}
              />
            </div>

            <button
              onClick={() => {
                setVentaMeta('');
                setContriMeta('');
              }}
              title="Vaciar los campos para ingresar cifras nuevas"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/20 text-xs font-bold transition-all shadow-sm cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Limpiar</span>
            </button>

            <button
              onClick={() => {
                setVentaMeta(initialVentaMeta);
                setContriMeta(initialContriMeta);
              }}
              title="Cargar metas predeterminadas del sistema"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition-all shadow-sm cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Por Defecto</span>
            </button>
          </div>

        </div>
      </div>

      {/* --- CUMPLIMIENTO KPI CARDS --- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1: Venta Real */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleBlue}`}>
              <Target className="w-4 h-4" /> VENTA TOTAL REAL
            </span>
            <span className="p-1.5 rounded-lg bg-blue-500/10 text-blue-500">
              <ArrowUpRight className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleBlue}`}>${ventaReal.toFixed(1)} M</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              pctVenta >= 100 
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' 
                : 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20'
            }`}>
              {numVentaMeta > 0 ? `${pctVenta}% Meta` : 'Sin Meta'}
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Meta Objetivo: <strong className={isDark ? "text-white" : "text-slate-900"}>${numVentaMeta.toFixed(1)} M</strong></span>
          </div>
        </div>

        {/* KPI 2: Proyectado Venta */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titlePurple}`}>
              <TrendingUp className="w-4 h-4" /> PROYECTADO VENTA CIERRE
            </span>
            <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-500">
              <TrendingUp className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titlePurple}`}>${ventaProyeccion} M</span>
            <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">
              {pctProyeccionVenta}%
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Ritmo Diario: <strong className={titleEmerald}>${(ventaReal / (daysElapsed || 1)).toFixed(2)}M / día</strong></span>
          </div>
        </div>

        {/* KPI 3: Contribución Real */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleEmerald}`}>
              <CheckCircle2 className="w-4 h-4" /> CONTRIBUCIÓN REAL
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500">
              <Award className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleEmerald}`}>${contriReal.toFixed(1)} M</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
              pctContri >= 100 
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' 
                : 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20'
            }`}>
              {numContriMeta > 0 ? `${pctContri}% Meta` : 'Sin Meta'}
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Meta Contribución: <strong className={isDark ? "text-white" : "text-slate-900"}>${numContriMeta.toFixed(1)} M</strong></span>
          </div>
        </div>

        {/* KPI 4: Proyectado Contribución */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleAmber}`}>
              <Award className="w-4 h-4" /> PROYECTADO CONTRIBUCIÓN
            </span>
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-500">
              <Award className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleAmber}`}>${contriProyeccion} M</span>
            <span className="text-[10px] font-bold text-amber-700 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
              {Math.round((contriProyeccion / (numContriMeta || 1)) * 100)}%
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Contri. Diaria: <strong className={titleEmerald}>${(contriReal / (daysElapsed || 1)).toFixed(2)}M / día</strong></span>
          </div>
        </div>

      </div>

      {/* --- TABLA DESGLOSE POR CANAL DE VENTA --- */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
            <BarChart2 className="w-4 h-4" /> DESGLOSE DE CONTRIBUCIÓN & PROYECTADO POR CANAL DE VENTA ($ M)
          </h3>
          <span className={`text-xs font-bold ${subtextColor}`}>Ciclo {cicloComercial.label}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className={`border-b text-[11px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <th className="py-3 px-4">CANAL</th>
                <th className="py-3 px-4 text-right">CONTRIBUCIÓN</th>
                <th className="py-3 px-4 text-right">PROYECCIÓN</th>
                <th className="py-3 px-4 text-right">META</th>
                <th className="py-3 px-4 text-right">VENTA DIARIA</th>
                <th className="py-3 px-4 text-right">YoY %</th>
                <th className="py-3 px-4 text-right">META %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#2C2C2E] font-medium">
              {channelBreakdown.map((row) => (
                <tr key={row.canal} className={`hover:bg-blue-500/10 transition-colors ${
                  isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                }`}>
                  <td className={`py-3 px-4 font-black ${titleBlue}`}>{row.canal}</td>
                  <td className={`py-3 px-4 text-right font-black ${titleEmerald}`}>${row.contri.toFixed(1)} M</td>
                  <td className="py-3 px-4 text-right font-bold">${row.proy.toFixed(1)} M</td>
                  <td className={`py-3 px-4 text-right font-semibold ${subtextColor}`}>${row.meta.toFixed(1)} M</td>
                  <td className="py-3 px-4 text-right font-semibold">${row.ventaDiaria.toFixed(1)} M</td>
                  <td className={`py-3 px-4 text-right font-bold ${
                    row.yoyPct >= 0 ? titleEmerald : (isDark ? 'text-rose-400' : 'text-rose-700')
                  }`}>
                    {row.yoyPct > 0 ? `+${row.yoyPct}%` : `${row.yoyPct}%`}
                  </td>
                  <td className={`py-3 px-4 text-right font-bold ${
                    row.metaPct >= 0 ? titleEmerald : (isDark ? 'text-rose-400' : 'text-rose-700')
                  }`}>
                    {row.metaPct > 0 ? `+${row.metaPct}%` : `${row.metaPct}%`}
                  </td>
                </tr>
              ))}
              <tr className={`font-black text-sm border-t-2 ${
                isDark ? 'border-[#333339] bg-[#17171A] text-white' : 'border-slate-300 bg-slate-100 text-slate-900'
              }`}>
                <td className="py-3 px-4">TOTAL GENERAL</td>
                <td className={`py-3 px-4 text-right ${titleEmerald}`}>${contriReal.toFixed(1)} M</td>
                <td className="py-3 px-4 text-right">${contriProyeccion.toFixed(1)} M</td>
                <td className={`py-3 px-4 text-right ${subtextColor}`}>${numContriMeta.toFixed(1)} M</td>
                <td className="py-3 px-4 text-right">${(ventaReal / (daysElapsed || 1)).toFixed(1)} M</td>
                <td className={`py-3 px-4 text-right ${(() => {
                  const yoyTotal = cumplimientoData?.ventaYoyTotal;
                  return yoyTotal ? (ventaReal >= yoyTotal ? titleEmerald : (isDark ? 'text-rose-400' : 'text-rose-700')) : subtextColor;
                })()}`}>
                  {(() => {
                    const yoyTotal = cumplimientoData?.ventaYoyTotal;
                    if (!yoyTotal) return '—';
                    const pct = ((ventaReal - yoyTotal) / yoyTotal) * 100;
                    return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
                  })()}
                </td>
                <td className={`py-3 px-4 text-right ${titleEmerald}`}>+{pctContri}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* --- HITOS DE META (70% - 140%) --- */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleAmber}`}>
            <Target className="w-4 h-4" /> BRECHA EN CONTRIBUCIÓN PARA HITOS DE META (70% - 140%)
          </h3>
          <span className={`text-xs font-bold ${subtextColor}`}>
            Diferencia vs Contribución Actual (${contriReal}M)
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {thresholdCards.map((card) => {
            const isSuperado = card.diffNum >= 0;
            return (
              <div
                key={card.pct}
                className={`p-3.5 rounded-xl border transition-all ${
                  isDark ? 'bg-[#17171A] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[10px] font-black uppercase ${subtextColor}`}>
                    Meta {card.pct}%
                  </span>
                  {isSuperado ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                  )}
                </div>
                <p className={`text-base font-black ${
                  isSuperado 
                    ? (isDark ? 'text-emerald-400' : 'text-emerald-700') 
                    : (isDark ? 'text-amber-400' : 'text-amber-800')
                }`}>
                  {isSuperado ? `+$${card.diff} M` : `-$${Math.abs(card.diffNum).toFixed(1)} M`}
                </p>
                <p className={`text-[10px] font-medium mt-0.5 ${subtextColor}`}>
                  Target: ${card.required} M
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* --- GRÁFICOS DUALES --- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Gráfico 1: Histórico */}
        <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
          <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titleBlue}`}>
            <TrendingUp className="w-4 h-4" /> COMPARATIVO HISTÓRICO DE CUMPLIMIENTO ($ M & %)
          </h3>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={historicalTrend} margin={{ top: 15, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? '#2C2C2E' : '#E2E8F0'} />
                <XAxis dataKey="año" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} tickLine={false} />
                <YAxis yAxisId="left" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} unit="M" tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" hide />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#1F1F23' : '#FFFFFF',
                    borderColor: isDark ? '#333339' : '#E2E8F0',
                    color: isDark ? '#EDEDED' : '#1E293B',
                    borderRadius: '12px'
                  }}
                />
                <Bar yAxisId="left" dataKey="meta" name="Meta ($M)" fill={isDark ? '#38383A' : '#cbd5e1'} radius={[4, 4, 0, 0]} />
                <Bar yAxisId="left" dataKey="contribucion" name="Contribución ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="cumplimiento" name="Cumplimiento %" stroke="#30D158" strokeWidth={2.5} dot={{ r: 5 }}>
                  <LabelList dataKey="cumplimiento" position="top" formatter={(val: number) => `${val}%`} fill="#30D158" fontSize={10} fontWeight="bold" />
                </Line>
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Gráfico 2: Unidades por Categoría */}
        <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
          <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titlePurple}`}>
            <PieChartIcon className="w-4 h-4" /> UNIDADES POR CATEGORÍA ({prevYear} VS {currentYear})
          </h3>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={categorySales} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={isDark ? '#2C2C2E' : '#E2E8F0'} />
                <XAxis type="number" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} tickLine={false} />
                <YAxis dataKey="cat" type="category" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} width={120} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#1F1F23' : '#FFFFFF',
                    borderColor: isDark ? '#333339' : '#E2E8F0',
                    color: isDark ? '#EDEDED' : '#1E293B',
                    borderRadius: '12px'
                  }}
                />
                <Bar dataKey="y2025" name={`${prevYear} (u.)`} fill={isDark ? '#38383A' : '#cbd5e1'} radius={[0, 4, 4, 0]} />
                <Bar dataKey="y2026" name={`${currentYear} (u.)`} fill="#BF5AF2" radius={[0, 4, 4, 0]} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* --- MATRIZ DE REQUERIMIENTOS SKU --- */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <h3 className="text-xs font-black uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-1 flex items-center gap-2">
          <Package className="w-4 h-4" /> MATRIZ DE REQUERIMIENTO DE UNIDADES POR SKU
        </h3>
        <p className={`text-xs mb-4 font-medium ${subtextColor}`}>
          Diferencia estimada en unidades y monto para alcanzar los tramos clave de meta
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className={`border-b text-[10px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <th className="py-2.5 px-3">PRODUCTO / DESCRIPCIÓN</th>
                <th className="py-2.5 px-3 text-center bg-blue-500/10 text-blue-600 dark:text-blue-400">UNID. 70%</th>
                <th className="py-2.5 px-3 text-center bg-blue-500/10 text-blue-600 dark:text-blue-400">VENTA 70%</th>
                <th className="py-2.5 px-3 text-center bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">UNID. 100%</th>
                <th className="py-2.5 px-3 text-center bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">VENTA 100%</th>
                <th className="py-2.5 px-3 text-center bg-purple-500/10 text-purple-600 dark:text-purple-400">UNID. 140%</th>
                <th className="py-2.5 px-3 text-center bg-purple-500/10 text-purple-600 dark:text-purple-400">VENTA 140%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {skuTargetMatrix.map((item) => (
                <tr key={item.desc} className={`hover:bg-blue-500/10 transition-colors ${
                  isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                }`}>
                  <td className="py-2.5 px-3 font-bold">{item.desc}</td>
                  <td className="py-2.5 px-3 text-center font-semibold">{item.u70}</td>
                  <td className={`py-2.5 px-3 text-center ${subtextColor}`}>${item.v70} M</td>
                  <td className={`py-2.5 px-3 text-center font-bold ${titleEmerald}`}>{item.u100}</td>
                  <td className={`py-2.5 px-3 text-center font-bold ${titleEmerald}`}>${item.v100} M</td>
                  <td className={`py-2.5 px-3 text-center font-bold ${titlePurple}`}>+{item.u140}</td>
                  <td className={`py-2.5 px-3 text-center font-bold ${titlePurple}`}>+${item.v140} M</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};

export default SalesTargetCumplimientoView;