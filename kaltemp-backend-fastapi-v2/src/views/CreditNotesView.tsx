// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\components\CreditNotesView.tsx
// (o la carpeta donde ya vive hoy tu CreditNotesView.tsx -- solo reemplaza ese archivo)
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { CreditNoteItem, ThemeMode, BrandMode} from '../types';
import { getBrandTokens } from '../theme/brandTokens';
import { FileSpreadsheet, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { fetchNotasCredito } from '../services/api';
import { useGlobalFilter } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';

interface Props {
  theme: ThemeMode;
  brandMode: BrandMode;
}

export const CreditNotesView: React.FC<Props> = ({ theme, brandMode }) => {
  const isDark = theme === 'dark';
  const brandTokens = getBrandTokens(brandMode, isDark);

  // Filtro de fechas GLOBAL (sidebar) -- antes este módulo lo ignoraba
  // por completo y siempre traía el histórico entero sin filtrar.
  const { startDate, endDate } = useGlobalFilter();

  // Filtro cruzado LOCAL a este módulo (clic en tarjeta con desfase)
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);

  const collator = useMemo(() => new Intl.Collator('es', { numeric: true, sensitivity: 'base' }), []);

  // Formatea un ISO string (con o sin hora) a DD/MM/AAAA -- las fechas
  // vienen del backend como .isoformat() (ej. "2026-07-06T21:00:32"),
  // que mostraba también la hora. Acá solo se cambia la presentación en
  // esta tabla; el ISO original se sigue usando para ordenar.
  const formatFecha = (iso: string | null | undefined): string => {
    if (!iso) return '—';
    const soloFecha = iso.split('T')[0]; // "2026-07-06"
    const [anio, mes, dia] = soloFecha.split('-');
    if (!anio || !mes || !dia) return iso;
    return `${dia}/${mes}/${anio}`;
  };

  const [CREDIT_NOTES_DATA, setCreditNotesData] = useState<CreditNoteItem[]>([]);
  const [disponible, setDisponible] = useState(true);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const cargarNotasCredito = useCallback(() => {
    setLoading(true);
    fetchNotasCredito(startDate, endDate)
      .then((res) => {
        setDisponible(res.disponible);
        setMensaje(res.mensaje);
        setCreditNotesData(Array.isArray(res.items) ? (res.items as CreditNoteItem[]) : []);
      })
      .catch((err) => {
        setDisponible(false);
        setMensaje(err.message);
      })
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  // Se re-ejecuta automáticamente cada vez que cambia el rango de fechas
  // del sidebar -- ya no hace falta un botón "Actualizar" separado para
  // que la vista refleje el filtro.
  useEffect(() => {
    cargarNotasCredito();
  }, [cargarNotasCredito]);

  // Sorting state
  const [sortKey, setSortKey] = useState<string>('diasDesfase');
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
    let list = CREDIT_NOTES_DATA || [];
    if (selectedStatus) {
      if (selectedStatus === 'Desfase') {
        list = list.filter((i) => i.alerta);
      } else if (selectedStatus === 'Normal') {
        list = list.filter((i) => !i.alerta);
      }
    }

    return [...list].sort((a: any, b: any) => {
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
  }, [CREDIT_NOTES_DATA, selectedStatus, sortKey, sortDir, collator]);

  const totalNc = CREDIT_NOTES_DATA.length;
  const desfaseNc = CREDIT_NOTES_DATA.filter((n) => n.alerta).length;
  const montoDesfase = CREDIT_NOTES_DATA.filter((n) => n.alerta).reduce((acc, n) => acc + (n.monto || 0), 0);
  const diasPromDesfase =
    CREDIT_NOTES_DATA.filter((n) => n.alerta).reduce((acc, n) => acc + (n.diasDesfase || 0), 0) / (desfaseNc || 1);

  // Estilos de Apple HIG para Fondos y Títulos
  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleRed = isDark ? "text-red-400" : "text-red-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titleAmber = isDark ? "text-amber-400" : "text-amber-800";
  const titlePurple = isDark ? "text-purple-400" : "text-purple-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600" />
        <span className={`text-sm font-semibold ${subtextColor}`}>Cargando notas de crédito...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {!disponible && (
        <div className={`px-4 py-3 rounded-2xl text-xs font-bold ${isDark ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20' : 'bg-amber-50 text-amber-800 border border-amber-200'}`}>
          {mensaje}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5" style={{ color: brandTokens.accent }}>
          <FileSpreadsheet className="w-7 h-7" style={{ color: brandTokens.accent }} /> Notas de Crédito
        </h1>
        <button
          onClick={cargarNotasCredito}
          disabled={loading}
          title="Volver a pedir los datos al servidor"
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
            isDark ? 'bg-white/5 hover:bg-white/10 text-[#EDEDED]' : 'bg-black/5 hover:bg-black/10 text-slate-700'
          } disabled:opacity-50`}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Actualizar
        </button>
      </div>

      {/* KPI Cards Estilo Apple HIG */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1: Total NCs */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <span className={`text-[10px] font-black uppercase tracking-wider ${titleBlue}`}>
            TOTAL NOTAS DE CRÉDITO
          </span>
          <div className={`text-3xl font-black mt-2 ${titleBlue}`}>
            {totalNc} NCs
          </div>
          <span className={`text-xs block mt-1 font-medium ${subtextColor}`}>
            En el periodo de análisis
          </span>
        </div>

        {/* KPI 2: Con Desfase RCOF (Filtro Interactivo) */}
        <div 
          onClick={() => setSelectedStatus(selectedStatus === 'Desfase' ? null : 'Desfase')}
          className={`p-5 rounded-2xl border cursor-pointer transition-all hover:shadow-md ${
            selectedStatus === 'Desfase'
              ? (isDark ? 'border-red-500 ring-2 ring-red-500/30 bg-red-500/10' : 'border-red-500 ring-2 ring-red-500/20 bg-red-50')
              : panelBg
          }`}
        >
          <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleRed}`}>
            <AlertTriangle className="w-3.5 h-3.5" /> CON DESFASE RCOF
          </span>
          <div className={`text-3xl font-black mt-2 ${titleRed}`}>
            {desfaseNc} NCs ({totalNc ? ((desfaseNc / totalNc) * 100).toFixed(0) : 0}%)
          </div>
          <span className="text-xs block mt-1 text-red-600 dark:text-red-400 font-extrabold">
            {selectedStatus === 'Desfase' ? '✓ Filtro desfases activo (clic para quitar)' : 'Haz clic para filtrar desfases'}
          </span>
        </div>

        {/* KPI 3: Monto en Desfase */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <span className={`text-[10px] font-black uppercase tracking-wider ${titleAmber}`}>
            MONTO EN DESFASE
          </span>
          <div className={`text-3xl font-black mt-2 ${titleAmber}`}>
            ${(montoDesfase / 1000000).toFixed(2)} M
          </div>
          <span className={`text-xs block mt-1 font-medium ${subtextColor}`}>
            Monto neto diferido
          </span>
        </div>

        {/* KPI 4: Días Promedio Desfase */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <span className={`text-[10px] font-black uppercase tracking-wider ${titlePurple}`}>
            DÍAS PROM. DESFASE
          </span>
          <div className={`text-3xl font-black mt-2 ${titlePurple}`}>
            {diasPromDesfase.toFixed(1)} Días
          </div>
          <span className={`text-xs block mt-1 font-medium ${subtextColor}`}>
            Emisión vs Registro RCOF
          </span>
        </div>

      </div>

      {/* Audit Table */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
            <FileSpreadsheet className="w-4 h-4" /> AUDITORÍA DE NOTAS DE CRÉDITO
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse min-w-[1200px]">
            <thead>
              <tr className={`border-b text-[10px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <SortableTh label="ALERTA DESFASE" sortKey="alerta" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="DOCUMENTO" sortKey="documento" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="DOCUMENTO ORIGINAL" sortKey="documentoOriginal" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="DESCRIPCIÓN" sortKey="descripcionProducto" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="CLIENTE" sortKey="cliente" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="VENDEDOR" sortKey="vendedor" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="FECHA CREACIÓN" sortKey="fechaGeneracion" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                <SortableTh label="FECHA IMPACTO" sortKey="fechaEmision" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                <SortableTh label="DÍAS DESFASE" sortKey="diasDesfase" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                <SortableTh label="MONTO NETO" sortKey="monto" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339] font-medium">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-6 text-center text-slate-400 italic">
                    Sin notas de crédito registradas para este filtro
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr key={item.id} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-2.5 font-bold">
                      {item.alerta ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 font-black flex items-center gap-1 w-max">
                          <AlertTriangle className="w-3 h-3" /> ⚠️ +{item.diasDesfase}d Desfase
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-black flex items-center gap-1 w-max">
                          <CheckCircle2 className="w-3 h-3" /> ✅ Normal
                        </span>
                      )}
                    </td>
                    <td className={`p-2.5 font-black ${titleBlue}`}>{item.documento}</td>
                    <td className="p-2.5 font-bold">
                      {item.documentoOriginal ? (
                        item.documentoOriginal
                      ) : (
                        <span className="opacity-40 italic">—</span>
                      )}
                    </td>
                    <td className="p-2.5 max-w-[220px] truncate" title={item.descripcionProducto || undefined}>
                      {item.descripcionProducto ? (
                        item.descripcionProducto
                      ) : (
                        <span className="opacity-40 italic">—</span>
                      )}
                    </td>
                    <td className="p-2.5 font-semibold">{item.cliente}</td>
                    <td className={`p-2.5 font-extrabold ${titleAmber}`}>{item.vendedor || 'Sin vendedor'}</td>
                    <td className="p-2.5 text-center font-medium">
                      {item.fechaGeneracion ? formatFecha(item.fechaGeneracion) : <span className="opacity-40 italic">—</span>}
                    </td>
                    <td className="p-2.5 text-center font-medium">{formatFecha(item.fechaEmision)}</td>
                    <td className={`p-2.5 text-center font-black ${item.alerta ? titleRed : titleAmber}`}>{item.diasDesfase}d</td>
                    <td className={`p-2.5 text-right font-black ${titleEmerald}`}>${(item.monto || 0).toLocaleString('es-CL')}</td>
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

export default CreditNotesView;