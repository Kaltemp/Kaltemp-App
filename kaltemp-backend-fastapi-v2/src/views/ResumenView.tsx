// ============================================================
// ARCHIVO: ResumenView.tsx
// RUTA: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\views\ResumenView.tsx
// ============================================================

import React, { useEffect, useMemo, useState } from 'react';
import {
  Package, ClipboardList, Send, Target, ShoppingCart, Megaphone,
  TrendingUp, Building2, Building, Thermometer, Trophy, AlertTriangle,
  Loader2, ArrowRight, PieChart as PieIcon, BarChart3, Truck, User
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Line, ComposedChart,
  LabelList, PieChart, Pie, Cell
} from 'recharts';
import { ModuleId, ThemeMode } from '../types';
import { fetchResumen } from '../services/api';
import { useUser } from '../context/UserContext';
import { useGlobalFilter } from '../context/FilterContext';
import { KPICard } from '../components/KPICard';

interface Props {
  theme: ThemeMode;
  onSelectModule: (m: ModuleId) => void;
}

let _GLOBAL_RESUMEN_CACHE: Record<string, any> = {};

const fmtM = (n: number) => `$${((n || 0) / 1_000_000).toFixed(1)} M`;
const fmtInt = (n: number) => Math.round(n || 0).toLocaleString('es-CL');
const fmtClp = (n: number) => `$${Math.round(n || 0).toLocaleString('es-CL')}`;
const fmtPct = (n: number, dec = 1) => `${(n || 0).toFixed(dec)}%`;

const safePctVar = (cy: number, prev: number): { val: number; text: string; isValid: boolean } => {
  if (!prev || prev <= 0) {
    if (cy > 0) return { val: 100, text: '+100%', isValid: true };
    return { val: 0, text: '0.0%', isValid: false };
  }
  const pct = ((cy - prev) / Math.abs(prev)) * 100;
  if (pct > 999) return { val: 999, text: '>+999%', isValid: true };
  if (pct < -999) return { val: -999, text: '<-999%', isValid: true };
  return { val: pct, text: `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`, isValid: true };
};

const PALETA_NEON = ['#0A84FF', '#30D158', '#BF5AF2', '#FF9F0A', '#FF453A', '#5AC8FA', '#FFD60A'];

const SIN_DATOS = (isDark: boolean) => (
  <p className={`text-xs italic py-2 ${isDark ? 'text-[#8E8E93]' : 'text-slate-400'}`}>Sin datos disponibles.</p>
);

function buildSparklineSvg(values: number[], color: string): string {
  if (!values || values.filter((v) => v !== null && v !== undefined).length < 2) return '';
  const w = 110, h = 32, pad = 3;
  const clean = values.map((v) => (typeof v === 'number' && !isNaN(v) ? v : 0));
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (clean.length - 1);
  const points = clean.map((v, i) => ({
    x: Number((pad + i * stepX).toFixed(1)),
    y: Number((h - pad - ((v - min) / range) * (h - pad * 2 - 4)).toFixed(1)),
  }));
  const polyline = points.map((p) => `${p.x},${p.y}`).join(' ');
  const polygon = `${points[0].x},${h} ${polyline} ${points[points.length - 1].x},${h}`;
  const last = points[points.length - 1];
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polygon points="${polygon}" fill="${color}" opacity="0.15"/><polyline points="${polyline}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/><circle cx="${last.x}" cy="${last.y}" r="3" fill="${color}"/></svg>`;
}

const CustomTooltipGraph = ({ active, payload, label, theme }: any) => {
  if (active && payload && payload.length) {
    const isDark = theme === 'dark';
    return (
      <div className={`p-3 rounded-xl border text-xs space-y-1.5 shadow-xl backdrop-blur-md ${
        isDark ? 'bg-[#1C1C1E]/95 border-[#333339] text-white' : 'bg-white/95 border-slate-200 text-slate-900 shadow-lg'
      }`}>
        <p className="font-black border-b pb-1 border-slate-200 dark:border-[#333339]">{label || payload[0].name}</p>
        {payload.map((entry: any, i: number) => (
          <div key={i} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 font-bold" style={{ color: entry.color }}>
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              {entry.name}:
            </span>
            <span className="font-extrabold font-mono">
              {typeof entry.value === 'number' && entry.value > 100000 
                ? fmtM(entry.value) 
                : (typeof entry.value === 'number' ? entry.value.toLocaleString('es-CL') : entry.value)}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

const CustomLineLabel = (props: any) => {
  const { x, y, index, data } = props;
  const item = (data && data[index]) ? data[index] : (props.payload || {});
  if (!item || item.cy === undefined || item.cy === null || item.cy <= 0) return null;
  const yoyVal = item.yoy;
  if (yoyVal === undefined || yoyVal === null) return null;
  const isPositive = yoyVal >= 0;
  const fillColor = isPositive ? '#30D158' : '#DC2626';
  const textLabel = `${isPositive ? '+' : ''}${Number(yoyVal).toFixed(1)}%`;
  const labelY = y < 22 ? y + 18 : y - 10;
  return <text x={x} y={labelY} fill={fillColor} textAnchor="middle" fontSize={11} fontWeight="900">{textLabel}</text>;
};

const SectionHeader: React.FC<{
  icon: React.ElementType;
  title: string;
  subtitle?: string;
  isDark: boolean;
  isFirst?: boolean;
}> = ({ icon: Icon, title, subtitle, isDark, isFirst = false }) => (
  <div className={`flex items-center gap-3 ${isFirst ? 'pt-0' : 'pt-2'} pb-1 min-w-0`}>
    <div className="flex items-center gap-2 shrink-0">
      <div className={`p-1.5 rounded-lg border ${
        isDark ? 'bg-white/5 border-white/10 text-zinc-300' : 'bg-white border-slate-200 text-slate-700 shadow-sm'
      }`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <h3 className={`text-xs font-black uppercase tracking-wider ${isDark ? 'text-zinc-200' : 'text-slate-800'}`}>
        {title}
      </h3>
    </div>
    <div className={`h-[1px] flex-1 min-w-4 ${isDark ? 'bg-white/10' : 'bg-slate-200'}`} />
    {subtitle && (
      <span className={`text-[10.5px] font-semibold hidden sm:inline-block truncate ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
        {subtitle}
      </span>
    )}
  </div>
);

const AppleRankItem: React.FC<{
  rank: number;
  name: string;
  meta?: string;
  value: string;
  yoyValue?: string;
  yoyPct?: number;
  isDark: boolean;
  accentColor: string;
}> = ({ rank, name, meta, value, yoyValue, yoyPct, isDark, accentColor }) => {
  const isPos = yoyPct !== undefined && yoyPct >= 0;
  return (
    <div className={`p-2.5 rounded-xl border flex items-center justify-between gap-2.5 transition-all hover:scale-[1.01] ${
      isDark
        ? 'bg-black/30 border-white/10 text-white shadow-sm'
        : 'bg-slate-50/80 border-slate-200 text-slate-900 shadow-sm'
    }`}>
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        <span
          className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0 shadow-sm"
          style={{ backgroundColor: accentColor }}
        >
          {rank}
        </span>
        <div className="min-w-0 flex-1 pr-1">
          <p className={`text-[11.5px] font-medium leading-snug break-words line-clamp-2 ${
            isDark ? 'text-zinc-200' : 'text-slate-800'
          }`} title={name}>
            {name}
          </p>
          {meta && (
            <p className={`text-[10px] font-normal leading-tight mt-0.5 ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
              {meta}
            </p>
          )}
        </div>
      </div>
      
      <div className="flex flex-col items-end shrink-0 leading-tight pl-1 text-right">
        <span className={`text-xs font-black tracking-tight font-mono ${
          isDark ? 'text-white' : 'text-slate-900'
        }`}>{value}</span>
        {yoyValue && (
          <span className={`text-[9.5px] font-normal font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
            YoY {yoyValue}
          </span>
        )}
        {yoyPct !== undefined && (
          <span
            className={`text-[9px] font-black font-mono px-1.5 py-0.5 rounded-md mt-0.5 border ${
              isPos
                ? isDark
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : isDark
                  ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}
          >
            {isPos ? '+' : ''}{yoyPct.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
};

interface ModuleCardFuturisticProps {
  icon: React.ElementType;
  title: string;
  badge?: string;
  color: string;
  onClick: () => void;
  isDark: boolean;
  children: React.ReactNode;
}

const ModuleCardFuturistic: React.FC<ModuleCardFuturisticProps> = ({ icon: Icon, title, badge, color, onClick, isDark, children }) => {
  return (
    <div className={`p-4 sm:p-5 rounded-2xl border transition-all duration-200 hover:shadow-md group h-full flex flex-col justify-between min-w-0 overflow-hidden ${
      isDark ? 'bg-[#1C1C1E]/80 border-[#2C2C2E] backdrop-blur-md' : 'bg-white border-slate-200 shadow-sm'
    }`}>
      <div className="min-w-0">
        <div className="flex items-center justify-between mb-3.5 pb-2 border-b border-slate-100 dark:border-[#2C2C2E]">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="p-2 rounded-xl shrink-0" style={{ backgroundColor: `${color}15`, color }}>
              <Icon className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-black uppercase tracking-wider truncate" style={{ color }}>{title}</h3>
            {badge && (
              <span className="text-[9.5px] font-black px-2 py-0.5 rounded-full uppercase border shrink-0 hidden sm:inline-block" style={{ backgroundColor: `${color}10`, color, borderColor: `${color}30` }}>
                {badge}
              </span>
            )}
          </div>
          <button onClick={onClick} className={`p-1.5 rounded-lg transition-all opacity-70 group-hover:opacity-100 shrink-0 cursor-pointer ${
            isDark ? 'hover:bg-white/10 text-white' : 'hover:bg-slate-100 text-slate-700'
          }`}>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

export const ResumenView: React.FC<Props> = ({ theme, onSelectModule }) => {
  const isDark = theme === 'dark';
  const { isModuleAllowed } = useUser();
  const globalFilter = useGlobalFilter();
  
  const { startDateISO, endDateISO } = useMemo(() => {
    const start = globalFilter?.dateRange?.startDate || (globalFilter as any)?.startDate;
    const end = globalFilter?.dateRange?.endDate || (globalFilter as any)?.endDate;
    const hoy = new Date();
    const hace30 = new Date(hoy.getTime() - 30 * 24 * 60 * 60 * 1000);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    return {
      startDateISO: start ? String(start).slice(0, 10) : iso(hace30),
      endDateISO: end ? String(end).slice(0, 10) : iso(hoy)
    };
  }, [globalFilter]);

  const cacheKey = `${startDateISO}_${endDateISO}`;
  const [resumenData, setResumenData] = useState<Record<string, any> | null>(_GLOBAL_RESUMEN_CACHE[cacheKey] || null);
  const [loading, setLoading] = useState(!_GLOBAL_RESUMEN_CACHE[cacheKey]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!_GLOBAL_RESUMEN_CACHE[cacheKey]) {
      setLoading(true);
    }
    fetchResumen(startDateISO, endDateISO)
      .then((data) => {
        _GLOBAL_RESUMEN_CACHE[cacheKey] = data;
        setResumenData(data);
        setError(null);
      })
      .catch((err) => {
        if (!_GLOBAL_RESUMEN_CACHE[cacheKey]) {
          setError(err?.message || 'Error al cargar resumen');
        }
      })
      .finally(() => setLoading(false));
  }, [startDateISO, endDateISO, cacheKey]);

  const heroData = resumenData?.kpis_hero || {
    disponible: true,
    venta: { actual: 0, wow: 0, yoy: 0, twoyoy: 0, serie: [] },
    contribucion: { actual: 0, wow: 0, yoy: 0, twoyoy: 0, serie: [] },
    margen: { actual: 0, wow: 0, yoy: 0, twoyoy: 0, serie: [] },
    tkp: { actual: 0, wow: 0, yoy: 0, twoyoy: 0, serie: [] }
  };

  const processedMonthsData = resumenData?.tendencia_mensual || [];

  const mktAgregado = useMemo(() => {
    const mkt = resumenData?.marketing;
    const invTotal = mkt?.inversion ?? 0;
    const invKal = mkt?.kaltemp?.inversion ?? 0;
    const invTp = mkt?.tom_palmer?.inversion ?? 0;
    const vKal = mkt?.kaltemp?.venta ?? 0;
    const vTp = mkt?.tom_palmer?.venta ?? 0;

    return {
      disponible: mkt?.disponible ?? false,
      global: {
        inversion: invTotal,
        varInversionYoy: mkt?.var_inversion_yoy ?? 0,
        impresiones: mkt?.impresiones ?? 0,
        varImpresionesYoy: mkt?.var_impresiones_yoy ?? 0,
        ctr: mkt?.ctr ?? 0,
        varCtrYoy: mkt?.var_ctr_yoy ?? 0,
        tacos: mkt?.tacos_global ?? 0,
        varTacosYoy: 0,
      },
      kaltemp: {
        inversion: invKal,
        venta: vKal,
        tacos: mkt?.kaltemp?.tacos ?? 0,
      },
      tomPalmer: {
        inversion: invTp,
        venta: vTp,
        tacos: mkt?.tom_palmer?.tacos ?? 0,
      },
      chartBimarca: [
        { marca: 'Kaltemp', inversion: invKal / 1_000_000, venta: vKal / 1_000_000 },
        { marca: 'Tom Palmer', inversion: invTp / 1_000_000, venta: vTp / 1_000_000 }
      ]
    };
  }, [resumenData]);

  const d2cProcessed = useMemo(() => {
    const kalV = resumenData?.d2c_kaltemp?.totalD2CSales ?? 0;
    const kalVy = resumenData?.d2c_kaltemp?.totalD2CSalesYoy ?? 0;
    const kalS = resumenData?.d2c_kaltemp?.totalSessions ?? 0;
    const kalSy = resumenData?.d2c_kaltemp?.totalSessionsYoy ?? 0;

    const tpV = resumenData?.d2c_tompalmer?.totalD2CSales ?? 0;
    const tpVy = resumenData?.d2c_tompalmer?.totalD2CSalesYoy ?? 0;
    const tpS = resumenData?.d2c_tompalmer?.totalSessions ?? 0;
    const tpSy = resumenData?.d2c_tompalmer?.totalSessionsYoy ?? 0;

    const kalVarS = safePctVar(kalS, kalSy);
    const tpVarS = safePctVar(tpS, tpSy);

    return {
      kaltemp: {
        venta: kalV,
        ventaYoy: kalVy,
        varVentaVal: safePctVar(kalV, kalVy).val,
        varVentaText: safePctVar(kalV, kalVy).text,
        sesiones: kalS,
        sesionesYoy: kalSy,
        varSesionesVal: kalVarS.val,
        varSesionesText: kalVarS.text,
      },
      tomPalmer: {
        venta: tpV,
        ventaYoy: tpVy,
        varVentaVal: safePctVar(tpV, tpVy).val,
        varVentaText: safePctVar(tpV, tpVy).text,
        sesiones: tpS,
        sesionesYoy: tpSy,
        varSesionesVal: tpVarS.val,
        varSesionesText: tpVarS.text,
      }
    };
  }, [resumenData]);

  const { top3Productos, bottom3Productos, top3Categorias, bottom3Categorias } = resumenData?.rankings_sku || {
    top3Productos: [], bottom3Productos: [], top3Categorias: [], bottom3Categorias: []
  };

  const dataPieCanales = useMemo(() => {
    return (resumenData?.channels || []).slice(0, 5).map((c: any) => {
      const varInfo = safePctVar(c.totalBruto, c.totalBrutoYoy !== undefined ? c.totalBrutoYoy : c.yoy);
      return {
        name: c.canal,
        value: c.totalBruto || 0,
        share: c.share || 0,
        yoyVal: varInfo.val,
        yoyText: varInfo.text,
        isValid: varInfo.isValid,
      };
    });
  }, [resumenData]);

  const dataTempChartExact = useMemo(() => {
    return (resumenData?.temperatura || []).map((t: any) => ({
      fecha: t.fechaDisp || t.fecha || '',
      venta: (t.brutoTotal || 0) / 1_000_000,
      tempMax: t.tempMax || 0,
      tempMaxYoY: t.tempMaxYoY || 0,
      tempMin: t.tempMin || 0,
      tempMinYoY: t.tempMinYoY || 0,
    }));
  }, [resumenData]);

  const panelBg = isDark ? 'bg-[#1C1C1E]/80 border-[#2C2C2E]' : 'bg-white border-slate-200 shadow-sm';
  const mutedText = isDark ? 'text-[#8E8E93]' : 'text-slate-500';

  if (loading && !resumenData) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[350px]">
        <Loader2 className="w-9 h-9 animate-spin text-blue-500 mb-2.5" />
        <p className={`text-xs font-black uppercase tracking-widest ${mutedText}`}>Cargando Centro de Control...</p>
      </div>
    );
  }

  return (
    <div className={`p-3 sm:p-5 pt-1 space-y-4.5 min-w-0 overflow-x-hidden ${
      isDark ? 'text-white' : 'text-slate-900'
    }`}>

      {error && (
        <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* =========================================================================
          ZONA 1: RENDIMIENTO EJECUTIVO & MIX DE VENTAS
          ========================================================================= */}
      <section className="space-y-3.5 min-w-0">
        <SectionHeader
          icon={BarChart3}
          title="Rendimiento Ejecutivo & Mix de Ventas"
          subtitle="Consolidado de ventas, cumplimiento y rotación de catálogo"
          isDark={isDark}
          isFirst={true}
        />

        {/* 4 KPIs Hero */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 min-w-0">
          <button onClick={() => onSelectModule('principal')} className="text-left cursor-pointer transition-transform hover:-translate-y-0.5 min-w-0">
            <KPICard
              title="VENTA TOTAL (BRUTO)" mainValue={fmtM(heroData.venta.actual)}
              colorValue={isDark ? '#38BDF8' : '#0055D6'}
              sparklineSvg={buildSparklineSvg(heroData.venta.serie, isDark ? '#38BDF8' : '#0055D6')}
              theme={theme}
              rows={[
                { label: 'WOW', value: fmtM(heroData.venta.wow), current: heroData.venta.actual, target: heroData.venta.wow },
                { label: 'YOY', value: fmtM(heroData.venta.yoy), current: heroData.venta.actual, target: heroData.venta.yoy },
                { label: '2YOY', value: fmtM(heroData.venta.twoyoy), current: heroData.venta.actual, target: heroData.venta.twoyoy },
              ]}
            />
          </button>
          <button onClick={() => onSelectModule('principal')} className="text-left cursor-pointer transition-transform hover:-translate-y-0.5 min-w-0">
            <KPICard
              title="CONTRIBUCIÓN ($)" mainValue={fmtM(heroData.contribucion.actual)}
              colorValue={isDark ? '#F5F5F7' : '#0F172A'}
              sparklineSvg={buildSparklineSvg(heroData.contribucion.serie, isDark ? '#F5F5F7' : '#0F172A')}
              theme={theme}
              rows={[
                { label: 'WOW', value: fmtM(heroData.contribucion.wow), current: heroData.contribucion.actual, target: heroData.contribucion.wow },
                { label: 'YOY', value: fmtM(heroData.contribucion.yoy), current: heroData.contribucion.yoy, target: heroData.contribucion.yoy },
                { label: '2YOY', value: fmtM(heroData.contribucion.twoyoy), current: heroData.contribucion.actual, target: heroData.contribucion.twoyoy },
              ]}
            />
          </button>
          <button onClick={() => onSelectModule('principal')} className="text-left cursor-pointer transition-transform hover:-translate-y-0.5 min-w-0">
            <KPICard
              title="MARGEN FRONTAL (%)" mainValue={fmtPct(heroData.margen.actual)}
              colorValue={isDark ? '#30D158' : '#15803D'}
              sparklineSvg={buildSparklineSvg(heroData.margen.serie, isDark ? '#30D158' : '#15803D')}
              theme={theme}
              rows={[
                { label: 'WOW', value: fmtPct(heroData.margen.wow), current: heroData.margen.actual, target: heroData.margen.wow, isPP: true },
                { label: 'YOY', value: fmtPct(heroData.margen.yoy), current: heroData.margen.actual, target: heroData.margen.yoy, isPP: true },
                { label: '2YOY', value: fmtPct(heroData.margen.twoyoy), current: heroData.margen.actual, target: heroData.margen.twoyoy, isPP: true },
              ]}
            />
          </button>
          <button onClick={() => onSelectModule('principal')} className="text-left cursor-pointer transition-transform hover:-translate-y-0.5 min-w-0">
            <KPICard
              title="TICKET PROMEDIO (TKP)" mainValue={fmtClp(heroData.tkp.actual)}
              colorValue={isDark ? '#FF9F0A' : '#B45309'}
              sparklineSvg={buildSparklineSvg(heroData.tkp.serie, isDark ? '#FF9F0A' : '#B45309')}
              theme={theme}
              rows={[
                { label: 'WOW', value: fmtClp(heroData.tkp.wow), current: heroData.tkp.actual, target: heroData.tkp.wow },
                { label: 'YOY', value: fmtClp(heroData.tkp.yoy), current: heroData.tkp.actual, target: heroData.tkp.yoy },
                { label: '2YOY', value: fmtClp(heroData.tkp.twoyoy), current: heroData.tkp.actual, target: heroData.tkp.twoyoy },
              ]}
            />
          </button>
        </div>

        {/* Tendencia Mensual + Donut Canales */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3.5 min-w-0">
          <div className={`lg:col-span-3 p-4 sm:p-5 rounded-2xl border min-w-0 overflow-hidden ${panelBg}`}>
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="text-xs font-black uppercase tracking-wider text-blue-500 flex items-center gap-2 truncate">
                <TrendingUp className="w-4 h-4 shrink-0" /> TENDENCIA MENSUAL YOY (%) & VENTA ($ M)
              </h3>
              <button onClick={() => onSelectModule('principal')} className={`text-[11px] font-bold flex items-center gap-1 ${mutedText} hover:text-blue-500 cursor-pointer shrink-0`}>
                Detalle <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="h-60 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%" debounce={50}>
                <ComposedChart data={processedMonthsData} margin={{ top: 20, right: 15, left: 15, bottom: 5 }}>
                  <XAxis dataKey="month" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={11} tickLine={false} />
                  <YAxis yAxisId="left" hide />
                  <YAxis yAxisId="right" hide domain={['dataMin - 15', 'dataMax + 25']} />
                  <Tooltip content={<CustomTooltipGraph theme={theme} />} />
                  <Bar yAxisId="left" dataKey="ly" name="Año Anterior" fill={isDark ? '#2C2C2E' : '#cbd5e1'} radius={[4, 4, 0, 0]} />
                  <Bar yAxisId="left" dataKey="cy" name="Año Actual" fill="#0A84FF" radius={[4, 4, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="yoy" name="VAR YoY%" stroke="#30D158" strokeWidth={2.5} connectNulls={false}
                    dot={(dotProps: any) => {
                      const { cx, cy, payload } = dotProps;
                      if (!payload || !payload.cy || payload.cy <= 0) return <React.Fragment key={dotProps.index} />;
                      return <circle key={dotProps.index} cx={cx} cy={cy} r={4.5} fill="#30D158" />;
                    }}
                  >
                    <LabelList dataKey="yoy" content={<CustomLineLabel data={processedMonthsData} />} />
                  </Line>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`p-4 sm:p-5 rounded-2xl border min-w-0 overflow-hidden ${panelBg} flex flex-col justify-between`}>
            <h3 className="text-xs font-black uppercase tracking-wider text-purple-500 flex items-center gap-2 truncate">
              <PieIcon className="w-4 h-4 shrink-0" /> MIX VENTA POR CANAL
            </h3>
            <div className="h-40 w-full relative min-w-0">
              <ResponsiveContainer width="100%" height="100%" debounce={50}>
                <PieChart>
                  <Pie data={dataPieCanales} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={42} outerRadius={64} paddingAngle={4}>
                    {dataPieCanales.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PALETA_NEON[index % PALETA_NEON.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltipGraph theme={theme} />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className={`text-[9.5px] font-black uppercase ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Total</span>
                <span className={`text-xs font-black ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(dataPieCanales.reduce((a, c) => a + c.value, 0))}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-1.5 pt-2 border-t border-slate-100 dark:border-[#2C2C2E] min-w-0">
              {dataPieCanales.map((c, i) => {
                const isPos = c.yoyVal >= 0;
                return (
                  <div key={i} className="flex items-center justify-between text-[10.5px] min-w-0">
                    <div className="flex items-center gap-1.5 min-w-0 truncate">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: PALETA_NEON[i % PALETA_NEON.length] }} />
                      <span className={`truncate font-bold ${isDark ? 'text-zinc-300' : 'text-slate-700'}`}>{c.name}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                      <span className={`font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(c.value)}</span>
                      {c.isValid && (
                        <span className={`font-black px-1 py-0.2 rounded text-[9.5px] ${
                          isPos ? (isDark ? 'bg-emerald-500/10 text-emerald-400' : 'bg-emerald-50 text-emerald-700') : (isDark ? 'bg-rose-500/10 text-rose-400' : 'bg-rose-50 text-rose-700')
                        }`}>
                          {c.yoyText}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Rankings Top 3 & Bottom 3 SKUs y Categorías */}
        {isModuleAllowed('ventas_sku') && (
          <ModuleCardFuturistic
            icon={Package}
            title="RANKING VENTAS POR PRODUCTO Y CATEGORÍA (TOP 3 VS. BOTTOM 3)"
            color={isDark ? '#38BDF8' : '#0055D6'}
            onClick={() => onSelectModule('ventas_sku')}
            isDark={isDark}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5 min-w-0">
              {/* Top 3 Productos */}
              <div className={`p-3.5 rounded-2xl border min-w-0 ${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-emerald-50/60 border-emerald-200'}`}>
                <div className="flex items-center justify-between mb-2.5 pb-1.5 border-b border-emerald-500/20">
                  <span className={`text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 truncate ${isDark ? 'text-emerald-400' : 'text-emerald-800'}`}>
                    <Trophy className="w-3.5 h-3.5 text-emerald-500 shrink-0" /> Top 3 Productos
                  </span>
                  <span className="text-[9.5px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 shrink-0">Líderes</span>
                </div>
                <div className="space-y-2">
                  {top3Productos.length === 0 ? SIN_DATOS(isDark) : top3Productos.map((p: any, i: number) => (
                    <AppleRankItem
                      key={i} rank={i + 1} name={p.nombre} meta={`${fmtInt(p.cantCy)} u.`}
                      value={fmtM(p.ventaCy)} yoyValue={p.ventaYoy ? fmtM(p.ventaYoy) : undefined}
                      yoyPct={safePctVar(p.ventaCy, p.ventaYoy).isValid ? safePctVar(p.ventaCy, p.ventaYoy).val : undefined}
                      isDark={isDark} accentColor="#30D158"
                    />
                  ))}
                </div>
              </div>

              {/* Bottom 3 Productos */}
              <div className={`p-3.5 rounded-2xl border min-w-0 ${isDark ? 'bg-rose-500/10 border-rose-500/20' : 'bg-rose-50/60 border-rose-200'}`}>
                <div className="flex items-center justify-between mb-2.5 pb-1.5 border-b border-rose-500/20">
                  <span className={`text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 truncate ${isDark ? 'text-rose-400' : 'text-rose-800'}`}>
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-500 shrink-0" /> Bottom 3 Productos
                  </span>
                  <span className="text-[9.5px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-600 dark:text-rose-400 shrink-0">Oportunidad</span>
                </div>
                <div className="space-y-2">
                  {bottom3Productos.length === 0 ? SIN_DATOS(isDark) : bottom3Productos.map((p: any, i: number) => (
                    <AppleRankItem
                      key={i} rank={i + 1} name={p.nombre} meta={`${fmtInt(p.cantCy)} u.`}
                      value={fmtM(p.ventaCy)} yoyValue={p.ventaYoy ? fmtM(p.ventaYoy) : undefined}
                      yoyPct={safePctVar(p.ventaCy, p.ventaYoy).isValid ? safePctVar(p.ventaCy, p.ventaYoy).val : undefined}
                      isDark={isDark} accentColor="#FF453A"
                    />
                  ))}
                </div>
              </div>

              {/* Top 3 Categorías */}
              <div className={`p-3.5 rounded-2xl border min-w-0 ${isDark ? 'bg-blue-500/10 border-blue-500/20' : 'bg-blue-50/60 border-blue-200'}`}>
                <div className="flex items-center justify-between mb-2.5 pb-1.5 border-b border-blue-500/20">
                  <span className={`text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 truncate ${isDark ? 'text-blue-400' : 'text-blue-800'}`}>
                    <Trophy className="w-3.5 h-3.5 text-blue-500 shrink-0" /> Top 3 Categorías
                  </span>
                  <span className="text-[9.5px] font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-600 dark:text-blue-400 shrink-0">Líderes</span>
                </div>
                <div className="space-y-2">
                  {top3Categorias.length === 0 ? SIN_DATOS(isDark) : top3Categorias.map((c: any, i: number) => (
                    <AppleRankItem
                      key={i} rank={i + 1} name={c.categoria} meta={`${fmtInt(c.cantCy)} u.`}
                      value={fmtM(c.ventaCy)} yoyValue={c.ventaYoy ? fmtM(c.ventaYoy) : undefined}
                      yoyPct={safePctVar(c.ventaCy, c.ventaYoy).isValid ? safePctVar(c.ventaCy, c.ventaYoy).val : undefined}
                      isDark={isDark} accentColor="#0A84FF"
                    />
                  ))}
                </div>
              </div>

              {/* Bottom 3 Categorías */}
              <div className={`p-3.5 rounded-2xl border min-w-0 ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50/60 border-amber-200'}`}>
                <div className="flex items-center justify-between mb-2.5 pb-1.5 border-b border-amber-500/20">
                  <span className={`text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 truncate ${isDark ? 'text-amber-400' : 'text-amber-800'}`}>
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" /> Bottom 3 Categorías
                  </span>
                  <span className="text-[9.5px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-400 shrink-0">Oportunidad</span>
                </div>
                <div className="space-y-2">
                  {bottom3Categorias.length === 0 ? SIN_DATOS(isDark) : bottom3Categorias.map((c: any, i: number) => (
                    <AppleRankItem
                      key={i} rank={i + 1} name={c.categoria} meta={`${fmtInt(c.cantCy)} u.`}
                      value={fmtM(c.ventaCy)} yoyValue={c.ventaYoy ? fmtM(c.ventaYoy) : undefined}
                      yoyPct={safePctVar(c.ventaCy, c.ventaYoy).isValid ? safePctVar(c.ventaCy, c.ventaYoy).val : undefined}
                      isDark={isDark} accentColor="#FF9F0A"
                    />
                  ))}
                </div>
              </div>
            </div>
          </ModuleCardFuturistic>
        )}
      </section>

      {/* =========================================================================
          ZONA 2: CANALES B2B CORPORATIVOS
          ========================================================================= */}
      <section className="space-y-3.5 min-w-0">
        <SectionHeader
          icon={Building2}
          title="Canales B2B & Cuentas Clave"
          subtitle="Desempeño en distribuidores mayoristas y proyectos inmobiliarios"
          isDark={isDark}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 min-w-0">
          {/* DISTRIBUIDORES B2B */}
          {isModuleAllowed('distribuidores') && (
            <ModuleCardFuturistic 
              icon={Building2} 
              title="CANAL DISTRIBUIDORES B2B (TOP 3 VS. BOTTOM 3)" 
              badge="Mayoristas"
              color={isDark ? '#0A84FF' : '#0055D6'} 
              onClick={() => onSelectModule('distribuidores')} 
              isDark={isDark}
            >
              <div className="space-y-3 min-w-0">
                <div className={`flex items-center justify-between p-3 rounded-xl border ${
                  isDark ? 'bg-black/30 border-white/10' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div>
                    <span className={`text-[10px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Venta Canal Distribuidores</span>
                    <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(resumenData?.distribuidores?.venta_actual)}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-[10px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Año Anterior</span>
                    <span className={`text-xs font-bold font-mono ${isDark ? 'text-zinc-400' : 'text-slate-600'}`}>{fmtM(resumenData?.distribuidores?.venta_yoy)}</span>
                  </div>
                  <span className={`text-[10.5px] font-black px-2.5 py-1 rounded-md border ${
                    (resumenData?.distribuidores?.var_pct_yoy || 0) >= 0
                      ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    YoY {(resumenData?.distribuidores?.var_pct_yoy || 0) >= 0 ? '+' : ''}{resumenData?.distribuidores?.var_pct_yoy || 0}%
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 min-w-0">
                  <div className="space-y-1.5 min-w-0">
                    <span className="text-[10px] font-black uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1 truncate">
                      <Trophy className="w-3 h-3 shrink-0" /> Top 3 Clientes Líderes
                    </span>
                    {(resumenData?.distribuidores?.top3 || []).map((d: any, idx: number) => (
                      <AppleRankItem
                        key={idx} rank={idx + 1} name={d.nombre} 
                        value={fmtM(d.venta)} yoyValue={fmtM(d.venta_yoy)}
                        yoyPct={d.var_pct_yoy} isDark={isDark} accentColor="#30D158"
                      />
                    ))}
                    {(resumenData?.distribuidores?.top3 || []).length === 0 && SIN_DATOS(isDark)}
                  </div>

                  <div className="space-y-1.5 min-w-0">
                    <span className="text-[10px] font-black uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1 truncate">
                      <AlertTriangle className="w-3 h-3 shrink-0" /> Bottom 3 En Observación
                    </span>
                    {(resumenData?.distribuidores?.bottom3 || []).map((d: any, idx: number) => (
                      <AppleRankItem
                        key={idx} rank={idx + 1} name={d.nombre} 
                        value={fmtM(d.venta)} yoyValue={fmtM(d.venta_yoy)}
                        yoyPct={d.var_pct_yoy} isDark={isDark} accentColor="#FF9F0A"
                      />
                    ))}
                    {(resumenData?.distribuidores?.bottom3 || []).length === 0 && SIN_DATOS(isDark)}
                  </div>
                </div>
              </div>
            </ModuleCardFuturistic>
          )}

          {/* INMOBILIARIA & PROYECTOS */}
          {isModuleAllowed('inmobiliaria') && (
            <ModuleCardFuturistic 
              icon={Building} 
              title="CANAL INMOBILIARIA & PROYECTOS (TOP 3 VS. BOTTOM 3)" 
              badge="Constructoras"
              color={isDark ? '#BF5AF2' : '#7C3AED'} 
              onClick={() => onSelectModule('inmobiliaria')} 
              isDark={isDark}
            >
              <div className="space-y-3 min-w-0">
                <div className={`flex items-center justify-between p-3 rounded-xl border ${
                  isDark ? 'bg-black/30 border-white/10' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div>
                    <span className={`text-[10px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Venta Canal Inmobiliaria</span>
                    <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(resumenData?.inmobiliaria?.venta_actual)}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-[10px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Año Anterior</span>
                    <span className={`text-xs font-bold font-mono ${isDark ? 'text-zinc-400' : 'text-slate-600'}`}>{fmtM(resumenData?.inmobiliaria?.venta_yoy)}</span>
                  </div>
                  <span className={`text-[10.5px] font-black px-2.5 py-1 rounded-md border ${
                    (resumenData?.inmobiliaria?.var_pct_yoy || 0) >= 0
                      ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    YoY {(resumenData?.inmobiliaria?.var_pct_yoy || 0) >= 0 ? '+' : ''}{resumenData?.inmobiliaria?.var_pct_yoy || 0}%
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 min-w-0">
                  <div className="space-y-1.5 min-w-0">
                    <span className="text-[10px] font-black uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1 truncate">
                      <Trophy className="w-3 h-3 shrink-0" /> Top 3 Cuentas Líderes
                    </span>
                    {(resumenData?.inmobiliaria?.top3 || []).map((d: any, idx: number) => (
                      <AppleRankItem
                        key={idx} rank={idx + 1} name={d.nombre} 
                        value={fmtM(d.venta)} yoyValue={fmtM(d.venta_yoy)}
                        yoyPct={d.var_pct_yoy} isDark={isDark} accentColor="#BF5AF2"
                      />
                    ))}
                    {(resumenData?.inmobiliaria?.top3 || []).length === 0 && SIN_DATOS(isDark)}
                  </div>

                  <div className="space-y-1.5 min-w-0">
                    <span className="text-[10px] font-black uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1 truncate">
                      <AlertTriangle className="w-3 h-3 shrink-0" /> Bottom 3 En Observación
                    </span>
                    {(resumenData?.inmobiliaria?.bottom3 || []).map((d: any, idx: number) => (
                      <AppleRankItem
                        key={idx} rank={idx + 1} name={d.nombre} 
                        value={fmtM(d.venta)} yoyValue={fmtM(d.venta_yoy)}
                        yoyPct={d.var_pct_yoy} isDark={isDark} accentColor="#FF9F0A"
                      />
                    ))}
                    {(resumenData?.inmobiliaria?.bottom3 || []).length === 0 && SIN_DATOS(isDark)}
                  </div>
                </div>
              </div>
            </ModuleCardFuturistic>
          )}
        </div>
      </section>

      {/* =========================================================================
          ZONA 3: LOGÍSTICA, OPERACIONES & RIESGO
          ========================================================================= */}
      <section className="space-y-3.5 min-w-0">
        <SectionHeader
          icon={Truck}
          title="Logística, Operaciones & Riesgo"
          subtitle="Documentos retenidos por despachar y balance operativo de couriers"
          isDark={isDark}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 min-w-0">
          {isModuleAllowed('pendientes_despacho') && (
            <ModuleCardFuturistic icon={ClipboardList} title="PENDIENTES POR DESPACHAR" badge="Exposición" color={isDark ? '#FF9F0A' : '#B45309'} onClick={() => onSelectModule('pendientes_despacho')} isDark={isDark}>
              <div className="space-y-3 min-w-0">
                <div className="grid grid-cols-2 gap-3">
                  <div className={`p-3 rounded-xl border ${isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-black uppercase text-amber-500 block">Doc. Retenidos</span>
                    <span className={`text-xl font-black ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtInt(resumenData?.pendientes_despacho?.documentos_pendientes)}</span>
                  </div>
                  <div className={`p-3 rounded-xl border ${isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-black uppercase text-amber-500 block">Monto en Riesgo</span>
                    <span className="text-xl font-black text-rose-500">{fmtM(resumenData?.pendientes_despacho?.monto_total)}</span>
                  </div>
                </div>
                <div>
                  <p className={`text-[10px] font-black uppercase tracking-wider mb-2 ${mutedText}`}>Mayor Concentración por Vendedor</p>
                  <div className="space-y-2">
                    {(resumenData?.pendientes_despacho?.top_vendedores || []).slice(0, 3).map((v: any, i: number) => (
                      <div key={i} className={`flex items-center justify-between text-xs p-2 rounded-lg border ${
                        isDark ? 'bg-white/5 border-white/5' : 'bg-slate-50 border-slate-200'
                      }`}>
                        <span className={`font-bold truncate ${isDark ? 'text-zinc-200' : 'text-slate-800'}`}>{v.vendedor}</span>
                        <span className="font-black text-rose-500 font-mono">{fmtM(v.monto)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ModuleCardFuturistic>
          )}

          {isModuleAllowed('control_logistico') && (
            <ModuleCardFuturistic icon={Send} title="CONTROL LOGÍSTICO & MARGEN FLETE" badge="Envíame ↔ Bsale" color={isDark ? '#0A84FF' : '#0055D6'} onClick={() => onSelectModule('control_logistico')} isDark={isDark}>
              {resumenData?.logistica?.disponible ? (
                <div className="space-y-3 min-w-0">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-blue-500/10 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
                      <span className={`text-[9.5px] font-black uppercase block ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>Despachos</span>
                      <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtInt(resumenData.logistica.despachosCy)}</span>
                    </div>
                    <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50 border-amber-200'}`}>
                      <span className={`text-[9.5px] font-black uppercase block ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>Costo Envíame</span>
                      <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtClp(resumenData.logistica.costoEnviameCy)}</span>
                    </div>
                    <div className={`p-2.5 rounded-xl border ${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-emerald-50 border-emerald-200'}`}>
                      <span className={`text-[9.5px] font-black uppercase block ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>Cobro Bsale</span>
                      <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtClp(resumenData.logistica.cobroBsaleCy)}</span>
                    </div>
                  </div>

                  <div className={`p-3 rounded-xl border ${
                    resumenData.logistica.diferencia < 0 
                      ? (isDark ? 'bg-rose-500/10 border-rose-500/30' : 'bg-rose-50 border-rose-200') 
                      : (isDark ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-emerald-50 border-emerald-200')
                  }`}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className={`font-black uppercase ${isDark ? 'text-zinc-200' : 'text-slate-800'}`}>Resultado Flete Operativo:</span>
                      <span className={`font-extrabold text-sm ${resumenData.logistica.diferencia < 0 ? 'text-rose-500' : 'text-emerald-600 dark:text-emerald-400'}`}>
                        {fmtClp(resumenData.logistica.diferencia)} {resumenData.logistica.diferencia < 0 ? '(Déficit)' : '(Superávit)'}
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                      <div className={`h-full rounded-full ${resumenData.logistica.diferencia < 0 ? 'bg-rose-500' : 'bg-emerald-500'}`} style={{ width: '100%' }} />
                    </div>
                  </div>
                </div>
              ) : null}
            </ModuleCardFuturistic>
          )}
        </div>
      </section>

      {/* =========================================================================
          ZONA 4: MARKETING DIGITAL, CLIMA & E-COMMERCE
          ========================================================================= */}
      <section className="space-y-3.5 min-w-0">
        <SectionHeader
          icon={Megaphone}
          title="Marketing Digital, Demanda & Conversión Web"
          subtitle="Pauta bimarca, correlación climática y embudo de conversión D2C"
          isDark={isDark}
        />

        {/* Marketing Bimarca */}
        {isModuleAllowed('campanas_mkt') && (
          <ModuleCardFuturistic 
            icon={Megaphone} 
            title="MARKETING DIGITAL: INVERSIÓN, RETORNO & TACOS (%) POR MARCA" 
            badge="Kaltemp vs. Tom Palmer" 
            color={isDark ? '#0A84FF' : '#0055D6'} 
            onClick={() => onSelectModule('campanas_mkt')} 
            isDark={isDark}
          >
            <div className="space-y-3.5 min-w-0">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center min-w-0">
                <div className={`p-3 rounded-xl border ${isDark ? 'bg-blue-500/10 border-blue-500/20' : 'bg-blue-50/60 border-blue-100'}`}>
                  <span className={`text-[9.5px] font-black uppercase block mb-0.5 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>Inversión Total</span>
                  <span className={`text-base font-black block font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(mktAgregado.global.inversion)}</span>
                  <span className={`text-[10px] font-black inline-block mt-1 px-1.5 py-0.5 rounded ${
                    mktAgregado.global.varInversionYoy >= 0 ? (isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-100 text-emerald-800') : (isDark ? 'bg-rose-500/20 text-rose-400' : 'bg-rose-100 text-rose-800')
                  }`}>
                    YoY {mktAgregado.global.varInversionYoy >= 0 ? '+' : ''}{mktAgregado.global.varInversionYoy.toFixed(1)}%
                  </span>
                </div>

                <div className={`p-3 rounded-xl border ${isDark ? 'bg-purple-500/10 border-purple-500/20' : 'bg-purple-50/60 border-purple-100'}`}>
                  <span className={`text-[9.5px] font-black uppercase block mb-0.5 ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>Impresiones</span>
                  <span className={`text-base font-black block font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtInt(mktAgregado.global.impresiones)}</span>
                  <span className={`text-[10px] font-black inline-block mt-1 px-1.5 py-0.5 rounded ${
                    mktAgregado.global.varImpresionesYoy >= 0 ? (isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-100 text-emerald-800') : (isDark ? 'bg-rose-500/20 text-rose-400' : 'bg-rose-100 text-rose-800')
                  }`}>
                    YoY {mktAgregado.global.varImpresionesYoy >= 0 ? '+' : ''}{mktAgregado.global.varImpresionesYoy.toFixed(1)}%
                  </span>
                </div>

                <div className={`p-3 rounded-xl border ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50/60 border-amber-100'}`}>
                  <span className={`text-[9.5px] font-black uppercase block mb-0.5 ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>CTR Promedio</span>
                  <span className={`text-base font-black block font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtPct(mktAgregado.global.ctr, 2)}</span>
                  <span className={`text-[10px] font-black inline-block mt-1 px-1.5 py-0.5 rounded ${
                    mktAgregado.global.varCtrYoy >= 0 ? (isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-100 text-emerald-800') : (isDark ? 'bg-rose-500/20 text-rose-400' : 'bg-rose-100 text-rose-800')
                  }`}>
                    YoY {mktAgregado.global.varCtrYoy >= 0 ? '+' : ''}{mktAgregado.global.varCtrYoy.toFixed(1)}%
                  </span>
                </div>

                <div className={`p-3 rounded-xl border ${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-emerald-50/60 border-emerald-200'}`}>
                  <span className={`text-[9.5px] font-black uppercase block mb-0.5 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>TACOS Global</span>
                  <span className={`text-base font-black block font-mono ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>{fmtPct(mktAgregado.global.tacos, 2)}</span>
                  <span className={`text-[10px] font-black inline-block mt-1 px-1.5 py-0.5 rounded ${
                    mktAgregado.global.varTacosYoy <= 0 ? (isDark ? 'bg-emerald-500/20 text-emerald-400' : 'bg-emerald-100 text-emerald-800') : (isDark ? 'bg-rose-500/20 text-rose-400' : 'bg-rose-100 text-rose-800')
                  }`}>
                    YoY {mktAgregado.global.varTacosYoy >= 0 ? '+' : ''}{mktAgregado.global.varTacosYoy.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Bimarca cards */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-center min-w-0">
                <div className={`lg:col-span-4 p-3.5 rounded-2xl border space-y-1.5 text-xs min-w-0 ${
                  isDark ? 'bg-blue-500/10 border-blue-500/30' : 'bg-blue-50/40 border-blue-100'
                }`}>
                  <div className="flex items-center justify-between pb-1 border-b border-blue-500/20">
                    <span className={`font-black uppercase ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>Kaltemp</span>
                    <span className={`font-black font-mono ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>TACOS: {fmtPct(mktAgregado.kaltemp.tacos, 1)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className={`${isDark ? 'text-zinc-400' : 'text-slate-600'} font-medium`}>Inversión:</span>
                    <span className={`font-mono font-black ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(mktAgregado.kaltemp.inversion)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className={`${isDark ? 'text-zinc-400' : 'text-slate-600'} font-medium`}>Venta D2C:</span>
                    <span className={`font-mono font-black ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>{fmtM(mktAgregado.kaltemp.venta)}</span>
                  </div>
                </div>

                <div className={`lg:col-span-4 p-3.5 rounded-2xl border space-y-1.5 text-xs min-w-0 ${
                  isDark ? 'bg-purple-500/10 border-purple-500/30' : 'bg-purple-50/40 border-purple-100'
                }`}>
                  <div className="flex items-center justify-between pb-1 border-b border-purple-500/20">
                    <span className={`font-black uppercase ${isDark ? 'text-purple-400' : 'text-purple-700'}`}>Tom Palmer</span>
                    <span className={`font-black font-mono ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>TACOS: {fmtPct(mktAgregado.tomPalmer.tacos, 1)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className={`${isDark ? 'text-zinc-400' : 'text-slate-600'} font-medium`}>Inversión:</span>
                    <span className={`font-mono font-black ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(mktAgregado.tomPalmer.inversion)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className={`${isDark ? 'text-zinc-400' : 'text-slate-600'} font-medium`}>Venta D2C:</span>
                    <span className={`font-mono font-black ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>{fmtM(mktAgregado.tomPalmer.venta)}</span>
                  </div>
                </div>

                <div className="lg:col-span-4 h-28 w-full min-w-0">
                  <ResponsiveContainer width="100%" height="100%" debounce={50}>
                    <BarChart data={mktAgregado.chartBimarca} margin={{ top: 12, right: 10, left: 10, bottom: 0 }}>
                      <XAxis dataKey="marca" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={10} tickLine={false} />
                      <YAxis hide />
                      <Tooltip content={<CustomTooltipGraph theme={theme} />} />
                      <Bar dataKey="inversion" name="Inversión ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
                        <LabelList dataKey="inversion" position="top" formatter={(v: number) => `$${v.toFixed(1)}M`} style={{ fontSize: '9px', fontWeight: 'bold', fill: isDark ? '#F5F5F7' : '#1E293B' }} />
                      </Bar>
                      <Bar dataKey="venta" name="Venta D2C ($M)" fill="#30D158" radius={[4, 4, 0, 0]}>
                        <LabelList dataKey="venta" position="top" formatter={(v: number) => `$${v.toFixed(1)}M`} style={{ fontSize: '9px', fontWeight: 'bold', fill: '#30D158' }} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </ModuleCardFuturistic>
        )}

        {/* Ventas vs Temperatura Santiago */}
        {isModuleAllowed('ventas_temperatura') && (
          <ModuleCardFuturistic 
            icon={Thermometer} 
            title="COMPORTAMIENTO DIARIO DE VENTAS VS. TEMPERATURAS SANTIAGO (ACTUAL Y YOY - SIN EJE Y)" 
            badge="Santiago" 
            color={isDark ? '#FF9F0A' : '#B45309'} 
            onClick={() => onSelectModule('ventas_temperatura')} 
            isDark={isDark}
          >
            <div className="space-y-2.5 min-w-0">
              <div className="flex flex-wrap items-center justify-center gap-4 text-[10.5px] font-bold py-0.5">
                <span className="flex items-center gap-1.5 text-amber-500">
                  <span className="w-2.5 h-0.5 bg-amber-500" />
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                  Temp. Máx Actual (°C)
                </span>
                <span className="flex items-center gap-1.5 text-amber-500/80">
                  <span className="w-3 h-0.5 border-b border-dashed border-amber-500 shrink-0" />
                  Temp. Máx YoY (°C)
                </span>
                <span className="flex items-center gap-1.5 text-sky-400">
                  <span className="w-2.5 h-0.5 bg-sky-400" />
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0" />
                  Temp. Mín Actual (°C)
                </span>
                <span className="flex items-center gap-1.5 text-sky-400/80">
                  <span className="w-3 h-0.5 border-b border-dashed border-sky-400 shrink-0" />
                  Temp. Mín YoY (°C)
                </span>
                <span className="flex items-center gap-1.5 text-blue-500">
                  <span className="w-2.5 h-2.5 rounded-sm bg-[#0A84FF] shrink-0" />
                  Venta ($M)
                </span>
              </div>

              <div className="h-60 w-full min-w-0">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <ComposedChart data={dataTempChartExact} margin={{ top: 20, right: 15, left: 15, bottom: 5 }}>
                    <XAxis dataKey="fecha" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={10} tickLine={false} />
                    <YAxis yAxisId="venta" hide />
                    <YAxis yAxisId="temp" hide domain={['dataMin - 4', 'dataMax + 4']} />
                    <Tooltip content={<CustomTooltipGraph theme={theme} />} />

                    <Bar yAxisId="venta" dataKey="venta" name="Venta ($M)" fill="#0A84FF" radius={[3, 3, 0, 0]}>
                      <LabelList dataKey="venta" position="top" formatter={(v: number) => `$${v.toFixed(1)}M`} style={{ fontSize: '9.5px', fontWeight: 'bold', fill: isDark ? '#F5F5F7' : '#1E293B' }} />
                    </Bar>

                    <Line yAxisId="temp" type="monotone" dataKey="tempMax" name="Temp. Máx Actual (°C)" stroke="#FF9F0A" strokeWidth={2.5} dot={{ r: 3.5, fill: '#FF9F0A' }}>
                      <LabelList dataKey="tempMax" position="top" formatter={(v: number) => `${v.toFixed(1)}°C`} style={{ fontSize: '9px', fontWeight: 'bold', fill: '#FF9F0A' }} />
                    </Line>
                    <Line yAxisId="temp" type="monotone" dataKey="tempMaxYoY" name="Temp. Máx YoY (°C)" stroke="#FF9F0A" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                    <Line yAxisId="temp" type="monotone" dataKey="tempMin" name="Temp. Mín Actual (°C)" stroke="#5AC8FA" strokeWidth={2.5} dot={{ r: 3.5, fill: '#5AC8FA' }}>
                      <LabelList dataKey="tempMin" position="bottom" formatter={(v: number) => `${v.toFixed(1)}°C`} style={{ fontSize: '9px', fontWeight: 'bold', fill: '#5AC8FA' }} />
                    </Line>
                    <Line yAxisId="temp" type="monotone" dataKey="tempMinYoY" name="Temp. Mín YoY (°C)" stroke="#5AC8FA" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          </ModuleCardFuturistic>
        )}

        {/* Módulos Digitales */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5 min-w-0">
          
          {/* CRM LEADS CON TOP VENDEDOR Y TOP PRODUCTO */}
          {isModuleAllowed('leads') && (
            <ModuleCardFuturistic icon={Target} title="CRM LEADS" badge="Leads & YoY" color={isDark ? '#0A84FF' : '#0055D6'} onClick={() => onSelectModule('leads')} isDark={isDark}>
              <div className="space-y-2.5 min-w-0">
                {/* Métricas Generales */}
                <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
                  isDark ? 'bg-black/30 border-white/10' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div>
                    <span className={`text-[9.5px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Leads Actual</span>
                    <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtInt(resumenData?.leads?.leads_actual)}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-[9.5px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Leads YoY</span>
                    <span className={`text-xs font-bold font-mono ${isDark ? 'text-zinc-400' : 'text-slate-600'}`}>{fmtInt(resumenData?.leads?.leads_yoy)}</span>
                  </div>
                  <span className={`text-[10px] font-black px-2 py-1 rounded-md border ${
                    (resumenData?.leads?.leads_var_pct_yoy || 0) >= 0
                      ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    {(resumenData?.leads?.leads_var_pct_yoy || 0) >= 0 ? '+' : ''}{resumenData?.leads?.leads_var_pct_yoy || 0}%
                  </span>
                </div>

                {/* Tasa de Conversión */}
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className={`font-bold ${isDark ? 'text-zinc-400' : 'text-slate-600'}`}>Convertidos a Venta:</span>
                    <span className="font-mono font-black text-emerald-600 dark:text-emerald-400">
                      {fmtInt(resumenData?.leads?.convertidos)} ({resumenData?.leads?.tasaConversion}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(100, resumenData?.leads?.tasaConversion || 0)}%` }} />
                  </div>
                </div>

                {/* Top Vendedor & Top Producto */}
                <div className="pt-1.5 border-t border-slate-100 dark:border-white/5 space-y-1.5">
                  {/* Top Vendedor */}
                  {resumenData?.leads?.top_vendedor && (
                    <div className={`p-2 rounded-xl border flex items-center justify-between gap-2 ${
                      isDark ? 'bg-white/[0.03] border-white/5' : 'bg-slate-50/80 border-slate-200'
                    }`}>
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <div className="p-1 rounded-lg bg-blue-500/10 text-blue-500 shrink-0">
                          <User className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>Vendedor Top</p>
                          <p className={`text-[11px] font-medium leading-tight truncate ${isDark ? 'text-zinc-200' : 'text-slate-800'}`}>
                            {resumenData.leads.top_vendedor.nombre}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end shrink-0 text-right leading-tight">
                        <span className={`text-[11.5px] font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          {fmtInt(resumenData.leads.top_vendedor.cant)} <span className="text-[9.5px] font-normal text-zinc-400">leads</span>
                        </span>
                        <span className={`text-[9px] font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
                          YoY {fmtInt(resumenData.leads.top_vendedor.cant_yoy)}
                        </span>
                        <span className={`text-[8.5px] font-black font-mono px-1 py-0.2 rounded mt-0.5 border ${
                          resumenData.leads.top_vendedor.var_pct_yoy >= 0
                            ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>
                          {resumenData.leads.top_vendedor.var_pct_yoy >= 0 ? '+' : ''}{resumenData.leads.top_vendedor.var_pct_yoy.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Top Producto */}
                  {resumenData?.leads?.top_producto && (
                    <div className={`p-2 rounded-xl border flex items-center justify-between gap-2 ${
                      isDark ? 'bg-white/[0.03] border-white/5' : 'bg-slate-50/80 border-slate-200'
                    }`}>
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <div className="p-1 rounded-lg bg-emerald-500/10 text-emerald-500 shrink-0">
                          <Package className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>Producto Top</p>
                          <p className={`text-[11px] font-medium leading-tight truncate ${isDark ? 'text-zinc-200' : 'text-slate-800'}`}>
                            {resumenData.leads.top_producto.nombre}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end shrink-0 text-right leading-tight">
                        <span className={`text-[11.5px] font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          {fmtInt(resumenData.leads.top_producto.cant)} <span className="text-[9.5px] font-normal text-zinc-400">leads</span>
                        </span>
                        <span className={`text-[9px] font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
                          YoY {fmtInt(resumenData.leads.top_producto.cant_yoy)}
                        </span>
                        <span className={`text-[8.5px] font-black font-mono px-1 py-0.2 rounded mt-0.5 border ${
                          resumenData.leads.top_producto.var_pct_yoy >= 0
                            ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>
                          {resumenData.leads.top_producto.var_pct_yoy >= 0 ? '+' : ''}{resumenData.leads.top_producto.var_pct_yoy.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </ModuleCardFuturistic>
          )}

          {/* CARRITOS ABANDONADOS CON TOP 3 PRODUCTOS Y PRECIO */}
          {isModuleAllowed('carros_abandonados') && (
            <ModuleCardFuturistic icon={ShoppingCart} title="CARRITOS ABANDONADOS" badge="Shopify" color={isDark ? '#FF453A' : '#DC2626'} onClick={() => onSelectModule('carros_abandonados')} isDark={isDark}>
              <div className="space-y-2.5 min-w-0">
                {/* Resumen General */}
                <div className={`p-2.5 rounded-xl border flex items-center justify-between ${
                  isDark ? 'bg-black/30 border-white/10' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div>
                    <span className={`text-[9.5px] font-black uppercase block ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Carritos</span>
                    <span className={`text-lg font-black font-mono ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtInt(resumenData?.carros_abandonados?.totalCarritos)}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[9.5px] font-black uppercase block text-rose-500">Monto en Riesgo</span>
                    <span className="text-base font-black font-mono text-rose-500">{fmtM(resumenData?.carros_abandonados?.oportunidadPerdida)}</span>
                  </div>
                </div>

                {/* Top 3 Productos Abandonados */}
                <div className="pt-1 border-t border-slate-100 dark:border-white/5 space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 flex items-center gap-1 truncate">
                    <AlertTriangle className="w-3 h-3 shrink-0" /> Top 3 Productos en Abandono
                  </span>

                  {(resumenData?.carros_abandonados?.top_productos || []).length === 0 ? (
                    SIN_DATOS(isDark)
                  ) : (
                    (resumenData?.carros_abandonados?.top_productos || []).map((p: any, idx: number) => (
                      <div key={idx} className={`p-2 rounded-xl border flex items-center justify-between gap-2 transition-all hover:scale-[1.01] ${
                        isDark ? 'bg-white/[0.03] border-white/5 text-white' : 'bg-slate-50/80 border-slate-200 text-slate-900'
                      }`}>
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <span className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0 bg-rose-500 shadow-sm">
                            {idx + 1}
                          </span>
                          <div className="min-w-0 flex-1 pr-1">
                            <p className={`text-[11px] font-medium leading-tight truncate ${isDark ? 'text-zinc-200' : 'text-slate-800'}`} title={p.nombre}>
                              {p.nombre}
                            </p>
                            <p className={`text-[9.5px] font-normal leading-tight mt-0.5 ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
                              {fmtInt(p.cant)} en carritos
                            </p>
                          </div>
                        </div>
                        <div className="flex flex-col items-end shrink-0 leading-tight pl-1 text-right">
                          <span className={`text-[11.5px] font-black font-mono ${isDark ? 'text-rose-400' : 'text-rose-600'}`}>
                            {fmtClp(p.precio)}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </ModuleCardFuturistic>
          )}

          {/* D2C & FUNNEL GA4 CON SESIONES YOY & VAR% */}
          {isModuleAllowed('indicadores_d2c') && (
            <ModuleCardFuturistic icon={TrendingUp} title="D2C & FUNNEL GA4" badge="Venta & Sesiones" color={isDark ? '#BF5AF2' : '#7C3AED'} onClick={() => onSelectModule('indicadores_d2c')} isDark={isDark}>
              <div className="space-y-2.5 min-w-0">
                
                {/* Kaltemp D2C */}
                <div className={`p-2.5 rounded-xl border space-y-1.5 ${
                  isDark ? 'bg-black/30 border-white/10' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="flex items-center justify-between border-b border-slate-200/60 dark:border-white/5 pb-1">
                    <span className="font-black text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">Kaltemp D2C</span>
                    <span className={`text-[9.5px] font-black font-mono px-2 py-0.5 rounded border ${
                      d2cProcessed.kaltemp.varVentaVal >= 0
                        ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}>
                      {d2cProcessed.kaltemp.varVentaText}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className={`text-[10px] block font-medium ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Venta Actual:</span>
                      <span className={`font-mono font-black text-sm ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(d2cProcessed.kaltemp.venta)}</span>
                      <span className={`text-[10px] block font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>YoY: {fmtM(d2cProcessed.kaltemp.ventaYoy)}</span>
                    </div>
                    <div className="text-right flex flex-col justify-end">
                      <span className={`text-[10px] block font-medium ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Sesiones GA4:</span>
                      <span className="font-mono font-black text-emerald-600 dark:text-emerald-400 text-sm">
                        {fmtInt(d2cProcessed.kaltemp.sesiones)}
                      </span>
                      <div className="flex items-center justify-end gap-1 mt-0.5">
                        <span className={`text-[9.5px] font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
                          YoY {fmtInt(d2cProcessed.kaltemp.sesionesYoy)}
                        </span>
                        <span className={`text-[8.5px] font-black font-mono px-1 py-0.2 rounded border ${
                          d2cProcessed.kaltemp.varSesionesVal >= 0
                            ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>
                          {d2cProcessed.kaltemp.varSesionesText}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Tom Palmer D2C */}
                <div className={`p-2.5 rounded-xl border space-y-1.5 ${
                  isDark ? 'bg-black/30 border-white/10' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="flex items-center justify-between border-b border-slate-200/60 dark:border-white/5 pb-1">
                    <span className="font-black text-xs text-blue-600 dark:text-blue-400 uppercase tracking-wide">Tom Palmer D2C</span>
                    <span className={`text-[9.5px] font-black font-mono px-2 py-0.5 rounded border ${
                      d2cProcessed.tomPalmer.varVentaVal >= 0
                        ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}>
                      {d2cProcessed.tomPalmer.varVentaText}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className={`text-[10px] block font-medium ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Venta Actual:</span>
                      <span className={`font-mono font-black text-sm ${isDark ? 'text-white' : 'text-slate-900'}`}>{fmtM(d2cProcessed.tomPalmer.venta)}</span>
                      <span className={`text-[10px] block font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>YoY: {fmtM(d2cProcessed.tomPalmer.ventaYoy)}</span>
                    </div>
                    <div className="text-right flex flex-col justify-end">
                      <span className={`text-[10px] block font-medium ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>Sesiones GA4:</span>
                      <span className="font-mono font-black text-blue-600 dark:text-blue-400 text-sm">
                        {fmtInt(d2cProcessed.tomPalmer.sesiones)}
                      </span>
                      <div className="flex items-center justify-end gap-1 mt-0.5">
                        <span className={`text-[9.5px] font-mono ${isDark ? 'text-zinc-400' : 'text-slate-500'}`}>
                          YoY {fmtInt(d2cProcessed.tomPalmer.sesionesYoy)}
                        </span>
                        <span className={`text-[8.5px] font-black font-mono px-1 py-0.2 rounded border ${
                          d2cProcessed.tomPalmer.varSesionesVal >= 0
                            ? isDark ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : isDark ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}>
                          {d2cProcessed.tomPalmer.varSesionesText}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </ModuleCardFuturistic>
          )}

        </div>
      </section>

    </div>
  );
};