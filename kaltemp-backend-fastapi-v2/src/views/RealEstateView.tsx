import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode } from '../types';
import { Building, DollarSign, TrendingUp, TrendingDown, ChevronRight, ChevronDown, Package, Filter } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchRealEstate, fetchRealEstateProductosPorCategoria, fetchRealEstateClientesPorProducto } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
}

export const RealEstateView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { startDate, endDate } = useGlobalFilter();

  // Filtro cruzado LOCAL a este módulo (clic en el ícono de embudo de una
  // fila de la Tabla 1) -- no vive en FilterContext, se resetea solo al
  // salir de esta vista.
  const [selectedCategoria, setSelectedCategoria] = useState<string | null>(null);

  // Estados locales -- /api/real-estate devuelve un objeto rico (mismo shape
  // que /api/distributors): totalVentas, ventaYoy, variacionYoy, totalProyectos,
  // rankingProyectos, distribucionCategoria, tendenciaMensual. NO trae
  // cantidades (no hay c2026/c2025/c2024), solo montos de venta.
  const [totalVentas, setTotalVentas] = useState(0);
  const [ventaYoy, setVentaYoy] = useState(0);
  const [varPctYoY, setVarPctYoY] = useState(0);
  const [totalProyectosCount, setTotalProyectosCount] = useState(0);

  const [categoryTableData, setCategoryTableData] = useState<any[]>([]);
  const [proyectosList, setProyectosList] = useState<any[]>([]);

  // Años reales de cada período (Actual/YoY/2YoY/3YoY) -- 18-ago-2026, a
  // pedido de William: "quitemos las siglas... asigna el año según
  // corresponda". El backend calcula el año real según el filtro de fecha
  // vigente (aniosPeriodos); mientras carga usamos el año calendario actual
  // como valor por defecto para que las columnas no se vean vacías.
  const anioActualDefault = new Date().getFullYear();
  const [periodYears, setPeriodYears] = useState<number[]>([
    anioActualDefault, anioActualDefault - 1, anioActualDefault - 2, anioActualDefault - 3
  ]);

  // Gráfico "COMPARATIVO MENSUAL HISTÓRICO" -- se carga en un efecto APARTE
  // (más abajo) que a propósito NO depende de startDate/endDate. Es una
  // tendencia anual: siempre debe mostrar el año completo, sin importar el
  // filtro de fechas del sidebar.
  const [monthlyData, setMonthlyData] = useState<{ mes: string; yActual: number; yAnterior: number; varPct: string }[]>([]);
  const [trendVarPctYoY, setTrendVarPctYoY] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- Acordeón Tabla 1: Categoría -> Producto -> Proyecto/Cliente (18-ago-2026) ---
  const [expandedCat, setExpandedCat] = useState<Record<string, boolean>>({});
  const [expandedProd, setExpandedProd] = useState<Record<string, boolean>>({});
  const [productosPorCategoria, setProductosPorCategoria] = useState<Record<string, any[]>>({});
  const [loadingProductosCat, setLoadingProductosCat] = useState<Record<string, boolean>>({});
  const [clientesPorProducto, setClientesPorProducto] = useState<Record<string, any[]>>({});
  const [loadingClientesProd, setLoadingClientesProd] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setLoading(true);

    // El acordeón queda obsoleto si cambia el rango de fechas -- se limpia
    // para forzar una recarga perezosa la próxima vez que se despliegue.
    setSelectedCategoria(null);
    setExpandedCat({});
    setExpandedProd({});
    setProductosPorCategoria({});
    setClientesPorProducto({});

    fetchRealEstate(startDate, endDate)
      .then((data: any) => {
        if (!data) return;

        const ventas = Number(data.totalVentas || 0);
        const yoy = Number(data.ventaYoy || 0);
        const vVar = Number(data.variacionYoy || 0);

        setTotalVentas(ventas);
        setVentaYoy(yoy);
        setVarPctYoY(vVar);
        setTotalProyectosCount(Number(data.totalProyectos || 0));

        // Ranking de Proyectos/Clientes Inmobiliarios -- Tabla 2: Venta Actual,
        // YoY, 2YoY y 3YoY (18-ago-2026, "potenciar" a pedido de William) --
        // solo montos, sin cantidad.
        const rawProyectos = data.rankingProyectos || [];
        const normProyectos = rawProyectos.map((p: any, idx: number) => ({
          id: p.id || idx,
          proyecto: p.proyecto || p.cliente || p.name || 'Proyecto sin nombre',
          venta: Number(p.venta ?? 0),
          ventaYoy: Number(p.ventaYoy ?? 0),
          venta2Yoy: Number(p.venta2Yoy ?? 0),
          venta3Yoy: Number(p.venta3Yoy ?? 0),
          varPct: Number(p.variacion ?? 0),
          categoria: p.categoria || 'Sin Categoría Mapeada'
        }));
        setProyectosList(normProyectos);

        // Categorías Bsale -- Tabla 1 (nivel 1): Cantidad y Venta, cada una
        // con Actual/YoY/2YoY/3YoY (18-ago-2026, a pedido de William).
        const rawCats = data.distribucionCategoria || [];
        const normCats = rawCats.map((cat: any) => ({
          categoria: cat.categoria || cat.name || 'Categoría',
          venta: Number(cat.venta ?? cat.value ?? 0),
          cantActual: Number(cat.cantidad ?? cat.count ?? 0),
          ventaYoy: Number(cat.ventaYoy ?? 0),
          cantYoy: Number(cat.cantidadYoy ?? cat.cantYoy ?? 0),
          venta2Yoy: Number(cat.venta2Yoy ?? 0),
          cant2Yoy: Number(cat.cantidad2Yoy ?? 0),
          venta3Yoy: Number(cat.venta3Yoy ?? 0),
          cant3Yoy: Number(cat.cantidad3Yoy ?? 0)
        }));
        setCategoryTableData(normCats);

        // Años reales para los encabezados de Tabla 1 y Tabla 2 (18-ago-2026)
        const rawAnios = Array.isArray(data.aniosPeriodos) ? data.aniosPeriodos : [];
        if (rawAnios.length === 4) {
          setPeriodYears(rawAnios.map((a: any) => Number(a)));
        }

        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  // --- Gráfico anual: SIEMPRE año completo, independiente del filtro del
  // sidebar (a pedido de William, 18-ago-2026). Se pide con un rango fijo
  // 1-ene a 31-dic del año en curso, en vez de startDate/endDate.
  useEffect(() => {
    const currentYear = new Date().getFullYear();
    const yearStart = `${currentYear}-01-01`;
    const yearEnd = `${currentYear}-12-31`;

    fetchRealEstate(yearStart, yearEnd)
      .then((data: any) => {
        if (!data) return;

        const rawTrend = data.tendenciaMensual || [];
        const normTrend = rawTrend.map((t: any) => {
          const cyVal = Number(t.venta ?? 0) / 1000000;
          const lyVal = Number(t.ventaYoy ?? 0) / 1000000;
          const varVal = lyVal > 0 ? (((cyVal - lyVal) / lyVal) * 100).toFixed(1) : '0.0';
          return {
            mes: t.mes || '',
            yActual: Number(cyVal.toFixed(1)),
            yAnterior: Number(lyVal.toFixed(1)),
            varPct: `${Number(varVal) >= 0 ? '+' : ''}${varVal}%`
          };
        });
        setMonthlyData(normTrend);
        setTrendVarPctYoY(Number(data.variacionYoy || 0));
      })
      .catch(() => {
        // Silencioso: si falla, el gráfico simplemente queda vacío -- los
        // KPIs de arriba (que sí dependen del filtro) ya muestran su propio
        // error si corresponde.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intencional:
    // este efecto NO debe reaccionar a startDate/endDate, es tendencia anual.
  }, []);

  const [sortKeyTable1, setSortKeyTable1] = useState<string>('venta');
  const [sortDirTable1, setSortDirTable1] = useState<'asc' | 'desc'>('desc');

  const [sortKeyTable2, setSortKeyTable2] = useState<string>('venta');
  const [sortDirTable2, setSortDirTable2] = useState<'asc' | 'desc'>('desc');

  // NOTA: mismo denominador estimado fijo que usa DistributorsView.tsx --
  // pendiente de conectar a /api/channels con el mismo rango si se quiere exacto.
  const totalKaltempSales = 245000000;
  const distWeightPct = totalKaltempSales > 0 ? ((totalVentas / totalKaltempSales) * 100).toFixed(1) : '0.0';

  // VAR % genérico -- mismo cálculo que usa el backend (_ranking_por_columna)
  // para que categoría/producto/proyecto del acordeón queden consistentes
  // aunque el backend no traiga la variación ya calculada.
  const calcVarPct = (venta: number, ventaYoy: number) => {
    if (ventaYoy > 0) return ((venta - ventaYoy) / ventaYoy) * 100;
    return venta > 0 ? 100 : 0;
  };

  // Formato compacto ($1,2M / $850K) para los montos de Tabla 1 y Tabla 2 --
  // 18-ago-2026, a pedido de William para reducir el ancho de las tablas
  // (menos scroll lateral) ahora que cada fila muestra 4 períodos.
  const formatCompactCLP = (n: number) => {
    const val = n || 0;
    const abs = Math.abs(val);
    if (abs >= 1_000_000) return "$" + (val / 1_000_000).toLocaleString('es-CL', { maximumFractionDigits: 1, minimumFractionDigits: 0 }) + "M";
    if (abs >= 1_000) return "$" + (val / 1_000).toLocaleString('es-CL', { maximumFractionDigits: 0 }) + "K";
    return "$" + val.toLocaleString('es-CL');
  };

  const sortedCategoryData = useMemo(() => {
    return [...categoryTableData].sort((a: any, b: any) => {
      let aVal = a[sortKeyTable1];
      let bVal = b[sortKeyTable1];
      if (aVal < bVal) return sortDirTable1 === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirTable1 === 'asc' ? 1 : -1;
      return 0;
    });
  }, [categoryTableData, sortKeyTable1, sortDirTable1]);

  const filteredProyectos = useMemo(() => {
    let list = proyectosList;
    if (selectedCategoria) {
      list = list.filter((p) => (p.categoria || '').toLowerCase().includes(selectedCategoria.toLowerCase()));
    }
    return [...list].sort((a: any, b: any) => {
      let aVal = a[sortKeyTable2];
      let bVal = b[sortKeyTable2];
      if (aVal < bVal) return sortDirTable2 === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirTable2 === 'asc' ? 1 : -1;
      return 0;
    });
  }, [proyectosList, selectedCategoria, sortKeyTable2, sortDirTable2]);

  const bestProyecto = filteredProyectos.length > 0 ? filteredProyectos[0] : null;
  const worstProyecto = filteredProyectos.length > 1 ? filteredProyectos[filteredProyectos.length - 1] : null;

  // --- Handlers del acordeón Tabla 1 ---
  const toggleExpandCategoria = (catName: string) => {
    const willExpand = !expandedCat[catName];
    setExpandedCat((prev) => ({ ...prev, [catName]: willExpand }));
    if (willExpand && !productosPorCategoria[catName]) {
      setLoadingProductosCat((prev) => ({ ...prev, [catName]: true }));
      fetchRealEstateProductosPorCategoria(catName, startDate, endDate)
        .then((data) => setProductosPorCategoria((prev) => ({ ...prev, [catName]: Array.isArray(data) ? data : [] })))
        .catch(() => setProductosPorCategoria((prev) => ({ ...prev, [catName]: [] })))
        .finally(() => setLoadingProductosCat((prev) => ({ ...prev, [catName]: false })));
    }
  };

  const toggleExpandProducto = (catName: string, prodName: string) => {
    const key = `${catName}__${prodName}`;
    const willExpand = !expandedProd[key];
    setExpandedProd((prev) => ({ ...prev, [key]: willExpand }));
    if (willExpand && !clientesPorProducto[key]) {
      setLoadingClientesProd((prev) => ({ ...prev, [key]: true }));
      fetchRealEstateClientesPorProducto(prodName, catName, startDate, endDate)
        .then((data) => setClientesPorProducto((prev) => ({ ...prev, [key]: Array.isArray(data) ? data : [] })))
        .catch(() => setClientesPorProducto((prev) => ({ ...prev, [key]: [] })))
        .finally(() => setLoadingClientesProd((prev) => ({ ...prev, [key]: false })));
    }
  };

  const toggleFiltroCategoria = (e: React.MouseEvent, catName: string) => {
    e.stopPropagation();
    setSelectedCategoria((prev) => (prev === catName ? null : catName));
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {error && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-red-500/10 text-red-300' : 'bg-red-50 text-red-600'}`}>
          Error al cargar datos inmobiliarios: {error}
        </div>
      )}
      {loading && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-white/5 text-white/50' : 'bg-black/5 text-black/50'}`}>
          Cargando datos inmobiliarios...
        </div>
      )}

      {/* Top Banner KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Venta B2B con YoY & VAR % */}
        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-blue-500 block truncate">
            VENTA B2B INMOBILIARIAS
          </span>
          <div className="text-2xl font-extrabold text-blue-500 mt-1">
            ${(totalVentas / 1000000).toFixed(1)} M CLP
          </div>
          <div className="mt-2 space-y-0.5 text-xs font-semibold">
            <div className="flex justify-between">
              <span className="opacity-70">YoY (período anterior):</span>
              <span>${(ventaYoy / 1000000).toFixed(1)}M</span>
            </div>
            <div className={"flex justify-between font-extrabold pt-0.5 border-t border-slate-200 dark:border-[#333339] " + (varPctYoY >= 0 ? 'text-emerald-500' : 'text-rose-500')}>
              <span>VAR % (YoY):</span>
              <span>{varPctYoY >= 0 ? '+' : ''}{varPctYoY.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Card 2: Peso Canal Inmobiliaria vs Total Kaltemp */}
        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-purple-500 block truncate">
            PESO CANAL INMOBILIARIAS / TOTAL KALTEMP
          </span>
          <div className="text-2xl font-extrabold text-purple-500 mt-1">
            {distWeightPct}% SHARE
          </div>
          <div className="mt-2 space-y-0.5 text-xs font-semibold">
            <div className="flex justify-between">
              <span className="opacity-70">Monto Inmobiliarias:</span>
              <span className="text-blue-500 font-extrabold">${(totalVentas / 1000000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between">
              <span className="opacity-70">Proyectos activos:</span>
              <span>{totalProyectosCount}</span>
            </div>
          </div>
        </div>

        {/* Card 3: Mejor y Peor Proyecto YoY */}
        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-500 block truncate">
            DESEMPEÑO YOY (MEJOR VS PEOR PROYECTO)
          </span>
          <div className="mt-2 space-y-2 text-xs">
            {bestProyecto && (
              <div className="flex items-center justify-between p-2 rounded bg-emerald-500/10 border border-emerald-500/20">
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-emerald-500 shrink-0" />
                  <div className="truncate">
                    <span className="font-extrabold block text-emerald-500 truncate">{bestProyecto.proyecto}</span>
                    <span className="text-[10px] opacity-70">Monto: ${(bestProyecto.venta / 1000000).toFixed(1)}M</span>
                  </div>
                </div>
                <span className="text-xs font-extrabold text-emerald-500 shrink-0">{bestProyecto.varPct >= 0 ? '+' : ''}{bestProyecto.varPct.toFixed(1)}% VAR</span>
              </div>
            )}

            {worstProyecto && (
              <div className="flex items-center justify-between p-2 rounded bg-rose-500/10 border border-rose-500/20">
                <div className="flex items-center gap-1.5">
                  <TrendingDown className="w-4 h-4 text-rose-500 shrink-0" />
                  <div className="truncate">
                    <span className="font-extrabold block text-rose-500 truncate">{worstProyecto.proyecto}</span>
                    <span className="text-[10px] opacity-70">Monto: ${(worstProyecto.venta / 1000000).toFixed(1)}M</span>
                  </div>
                </div>
                <span className="text-xs font-extrabold text-rose-500 shrink-0">{worstProyecto.varPct >= 0 ? '+' : ''}{worstProyecto.varPct.toFixed(1)}% VAR</span>
              </div>
            )}

            {!bestProyecto && !worstProyecto && (
              <span className="opacity-50 italic">Sin datos en el período</span>
            )}
          </div>
        </div>
      </div>

      {/* Monthly B2B Comparison Bar Chart -- tendencia ANUAL: siempre año
          completo, no reacciona al filtro de fecha del sidebar (ver
          useEffect([]) arriba) */}
      <div
        className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
            <Building className="w-4 h-4" /> VENTA TOTAL B2B AÑO - COMPARATIVO MENSUAL HISTÓRICO ($ M)
          </h3>
          <span className={"text-xs font-extrabold px-2.5 py-1 rounded-full border " + (trendVarPctYoY >= 0
            ? "text-emerald-500 bg-emerald-500/10 border-emerald-500/20"
            : "text-rose-500 bg-rose-500/10 border-rose-500/20")}>
            VAR% YoY Promedio: {trendVarPctYoY >= 0 ? '+' : ''}{trendVarPctYoY.toFixed(1)}%
          </span>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthlyData} margin={{ top: 20 }}>
              <XAxis dataKey="mes" stroke={isDark ? '#B8B8BE' : '#64748b'} fontSize={11} />
              <YAxis stroke={isDark ? '#B8B8BE' : '#64748b'} fontSize={11} unit="M" />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className={`p-3 rounded-xl border shadow-lg text-xs font-medium ${
                        isDark ? 'bg-[#17171A] border-[#333339] text-[#EDEDED]' : 'bg-white border-slate-200 text-slate-800'
                      }`}>
                        <p className="font-extrabold mb-1">{label}</p>
                        <p className="text-slate-400">Año Anterior: <span className="font-bold text-slate-300">${data.yAnterior}M</span></p>
                        <p className="text-blue-500">Actual: <span className="font-bold">${data.yActual}M</span></p>
                        <p className={"font-extrabold mt-1 " + (String(data.varPct).trim().startsWith('-') ? 'text-rose-500' : 'text-emerald-500')}>VAR% YoY: {data.varPct}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend
                verticalAlign="top"
                align="right"
                height={28}
                iconType="circle"
                wrapperStyle={{ fontSize: 11, fontWeight: 700, color: isDark ? '#8E8E93' : '#64748b' }}
              />
              <Bar dataKey="yAnterior" name="Año Anterior ($M)" fill={isDark ? '#48484A' : '#94a3b8'} radius={[4, 4, 0, 0]} />
              <Bar dataKey="yActual" name="Actual ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
                <LabelList
                  dataKey="varPct"
                  position="top"
                  content={(props: any) => {
                    const { x, y, width, value } = props;
                    if (value === undefined || value === null) return null;
                    const esNegativo = String(value).trim().startsWith('-');
                    return (
                      <text
                        x={(x ?? 0) + (width ?? 0) / 2}
                        y={(y ?? 0) - 6}
                        textAnchor="middle"
                        fill={esNegativo ? '#FF453A' : '#30D158'}
                        fontSize={11}
                        fontWeight="bold"
                      >
                        {value}
                      </text>
                    );
                  }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Side-by-side Tables Grid -- 18-ago-2026: proporción asimétrica (en
          vez de 50/50) -- Tabla 1 tiene más columnas (10) y necesitaba el
          ancho extra para eliminar el scroll lateral; se lo cedemos
          achicando Tabla 2 (que ahora además trunca el nombre de
          proyecto/cliente), a pedido de William. */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-4 items-start">
        {/* Table 1 -- acordeón: Categoría -> Producto -> Proyecto/Cliente */}
        <div
          className={`p-4 rounded-xl border shadow-md space-y-4 min-w-0 ${
            isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
              <DollarSign className="w-4 h-4" /> TABLA 1: DESGLOSE POR CATEGORÍA
            </h3>
            <span className="text-[10px] text-slate-400">
              Clic en fila = desplegar · <Filter className="w-3 h-3 inline -mt-0.5" /> = filtro cruzado Tabla 2
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[760px]">
              <thead>
                {/* Fila 1: agrupa CANTIDAD / VENTA para no repetir esas
                    palabras en cada una de las 4 columnas de años -- reduce
                    bastante el ancho total de la tabla (18-ago-2026). */}
                <tr className={`border-b text-[9px] font-bold uppercase tracking-wider ${
                  isDark ? 'border-[#333339] text-[#B8B8BE] bg-[#17171A]' : 'border-slate-200 text-slate-500 bg-slate-50'
                }`}>
                  <th className="p-0"></th>
                  <th colSpan={4} className="p-1 text-center border-l border-slate-500/10">CANTIDAD</th>
                  <th colSpan={4} className="p-1 text-center border-l border-slate-500/10 text-blue-500">VENTA</th>
                  <th className="p-0"></th>
                </tr>
                <tr className={`border-b text-[11px] font-bold ${
                  isDark ? 'border-[#333339] text-[#B8B8BE] bg-[#17171A]' : 'border-slate-200 text-slate-500 bg-slate-50'
                }`}>
                  <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label={String(periodYears[0])} sortKey="cantActual" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[1])} sortKey="cantYoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[2])} sortKey="cant2Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[3])} sortKey="cant3Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[0])} sortKey="venta" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className="text-blue-500" />
                  <SortableTh label={String(periodYears[1])} sortKey="ventaYoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[2])} sortKey="venta2Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[3])} sortKey="venta3Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <th className="p-2 text-center">VAR %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
                {sortedCategoryData.length === 0 && (
                  <tr><td colSpan={10} className="p-3 text-center opacity-50 italic">Sin datos en el período</td></tr>
                )}
                {sortedCategoryData.map((cat, idx) => {
                  const isFiltered = selectedCategoria === cat.categoria;
                  const isExpanded = !!expandedCat[cat.categoria];
                  const catVarPct = calcVarPct(cat.venta, cat.ventaYoy);

                  return (
                    <React.Fragment key={cat.categoria + idx}>
                      <tr
                        onClick={() => toggleExpandCategoria(cat.categoria)}
                        className={`cursor-pointer transition-colors font-bold ${
                          isFiltered
                            ? isDark ? 'bg-blue-600/30 border-l-4 border-l-blue-500' : 'bg-blue-100 border-l-4 border-l-blue-500'
                            : isDark ? 'hover:bg-blue-500/10 text-[#EDEDED]' : 'hover:bg-blue-500/10 text-slate-800'
                        }`}
                      >
                        <td className="p-2 flex items-center gap-1.5 min-w-[140px]">
                          {isExpanded ? <ChevronDown className="w-4 h-4 shrink-0 text-blue-500" /> : <ChevronRight className="w-4 h-4 shrink-0 text-blue-500" />}
                          <span className="truncate">{cat.categoria}</span>
                          <button
                            onClick={(e) => toggleFiltroCategoria(e, cat.categoria)}
                            title="Filtrar Tabla 2 por esta categoría"
                            className={"ml-auto p-1 rounded-md shrink-0 transition-colors " + (isFiltered ? 'bg-blue-500/20 text-blue-500' : 'text-slate-400 hover:text-blue-500 hover:bg-blue-500/10')}
                          >
                            <Filter className="w-3 h-3" />
                          </button>
                        </td>
                        <td className="p-2.5 text-center font-black">{(cat.cantActual || 0).toLocaleString('es-CL')}</td>
                        <td className="p-2.5 text-center opacity-70">{(cat.cantYoy || 0).toLocaleString('es-CL')}</td>
                        <td className="p-2.5 text-center opacity-50">{(cat.cant2Yoy || 0).toLocaleString('es-CL')}</td>
                        <td className="p-2.5 text-center opacity-40">{(cat.cant3Yoy || 0).toLocaleString('es-CL')}</td>
                        <td className="p-2 text-right font-extrabold text-blue-500">{formatCompactCLP(cat.venta)}</td>
                        <td className="p-2 text-right opacity-70">{formatCompactCLP(cat.ventaYoy)}</td>
                        <td className="p-2 text-right opacity-50">{formatCompactCLP(cat.venta2Yoy)}</td>
                        <td className="p-2 text-right opacity-40">{formatCompactCLP(cat.venta3Yoy)}</td>
                        <td className={`p-2 text-center font-black ${catVarPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                          {(catVarPct >= 0 ? '+' : '') + catVarPct.toFixed(1)}%
                        </td>
                      </tr>

                      {/* NIVEL 2: Productos de la categoría */}
                      {isExpanded && (
                        loadingProductosCat[cat.categoria] ? (
                          <tr><td colSpan={10} className="p-2 pl-8 text-[11px] italic opacity-50">Cargando productos...</td></tr>
                        ) : (productosPorCategoria[cat.categoria] || []).length === 0 ? (
                          <tr><td colSpan={10} className="p-2 pl-8 text-[11px] italic opacity-50">Sin productos registrados en este período</td></tr>
                        ) : (
                          (productosPorCategoria[cat.categoria] || []).map((prod: any, pIdx: number) => {
                            const prodKey = `${cat.categoria}__${prod.producto}`;
                            const isProdExpanded = !!expandedProd[prodKey];
                            const prodVarPct = Number(prod.variacion ?? calcVarPct(prod.venta, prod.ventaYoy));

                            return (
                              <React.Fragment key={prodKey + pIdx}>
                                <tr
                                  onClick={() => toggleExpandProducto(cat.categoria, prod.producto)}
                                  className={`cursor-pointer text-[11px] transition-colors ${
                                    isDark ? 'bg-[#17171A] hover:bg-[#222226] text-[#EDEDED]' : 'bg-slate-50 hover:bg-slate-100 text-slate-800'
                                  }`}
                                >
                                  <td className="p-2 pl-8 font-bold flex items-center gap-2 min-w-[140px]">
                                    {isProdExpanded ? <ChevronDown className="w-3.5 h-3.5 text-amber-500 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                                    <Package className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                                    <span className="truncate">{prod.producto}</span>
                                  </td>
                                  <td className="p-2 text-center font-bold">{Math.round(prod.cantidad || 0).toLocaleString('es-CL')}</td>
                                  <td className="p-2 text-center opacity-60">{Math.round(prod.cantidadYoy || 0).toLocaleString('es-CL')}</td>
                                  <td className="p-2 text-center opacity-50">{Math.round(prod.cantidad2Yoy || 0).toLocaleString('es-CL')}</td>
                                  <td className="p-2 text-center opacity-40">{Math.round(prod.cantidad3Yoy || 0).toLocaleString('es-CL')}</td>
                                  <td className="p-2 text-right font-black text-blue-500">{formatCompactCLP(prod.venta)}</td>
                                  <td className="p-2 text-right opacity-70">{formatCompactCLP(prod.ventaYoy)}</td>
                                  <td className="p-2 text-right opacity-50">{formatCompactCLP(prod.venta2Yoy)}</td>
                                  <td className="p-2 text-right opacity-40">{formatCompactCLP(prod.venta3Yoy)}</td>
                                  <td className={`p-2 text-center font-black ${prodVarPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                    {(prodVarPct >= 0 ? '+' : '') + prodVarPct.toFixed(1)}%
                                  </td>
                                </tr>

                                {/* NIVEL 3: Proyectos/Clientes que compraron ese producto */}
                                {isProdExpanded && (
                                  loadingClientesProd[prodKey] ? (
                                    <tr><td colSpan={10} className="p-2 pl-16 text-[10px] italic opacity-50">Cargando proyectos/clientes...</td></tr>
                                  ) : (clientesPorProducto[prodKey] || []).length === 0 ? (
                                    <tr><td colSpan={10} className="p-2 pl-16 text-[10px] italic opacity-50">Sin proyectos/clientes registrados en este período</td></tr>
                                  ) : (
                                    (clientesPorProducto[prodKey] || []).map((cli: any, cIdx: number) => {
                                      const cliVarPct = Number(cli.variacion ?? calcVarPct(cli.venta, cli.ventaYoy));
                                      return (
                                        <tr
                                          key={prodKey + '_' + cIdx}
                                          className={`text-[10px] ${isDark ? 'bg-[#121214] text-slate-400' : 'bg-slate-200/50 text-slate-700'}`}
                                        >
                                          <td className="p-1.5 pl-16 font-bold flex items-center gap-2 min-w-[140px]">
                                            <Building className="w-3 h-3 text-cyan-500 shrink-0" />
                                            <span className="font-bold truncate">{cli.cliente}</span>
                                          </td>
                                          <td className="p-1.5 text-center font-bold">{Math.round(cli.cantidad || 0).toLocaleString('es-CL')}</td>
                                          <td className="p-1.5 text-center opacity-50">{Math.round(cli.cantidadYoy || 0).toLocaleString('es-CL')}</td>
                                          <td className="p-1.5 text-center opacity-40">{Math.round(cli.cantidad2Yoy || 0).toLocaleString('es-CL')}</td>
                                          <td className="p-1.5 text-center opacity-30">{Math.round(cli.cantidad3Yoy || 0).toLocaleString('es-CL')}</td>
                                          <td className="p-1.5 text-right font-black text-blue-500">{formatCompactCLP(cli.venta)}</td>
                                          <td className="p-1.5 text-right opacity-60">{formatCompactCLP(cli.ventaYoy)}</td>
                                          <td className="p-1.5 text-right opacity-50">{formatCompactCLP(cli.venta2Yoy)}</td>
                                          <td className="p-1.5 text-right opacity-40">{formatCompactCLP(cli.venta3Yoy)}</td>
                                          <td className={`p-1.5 text-center font-bold ${cliVarPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                            {(cliVarPct >= 0 ? '+' : '') + cliVarPct.toFixed(1)}%
                                          </td>
                                        </tr>
                                      );
                                    })
                                  )
                                )}
                              </React.Fragment>
                            );
                          })
                        )
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Table 2 -- con scroll interno cuando hay mucha información */}
        <div
          className={`p-4 rounded-xl border shadow-md space-y-4 min-w-0 ${
            isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
              <Building className="w-4 h-4" /> TABLA 2: RANKING DE PROYECTOS (YOY &amp; VAR %)
            </h3>
            {selectedCategoria && (
              <button
                onClick={() => setSelectedCategoria(null)}
                className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-500 border border-blue-500/30 flex items-center gap-1"
              >
                Filtrado: {selectedCategoria} ×
              </button>
            )}
          </div>

          <div className="overflow-x-auto overflow-y-auto max-h-[420px] rounded-xl">
            <table className="w-full text-left text-xs border-collapse min-w-[420px]">
              <thead className="sticky top-0 z-10">
                <tr className={`border-b text-[11px] font-bold ${
                  isDark ? 'border-[#333339] text-[#B8B8BE] bg-[#17171A]' : 'border-slate-200 text-slate-500 bg-slate-50'
                }`}>
                  <SortableTh label="PROYECTO" sortKey="proyecto" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label={String(periodYears[0])} sortKey="venta" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className="text-blue-500" />
                  <SortableTh label={String(periodYears[1])} sortKey="ventaYoy" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[2])} sortKey="venta2Yoy" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[3])} sortKey="venta3Yoy" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label="VAR %" sortKey="varPct" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" className="text-emerald-500" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
                {filteredProyectos.length === 0 && (
                  <tr><td colSpan={6} className="p-3 text-center opacity-50 italic">Sin datos en el período</td></tr>
                )}
                {filteredProyectos.map((p, idx) => (
                  <tr key={p.id ?? idx} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-2 font-bold max-w-[110px]">
                      <span className="block truncate" title={p.proyecto}>{p.proyecto}</span>
                    </td>
                    <td className="p-2 text-right font-extrabold text-blue-500">{formatCompactCLP(p.venta)}</td>
                    <td className="p-2 text-right opacity-70">{formatCompactCLP(p.ventaYoy)}</td>
                    <td className="p-2 text-right opacity-50">{formatCompactCLP(p.venta2Yoy)}</td>
                    <td className="p-2 text-right opacity-40">{formatCompactCLP(p.venta3Yoy)}</td>
                    <td className={"p-2 text-center font-extrabold " + ((p.varPct || 0) >= 0 ? 'text-emerald-500' : 'text-rose-500')}>{p.varPct >= 0 ? '+' : ''}{(p.varPct || 0).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RealEstateView;