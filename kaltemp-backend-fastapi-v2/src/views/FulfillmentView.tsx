import React, { useState, useEffect, useMemo } from 'react';
import { ThemeMode } from '../types';
import { Truck, Store, Layers, RefreshCw, ArrowUpRight, CheckCircle2 } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchFulfillment, fetchFulfillmentPorProducto } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';

interface Props {
  theme: ThemeMode;
}

const COLORES_CANAL = ['#30D158', '#FF9F0A', '#0A84FF', '#5E5CE6', '#FF375F', '#64D2FF'];

const fmtM = (n: number) => `$${((n || 0) / 1000000).toFixed(1)} M`;
const fmtVar = (cy: number, prev: number) => {
  if (!prev) return null;
  return ((cy - prev) / prev) * 100;
};

export const FulfillmentView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { startDate, endDate } = useGlobalFilter();

  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);

  const collator = useMemo(() => new Intl.Collator('es', { numeric: true, sensitivity: 'base' }), []);

  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [productos, setProductos] = useState<any[]>([]);
  const [productosLoading, setProductosLoading] = useState(true);
  const [productosError, setProductosError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchFulfillment(startDate, endDate)
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));

    setProductosLoading(true);
    fetchFulfillmentPorProducto(startDate, endDate)
      .then((res) => {
        setProductos(Array.isArray(res?.items) ? res.items : []);
        setProductosError(null);
      })
      .catch((err) => setProductosError(err.message))
      .finally(() => setProductosLoading(false));
  }, [startDate, endDate]);

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

  const sortedProductos = useMemo(() => {
    return [...(productos || [])].sort((a: any, b: any) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];
      if (aVal === undefined || aVal === null) aVal = '';
      if (bVal === undefined || bVal === null) bVal = '';

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        const cmp = collator.compare(aVal, bVal);
        return sortDir === 'asc' ? cmp : -cmp;
      }
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [productos, sortKey, sortDir, collator]);

  const ventaCy = data?.ventaCy || 0;
  const ventaYoy = data?.ventaYoy || 0;
  const varVenta = fmtVar(ventaCy, ventaYoy);

  const ventaDirectaCy = data?.ventaDirectaCy || 0;
  const shareCy = data?.shareFulfillmentCy || 0;
  const shareYoy = data?.shareFulfillmentYoy || 0;
  const totalConsolidado = data?.totalConsolidadoCy || 0;
  const shareDirecta = totalConsolidado ? 100 - shareCy : 0;

  const programas: { canal: string; origen: string; venta: number }[] = Array.isArray(data?.programas) ? data.programas : [];

  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titlePurple = isDark ? "text-purple-400" : "text-purple-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600" />
        <span className={"text-sm font-semibold " + subtextColor}>Cargando datos de Fulfillment...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {error && (
        <div className={isDark ? "px-4 py-3 rounded-2xl text-xs font-bold bg-rose-500/10 text-rose-300 border border-rose-500/20" : "px-4 py-3 rounded-2xl text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200"}>
          {error}
        </div>
      )}

      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <h1 className={"text-2xl font-black tracking-tight flex items-center gap-2.5 " + titleBlue}>
          <Truck className="w-7 h-7 text-blue-600 dark:text-blue-400" /> Detalle Fulfillment
        </h1>
      </div>

      {/* Top Banner KPI Cards Estilo Apple HIG */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        
        {/* KPI 1: Venta Bruta Fulfillment */}
        <div className={"p-5 rounded-2xl border transition-all hover:shadow-md " + panelBg}>
          <span className={"text-[10px] font-black uppercase tracking-wider block " + titleBlue}>
            VENTA BRUTA FULFILLMENT
          </span>
          <div className={"text-3xl font-black mt-2 " + titleBlue}>
            {fmtM(ventaCy)} CLP
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs font-medium border-t pt-2 border-slate-100 dark:border-[#2C2C2E]">
            <span className={subtextColor}>YoY: {fmtM(ventaYoy)}</span>
            {varVenta !== null && (
              <span className={varVenta >= 0 ? "px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20" : "px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"}>
                {(varVenta >= 0 ? '+' : '') + varVenta.toFixed(1) + '% VAR'}
              </span>
            )}
          </div>
        </div>

        {/* KPI 2: Venta Bruta Bsale Directa */}
        <div className={"p-5 rounded-2xl border transition-all hover:shadow-md " + panelBg}>
          <span className={"text-[10px] font-black uppercase tracking-wider block " + titleEmerald}>
            VENTA BRUTA BSALE (DIRECTA)
          </span>
          <div className={"text-3xl font-black mt-2 " + titleEmerald}>
            {fmtM(ventaDirectaCy)} CLP
          </div>
          <div className="mt-3 border-t pt-2 border-slate-100 dark:border-[#2C2C2E]">
            <span className={"text-[11px] font-medium block " + subtextColor}>
              Ventas procesadas fuera de bodegas externas
            </span>
          </div>
        </div>

        {/* KPI 3: Share de Venta Fulfillment */}
        <div className={"p-5 rounded-2xl border transition-all hover:shadow-md " + panelBg}>
          <span className={"text-[10px] font-black uppercase tracking-wider block " + titlePurple}>
            SHARE DE VENTA FULFILLMENT
          </span>
          <div className={"text-3xl font-black mt-2 " + titlePurple}>
            {shareCy.toFixed(1)}%
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs font-medium border-t pt-2 border-slate-100 dark:border-[#2C2C2E]">
            <span className={subtextColor}>YoY: {shareYoy.toFixed(1)}%</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
              {((shareCy - shareYoy) >= 0 ? '+' : '') + (shareCy - shareYoy).toFixed(1) + ' pp VAR'}
            </span>
          </div>
        </div>

      </div>

      {/* Program Cards Row */}
      {programas.length > 0 && (
        <div>
          <h3 className={"text-xs font-black uppercase tracking-wider mb-3 flex items-center gap-2 " + titleBlue}>
            <Store className="w-4 h-4" /> VENTA FULFILLMENT POR CANAL
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {programas.map((prog, idx) => {
              const isSelected = selectedChannel === prog.canal;
              const color = COLORES_CANAL[idx % COLORES_CANAL.length];

              return (
                <div
                  key={prog.canal + '-' + prog.origen}
                  onClick={() => setSelectedChannel(isSelected ? null : prog.canal)}
                  className={"p-5 rounded-2xl text-slate-900 shadow-md flex flex-col justify-between transition-all cursor-pointer " + (isSelected ? 'ring-4 ring-blue-500 scale-[1.02]' : 'hover:scale-[1.01]')}
                  style={{ backgroundColor: color }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black uppercase tracking-wide bg-black/20 text-white px-2.5 py-1 rounded-lg">
                      {prog.canal || 'Sin canal'}
                    </span>
                    <Truck className="w-5 h-5 text-white/80" />
                  </div>
                  <div className="mt-4">
                    <div className="text-3xl font-black text-white">
                      {fmtM(prog.venta)}
                    </div>
                    <p className="text-xs font-extrabold text-white/90 mt-1">{prog.origen}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Comparativa: Venta Directa vs Fulfillment */}
      {data && (
        <div className={"p-6 rounded-2xl border shadow-sm space-y-4 " + panelBg}>
          <div className="flex items-center justify-between">
            <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
              <Layers className="w-4 h-4" /> COMPARATIVA: VENTA BRUTA BSALE DIRECTA VS FULFILLMENT
            </h3>
            <span className={"text-xs font-extrabold bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-500/20 " + titleBlue}>
              Total Consolidado: {fmtM(totalConsolidado)} CLP
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className={isDark ? "p-4 rounded-xl border bg-[#121214] border-[#2C2C2E]" : "p-4 rounded-xl border bg-slate-50 border-slate-200"}>
              <div className="flex items-center justify-between mb-2">
                <span className={"text-xs font-black uppercase " + titleEmerald}>
                  1. Venta Directa (Bsale / Sitio Propio)
                </span>
                <span className={"text-xs font-black px-2 py-0.5 rounded bg-emerald-500/10 " + titleEmerald}>
                  ${ventaDirectaCy.toLocaleString('es-CL')} ({shareDirecta.toFixed(1)}% Share)
                </span>
              </div>
              <p className={"text-xs font-medium leading-relaxed mb-3 " + subtextColor}>
                Ventas procesadas directamente en Bsale (E-Commerce, Showroom, Distribuidores, etc.).
              </p>
              <div className={isDark ? "w-full h-2.5 rounded-full overflow-hidden bg-[#2C2C2E]" : "w-full h-2.5 rounded-full overflow-hidden bg-slate-200"}>
                <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${shareDirecta}%` }} />
              </div>
            </div>

            <div className={isDark ? "p-4 rounded-xl border bg-[#121214] border-[#2C2C2E]" : "p-4 rounded-xl border bg-slate-50 border-slate-200"}>
              <div className="flex items-center justify-between mb-2">
                <span className={"text-xs font-black uppercase " + titlePurple}>
                  2. Fulfillment Marketplaces
                </span>
                <span className={"text-xs font-black px-2 py-0.5 rounded bg-purple-500/10 " + titlePurple}>
                  ${ventaCy.toLocaleString('es-CL')} ({shareCy.toFixed(1)}% Share)
                </span>
              </div>
              <p className={"text-xs font-medium leading-relaxed mb-3 " + subtextColor}>
                Ventas brutas consolidadas en bodegas externas de marketplaces (Falabella Full / MercadoLibre Full).
              </p>
              <div className={isDark ? "w-full h-2.5 rounded-full overflow-hidden bg-[#2C2C2E]" : "w-full h-2.5 rounded-full overflow-hidden bg-slate-200"}>
                <div className="h-full bg-purple-500 rounded-full transition-all duration-500" style={{ width: `${shareCy}%` }} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabla Venta por Producto y Canal */}
      <div className={"p-6 rounded-2xl border shadow-sm space-y-4 " + panelBg}>
        <h3 className={"text-xs font-black uppercase tracking-wider flex items-center gap-2 " + titleBlue}>
          <Layers className="w-4 h-4" /> VENTA POR PRODUCTO Y CANAL FULFILLMENT
        </h3>

        {productosError && (
          <div className={isDark ? "px-4 py-3 rounded-2xl text-xs font-bold bg-rose-500/10 text-rose-300 border border-rose-500/20" : "px-4 py-3 rounded-2xl text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200"}>
            {productosError}
          </div>
        )}

        {productosLoading ? (
          <div className="flex items-center justify-center p-8 space-x-2">
            <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
            <span className={"text-xs font-semibold " + subtextColor}>Cargando detalle por producto...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse min-w-[900px]">
              <thead>
                <tr className={"border-b text-[10px] font-black uppercase tracking-wider " + tableHeaderClass}>
                  <SortableTh label="PRODUCTO" sortKey="producto" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                  <SortableTh label="CANAL" sortKey="canal" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                  <SortableTh label="UNIDADES" sortKey="unidades" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" className={titleBlue + " font-black"} />
                  <SortableTh label="UNIDADES YoY" sortKey="unidadesYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                  <SortableTh label="VAR %" sortKey="varPct" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                  <SortableTh label="VENTA $" sortKey="venta" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={titleEmerald + " font-black"} />
                  <SortableTh label="VENTA YoY" sortKey="ventaYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                  <SortableTh label="VAR % VENTA" sortKey="ventaVarPct" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
                {sortedProductos.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-6 text-center text-slate-400 italic">
                      Sin ventas de fulfillment por producto en este periodo.
                    </td>
                  </tr>
                ) : (
                  sortedProductos.map((row, idx) => {
                    const varPctVal = row.varPct || 0;
                    const ventaVarPctVal = row.ventaVarPct || 0;

                    return (
                      <tr key={(row.id || idx) + '-row'} className={`hover:bg-blue-500/10 transition-colors ${
                        isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                      }`}>
                        <td className="p-2.5 font-extrabold">{row.producto}</td>
                        <td className="p-2.5">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                            {row.canal}
                          </span>
                        </td>
                        <td className={`p-2.5 text-center font-black ${titleBlue}`}>{row.unidades || 0} u.</td>
                        <td className={`p-2.5 text-center ${subtextColor}`}>{row.unidadesYoy || 0} u.</td>
                        <td className="p-2.5 text-center font-black">
                          <span className={varPctVal >= 0 ? "px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20" : "px-2 py-0.5 rounded-full text-[10px] bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"}>
                            {(varPctVal >= 0 ? '+' : '') + varPctVal.toFixed(1) + '%'}
                          </span>
                        </td>
                        <td className={`p-2.5 text-right font-black ${titleEmerald}`}>${(row.venta || 0).toLocaleString('es-CL')}</td>
                        <td className={`p-2.5 text-right font-semibold ${subtextColor}`}>${(row.ventaYoy || 0).toLocaleString('es-CL')}</td>
                        <td className="p-2.5 text-center font-black">
                          <span className={ventaVarPctVal >= 0 ? "px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20" : "px-2 py-0.5 rounded-full text-[10px] bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"}>
                            {(ventaVarPctVal >= 0 ? '+' : '') + ventaVarPctVal.toFixed(1) + '%'}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default FulfillmentView;