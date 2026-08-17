import React, { useState, useMemo, useEffect } from 'react';
import { PendingDispatchItem, PendingDispatchDocItem, ThemeMode} from '../types';
import { ClipboardList, AlertCircle, PackageSearch, User } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchPendientesDespacho, fetchPendientesDespachoDocumentos } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';

interface Props {
  theme: ThemeMode;
}

export const PendingDispatchView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  // Filtros globales del sidebar
  const { matchesCategory, matchesWarehouse, matchesRep } = useGlobalFilter();

  // Filtro cruzado LOCAL a este módulo (clic en una tarjeta de vendedor)
  const [selectedRep, setSelectedRep] = useState<string | null>(null);

  const collator = useMemo(() => new Intl.Collator('es', { numeric: true, sensitivity: 'base' }), []);

  const compareValues = (aVal: any, bVal: any, dir: 'asc' | 'desc'): number => {
    if (aVal === undefined || aVal === null) aVal = '';
    if (bVal === undefined || bVal === null) bVal = '';

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      const cmp = collator.compare(aVal, bVal);
      return dir === 'asc' ? cmp : -cmp;
    }

    if (aVal < bVal) return dir === 'asc' ? -1 : 1;
    if (aVal > bVal) return dir === 'asc' ? 1 : -1;
    return 0;
  };

  const [PENDING_DATA, setPendingData] = useState<PendingDispatchItem[]>([]);
  const [disponible, setDisponible] = useState(true);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [DOCS_DATA, setDocsData] = useState<PendingDispatchDocItem[]>([]);
  const [docsDisponible, setDocsDisponible] = useState(true);
  const [docsMensaje, setDocsMensaje] = useState<string | null>(null);
  const [docsLoading, setDocsLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchPendientesDespacho()
      .then((res) => {
        setDisponible(res.disponible);
        setMensaje(res.mensaje);
        setPendingData(res.items as PendingDispatchItem[]);
      })
      .catch((err) => {
        setDisponible(false);
        setMensaje(err.message);
      })
      .finally(() => setLoading(false));

    setDocsLoading(true);
    fetchPendientesDespachoDocumentos()
      .then((res) => {
        setDocsDisponible(res.disponible);
        setDocsMensaje(res.mensaje);
        setDocsData(res.items as PendingDispatchDocItem[]);
      })
      .catch((err) => {
        setDocsDisponible(false);
        setDocsMensaje(err.message);
      })
      .finally(() => setDocsLoading(false));
  }, []);

  const [sortKey, setSortKey] = useState<string>('cantidadReservada');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const filteredItems = useMemo(() => {
    const list = PENDING_DATA.filter(
      (i) => matchesCategory(i.categoria) && matchesWarehouse(i.bodega)
    );

    return [...list].sort((a: any, b: any) => compareValues(a[sortKey], b[sortKey], sortDir));
  }, [PENDING_DATA, matchesCategory, matchesWarehouse, sortKey, sortDir]);

  const totalUnidadesReservadas = filteredItems.reduce((acc, i) => acc + i.cantidadReservada, 0);
  const totalSkusAfectados = filteredItems.length;

  const porBodega = useMemo(() => {
    const map: Record<string, number> = {};
    filteredItems.forEach((i) => {
      map[i.bodega] = (map[i.bodega] || 0) + i.cantidadReservada;
    });
    return Object.entries(map)
      .map(([bodega, unidades]) => ({ bodega, unidades }))
      .sort((a, b) => b.unidades - a.unidades);
  }, [filteredItems]);

  // --- Tabla de documentos (tracking por vendedor) ---
  const [sortKeyDocs, setSortKeyDocs] = useState<string>('diasPendiente');
  const [sortDirDocs, setSortDirDocs] = useState<'asc' | 'desc'>('desc');

  const handleSortDocs = (key: string) => {
    if (sortKeyDocs === key) {
      setSortDirDocs((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKeyDocs(key);
      setSortDirDocs('desc');
    }
  };

  const filteredDocs = useMemo(() => {
    const list = DOCS_DATA.filter(
      (d) => matchesWarehouse(d.bodega) && matchesRep(d.vendedor) && (!selectedRep || d.vendedor === selectedRep)
    );

    return [...list].sort((a: any, b: any) => compareValues(a[sortKeyDocs], b[sortKeyDocs], sortDirDocs));
  }, [DOCS_DATA, matchesWarehouse, matchesRep, selectedRep, sortKeyDocs, sortDirDocs]);

  const resumenPorVendedor = useMemo(() => {
    const map: Record<string, { documentos: Set<string>; monto: number }> = {};
    filteredDocs.forEach((d) => {
      if (!map[d.vendedor]) map[d.vendedor] = { documentos: new Set(), monto: 0 };
      if (!map[d.vendedor].documentos.has(d.documento)) {
        map[d.vendedor].monto += d.montoDocumento;
      }
      map[d.vendedor].documentos.add(d.documento);
    });
    return Object.entries(map)
      .map(([vendedor, data]) => ({ vendedor, docs: data.documentos.size, monto: data.monto }))
      .sort((a, b) => b.monto - a.monto);
  }, [filteredDocs]);

  const handleClickVendedor = (vendedor: string) => {
    if (selectedRep === vendedor) {
      setSelectedRep(null);
    } else {
      setSelectedRep(vendedor);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {!disponible && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-amber-500/10 text-amber-300' : 'bg-amber-50 text-amber-700'}`}>
          {mensaje}
        </div>
      )}
      {loading && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-white/5 text-white/50' : 'bg-black/5 text-black/50'}`}>
          Cargando pendientes por despachar...
        </div>
      )}

      {/* Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5" /> UNIDADES RESERVADAS
          </span>
          <div className="text-2xl sm:text-3xl font-extrabold text-rose-500 mt-1">
            {totalUnidadesReservadas.toLocaleString('es-CL')}
          </div>
          <span className="text-[11px] block mt-1 opacity-70">Comprometidas, aún sin despachar</span>
        </div>

        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-blue-500 flex items-center gap-1.5">
            <PackageSearch className="w-3.5 h-3.5" /> SKUs AFECTADOS
          </span>
          <div className="text-2xl sm:text-3xl font-extrabold text-blue-500 mt-1">
            {totalSkusAfectados}
          </div>
          <span className="text-[11px] block mt-1 opacity-70">Combinaciones SKU + bodega</span>
        </div>

        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-500">
            BODEGA CON MÁS RESERVA
          </span>
          <div className="text-lg font-black text-amber-500 mt-1 truncate">
            {porBodega[0]?.bodega || 'N/A'}
          </div>
          <span className="text-[11px] block mt-1 opacity-70">
            {(porBodega[0]?.unidades || 0).toLocaleString('es-CL')} unidades
          </span>
        </div>
      </div>

      {/* Main Table */}
      <div
        className={`p-4 rounded-xl border shadow-md space-y-3 ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
          <ClipboardList className="w-4 h-4" /> STOCK RESERVADO PENDIENTE DE DESPACHO
        </h3>

        <div className="overflow-auto max-h-[520px] rounded-lg border border-slate-200/60 dark:border-[#2C2C2E]">
          <table className="w-full text-left text-xs border-collapse min-w-[700px]">
            <thead className={`sticky top-0 z-10 ${isDark ? 'bg-[#17171A]' : 'bg-slate-50'}`}>
              <tr className={`border-b text-[11px] font-bold ${
                isDark ? 'border-[#333339] text-[#B8B8BE]' : 'border-slate-200 text-slate-500'
              }`}>
                <SortableTh label="SKU" sortKey="sku" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="PRODUCTO" sortKey="producto" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="BODEGA" sortKey="bodega" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="UNIDADES RESERVADAS" sortKey="cantidadReservada" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" className="font-extrabold text-blue-500" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-4 text-center text-xs text-slate-400 italic">
                    Sin stock reservado pendiente de despacho para este filtro
                  </td>
                </tr>
              ) : (
                filteredItems.map((item, idx) => (
                  <tr key={`${item.id}-${idx}`} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-2.5 font-bold text-blue-500">{item.sku}</td>
                    <td className="p-2.5 font-semibold max-w-xs truncate">{item.producto}</td>
                    <td className="p-2.5 text-[11px] opacity-80">{item.categoria}</td>
                    <td className="p-2.5 text-[11px] opacity-80">{item.bodega}</td>
                    <td className="p-2.5 text-center font-extrabold text-rose-500">{item.cantidadReservada}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tracking por Vendedor */}
      <div className={`p-4 rounded-xl border shadow-md space-y-3 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200/80'
      }`}>
        <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
          <User className="w-4 h-4" /> RESUMEN POR VENDEDOR
        </h3>

        {!docsDisponible && (
          <div className={`px-3 py-2 rounded-lg text-[12px] ${isDark ? 'bg-amber-500/10 text-amber-300' : 'bg-amber-50 text-amber-700'}`}>
            {docsMensaje}
          </div>
        )}
        {docsLoading && (
          <div className={`px-3 py-2 rounded-lg text-[12px] ${isDark ? 'bg-white/5 text-white/50' : 'bg-black/5 text-black/50'}`}>
            Cargando documentos...
          </div>
        )}

        {docsDisponible && !docsLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {resumenPorVendedor.map((v) => {
              const activo = selectedRep === v.vendedor;
              return (
                <div
                  key={v.vendedor}
                  onClick={() => handleClickVendedor(v.vendedor)}
                  title={activo ? 'Click para quitar el filtro' : `Click para filtrar por ${v.vendedor}`}
                  className={`p-3 rounded-xl border cursor-pointer transition-all hover:border-blue-500/60 ${
                    activo
                      ? 'border-blue-500 ring-2 ring-blue-500/40 ' + (isDark ? 'bg-blue-500/10' : 'bg-blue-50')
                      : isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <span className="text-xs font-extrabold text-blue-500 flex items-center gap-1.5 truncate">
                    <User className="w-3.5 h-3.5 shrink-0" /> {v.vendedor}
                  </span>
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-[11px] opacity-70">{v.docs} docs</span>
                    <span className="text-sm font-black text-rose-500">
                      ${v.monto.toLocaleString('es-CL')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Detalle por documento */}
      <div
        className={`p-4 rounded-xl border shadow-md space-y-3 ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
          <ClipboardList className="w-4 h-4" /> DETALLE POR DOCUMENTO (BOLETA / FACTURA / COTIZACIÓN)
        </h3>

        <div className="overflow-auto max-h-[480px] rounded-lg border border-slate-200/60 dark:border-[#2C2C2E]">
          <table className="w-full text-left text-xs border-collapse min-w-[1150px]">
            <thead className={`sticky top-0 z-10 ${isDark ? 'bg-[#17171A]' : 'bg-slate-50'}`}>
              <tr className={`border-b text-[11px] font-bold ${
                isDark ? 'border-[#333339] text-[#B8B8BE]' : 'border-slate-200 text-slate-500'
              }`}>
                <SortableTh label="DOCUMENTO" sortKey="documento" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="TIPO" sortKey="tipoDocumento" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="SKU" sortKey="sku" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="DESCRIPCIÓN" sortKey="descripcion" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="VENDEDOR" sortKey="vendedor" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="CLIENTE" sortKey="cliente" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="BODEGA" sortKey="bodega" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} />
                <SortableTh label="FECHA EMISIÓN" sortKey="fechaEmision" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} align="center" />
                <SortableTh label="DÍAS" sortKey="diasPendiente" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} align="center" />
                <SortableTh label="CANT." sortKey="cantidad" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} align="center" />
                <SortableTh label="MONTO DOC." sortKey="montoDocumento" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} align="right" />
                <SortableTh label="# PEDIDO" sortKey="pedidoNumero" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} align="center" />
                <SortableTh label="ESTADO ENVÍO" sortKey="estadoEnvio" currentSortKey={sortKeyDocs} sortDirection={sortDirDocs} onSort={handleSortDocs} align="center" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={13} className="p-4 text-center text-xs text-slate-400 italic">
                    Sin documentos pendientes para este filtro
                  </td>
                </tr>
              ) : (
                filteredDocs.map((d, idx) => (
                  <tr key={`${d.id}-${idx}`} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-2.5 font-bold text-blue-500">{d.documento}</td>
                    <td className="p-2.5 text-[11px] opacity-80">{d.tipoDocumento}</td>
                    <td className="p-2.5 font-semibold">{d.sku}</td>
                    <td className="p-2.5 max-w-[180px] truncate">{d.descripcion}</td>
                    <td className="p-2.5 font-bold">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-500 border border-blue-500/20">
                        <User className="w-3 h-3" />
                        {d.vendedor}
                      </span>
                    </td>
                    <td className="p-2.5 max-w-[150px] truncate">{d.cliente}</td>
                    <td className="p-2.5 text-[11px] opacity-80">{d.bodega}</td>
                    <td className="p-2.5 text-center">{d.fechaEmision}</td>
                    <td className="p-2.5 text-center font-bold text-rose-500">{d.diasPendiente}d</td>
                    <td className="p-2.5 text-center font-bold">{d.cantidad}</td>
                    <td className="p-2.5 text-right font-extrabold">${d.montoDocumento.toLocaleString('es-CL')}</td>
                    <td className="p-2.5 text-center">
                      {d.pedidoNumero ? (
                        <span className="inline-flex flex-col items-center leading-tight">
                          <span className="font-bold">{d.pedidoNumero}</span>
                          {d.pedidoOrigen && (
                            <span className="text-[9.5px] opacity-60 uppercase">{d.pedidoOrigen}</span>
                          )}
                        </span>
                      ) : (
                        <span className="opacity-40 italic">—</span>
                      )}
                    </td>
                    <td className="p-2.5 text-center">
                      {d.estadoEnvio ? (
                        <span className="text-[11px] font-semibold">{d.estadoEnvio}</span>
                      ) : (
                        <span
                          className="text-[10px] opacity-40 italic"
                          title="Cruce con Envíame / Falabella Seller Center pendiente de implementar"
                        >
                          No disponible
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};