import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode} from '../types';
import { Building2, DollarSign, TrendingUp, TrendingDown, RefreshCw, ChevronRight, ChevronDown, Package, Filter } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchDistributors, fetchDistributorsProductosPorCategoria, fetchDistributorsClientesPorProducto } from '../services/api';
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

export const DistributorsView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { startDate, endDate } = useGlobalFilter();

  const [selectedCategoria, setSelectedCategoria] = useState<string | null>(null);

  const [totalV2026, setTotalV2026] = useState(0);
  const [totalV2025, setTotalV2025] = useState(0);
  const [varPctYoY, setVarPctYoY] = useState(0);
  const [totalClientesCount, setTotalClientesCount] = useState(0);

  const [categoryTableData, setCategoryTableData] = useState<any[]>([]);
  const [clientList, setClientList] = useState<any[]>([]);

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
  const [monthlyB2BData, setMonthlyB2BData] = useState<any[]>([]);
  const [trendVarPctYoY, setTrendVarPctYoY] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- Acordeón Tabla 1: Categoría -> Producto -> Cliente (18-ago-2026) ---
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

    fetchDistributors(startDate, endDate)
      .then((data: any) => {
        if (!data) return;

        if (Array.isArray(data)) {
          const v26 = data.reduce((acc, d) => acc + (d.v2026 || 0), 0);
          const v25 = data.reduce((acc, d) => acc + (d.v2025 || 0), 0);
          setTotalV2026(v26);
          setTotalV2025(v25);
          setClientList(data);
        } else {
          const v26 = Number(data.totalVentas || 0);
          const v25 = Number(data.ventaYoy || 0);
          const vVar = Number(data.variacionYoy || 0);

          setTotalV2026(v26);
          setTotalV2025(v25);
          setVarPctYoY(vVar);
          setTotalClientesCount(Number(data.totalClientes || 0));

          // Tabla 2: Venta Actual, YoY, 2YoY y 3YoY (18-ago-2026, "potenciar" a
          // pedido de William) -- solo montos, sin cantidad.
          const rawClients = Array.isArray(data.rankingClientes) ? data.rankingClientes : (Array.isArray(data.rankingProyectos) ? data.rankingProyectos : []);
          const normClients = rawClients.map((c: any, idx: number) => ({
            id: c.id || idx,
            cliente: c.cliente || c.name || c.proyecto || "Cliente B2B",
            v2026: Number(c.venta ?? c.v2026 ?? 0),
            v2025: Number(c.ventaYoy ?? c.v2025 ?? 0),
            v2024: Number(c.venta2Yoy ?? c.v2024 ?? 0),
            v2023: Number(c.venta3Yoy ?? c.v2023 ?? 0),
            varPct: Number(c.variacion ?? c.varPct ?? 0),
            categoria: c.categoria || "Sin Categoría Mapeada"
          }));
          setClientList(normClients);

          // Tabla 1 (nivel 1 - Categoría): Cantidad y Venta, cada una con
          // Actual/YoY/2YoY/3YoY (18-ago-2026, a pedido de William).
          const rawCats = Array.isArray(data.distribucionCategoria) ? data.distribucionCategoria : [];
          const normCats = rawCats.map((cat: any) => ({
            categoria: cat.categoria || cat.name || "Categoría",
            ventaActual: Number(cat.venta ?? cat.value ?? 0),
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

    fetchDistributors(yearStart, yearEnd)
      .then((data: any) => {
        if (!data || Array.isArray(data)) return;

        const rawTrend = Array.isArray(data.tendenciaMensual) ? data.tendenciaMensual : [];
        const normTrend = rawTrend.map((t: any) => {
          const cyVal = Number(t.venta ?? t.cy ?? 0) / 1000000;
          const lyVal = Number(t.ventaYoy ?? t.ly ?? 0) / 1000000;
          const varVal = lyVal > 0 ? (((cyVal - lyVal) / lyVal) * 100).toFixed(1) : "0.0";
          return {
            mes: t.mes || t.month || "",
            y2026: Number(cyVal.toFixed(1)),
            y2025: Number(lyVal.toFixed(1)),
            varPct: (Number(varVal) >= 0 ? '+' : '') + varVal + '%'
          };
        });
        setMonthlyB2BData(normTrend);
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

  const [sortKeyTable1, setSortKeyTable1] = useState<string>('ventaActual');
  const [sortDirTable1, setSortDirTable1] = useState<'asc' | 'desc'>('desc');

  const [sortKeyTable2, setSortKeyTable2] = useState<string>('v2026');
  const [sortDirTable2, setSortDirTable2] = useState<'asc' | 'desc'>('desc');

  const totalKaltempSales = 245000000;
  const distWeightPct = totalKaltempSales > 0 ? ((totalV2026 / totalKaltempSales) * 100).toFixed(1) : "0.0";

  // VAR % genérico -- mismo cálculo que usa el backend (ranking_por_columna)
  // para que categoría/producto/cliente del acordeón queden consistentes
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

  const filteredClients = useMemo(() => {
    let list = Array.isArray(clientList) ? clientList : [];

    if (selectedCategoria) {
      list = list.filter((d) => (d.categoria || "").toLowerCase().includes(selectedCategoria.toLowerCase()));
    }

    return [...list].sort((a: any, b: any) => {
      let aVal = a[sortKeyTable2];
      let bVal = b[sortKeyTable2];
      if (aVal < bVal) return sortDirTable2 === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirTable2 === 'asc' ? 1 : -1;
      return 0;
    });
  }, [clientList, selectedCategoria, sortKeyTable2, sortDirTable2]);

  const bestClient = filteredClients.length > 0 ? filteredClients[0] : null;
  const worstClient = filteredClients.length > 1 ? filteredClients[filteredClients.length - 1] : null;

  const bestVarVal = bestClient?.varPct ?? 0;
  const bestVarText = (bestVarVal >= 0 ? '+' : '') + bestVarVal.toFixed(1) + '% VAR';

  const worstVarVal = worstClient?.varPct ?? 0;
  const worstVarText = (worstVarVal >= 0 ? '+' : '') + worstVarVal.toFixed(1) + '% VAR';

  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titleAmber = isDark ? "text-amber-400" : "text-amber-800";
  const titlePurple = isDark ? "text-purple-400" : "text-purple-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  const cardBaseClass = "p-5 rounded-2xl border transition-all hover:shadow-md " + panelBg;

  // --- Handlers del acordeón Tabla 1 ---
  const toggleExpandCategoria = (catName: string) => {
    const willExpand = !expandedCat[catName];
    setExpandedCat((prev) => ({ ...prev, [catName]: willExpand }));
    if (willExpand && !productosPorCategoria[catName]) {
      setLoadingProductosCat((prev) => ({ ...prev, [catName]: true }));
      fetchDistributorsProductosPorCategoria(catName, startDate, endDate)
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
      fetchDistributorsClientesPorProducto(prodName, catName, startDate, endDate)
        .then((data) => setClientesPorProducto((prev) => ({ ...prev, [key]: Array.isArray(data) ? data : [] })))
        .catch(() => setClientesPorProducto((prev) => ({ ...prev, [key]: [] })))
        .finally(() => setLoadingClientesProd((prev) => ({ ...prev, [key]: false })));
    }
  };

  const toggleFiltroCategoria = (e: React.MouseEvent, catName: string) => {
    e.stopPropagation();
    setSelectedCategoria((prev) => (prev === catName ? null : catName));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600" />
        <span className={"text-sm font-semibold " + subtextColor}>Cargando datos de Distribuidores B2B...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {error && (
        <div className={isDark ? 'px-4 py-3 rounded-2xl text-xs font-bold bg-red-500/10 text-red-300 border border-red-500/20' : 'px-4 py-3 rounded-2xl text-xs font-bold bg-red-50 text-red-700 border border-red-200'}>
          Error al cargar distribuidores: {error}
        </div>
      )}

      {/* Top Banner KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* Card 1 */}
        <div className={cardBaseClass}>
          <span className={"text-[10px] font-black uppercase tracking-wider block " + titleBlue}>
            VENTA B2B DISTRIBUIDORES
          </span>
          <div className={"text-3xl font-black mt-2 " + titleBlue}>
            ${(totalV2026 / 1000000).toFixed(1)} M CLP
          </div>
          <div className="mt-3 space-y-1 text-xs font-medium border-t pt-2 border-slate-100 dark:border-[#2C2C2E]">
            <div className="flex justify-between">
              <span className={subtextColor}>YoY (Año Anterior):</span>
              <span className="font-bold">${(totalV2025 / 1000000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between font-black pt-1">
              <span className={subtextColor}>VAR % (YoY):</span>
              <span className={varPctYoY >= 0 ? titleEmerald : 'text-rose-500'}>
                {(varPctYoY >= 0 ? '+' : '') + varPctYoY.toFixed(1) + '%'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className={cardBaseClass}>
          <span className={"text-[10px] font-black uppercase tracking-wider block " + titlePurple}>
            PESO CANAL DISTRIBUIDORES / TOTAL
          </span>
          <div className={"text-3xl font-black mt-2 " + titlePurple}>
            {distWeightPct}% SHARE
          </div>
          <div className="mt-3 space-y-1 text-xs font-medium border-t pt-2 border-slate-100 dark:border-[#2C2C2E]">
            <div className="flex justify-between">
              <span className={subtextColor}>Clientes B2B Activos:</span>
              <span className={"font-black " + titleBlue}>{totalClientesCount || clientList.length} Clientes</span>
            </div>
          </div>
        </div>

        {/* Card 3 */}
        <div className={cardBaseClass}>
          <span className={"text-[10px] font-black uppercase tracking-wider block " + titleAmber}>
            DESEMPEÑO YOY (MEJOR VS PEOR CLIENTE)
          </span>
          <div className="mt-2 space-y-2 text-xs">
            {bestClient && (
              <div className="flex items-center justify-between p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-emerald-500 shrink-0" />
                  <div className="truncate">
                    <span className="font-extrabold block text-emerald-600 dark:text-emerald-400 truncate">{bestClient.cliente}</span>
                    <span className={"text-[10px] " + subtextColor}>Monto: ${(bestClient.v2026 / 1000000).toFixed(1)}M</span>
                  </div>
                </div>
                <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 shrink-0">{bestVarText}</span>
              </div>
            )}

            {worstClient && (
              <div className="flex items-center justify-between p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <div className="flex items-center gap-1.5">
                  <TrendingDown className="w-4 h-4 text-rose-500 shrink-0" />
                  <div className="truncate">
                    <span className="font-extrabold block text-rose-600 dark:text-rose-400 truncate">{worstClient.cliente}</span>
                    <span className={"text-[10px] " + subtextColor}>Monto: ${(worstClient.v2026 / 1000000).toFixed(1)}M</span>
                  </div>
                </div>
                <span className="text-xs font-black text-rose-600 dark:text-rose-400 shrink-0">{worstVarText}</span>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Gráfico Venta Mensual B2B -- tendencia ANUAL: siempre año completo,
          no reacciona al filtro de fecha del sidebar (ver useEffect([]) arriba) */}
      <div className={"p-6 rounded-2xl border shadow-sm " + panelBg}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
            <Building2 className="w-4 h-4" /> VENTA TOTAL B2B AÑO - COMPARATIVO MENSUAL HISTÓRICO ($ M)
          </h3>
          <span className={"text-xs font-black px-2.5 py-1 rounded-full border " + (trendVarPctYoY >= 0
            ? "bg-emerald-500/10 border-emerald-500/20 " + titleEmerald
            : "bg-rose-500/10 border-rose-500/20 text-rose-500")}>
            VAR% YoY Promedio: {(trendVarPctYoY >= 0 ? '+' : '') + trendVarPctYoY.toFixed(1) + '%'}
          </span>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthlyB2BData} margin={{ top: 20 }}>
              <XAxis dataKey="mes" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={11} tickLine={false} />
              <YAxis stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={11} unit="M" tickLine={false} axisLine={false} />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className={isDark ? "p-3.5 rounded-2xl border shadow-2xl text-xs font-medium bg-[#1C1C1E] border-[#2C2C2E] text-[#EDEDED]" : "p-3.5 rounded-2xl border shadow-2xl text-xs font-medium bg-white border-slate-200 text-slate-900"}>
                        <p className="font-extrabold mb-1">{label}</p>
                        <p className={subtextColor}>Año Anterior: <span className="font-bold text-slate-300">${data.y2025}M</span></p>
                        <p className={titleBlue}>Actual: <span className="font-bold">${data.y2026}M</span></p>
                        <p className={"font-black mt-1 " + (String(data.varPct).trim().startsWith('-') ? 'text-rose-500' : titleEmerald)}>VAR% YoY: {data.varPct}</p>
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
                wrapperStyle={{ fontSize: 11, fontWeight: 700, color: subtextColor.includes('8E8E93') ? '#8E8E93' : '#64748b' }}
              />
              <Bar dataKey="y2025" name="Año Anterior ($M)" fill={isDark ? '#38383A' : '#cbd5e1'} radius={[4, 4, 0, 0]} />
              <Bar dataKey="y2026" name="Actual ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
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

      {/* Tablas Lado a Lado */}
      {/* 18-ago-2026: proporción asimétrica (en vez de 50/50) -- Tabla 1
          tiene más columnas (10) y necesitaba el ancho extra para eliminar
          el scroll lateral; se lo cedemos achicando Tabla 2 (que ahora
          además trunca el nombre de cliente), a pedido de William. */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-6 items-start">

        {/* Tabla 1 -- acordeón: Categoría -> Producto -> Cliente */}
        <div className={"p-6 rounded-2xl border shadow-sm space-y-4 min-w-0 " + panelBg}>
          <div className="flex items-center justify-between">
            <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
              <DollarSign className="w-4 h-4" /> TABLA 1: DESGLOSE POR CATEGORÍA
            </h3>
            <span className={"text-[10px] font-medium " + subtextColor}>
              Clic en fila = desplegar · <Filter className="w-3 h-3 inline -mt-0.5" /> = filtro cruzado Tabla 2
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[760px]">
              <thead>
                {/* Fila 1: agrupa CANTIDAD / VENTA para no repetir esas
                    palabras en cada una de las 4 columnas de años -- reduce
                    bastante el ancho total de la tabla (18-ago-2026). */}
                <tr className={"border-b text-[9px] font-black uppercase tracking-wider " + tableHeaderClass}>
                  <th className="p-0"></th>
                  <th colSpan={4} className="p-1 text-center border-l border-slate-500/10">CANTIDAD</th>
                  <th colSpan={4} className={"p-1 text-center border-l border-slate-500/10 " + titleBlue}>VENTA</th>
                  <th className="p-0"></th>
                </tr>
                <tr className={"border-b text-[10px] font-black uppercase tracking-wider " + tableHeaderClass}>
                  <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label={String(periodYears[0])} sortKey="cantActual" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" className="bg-slate-500/5" />
                  <SortableTh label={String(periodYears[1])} sortKey="cantYoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[2])} sortKey="cant2Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[3])} sortKey="cant3Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" />
                  <SortableTh label={String(periodYears[0])} sortKey="ventaActual" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className={titleBlue} />
                  <SortableTh label={String(periodYears[1])} sortKey="ventaYoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[2])} sortKey="venta2Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[3])} sortKey="venta3Yoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <th className="p-2.5 text-center">VAR %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
                {sortedCategoryData.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="p-4 text-center text-slate-400 italic">
                      Sin categorías registradas
                    </td>
                  </tr>
                ) : (
                  sortedCategoryData.map((cat, idx) => {
                    const isFiltered = selectedCategoria === cat.categoria;
                    const isExpanded = !!expandedCat[cat.categoria];
                    const catVarPct = calcVarPct(cat.ventaActual, cat.ventaYoy);

                    const rowBg = isFiltered
                      ? (isDark ? 'bg-blue-600/30 border-l-4 border-l-blue-400' : 'bg-blue-50 border-l-4 border-l-blue-600')
                      : (isDark ? 'bg-[#121214] hover:bg-[#2C2C2E] text-[#EDEDED]' : 'bg-slate-100 hover:bg-slate-200/80 text-slate-900');

                    return (
                      <React.Fragment key={cat.categoria + idx}>
                        <tr
                          onClick={() => toggleExpandCategoria(cat.categoria)}
                          className={"cursor-pointer font-extrabold transition-colors " + rowBg}
                        >
                          <td className="p-2.5 flex items-center gap-1.5 min-w-[140px]">
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
                          <td className={"p-2.5 text-right font-black " + titleBlue}>{formatCompactCLP(cat.ventaActual)}</td>
                          <td className={"p-2.5 text-right " + subtextColor}>{formatCompactCLP(cat.ventaYoy)}</td>
                          <td className={"p-2.5 text-right opacity-70 " + subtextColor}>{formatCompactCLP(cat.venta2Yoy)}</td>
                          <td className={"p-2.5 text-right opacity-50 " + subtextColor}>{formatCompactCLP(cat.venta3Yoy)}</td>
                          <td className={"p-2.5 text-center font-black " + (catVarPct >= 0 ? titleEmerald : 'text-rose-500')}>
                            {(catVarPct >= 0 ? '+' : '') + catVarPct.toFixed(1)}%
                          </td>
                        </tr>

                        {/* NIVEL 2: Productos de la categoría */}
                        {isExpanded && (
                          loadingProductosCat[cat.categoria] ? (
                            <tr>
                              <td colSpan={10} className="p-3 pl-8 text-[11px] italic text-slate-400">Cargando productos...</td>
                            </tr>
                          ) : (productosPorCategoria[cat.categoria] || []).length === 0 ? (
                            <tr>
                              <td colSpan={10} className="p-3 pl-8 text-[11px] italic text-slate-400">Sin productos registrados en este período</td>
                            </tr>
                          ) : (
                            (productosPorCategoria[cat.categoria] || []).map((prod: any, pIdx: number) => {
                              const prodKey = `${cat.categoria}__${prod.producto}`;
                              const isProdExpanded = !!expandedProd[prodKey];
                              const prodVarPct = Number(prod.variacion ?? calcVarPct(prod.venta, prod.ventaYoy));

                              return (
                                <React.Fragment key={prodKey + pIdx}>
                                  <tr
                                    onClick={() => toggleExpandProducto(cat.categoria, prod.producto)}
                                    className={"cursor-pointer text-[11px] transition-colors " + (isDark ? 'bg-[#1F1F23] hover:bg-[#2C2C2E] text-[#EDEDED]' : 'bg-slate-50 hover:bg-slate-100 text-slate-800')}
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
                                    <td className={"p-2 text-right font-black " + titleBlue}>{formatCompactCLP(prod.venta)}</td>
                                    <td className="p-2 text-right opacity-70">{formatCompactCLP(prod.ventaYoy)}</td>
                                    <td className="p-2 text-right opacity-50">{formatCompactCLP(prod.venta2Yoy)}</td>
                                    <td className="p-2 text-right opacity-40">{formatCompactCLP(prod.venta3Yoy)}</td>
                                    <td className={"p-2 text-center font-black " + (prodVarPct >= 0 ? titleEmerald : 'text-rose-500')}>
                                      {(prodVarPct >= 0 ? '+' : '') + prodVarPct.toFixed(1)}%
                                    </td>
                                  </tr>

                                  {/* NIVEL 3: Clientes que compraron ese producto */}
                                  {isProdExpanded && (
                                    loadingClientesProd[prodKey] ? (
                                      <tr>
                                        <td colSpan={10} className="p-2 pl-16 text-[10px] italic text-slate-400">Cargando clientes...</td>
                                      </tr>
                                    ) : (clientesPorProducto[prodKey] || []).length === 0 ? (
                                      <tr>
                                        <td colSpan={10} className="p-2 pl-16 text-[10px] italic text-slate-400">Sin clientes registrados en este período</td>
                                      </tr>
                                    ) : (
                                      (clientesPorProducto[prodKey] || []).map((cli: any, cIdx: number) => {
                                        const cliVarPct = Number(cli.variacion ?? calcVarPct(cli.venta, cli.ventaYoy));
                                        return (
                                          <tr
                                            key={prodKey + '_' + cIdx}
                                            className={"text-[10px] " + (isDark ? 'bg-[#17171A] text-slate-400' : 'bg-slate-200/50 text-slate-700')}
                                          >
                                            <td className="p-1.5 pl-16 font-bold flex items-center gap-2 min-w-[140px]">
                                              <Building2 className="w-3 h-3 text-cyan-500 shrink-0" />
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
                                            <td className={"p-1.5 text-center font-bold " + (cliVarPct >= 0 ? titleEmerald : 'text-rose-500')}>
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
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Tabla 2 -- con scroll interno cuando hay mucha información */}
        <div className={"p-6 rounded-2xl border shadow-sm space-y-4 min-w-0 " + panelBg}>
          <div className="flex items-center justify-between">
            <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
              <Building2 className="w-4 h-4" /> TABLA 2: RANKING DE CLIENTES (YOY &amp; VAR %)
            </h3>
            {selectedCategoria && (
              <button
                onClick={() => setSelectedCategoria(null)}
                className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-blue-500/15 text-blue-500 border border-blue-500/30 flex items-center gap-1 cursor-pointer"
              >
                Filtrado: {selectedCategoria} ×
              </button>
            )}
          </div>

          <div className="overflow-x-auto overflow-y-auto max-h-[420px] rounded-xl">
            <table className="w-full text-left text-xs border-collapse min-w-[420px]">
              <thead className="sticky top-0 z-10">
                <tr className={"border-b text-[10px] font-black uppercase tracking-wider " + tableHeaderClass}>
                  <SortableTh label="CLIENTE" sortKey="cliente" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label={String(periodYears[0])} sortKey="v2026" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className={titleBlue} />
                  <SortableTh label={String(periodYears[1])} sortKey="v2025" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[2])} sortKey="v2024" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label={String(periodYears[3])} sortKey="v2023" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label="VAR %" sortKey="varPct" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" className={titleEmerald} />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
                {filteredClients.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-4 text-center text-slate-400 italic">
                      Sin clientes B2B registrados para esta selección
                    </td>
                  </tr>
                ) : (
                  filteredClients.map((d, idx) => {
                    const clientVarVal = d.varPct || 0;
                    const clientVarText = (clientVarVal >= 0 ? '+' : '') + clientVarVal.toFixed(1) + '%';

                    return (
                      <tr key={d.id || idx} className={`hover:bg-blue-500/10 transition-colors ${
                        isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                      }`}>
                        <td className="p-2.5 font-extrabold max-w-[110px]">
                          <span className="block truncate" title={d.cliente}>{d.cliente}</span>
                        </td>
                        <td className={"p-2.5 text-right font-black " + titleBlue}>{formatCompactCLP(d.v2026)}</td>
                        <td className={"p-2.5 text-right " + subtextColor}>{formatCompactCLP(d.v2025)}</td>
                        <td className={"p-2.5 text-right opacity-70 " + subtextColor}>{formatCompactCLP(d.v2024)}</td>
                        <td className={"p-2.5 text-right opacity-50 " + subtextColor}>{formatCompactCLP(d.v2023)}</td>
                        <td className={"p-2.5 text-center font-black " + (clientVarVal >= 0 ? titleEmerald : 'text-rose-500')}>
                          {clientVarText}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DistributorsView;