// ============================================================
// ARCHIVO: DatosManualesModal.tsx
// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\components\DatosManualesModal.tsx
// (Respaldar el archivo actual antes de reemplazar: Copy-Item DatosManualesModal.tsx DatosManualesModal.tsx.bak)
// ============================================================

// ============================================================
// Archivo: DatosManualesModal.tsx
// Ruta:    src/components/DatosManualesModal.tsx
// ============================================================

import React, { useState, useEffect } from 'react';
import { Database, X, Plus, Trash2, CheckCircle2 } from 'lucide-react';
import {
  DatoManual,
  TipoDatoManual,
  fetchDatosManuales,
  fetchTiposDatosManuales,
  guardarDatoManual,
  eliminarDatoManual,
} from '../services/api';

interface DatosManualesModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
  onCambiosGuardados?: () => void;
}

export const DatosManualesModal: React.FC<DatosManualesModalProps> = ({
  isOpen, onClose, isDark, onCambiosGuardados
}) => {
  const [datos, setDatos] = useState<DatoManual[]>([]);
  const [tipos, setTipos] = useState<TipoDatoManual[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [eliminando, setEliminando] = useState<string | null>(null);

  // Formulario de carga rápida
  const [periodo, setPeriodo] = useState('');
  const [tipo, setTipo] = useState('');
  const [monto, setMonto] = useState('');
  const [notas, setNotas] = useState('');

  const cargar = () => {
    setLoading(true);
    setError(null);
    Promise.all([fetchDatosManuales(), fetchTiposDatosManuales()])
      .then(([lista, tiposList]) => {
        setDatos(lista);
        setTipos(tiposList);
        if (!tipo && tiposList.length > 0) setTipo(tiposList[0].tipo);
      })
      .catch((err) => setError(err?.message || 'No se pudo cargar la lista.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  if (!isOpen) return null;

  const etiquetaTipo = (t: string) => tipos.find((x) => x.tipo === t)?.etiqueta || t;

  const handleGuardar = async () => {
    const montoNum = Number(monto);
    if (!periodo.trim() || !tipo || !monto || Number.isNaN(montoNum)) {
      setError('Completa período, tipo y un monto numérico válido.');
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      await guardarDatoManual({ periodo: periodo.trim(), tipo, monto: montoNum, notas: notas.trim() || undefined });
      setPeriodo('');
      setMonto('');
      setNotas('');
      cargar();
      onCambiosGuardados?.();
    } catch (err: any) {
      setError(err?.message || 'No se pudo guardar el dato.');
    } finally {
      setGuardando(false);
    }
  };

  const handleEliminar = async (d: DatoManual) => {
    const clave = `${d.periodo}|${d.tipo}`;
    setEliminando(clave);
    setError(null);
    try {
      await eliminarDatoManual(d.periodo, d.tipo);
      setDatos((prev) => prev.filter((x) => !(x.periodo === d.periodo && x.tipo === d.tipo)));
      onCambiosGuardados?.();
    } catch (err: any) {
      setError(err?.message || 'No se pudo eliminar el dato.');
    } finally {
      setEliminando(null);
    }
  };

  const inputCls = `w-full px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
    isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
  }`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className={`w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border shadow-2xl ${
        isDark ? 'bg-[#1C1C1E] border-[#333339]' : 'bg-white border-slate-200'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between p-5 border-b ${
          isDark ? 'border-[#333339]' : 'border-slate-200'
        }`}>
          <h2 className="text-sm font-black uppercase tracking-wider flex items-center gap-2 text-blue-500">
            <Database className="w-5 h-5" /> Datos Manuales (Metas & Presupuesto)
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-500/10">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Carga acá valores que no vienen de ninguna API: metas históricas por año,
            presupuesto de marketing, o cualquier otro dato de gestión. El gráfico
            "Comparativo Histórico" y otros indicadores los usan automáticamente.
          </p>

          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs font-semibold">
              {error}
            </div>
          )}

          {/* Formulario de carga */}
          <div className={`p-4 rounded-xl border grid grid-cols-2 sm:grid-cols-5 gap-2.5 items-end ${
            isDark ? 'bg-[#232328] border-[#333339]' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="col-span-1">
              <label className="block text-[10px] font-bold uppercase opacity-60 mb-1">Período</label>
              <input
                type="text"
                placeholder="2024 ó 2026-07"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
                className={inputCls}
              />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className="block text-[10px] font-bold uppercase opacity-60 mb-1">Tipo</label>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)} className={inputCls}>
                {tipos.map((t) => (
                  <option key={t.tipo} value={t.tipo}>{t.etiqueta}</option>
                ))}
              </select>
            </div>
            <div className="col-span-1">
              <label className="block text-[10px] font-bold uppercase opacity-60 mb-1">Monto ($)</label>
              <input
                type="number"
                placeholder="45000000"
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                className={inputCls}
              />
            </div>
            <div className="col-span-1">
              <label className="block text-[10px] font-bold uppercase opacity-60 mb-1">Notas</label>
              <input
                type="text"
                placeholder="Opcional"
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                className={inputCls}
              />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <button
                onClick={handleGuardar}
                disabled={guardando}
                className="w-full px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-extrabold disabled:opacity-40 flex items-center justify-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" /> {guardando ? '...' : 'Guardar'}
              </button>
            </div>
          </div>

          <p className="text-[10px] opacity-50 -mt-2">
            Tip: el monto va en pesos completos (ej. 45000000 para $45M). Para métricas
            anuales usa solo el año como período (ej. "2024"); para presupuesto de
            marketing mensual usa año-mes (ej. "2026-07").
          </p>

          {/* Lista de datos ya cargados */}
          {loading ? (
            <div className="py-8 text-center text-sm font-semibold opacity-50">Cargando...</div>
          ) : datos.length === 0 ? (
            <div className="py-8 text-center flex flex-col items-center gap-2 opacity-60">
              <CheckCircle2 className="w-6 h-6" />
              <span className="text-xs font-semibold">Aún no has cargado ningún dato manual.</span>
            </div>
          ) : (
            <div className="space-y-1.5">
              {datos.map((d) => {
                const clave = `${d.periodo}|${d.tipo}`;
                return (
                  <div
                    key={clave}
                    className={`p-2.5 rounded-lg border flex items-center gap-3 text-xs ${
                      isDark ? 'bg-[#232328] border-[#333339]' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <span className="font-mono font-bold text-blue-500 w-20 shrink-0">{d.periodo}</span>
                    <span className="flex-1 min-w-0 truncate font-semibold">{etiquetaTipo(d.tipo)}</span>
                    <span className="font-black shrink-0">${d.monto.toLocaleString('es-CL')}</span>
                    {d.notas && <span className="opacity-50 truncate max-w-[120px] hidden sm:inline">{d.notas}</span>}
                    <button
                      onClick={() => handleEliminar(d)}
                      disabled={eliminando === clave}
                      className="p-1 rounded-md hover:bg-rose-500/10 text-rose-500 shrink-0 disabled:opacity-40"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
