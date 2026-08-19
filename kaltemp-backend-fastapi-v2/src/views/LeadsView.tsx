import React, { useState, useEffect } from 'react';
import { ThemeMode } from '../types';
import {
  Target,
  Globe,
  Layers,
  TrendingUp,
  Calendar,
  User,
  MapPin,
  MessageSquare,
  CheckCircle2,
  Award,
  ArrowUpRight,
  Filter,
  Sparkles,
  Zap,
  Package,
  RefreshCw
} from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { fetchLeads } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
}

const ICONO_FUENTE: Record<string, { icon: any; color: string }> = {
  'kaltemp.cl': { icon: Globe, color: '#0A84FF' },
  Google: { icon: Zap, color: '#30D158' },
  Facebook: { icon: MessageSquare, color: '#BF5AF2' },
  Instagram: { icon: Sparkles, color: '#FF9F0A' },
};
const ICONO_DEFAULT = { icon: Filter, color: '#64748B' };

const AVATAR_COLORES = ['bg-blue-500', 'bg-purple-500', 'bg-amber-500', 'bg-emerald-500', 'bg-rose-500', 'bg-slate-500'];

const iniciales = (nombre: string) =>
  nombre
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('') || '??';

export const LeadsView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { startDate, endDate } = useGlobalFilter();

  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchLeads(startDate, endDate)
      .then(setData)
      .catch((err) => {
        console.error("Error cargando leads:", err);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titleAmber = isDark ? "text-amber-400" : "text-amber-800";
  const titlePurple = isDark ? "text-purple-400" : "text-purple-700";
  const titleRose = isDark ? "text-rose-400" : "text-rose-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600" />
        <span className={`text-sm font-semibold ${subtextColor}`}>Cargando métricas de CRM Leads...</span>
      </div>
    );
  }

  const totalLeads = data?.totalLeads ?? 0;
  const totalLeadsWow = data?.totalLeadsWow ?? 0;
  const totalLeadsYoy = data?.totalLeadsYoy ?? 0;
  const varWowTotal = totalLeadsWow ? (((totalLeads - totalLeadsWow) / totalLeadsWow) * 100).toFixed(1) : '—';
  const varYoyTotal = totalLeadsYoy ? (((totalLeads - totalLeadsYoy) / totalLeadsYoy) * 100).toFixed(1) : '—';

  // Clases de badge según signo -- antes eran siempre verdes aunque el
  // valor fuera negativo (19-ago-2026, se aprovecha para dejarlo correcto
  // en las dos badges -- WoW nueva y YoY existente -- al mismo tiempo).
  const badgeClase = (valor: string) =>
    valor !== '—' && Number(valor) < 0
      ? 'text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20'
      : 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20';

  const convertidos = data?.convertidos ?? 0;
  const tasaConversion = data?.tasaConversion ?? 0;
  const enProgreso = data?.pipelineStatuses?.find((s: any) => s.id === 'EN_PROGRESO')?.count ?? 0;

  const canalPrincipal = data?.canalPrincipal ?? { nombre: '—', pct: 0 };
  const topVendedor = data?.topVendedor ?? { nombre: '—', pct: 0 };
  const topProducto = data?.topProducto ?? { nombre: '—', pct: 0 };

  const sourcesData = Array.isArray(data?.sourcesData) ? data.sourcesData : [];
  const maxFuente = Math.max(1, ...sourcesData.map((s: any) => s.count || 0));

  const pipelineStatuses = (Array.isArray(data?.pipelineStatuses) ? data.pipelineStatuses : []).map((s: any) => ({
    ...s,
    color: s.id === 'EN_PROGRESO' ? '#FF9F0A' : s.id === 'SIN_VENTA' ? '#FF453A' : s.id === 'NUEVO' ? '#0A84FF' : '#30D158',
    desc:
      s.id === 'EN_PROGRESO' ? 'Cotización enviada / En seguimiento comercial' :
      s.id === 'SIN_VENTA' ? 'No interesado / Presupuesto / Competencia' :
      s.id === 'NUEVO' ? 'Por contactar / Recién asignado' :
      'Oportunidad ganada / Pedido en Bsale'
  }));

  const weeklyTrendData = Array.isArray(data?.weeklyTrend) ? data.weeklyTrend : [];
  const monthlyData = Array.isArray(data?.monthlyData) ? data.monthlyData : [];
  const [anioActual, anioAnterior, anio2Anterior] = data?.aniosDisponibles ?? [2026, 2025, 2024];

  const salesReps = (Array.isArray(data?.salesReps) ? data.salesReps : []).map((r: any, i: number) => ({
    ...r,
    avatar: iniciales(r.name || ""),
    color: AVATAR_COLORES[i % AVATAR_COLORES.length]
  }));

  const comunas = Array.isArray(data?.comunas) ? data.comunas : [];
  const maxComuna = Math.max(1, ...comunas.map((c: any) => c.count || 0));

  const productosData = Array.isArray(data?.productosData) ? data.productosData : [];
  const maxProducto = Math.max(1, ...productosData.map((p: any) => p.count || 0));

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <h1 className={`text-2xl font-black tracking-tight flex items-center gap-2.5 ${titleBlue}`}>
          <Target className="w-7 h-7 text-blue-600 dark:text-blue-400" /> CRM Leads &amp; Gestión Comercial
        </h1>
      </div>

      {/* --- EXECUTIVE HEADER CARDS (5 KPI Cards) --- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">

        {/* KPI 1: Total Leads -- AGREGADO 19-ago-2026 (pedido de William):
            antes solo tenía comparación YoY. Se agrega WoW (semana
            anterior, misma duración de rango corrida 7 días atrás) como
            una segunda badge, y una segunda línea al pie con el valor
            absoluto "Vs sem. ant." junto al "Vs {añoAnterior}" que ya
            existía. De paso, las badges ahora cambian a rojo cuando la
            variación es negativa (antes siempre eran verdes sin importar
            el signo). */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleBlue}`}>
              <Target className="w-4 h-4" /> TOTAL LEADS
            </span>
            <span className="p-1.5 rounded-lg bg-blue-500/10 text-blue-500">
              <ArrowUpRight className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleBlue}`}>{totalLeads}</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 flex-wrap">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeClase(varWowTotal)}`}>
              {varWowTotal === '—' ? 'WoW —' : `${Number(varWowTotal) >= 0 ? '+' : ''}${varWowTotal}% WoW`}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeClase(varYoyTotal)}`}>
              {varYoyTotal === '—' ? 'YoY —' : `${Number(varYoyTotal) >= 0 ? '+' : ''}${varYoyTotal}% YoY`}
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Vs sem. ant.: <strong className={isDark ? "text-white" : "text-slate-900"}>{totalLeadsWow} u.</strong></span>
            <span className={subtextColor}>Vs {anioAnterior}: <strong className={isDark ? "text-white" : "text-slate-900"}>{totalLeadsYoy} u.</strong></span>
          </div>
        </div>

        {/* KPI 2: Conversion to Sale */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleEmerald}`}>
              <CheckCircle2 className="w-4 h-4" /> CONVERTIDOS
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500">
              <Award className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleEmerald}`}>{convertidos}</span>
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              {tasaConversion}% Ratio
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>En Progreso: <strong className={titleAmber}>{enProgreso} u.</strong></span>
          </div>
        </div>

        {/* KPI 3: Top Producto / Categoría */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleRose}`}>
              <Package className="w-4 h-4" /> TOP PRODUCTO
            </span>
            <span className="p-1.5 rounded-lg bg-rose-500/10 text-rose-500">
              <Package className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className={`text-xl font-black tracking-tight truncate ${titleRose}`}>{topProducto.nombre}</span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Demanda: <strong className={titleRose}>{topProducto.pct}% de Leads</strong></span>
          </div>
        </div>

        {/* KPI 4: Top Channel Share */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titlePurple}`}>
              <MessageSquare className="w-4 h-4" /> CANAL LÍDER
            </span>
            <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-500">
              <Globe className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className={`text-2xl font-black tracking-tight truncate ${titlePurple}`}>{canalPrincipal.nombre}</span>
            <span className="text-xs font-black text-purple-600 dark:text-purple-400">{canalPrincipal.pct}%</span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>WhatsApp / Chat Web</span>
          </div>
        </div>

        {/* KPI 5: Top Sales Rep */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleAmber}`}>
              <User className="w-4 h-4" /> VENDEDOR LÍDER
            </span>
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-500">
              <Award className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className={`text-lg font-black tracking-tight truncate ${titleAmber}`}>{topVendedor.nombre}</span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Cuota: <strong className={isDark ? "text-white" : "text-slate-900"}>{topVendedor.pct}% Share</strong></span>
          </div>
        </div>

      </div>

      {/* --- SECTION 1: TENDENCIA SEMANAL --- */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div>
            <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
              <TrendingUp className="w-4 h-4" /> TENDENCIA SEMANAL DE LEADS (SEMANAS 1 A 52)
            </h3>
            <p className={`text-xs font-medium mt-1 ${subtextColor}`}>
              Comportamiento histórico de generación de prospectos comparando {anioActual} vs {anioAnterior} y {anio2Anterior}
            </p>
          </div>
          <div className={`flex items-center gap-4 text-xs font-bold px-3.5 py-1.5 rounded-xl border ${
            isDark ? 'bg-[#17171A] border-[#2C2C2E] text-slate-200' : 'bg-slate-100 border-slate-200 text-slate-700'
          }`}>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#0A84FF]" /> {anioActual} Actual</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#8E8E93]" /> {anioAnterior} YoY</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#BF5AF2]" /> {anio2Anterior} 2YoY</span>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={weeklyTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="leadGrad2026" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0A84FF" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#0A84FF" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="leadGrad2025" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8E8E93" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#8E8E93" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? '#2C2C2E' : '#E2E8F0'} />
              <XAxis dataKey="week" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} interval={3} tickLine={false} />
              <YAxis stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: isDark ? '#1F1F23' : '#FFFFFF',
                  borderColor: isDark ? '#333339' : '#E2E8F0',
                  color: isDark ? '#EDEDED' : '#1E293B',
                  borderRadius: '12px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
                }}
              />
              <Area type="monotone" dataKey="yActual" name={String(anioActual)} stroke="#0A84FF" strokeWidth={3} fill="url(#leadGrad2026)" connectNulls={false} />
              <Area type="monotone" dataKey="yAnterior" name={String(anioAnterior)} stroke="#8E8E93" strokeWidth={1.5} strokeDasharray="3 3" fill="url(#leadGrad2025)" />
              <Area type="monotone" dataKey="y2Anterior" name={String(anio2Anterior)} stroke="#BF5AF2" strokeWidth={1.5} strokeDasharray="2 2" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* --- SECTION 2: GRID DUAL - MONTHLY COMPARISON & PIPELINE FUNNEL --- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className={`lg:col-span-7 p-6 rounded-2xl border shadow-sm flex flex-col justify-between ${panelBg}`}>
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
                  <Calendar className="w-4 h-4" /> EVOLUCIÓN MENSUAL DE LEADS ({anio2Anterior} - {anioActual})
                </h3>
                <p className={`text-xs font-medium mt-0.5 ${subtextColor}`}>Volumen total captado por mes calendario</p>
              </div>
              <div className="flex gap-2 text-[10px] font-bold">
                <span className="px-2 py-0.5 rounded bg-[#0A84FF] text-white">{anioActual}</span>
                <span className="px-2 py-0.5 rounded bg-[#8E8E93] text-white">{anioAnterior}</span>
                <span className="px-2 py-0.5 rounded bg-[#BF5AF2] text-white">{anio2Anterior}</span>
              </div>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyData} margin={{ top: 15, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? '#2C2C2E' : '#E2E8F0'} />
                  <XAxis dataKey="mes" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} tickLine={false} />
                  <YAxis stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: isDark ? '#1F1F23' : '#FFFFFF',
                      borderColor: isDark ? '#333339' : '#E2E8F0',
                      color: isDark ? '#EDEDED' : '#1E293B',
                      borderRadius: '12px'
                    }}
                  />
                  <Bar dataKey="yActual" name={String(anioActual)} fill="#0A84FF" radius={[4, 4, 0, 0]}>
                    <LabelList dataKey="yActual" position="top" fill={isDark ? '#EDEDED' : '#1E293B'} fontSize={9} fontWeight="bold" />
                  </Bar>
                  <Bar dataKey="yAnterior" name={String(anioAnterior)} fill={isDark ? '#38383A' : '#cbd5e1'} radius={[4, 4, 0, 0]} opacity={0.7} />
                  <Bar dataKey="y2Anterior" name={String(anio2Anterior)} fill="#BF5AF2" radius={[4, 4, 0, 0]} opacity={0.5} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className={`lg:col-span-5 p-6 rounded-2xl border shadow-sm flex flex-col justify-between ${panelBg}`}>
          <div>
            <h3 className={`text-xs font-black uppercase tracking-wider mb-1 flex items-center gap-2 ${titleBlue}`}>
              <Layers className="w-4 h-4" /> PIPELINE DE ESTADO &amp; CONVERSIÓN
            </h3>
            <p className={`text-xs font-medium mb-5 ${subtextColor}`}>
              Estado de avance comercial de los {totalLeads} leads registrados
            </p>

            <div className="space-y-4">
              {pipelineStatuses.map((st: any) => (
                <div key={st.id} className={`p-3.5 rounded-xl border transition-all hover:scale-[1.01] ${
                  isDark ? 'bg-[#17171A] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: st.color }} />
                      <span className="text-xs font-extrabold">{st.label}</span>
                    </div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-sm font-black" style={{ color: st.color }}>{st.count} u.</span>
                      <span className={`text-[10px] font-bold ${subtextColor}`}>({st.pct}%)</span>
                    </div>
                  </div>

                  <div className={`w-full h-2 rounded-full overflow-hidden mb-1 ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-200'}`}>
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${st.pct}%`, backgroundColor: st.color }} />
                  </div>
                  <p className={`text-[10px] font-medium truncate ${subtextColor}`}>{st.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* --- SECTION 3: CUÁDRUPLE GRID --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

        {/* Panel 1: Productos de Interés -- AGREGADO 19-ago-2026 (pedido de
            William): la lista puede tener ~20 filas (una por cada valor
            distinto de PRODUCTO en el rango), y sin límite de alto
            estiraba toda la fila del grid (los otros 3 paneles quedaban
            con espacio vacío abajo). Se le da scroll interno con
            max-h + overflow-y-auto en vez de limitar la cantidad de
            productos mostrados -- así se sigue viendo el listado
            completo, solo que dentro de un alto fijo. */}
        <div className={`p-5 rounded-2xl border shadow-sm ${panelBg}`}>
          <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titleRose}`}>
            <Package className="w-4 h-4" /> PRODUCTO / CATEGORÍA DE INTERÉS
          </h3>
          <div className="space-y-3.5 max-h-[380px] overflow-y-auto overflow-x-hidden pr-1">
            {productosData.map((p: any) => (
              <div key={p.producto} className="space-y-1">
                <div className="flex justify-between items-center text-xs font-bold">
                  <span className={`truncate max-w-[140px] ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                    {p.producto}
                  </span>
                  <span className={`font-black ${titleRose}`}>
                    {p.count} u. <span className={`text-[10px] font-normal ${subtextColor}`}>({p.pct}%)</span>
                  </span>
                </div>
                <div className={`w-full h-2 rounded-full overflow-hidden ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-100'}`}>
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-rose-500 to-rose-400 transition-all duration-500"
                    style={{ width: `${(p.count / maxProducto) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Panel 2: Fuentes de Captación */}
        <div className={`p-5 rounded-2xl border shadow-sm ${panelBg}`}>
          <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titleBlue}`}>
            <Globe className="w-4 h-4" /> FUENTES DE CAPTACIÓN (ORIGEN)
          </h3>
          <div className="space-y-3.5">
            {sourcesData.map((src: any) => {
              const { icon: IconComp, color } = ICONO_FUENTE[src.name] ?? ICONO_DEFAULT;
              return (
                <div key={src.name} className="space-y-1">
                  <div className="flex justify-between items-center text-xs font-bold">
                    <span className={`flex items-center gap-1.5 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                      <IconComp className="w-3.5 h-3.5" style={{ color }} /> {src.name}
                    </span>
                    <span className="font-extrabold">{src.count} u. <span className={`text-[10px] font-normal ${subtextColor}`}>({src.share}%)</span></span>
                  </div>
                  <div className={`w-full h-2 rounded-full overflow-hidden ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-100'}`}>
                    <div className="h-full rounded-full" style={{ width: `${(src.count / maxFuente) * 100}%`, backgroundColor: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Panel 3: Vendedores Ranking */}
        <div className={`p-5 rounded-2xl border shadow-sm ${panelBg}`}>
          <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titleAmber}`}>
            <User className="w-4 h-4" /> ASIGNACIÓN POR VENDEDOR
          </h3>
          <div className="space-y-3">
            {salesReps.map((rep: any) => (
              <div key={rep.name} className={`flex items-center justify-between p-2.5 rounded-xl border transition-all ${
                isDark ? 'bg-[#17171A] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200/80'
              }`}>
                <div className="flex items-center gap-2.5">
                  <div className={`w-7 h-7 rounded-lg ${rep.color} text-white text-[11px] font-black flex items-center justify-center shrink-0`}>
                    {rep.avatar}
                  </div>
                  <span className={`text-xs font-bold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>{rep.name}</span>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-black block ${titleAmber}`}>{rep.leads} u.</span>
                  <span className={`text-[10px] font-medium ${subtextColor}`}>{rep.pct}% share</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Panel 4: Ubicación Comunas */}
        <div className={`p-5 rounded-2xl border shadow-sm ${panelBg}`}>
          <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titlePurple}`}>
            <MapPin className="w-4 h-4" /> DISTRIBUCIÓN GEOGRÁFICA
          </h3>
          <div className="space-y-3">
            {comunas.map((c: any) => (
              <div key={c.comuna} className="space-y-1">
                <div className="flex justify-between items-center text-xs font-bold">
                  <span className={isDark ? 'text-slate-200' : 'text-slate-800'}>{c.comuna}</span>
                  <span className={`font-black ${titlePurple}`}>{c.count} u. <span className={`text-[10px] font-normal ${subtextColor}`}>({c.pct}%)</span></span>
                </div>
                <div className={`w-full h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-100'}`}>
                  <div className="h-full rounded-full bg-purple-500" style={{ width: `${(c.count / maxComuna) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default LeadsView;