import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode} from '../types';
import { Building2, DollarSign, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchDistributors } from '../services/api';
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
  const [monthlyB2BData, setMonthlyB2BData] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchDistributors(startDate, endDate)
      .then((data: any) => {
        if (!data) return;

        if (Array.isArray(data)) {
          const v26 = data.reduce((acc, d) => acc + (d.v2026 || 0), 0);
          const v25 = data.reduce((acc, d) => acc + (d.v2025 || 0), 0);
          setTotalV2026(v26);
          setTotalV2025(v25);
          setClientList(data);
          setMonthlyB2BData([]);
        } else {
          const v26 = Number(data.totalVentas || 0);
          const v25 = Number(data.ventaYoy || 0);
          const vVar = Number(data.variacionYoy || 0);

          setTotalV2026(v26);
          setTotalV2025(v25);
          setVarPctYoY(vVar);
          setTotalClientesCount(Number(data.totalClientes || 0));

          const rawClients = Array.isArray(data.rankingClientes) ? data.rankingClientes : (Array.isArray(data.rankingProyectos) ? data.rankingProyectos : []);
          const normClients = rawClients.map((c: any, idx: number) => ({
            id: c.id || idx,
            cliente: c.cliente || c.name || c.proyecto || "Cliente B2B",
            v2026: Number(c.venta ?? c.v2026 ?? 0),
            v2025: Number(c.ventaYoy ?? c.v2025 ?? 0),
            varPct: Number(c.variacion ?? c.varPct ?? 0),
            categoria: c.categoria || "Sin Categoría Mapeada"
          }));
          setClientList(normClients);

          const rawCats = Array.isArray(data.distribucionCategoria) ? data.distribucionCategoria : [];
          const normCats = rawCats.map((cat: any) => ({
            categoria: cat.categoria || cat.name || "Categoría",
            ventaActual: Number(cat.venta ?? cat.value ?? 0),
            cantActual: Number(cat.cantidad ?? cat.count ?? 0),
            ventaYoy: Number(cat.ventaYoy ?? 0),
            cantYoy: Number(cat.cantYoy ?? 0)
          }));
          setCategoryTableData(normCats);

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
        }
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  const [sortKeyTable1, setSortKeyTable1] = useState<string>('ventaActual');
  const [sortDirTable1, setSortDirTable1] = useState<'asc' | 'desc'>('desc');

  const [sortKeyTable2, setSortKeyTable2] = useState<string>('v2026');
  const [sortDirTable2, setSortDirTable2] = useState<'asc' | 'desc'>('desc');

  const totalKaltempSales = 245000000;
  const distWeightPct = totalKaltempSales > 0 ? ((totalV2026 / totalKaltempSales) * 100).toFixed(1) : "0.0";

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

      {/* Gráfico Venta Mensual B2B */}
      <div className={"p-6 rounded-2xl border shadow-sm " + panelBg}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
            <Building2 className="w-4 h-4" /> VENTA TOTAL B2B AÑO - COMPARATIVO MENSUAL HISTÓRICO ($ M)
          </h3>
          <span className={"text-xs font-black bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 " + titleEmerald}>
            VAR% YoY Promedio: {(varPctYoY >= 0 ? '+' : '') + varPctYoY.toFixed(1) + '%'}
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
                        <p className={"font-black mt-1 " + titleEmerald}>VAR% YoY: {data.varPct}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="y2025" name="Año Anterior ($M)" fill={isDark ? '#38383A' : '#cbd5e1'} radius={[4, 4, 0, 0]} />
              <Bar dataKey="y2026" name="Actual ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="varPct" position="top" fill="#30D158" fontSize={11} fontWeight="bold" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tablas Lado a Lado */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        
        {/* Tabla 1 */}
        <div className={"p-6 rounded-2xl border shadow-sm space-y-4 min-w-0 " + panelBg}>
          <div className="flex items-center justify-between">
            <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
              <DollarSign className="w-4 h-4" /> TABLA 1: DESGLOSE POR CATEGORÍA
            </h3>
            <span className={"text-[10px] font-medium " + subtextColor}>Haz clic en una categoría para filtro cruzado</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[500px]">
              <thead>
                <tr className={"border-b text-[10px] font-black uppercase tracking-wider " + tableHeaderClass}>
                  <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label="VENTA ACTUAL" sortKey="ventaActual" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className={titleBlue} />
                  <SortableTh label="VENTA YOY" sortKey="ventaYoy" currentSortKey={sortKeyTable1} sortDirection={sortDirTable1} onSort={(k) => { setSortKeyTable1(k); setSortDirTable1(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
                {categoryTableData.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="p-4 text-center text-slate-400 italic">
                      Sin categorías registradas
                    </td>
                  </tr>
                ) : (
                  categoryTableData.map((cat, idx) => {
                    const isSelected = selectedCategoria === cat.categoria;
                    const rowBg = isSelected
                      ? (isDark ? 'bg-blue-600/30 font-bold border-l-4 border-l-blue-400' : 'bg-blue-50 font-bold border-l-4 border-l-blue-600')
                      : (isDark ? 'hover:bg-[#2C2C2E] text-[#EDEDED]' : 'hover:bg-slate-50 text-slate-800');

                    return (
                      <tr
                        key={cat.categoria + idx}
                        onClick={() => setSelectedCategoria(isSelected ? null : cat.categoria)}
                        className={"cursor-pointer transition-colors " + rowBg}
                      >
                        <td className="p-2.5 font-bold flex items-center gap-1.5">
                          {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                          {cat.categoria}
                        </td>
                        <td className={"p-2.5 text-right font-black " + titleBlue}>${(cat.ventaActual || 0).toLocaleString('es-CL')}</td>
                        <td className={"p-2.5 text-right " + subtextColor}>${(cat.ventaYoy || 0).toLocaleString('es-CL')}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Tabla 2 */}
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

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[450px]">
              <thead>
                <tr className={"border-b text-[10px] font-black uppercase tracking-wider " + tableHeaderClass}>
                  <SortableTh label="CLIENTE / DISTRIBUIDOR" sortKey="cliente" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} />
                  <SortableTh label="VENTA ACTUAL ($)" sortKey="v2026" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" className={titleBlue} />
                  <SortableTh label="VENTA YOY ($)" sortKey="v2025" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="right" />
                  <SortableTh label="VAR %" sortKey="varPct" currentSortKey={sortKeyTable2} sortDirection={sortDirTable2} onSort={(k) => { setSortKeyTable2(k); setSortDirTable2(p => p === 'asc' ? 'desc' : 'asc'); }} align="center" className={titleEmerald} />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
                {filteredClients.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-4 text-center text-slate-400 italic">
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
                        <td className="p-2.5 font-extrabold">{d.cliente}</td>
                        <td className={"p-2.5 text-right font-black " + titleBlue}>${(d.v2026 || 0).toLocaleString('es-CL')}</td>
                        <td className={"p-2.5 text-right " + subtextColor}>${(d.v2025 || 0).toLocaleString('es-CL')}</td>
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