import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode, BrandMode} from '../types';
import { getBrandTokens } from '../theme/brandTokens';
import { Building, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchRealEstate } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
  brandMode: BrandMode;
}

export const RealEstateView: React.FC<Props> = ({ theme, brandMode }) => {
  const isDark = theme === 'dark';
  const brandTokens = getBrandTokens(brandMode, isDark);
  const { startDate, endDate } = useGlobalFilter();

  // Filtro cruzado LOCAL a este módulo (clic en una fila de la Tabla 1) --
  // no vive en FilterContext, se resetea solo al salir de esta vista.
  const [selectedCategoria, setSelectedCategoria] = useState<string | null>(null);

  // Estados locales -- /api/real-estate devuelve un objeto rico (mismo shape
  // que /api/distributors): totalVentas, ventaYoy, variacionYoy, totalProyectos,
  // rankingProyectos, distribucionCategoria, tendenciaMensual. NO trae
  // cantidades (no hay c2026/c2025/c2024), solo montos de venta.
  const [totalVentas, setTotalVentas] = useState(0);
  const [ventaYoy, setVentaYoy] = useState(0);
  const [varPctYoY, setVarPctYoY] = useState(0);
  const [totalProyectosCount, setTotalProyectosCount] = useState(0);

  const [categoryTableData, setCategoryTableData] = useState<{ categoria: string; venta: number }[]>([]);
  const [proyectosList, setProyectosList] = useState<any[]>([]);
  const [monthlyData, setMonthlyData] = useState<{ mes: string; yActual: number; yAnterior: number; varPct: string }[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
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

        // Ranking de Proyectos/Clientes Inmobiliarios
        const rawProyectos = data.rankingProyectos || [];
        const normProyectos = rawProyectos.map((p: any, idx: number) => ({
          id: p.id || idx,
          proyecto: p.proyecto || p.cliente || p.name || 'Proyecto sin nombre',
          venta: Number(p.venta ?? 0),
          ventaYoy: Number(p.ventaYoy ?? 0),
          varPct: Number(p.variacion ?? 0),
          categoria: p.categoria || 'Sin Categoría Mapeada'
        }));
        setProyectosList(normProyectos);

        // Categorías Bsale
        const rawCats = data.distribucionCategoria || [];
        const normCats = rawCats.map((cat: any) => ({
          categoria: cat.categoria || cat.name || 'Categoría',
          venta: Number(cat.venta ?? cat.value ?? 0)
        }));
        setCategoryTableData(normCats);

        // Tendencia Mensual
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

        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  const [sortKeyTable1, setSortKeyTable1] = useState<string>('venta');
  const [sortDirTable1, setSortDirTable1] = useState<'asc' | 'desc'>('desc');

  const [sortKeyTable2, setSortKeyTable2] = useState<string>('venta');
  const [sortDirTable2, setSortDirTable2] = useState<'asc' | 'desc'>('desc');

  // NOTA: mismo denominador estimado fijo que usa DistributorsView.tsx --
  // pendiente de conectar a /api/channels con el mismo rango si se quiere exacto.
  const totalKaltempSales = 245000000;
  const distWeightPct = totalKaltempSales > 0 ? ((totalVentas / totalKaltempSales) * 100).toFixed(1) : '0.0';

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
          <span className="text-[11px] font-bold uppercase tracking-wider block truncate" style={{ color: brandTokens.accent }}>
            VENTA B2B INMOBILIARIAS
          </span>
          <div className="text-2xl font-extrabold mt-1" style={{ color: brandTokens.accent }}>
            ${(totalVentas / 1000000).toFixed(1)} M CLP
          </div>
          <div className="mt-2 space-y-0.5 text-xs font-semibold">
            <div className="flex justify-between">
              <span className="opacity-70">YoY (período anterior):</span>
              <span>${(ventaYoy / 1000000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between text-emerald-500 font-extrabold pt-0.5 border-t border-slate-200 dark:border-[#333339]">
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

      {/* Monthly B2B Comparison Bar Chart */}
      <div
        className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
            <Building className="w-4 h-4" /> VENTA TOTAL B2B AÑO - COMPARATIVO MENSUAL HISTÓRICO ($ M)
          </h3>
          <span className="text-xs font-extrabold text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            VAR% YoY Promedio: {varPctYoY >= 0 ? '+' : ''}{varPctYoY.toFixed(1)}%
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
                        <p className="text-emerald-500 font-extrabold mt-1">VAR% YoY: {data.varPct}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="yAnterior" name="Año Anterior ($M)" fill={isDark ? '#48484A' : '#94a3b8'} radius={[4, 4, 0, 0]} />
              <Bar dataKey="yActual" name="Actual ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="varPct" position="top" fill="#30D158" fontSize={11} fontWeight="bold" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Side-by-side Tables Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
        {/* Table 1: Categorías (solo Venta -- el backend no trae cantidades para este canal) */}
        <div
          className={`p-4 rounded-xl border shadow-md space-y-4 min-w-0 ${
            isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
              <DollarSign className="w-4 h-4" /> TABLA 1: DESGLOSE POR CATEGORÍA
            </h3>
            <span className="text-[10px] text-slate-400">Haz clic en una categoría para filtro cruzado</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[350px]">
              <thead>
                <tr className={`border-b text-[11px] font-bold ${
                  isDark ? 'border-[#333339] text-[#B8B8BE] bg-[#17171A]' : 'border-slate-200 text-slate-500 bg-slate-50'
                }`}>
                  <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label="VENTA ACTUAL" sortKey="venta" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className="text-blue-500" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
                {sortedCategoryData.length === 0 && (
                  <tr><td colSpan={2} className="p-3 text-center opacity-50 italic">Sin datos en el período</td></tr>
                )}
                {sortedCategoryData.map((cat, idx) => {
                  const isSelected = selectedCategoria === cat.categoria;
                  return (
                    <tr
                      key={cat.categoria + idx}
                      onClick={() => setSelectedCategoria(isSelected ? null : cat.categoria)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? isDark ? 'bg-blue-600/30 font-bold border-l-4 border-l-blue-500' : 'bg-blue-100 font-bold border-l-4 border-l-blue-500'
                          : isDark ? 'hover:bg-blue-500/10 text-[#EDEDED]' : 'hover:bg-blue-500/10 text-slate-800'
                      }`}
                    >
                      <td className="p-2 font-bold flex items-center gap-1.5">
                        {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                        {cat.categoria}
                      </td>
                      <td className="p-2 text-right font-extrabold text-blue-500">${(cat.venta || 0).toLocaleString('es-CL')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Table 2: Proyectos (Proyecto, Venta Actual $, Venta YoY, VAR %) */}
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

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[450px]">
              <thead>
                <tr className={`border-b text-[11px] font-bold ${
                  isDark ? 'border-[#333339] text-[#B8B8BE] bg-[#17171A]' : 'border-slate-200 text-slate-500 bg-slate-50'
                }`}>
                  <SortableTh label="PROYECTO / CLIENTE" sortKey="proyecto" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label="VENTA ACTUAL ($)" sortKey="venta" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className="text-blue-500" />
                  <SortableTh label="VENTA YOY ($)" sortKey="ventaYoy" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label="VAR %" sortKey="varPct" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" className="text-emerald-500" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
                {filteredProyectos.length === 0 && (
                  <tr><td colSpan={4} className="p-3 text-center opacity-50 italic">Sin datos en el período</td></tr>
                )}
                {filteredProyectos.map((p, idx) => (
                  <tr key={p.id ?? idx} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-2 font-bold">{p.proyecto}</td>
                    <td className="p-2 text-right font-extrabold text-blue-500">${(p.venta || 0).toLocaleString('es-CL')}</td>
                    <td className="p-2 text-right opacity-70">${(p.ventaYoy || 0).toLocaleString('es-CL')}</td>
                    <td className="p-2 text-center font-extrabold text-emerald-500">{p.varPct >= 0 ? '+' : ''}{(p.varPct || 0).toFixed(1)}%</td>
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