// ============================================================
// Archivo: SalesTargetCumplimientoView.tsx
// Ruta:    src/views/SalesTargetCumplimientoView.tsx
// ============================================================

import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode } from '../types';
import {
  useGlobalFilter,
  ALL_REPS,
  ALL_CATEGORIES,
  ALL_CHANNELS,
  ALL_WAREHOUSES
} from '../context/FilterContext';
import { fetchCumplimiento, fetchRecomendacionesPrecioStock, fetchHistoricoAnual, fetchProductosActual, fetchSkuDetalleCumplimiento } from '../services/api';
import { SortableTh } from '../components/SortableTh';
import { DatosManualesModal } from '../components/DatosManualesModal';
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
  Trash2,
  Percent,
  Lightbulb,
  Sparkles,
  Database,
  ChevronRight,
  ChevronDown
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

  const [recomendacionesData, setRecomendacionesData] = useState<any | null>(null);
  const [loadingRecomendaciones, setLoadingRecomendaciones] = useState(true);

  const [historicoAnual, setHistoricoAnual] = useState<any[]>([]);
  const [loadingHistorico, setLoadingHistorico] = useState(true);
  const [showDatosManualesModal, setShowDatosManualesModal] = useState(false);

  const [productosActual, setProductosActual] = useState<any[]>([]);
  const [loadingProductosActual, setLoadingProductosActual] = useState(true);

  const [skuDetalle, setSkuDetalle] = useState<{ skus: any[]; totalUnidades: number; totalVenta: number; totalContribucion: number } | null>(null);
  const [loadingSkuDetalle, setLoadingSkuDetalle] = useState(true);
  const [skuSortKey, setSkuSortKey] = useState<string>('contribucion');
  const [skuSortDir, setSkuSortDir] = useState<'asc' | 'desc'>('desc');
  const [expandedSkus, setExpandedSkus] = useState<Record<string, boolean>>({});

  const cargarHistoricoAnual = () => {
    setLoadingHistorico(true);
    fetchHistoricoAnual()
      .then((res) => setHistoricoAnual(res.anios || []))
      .catch((err) => {
        console.error("Error al cargar histórico anual:", err);
        setHistoricoAnual([]);
      })
      .finally(() => setLoadingHistorico(false));
  };

  useEffect(() => {
    cargarHistoricoAnual();
  }, []);

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

  useEffect(() => {
    setLoadingRecomendaciones(true);

    const vendedoresFiltro = selectedReps.length < ALL_REPS.length ? selectedReps : [];
    const categoriasFiltro = selectedCategories.length < ALL_CATEGORIES.length ? selectedCategories : [];
    const canalesFiltro = selectedChannels.length < ALL_CHANNELS.length ? selectedChannels : [];
    const bodegasFiltro = selectedWarehouses.length < ALL_WAREHOUSES.length ? selectedWarehouses : [];

    fetchRecomendacionesPrecioStock(
      cicloComercial.startDate,
      cicloComercial.endDate,
      vendedoresFiltro,
      categoriasFiltro,
      canalesFiltro,
      bodegasFiltro,
      20
    )
      .then(setRecomendacionesData)
      .catch((err) => {
        console.error("Error al cargar recomendaciones de precio/stock:", err);
        setRecomendacionesData(null);
      })
      .finally(() => setLoadingRecomendaciones(false));
  }, [cicloComercial, selectedReps, selectedCategories, selectedChannels, selectedWarehouses]);

  useEffect(() => {
    setLoadingProductosActual(true);

    const vendedoresFiltro = selectedReps.length < ALL_REPS.length ? selectedReps : [];
    const categoriasFiltro = selectedCategories.length < ALL_CATEGORIES.length ? selectedCategories : [];
    const canalesFiltro = selectedChannels.length < ALL_CHANNELS.length ? selectedChannels : [];
    const bodegasFiltro = selectedWarehouses.length < ALL_WAREHOUSES.length ? selectedWarehouses : [];

    fetchProductosActual(
      cicloComercial.startDate,
      cicloComercial.endDate,
      vendedoresFiltro,
      categoriasFiltro,
      canalesFiltro,
      bodegasFiltro,
      10
    )
      .then((res) => setProductosActual(res.productos || []))
      .catch((err) => {
        console.error("Error al cargar productos del período:", err);
        setProductosActual([]);
      })
      .finally(() => setLoadingProductosActual(false));
  }, [cicloComercial, selectedReps, selectedCategories, selectedChannels, selectedWarehouses]);

  useEffect(() => {
    setLoadingSkuDetalle(true);

    const vendedoresFiltro = selectedReps.length < ALL_REPS.length ? selectedReps : [];
    const categoriasFiltro = selectedCategories.length < ALL_CATEGORIES.length ? selectedCategories : [];
    const canalesFiltro = selectedChannels.length < ALL_CHANNELS.length ? selectedChannels : [];
    const bodegasFiltro = selectedWarehouses.length < ALL_WAREHOUSES.length ? selectedWarehouses : [];

    fetchSkuDetalleCumplimiento(
      cicloComercial.startDate,
      cicloComercial.endDate,
      vendedoresFiltro,
      categoriasFiltro,
      canalesFiltro,
      bodegasFiltro
    )
      .then(setSkuDetalle)
      .catch((err) => {
        console.error("Error al cargar detalle de SKUs:", err);
        setSkuDetalle(null);
      })
      .finally(() => setLoadingSkuDetalle(false));
  }, [cicloComercial, selectedReps, selectedCategories, selectedChannels, selectedWarehouses]);

  const handleSkuSort = (key: string) => {
    if (skuSortKey === key) {
      setSkuSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSkuSortKey(key);
      setSkuSortDir('desc');
    }
  };

  const sortedSkuDetalle = useMemo(() => {
    const lista = skuDetalle?.skus ?? [];
    const copia = [...lista];
    copia.sort((a: any, b: any) => {
      const va = a[skuSortKey];
      const vb = b[skuSortKey];
      if (typeof va === 'string') {
        return skuSortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return skuSortDir === 'asc' ? va - vb : vb - va;
    });
    return copia;
  }, [skuDetalle, skuSortKey, skuSortDir]);

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
  const margenPct = cumplimientoData?.margenPct ?? 0;

  const recomendaciones = recomendacionesData?.recomendaciones ?? [];
  const totalRecomendaciones = recomendacionesData?.totalRecomendaciones ?? 0;

  const pctVenta = Math.round((ventaReal / (numVentaMeta || 1)) * 100);
  const pctContri = Math.round((contriReal / (numContriMeta || 1)) * 100);

  const daysElapsed = cumplimientoData?.diasTranscurridos ?? 1;
  const totalDaysCycle = cumplimientoData?.diasTotalCiclo ?? 31;
  const runRateFactor = totalDaysCycle / (daysElapsed || 1);
  const ventaProyeccion = Number((ventaReal * runRateFactor).toFixed(1));
  const contriProyeccion = Number((contriReal * runRateFactor).toFixed(1));
  const pctProyeccionVenta = Math.round((ventaProyeccion / (numVentaMeta || 1)) * 100);

  // Días que quedan del ciclo comercial para seguir vendiendo (mínimo 1,
  // para no dividir por cero el último día) -- se usa para repartir la
  // brecha de contribución pendiente (si la hay) en un monto diario.
  const diasRestantes = Math.max(totalDaysCycle - daysElapsed, 1);

  // Cada canal reparte la META GLOBAL de contribución (numContriMeta, la
  // que el usuario edita arriba) según su propio share de la contribución
  // YA lograda -- mismo criterio que "meta" siempre tuvo acá. A partir de
  // esa meta por canal, "CONTRIBUCIÓN DIARIA" ahora es cuánto falta vender
  // POR DÍA para llegar al 100% de esa meta -- no el ritmo ya logrado.
  // Si el canal ya alcanzó o superó su meta (faltante <= 0), se marca
  // metaCumplida=true y NO se calcula ni muestra un monto "pendiente"
  // (bug reportado 19-ago-2026: seguía mostrando contribución pendiente
  // aun con más de 100% de la meta del canal).
  const channelBreakdown = useMemo(() => {
    const canales = cumplimientoData?.canalBreakdown ?? [];
    return canales.map((c: any) => {
      const meta = contriReal ? Number(((c.contri / contriReal) * numContriMeta).toFixed(1)) : 0;
      const faltante = Number((meta - c.contri).toFixed(2));
      const metaCumplida = faltante <= 0;
      const contriDiariaNecesaria = metaCumplida ? 0 : Number((faltante / diasRestantes).toFixed(2));
      return {
        canal: c.canal,
        contri: c.contri,
        proy: c.proy,
        meta,
        contriDiariaNecesaria,
        metaCumplida,
        yoyPct: c.yoyPct,
        margenPct: c.margenPct,
      };
    });
  }, [cumplimientoData, contriReal, numContriMeta, diasRestantes]);

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

  // Comparativo histórico por año calendario completo -- viene de
  // /api/cumplimiento/historico-anual (real desde `ventas` para años
  // con data sincronizada, manual desde Datos Manuales para el resto).
  // Años sin ninguna de las dos fuentes simplemente no aparecen acá
  // (nunca se inventa un número).
  const historicalTrend = useMemo(() => {
    return historicoAnual.map((a: any) => ({
      año: String(a.anio),
      meta: a.metaContribucion ?? 0,
      contribucion: a.contribucionReal ?? 0,
      cumplimiento: a.cumplimientoPct ?? 0,
      esManual: a.esManual,
    }));
  }, [historicoAnual]);

  const categorySales = useMemo(() => {
    return (cumplimientoData?.categorySales ?? []).map((c: any) => ({
      cat: c.cat,
      y2025: c.anterior,
      y2026: c.actual,
    }));
  }, [cumplimientoData]);

  // Matriz de Requerimiento de Unidades por SKU -- para cada producto real
  // del período (top 10 por contribución), reparte la brecha total hacia
  // cada tramo de meta (70%-140%) según el share de contribución de ese
  // producto en el período actual, y la convierte a unidades usando su
  // contribución promedio por unidad. Mismo signo que "Brecha en
  // Contribución" arriba: negativo = todavía falta, positivo = ya se
  // superó ese tramo con este producto.
  const skuTargetMatrix = useMemo(() => {
    if (!contriReal || productosActual.length === 0) return [];
    return productosActual.map((p: any) => {
      const contribucionPromedioPorUnidad = p.unidades > 0 ? p.contribucion / p.unidades : 0;
      const share = p.contribucion / contriReal;

      const tramos = targetMilestones.map((pct) => {
        const requiredContriTotal = (numContriMeta * pct) / 100;
        const diffTotal = contriReal - requiredContriTotal; // mismo signo que thresholdCards
        const diffProducto = diffTotal * share;
        const unidades = contribucionPromedioPorUnidad > 0
          ? Math.round(diffProducto / contribucionPromedioPorUnidad)
          : 0;
        return { pct, unidades, venta: Number(diffProducto.toFixed(1)) };
      });

      return { desc: p.producto, tramos };
    });
  }, [productosActual, contriReal, numContriMeta, targetMilestones]);

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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">

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

        {/* KPI 5: Margen */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titlePurple}`}>
              <Percent className="w-4 h-4" /> MARGEN
            </span>
            <span className="p-1.5 rounded-lg bg-purple-500/10 text-purple-500">
              <Percent className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titlePurple}`}>{margenPct}%</span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Contribución / Venta del período</span>
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
                <th className="py-3 px-4 text-right">CONTRIBUCIÓN DIARIA NECESARIA</th>
                <th className="py-3 px-4 text-right">YoY %</th>
                <th className="py-3 px-4 text-right">MARGEN</th>
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
                  <td className="py-3 px-4 text-right font-semibold">
                    {row.metaCumplida ? (
                      <span className={`inline-flex items-center gap-1 font-bold ${titleEmerald}`}>
                        <CheckCircle2 className="w-3.5 h-3.5" /> Meta cumplida
                      </span>
                    ) : (
                      `$${row.contriDiariaNecesaria.toFixed(2)} M`
                    )}
                  </td>
                  <td className={`py-3 px-4 text-right font-bold ${
                    row.yoyPct >= 0 ? titleEmerald : (isDark ? 'text-rose-400' : 'text-rose-700')
                  }`}>
                    {row.yoyPct > 0 ? `+${row.yoyPct}%` : `${row.yoyPct}%`}
                  </td>
                  <td className={`py-3 px-4 text-right font-bold ${titlePurple}`}>
                    {row.margenPct}%
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
                <td className="py-3 px-4 text-right">
                  {(() => {
                    const faltanteTotal = Number((numContriMeta - contriReal).toFixed(2));
                    if (faltanteTotal <= 0) {
                      return (
                        <span className={`inline-flex items-center gap-1 ${titleEmerald}`}>
                          <CheckCircle2 className="w-3.5 h-3.5" /> Meta cumplida
                        </span>
                      );
                    }
                    return `$${(faltanteTotal / diasRestantes).toFixed(2)} M`;
                  })()}
                </td>
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
                <td className={`py-3 px-4 text-right ${titlePurple}`}>
                  {margenPct}%
                </td>
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
          <div className="flex items-center justify-between mb-4">
            <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
              <TrendingUp className="w-4 h-4" /> COMPARATIVO HISTÓRICO DE CUMPLIMIENTO ($ M & %)
            </h3>
            <button
              onClick={() => setShowDatosManualesModal(true)}
              title="Cargar metas históricas y otros datos manuales"
              className={`p-1.5 rounded-lg transition-colors ${
                isDark ? 'hover:bg-[#2C2C2E] text-slate-400' : 'hover:bg-slate-100 text-slate-500'
              }`}
            >
              <Database className="w-4 h-4" />
            </button>
          </div>

          {loadingHistorico ? (
            <div className="h-64 flex items-center justify-center text-xs font-semibold opacity-50">
              Cargando histórico...
            </div>
          ) : historicalTrend.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center gap-2 text-center px-4">
              <Database className="w-6 h-6 opacity-40" />
              <span className="text-xs font-semibold opacity-60">
                Sin datos para mostrar todavía. Carga metas históricas con el ícono de arriba.
              </span>
            </div>
          ) : (
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
          )}
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
                <Bar dataKey="y2025" name={`${prevYear} (u.)`} stackId="unidades" fill={isDark ? '#38383A' : '#cbd5e1'} radius={[0, 0, 0, 0]} />
                <Bar dataKey="y2026" name={`${currentYear} (u.)`} stackId="unidades" fill="#BF5AF2" radius={[0, 4, 4, 0]} />
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
          Unidades necesarias por producto para alcanzar cada tramo de meta, según su share de
          contribución del período y su contribución promedio por unidad. Negativo = todavía
          falta esa cantidad; positivo = ya se superó ese tramo con este producto.
        </p>

        {loadingProductosActual ? (
          <div className="py-10 text-center text-xs font-semibold opacity-50">Calculando matriz...</div>
        ) : skuTargetMatrix.length === 0 ? (
          <div className="py-10 text-center text-xs font-semibold opacity-50">
            Sin productos con venta en este período y filtros.
          </div>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className={`border-b text-[10px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <th className="py-2.5 px-3">PRODUCTO / DESCRIPCIÓN</th>
                {targetMilestones.map((pct) => (
                  <th key={pct} className={`py-2.5 px-3 text-center ${
                    pct === 100 ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                    : pct > 100 ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                    : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                  }`}>
                    {pct}%
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {skuTargetMatrix.map((item: any) => (
                <tr key={item.desc} className={`hover:bg-blue-500/10 transition-colors ${
                  isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                }`}>
                  <td className="py-2.5 px-3 font-bold">{item.desc}</td>
                  {item.tramos.map((t: any) => (
                    <td
                      key={t.pct}
                      title={`${t.venta >= 0 ? '+' : ''}$${t.venta} M`}
                      className={`py-2.5 px-3 text-center font-bold cursor-help ${
                        t.unidades >= 0 ? titlePurple : subtextColor
                      }`}
                    >
                      {t.unidades >= 0 ? `+${t.unidades}` : t.unidades}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {/* --- RECOMENDACIONES DE PRECIO & STOCK (YoY) --- */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1">
          <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleAmber}`}>
            <Lightbulb className="w-4 h-4" /> RECOMENDACIONES DE PRECIO & STOCK (YoY)
          </h3>
          {totalRecomendaciones > 0 && (
            <span className={`text-xs font-bold ${subtextColor}`}>
              {totalRecomendaciones} SKU{totalRecomendaciones === 1 ? '' : 's'} con oportunidad detectada
            </span>
          )}
        </div>
        <p className={`text-xs mb-4 font-medium ${subtextColor}`}>
          SKUs donde el stock actual alcanza para igualar el volumen del año pasado y el precio promedio subió vs. YoY
        </p>

        {loadingRecomendaciones ? (
          <div className="p-8 text-center text-sm font-semibold">
            <span className={subtextColor}>Cruzando ventas YoY, stock y precios...</span>
          </div>
        ) : recomendaciones.length === 0 ? (
          <div className="p-8 text-center text-sm font-medium">
            <span className={subtextColor}>Sin oportunidades detectadas para este ciclo (ningún SKU cumple ambas condiciones: stock suficiente y precio al alza vs. YoY).</span>
          </div>
        ) : (
          <div className="space-y-3">
            {recomendaciones.map((r: any) => (
              <div
                key={r.sku}
                className={`p-4 rounded-xl border flex flex-col gap-3 ${
                  isDark ? 'bg-[#17171A] border-[#2C2C2E]' : 'bg-amber-50/50 border-amber-200'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-500 shrink-0 mt-0.5">
                    <Sparkles className="w-3.5 h-3.5" />
                  </span>
                  <p className={`text-sm font-semibold leading-snug ${isDark ? 'text-[#EDEDED]' : 'text-slate-800'}`}>
                    {r.mensaje}
                  </p>
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-1.5 pl-9 text-xs font-medium">
                  <span className={subtextColor}>SKU: <strong className={isDark ? 'text-white' : 'text-slate-900'}>{r.sku}</strong></span>
                  <span className={subtextColor}>Unid. YoY: <strong className={isDark ? 'text-white' : 'text-slate-900'}>{r.unidadesYoy}</strong></span>
                  <span className={subtextColor}>Stock actual: <strong className={titleEmerald}>{r.stockActual}</strong></span>
                  <span className={subtextColor}>Precio prom. actual: <strong className={isDark ? 'text-white' : 'text-slate-900'}>${r.precioPromActual.toLocaleString('es-CL')}</strong></span>
                  <span className={subtextColor}>Precio prom. YoY: <strong className={isDark ? 'text-white' : 'text-slate-900'}>${r.precioPromYoy.toLocaleString('es-CL')}</strong></span>
                  <span className={subtextColor}>Variación precio: <strong className={isDark ? 'text-rose-400' : 'text-rose-700'}>+{r.variacionPrecioPct}%</strong></span>
                  <span className={subtextColor}>Margen actual: <strong className={titlePurple}>{r.margenPct}%</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* --- DETALLE DE SKUs DEL PERÍODO (AUDITORÍA) --- */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <h3 className={`text-xs font-black uppercase tracking-wider mb-1 flex items-center gap-2 ${titleBlue}`}>
          <Package className="w-4 h-4" /> DETALLE DE SKUs DEL PERÍODO
        </h3>
        <p className={`text-xs mb-4 font-medium ${subtextColor}`}>
          Todos los SKUs vendidos con los filtros actuales -- la suma de la columna Contribución
          calza exactamente con la tarjeta "Contribución Real" de arriba ($
          {skuDetalle ? skuDetalle.totalContribucion.toFixed(1) : '...'} M).
        </p>

        {loadingSkuDetalle ? (
          <div className="py-10 text-center text-xs font-semibold opacity-50">Cargando detalle de SKUs...</div>
        ) : !skuDetalle || skuDetalle.skus.length === 0 ? (
          <div className="py-10 text-center text-xs font-semibold opacity-50">
            Sin SKUs vendidos en este período y filtros.
          </div>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse min-w-[900px]">
            <thead>
              <tr className={`border-b text-[10px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <th className="p-2 w-8"></th>
                <SortableTh label="SKU" sortKey="sku" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} />
                <SortableTh label="PRODUCTO" sortKey="producto" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} className="min-w-[220px]" />
                <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} />
                <SortableTh label="UNIDADES" sortKey="unidades" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} align="center" />
                <SortableTh label="VENTA" sortKey="venta" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} align="right" />
                <SortableTh label="CONTRIBUCIÓN" sortKey="contribucion" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} align="right" className={`${titleEmerald} bg-emerald-500/5 font-black`} />
                <SortableTh label="% MARGEN" sortKey="margenPct" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} align="right" />
                <SortableTh label="% SHARE" sortKey="sharePct" currentSortKey={skuSortKey} sortDirection={skuSortDir} onSort={handleSkuSort} align="right" className={`${titlePurple} bg-purple-500/5`} />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {sortedSkuDetalle.map((s: any) => {
                const isExpanded = !!expandedSkus[s.sku];
                const tieneCanales = s.canales && s.canales.length > 0;
                return (
                <React.Fragment key={s.sku}>
                  <tr
                    onClick={() => tieneCanales && setExpandedSkus((prev) => ({ ...prev, [s.sku]: !prev[s.sku] }))}
                    className={`hover:bg-blue-500/10 transition-colors ${tieneCanales ? 'cursor-pointer' : ''} ${
                      isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                    }`}
                  >
                    <td className="p-2 text-center">
                      {tieneCanales && (
                        isExpanded
                          ? <ChevronDown className="w-3.5 h-3.5 opacity-60 inline" />
                          : <ChevronRight className="w-3.5 h-3.5 opacity-60 inline" />
                      )}
                    </td>
                    <td className="p-2 font-mono text-[11px] font-bold text-blue-500">{s.sku}</td>
                    <td className="p-2 font-semibold truncate max-w-[220px]">{s.producto}</td>
                    <td className={`p-2 ${subtextColor}`}>{s.categoria}</td>
                    <td className="p-2 text-center font-bold">{s.unidades}</td>
                    <td className="p-2 text-right">${s.venta.toFixed(1)} M</td>
                    <td className={`p-2 text-right font-black ${titleEmerald}`}>${s.contribucion.toFixed(1)} M</td>
                    <td className="p-2 text-right">{s.margenPct}%</td>
                    <td className={`p-2 text-right font-bold ${titlePurple}`}>{s.sharePct}%</td>
                  </tr>
                  {isExpanded && tieneCanales && (
                    <tr>
                      <td colSpan={9} className={`p-0 ${isDark ? 'bg-[#141416]' : 'bg-slate-50'}`}>
                        <table className="w-full text-left text-[11px] border-collapse">
                          <thead>
                            <tr className={`text-[9px] font-bold uppercase tracking-wider ${subtextColor}`}>
                              <th className="p-2 pl-10 w-8"></th>
                              <th className="p-2">CANAL</th>
                              <th className="p-2 text-center">UNIDADES</th>
                              <th className="p-2 text-right">VENTA</th>
                              <th className="p-2 text-right">CONTRIBUCIÓN</th>
                              <th className="p-2 text-right">% MARGEN</th>
                            </tr>
                          </thead>
                          <tbody>
                            {s.canales.map((c: any) => (
                              <tr key={c.canal} className="border-t border-slate-200/50 dark:border-[#2C2C2E]/50">
                                <td className="p-2 pl-10"></td>
                                <td className="p-2 font-semibold">{c.canal}</td>
                                <td className="p-2 text-center">{c.unidades}</td>
                                <td className="p-2 text-right">${c.venta.toFixed(1)} M</td>
                                <td className={`p-2 text-right font-bold ${titleEmerald}`}>${c.contribucion.toFixed(1)} M</td>
                                <td className="p-2 text-right">{c.margenPct}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
                );
              })}
            </tbody>
            <tfoot>
              <tr className={`border-t-2 font-black ${isDark ? 'border-[#333339]' : 'border-slate-300'}`}>
                <td className="p-2.5" colSpan={4}>TOTAL ({skuDetalle.skus.length} SKUs)</td>
                <td className="p-2.5 text-center">{skuDetalle.totalUnidades}</td>
                <td className="p-2.5 text-right">${skuDetalle.totalVenta.toFixed(1)} M</td>
                <td className={`p-2.5 text-right ${titleEmerald}`}>${skuDetalle.totalContribucion.toFixed(1)} M</td>
                <td className="p-2.5"></td>
                <td className={`p-2.5 text-right ${titlePurple}`}>100%</td>
              </tr>
            </tfoot>
          </table>
        </div>
        )}
      </div>

      <DatosManualesModal
        isOpen={showDatosManualesModal}
        onClose={() => setShowDatosManualesModal(false)}
        isDark={isDark}
        onCambiosGuardados={cargarHistoricoAnual}
      />

    </div>
  );
};

export default SalesTargetCumplimientoView;