import React, { useState, useEffect } from 'react';
import { AlertTriangle, X, Tag, CheckCircle2 } from 'lucide-react';
import {
  SkuPendienteCategoria,
  fetchCategoriasPendientes,
  fetchCategoriasCatalogo,
  asignarCategoriaSku,
} from '../services/api';

interface CategoriaAlertaModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
  onCambiosGuardados?: () => void;
}

export const CategoriaAlertaModal: React.FC<CategoriaAlertaModalProps> = ({
  isOpen, onClose, isDark, onCambiosGuardados
}) => {
  const [items, setItems] = useState<SkuPendienteCategoria[]>([]);
  const [catalogo, setCatalogo] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Valor del selector/input por SKU mientras se edita
  const [seleccion, setSeleccion] = useState<Record<string, string>>({});
  const [guardando, setGuardando] = useState<Record<string, boolean>>({});
  const [guardados, setGuardados] = useState<Record<string, boolean>>({});

  const cargar = () => {
    setLoading(true);
    setError(null);
    Promise.all([fetchCategoriasPendientes(), fetchCategoriasCatalogo()])
      .then(([pendientes, cats]) => {
        setItems(pendientes.items);
        setCatalogo(cats);
      })
      .catch((err) => setError(err?.message || 'No se pudo cargar la lista.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) cargar();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleGuardar = async (sku: string) => {
    const categoria = (seleccion[sku] || '').trim();
    if (!categoria) return;
    setGuardando((prev) => ({ ...prev, [sku]: true }));
    try {
      await asignarCategoriaSku(sku, categoria);
      setGuardados((prev) => ({ ...prev, [sku]: true }));
      setItems((prev) => prev.filter((i) => i.sku !== sku));
      onCambiosGuardados?.();
    } catch (err: any) {
      setError(err?.message || `No se pudo guardar la categoría para ${sku}.`);
    } finally {
      setGuardando((prev) => ({ ...prev, [sku]: false }));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className={`w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border shadow-2xl ${
        isDark ? 'bg-[#1C1C1E] border-[#333339]' : 'bg-white border-slate-200'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between p-5 border-b ${
          isDark ? 'border-[#333339]' : 'border-slate-200'
        }`}>
          <h2 className="text-sm font-black uppercase tracking-wider flex items-center gap-2 text-amber-500">
            <AlertTriangle className="w-5 h-5" /> SKUs Vendidos Sin Categoría ({items.length})
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-500/10">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Estos productos tuvieron ventas pero no tienen una categoría real asignada (en Bsale
            figuran como "Sin Tipo"). Asígnales una categoría acá -- se va a aplicar
            automáticamente en la próxima sincronización de ventas.
          </p>

          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs font-semibold">
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-12 text-center text-sm font-semibold opacity-50">Cargando...</div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center flex flex-col items-center gap-2 text-emerald-500">
              <CheckCircle2 className="w-8 h-8" />
              <span className="text-sm font-bold">¡Todo al día! No hay SKUs vendidos sin categoría.</span>
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.sku}
                  className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center gap-2.5 ${
                    isDark ? 'bg-[#232328] border-[#333339]' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-blue-500">
                      <Tag className="w-3 h-3" /> {item.sku}
                    </div>
                    <div className="text-xs font-semibold truncate">{item.producto}</div>
                    <div className="text-[10px] opacity-60">
                      ${item.ventaTotal.toLocaleString('es-CL')} · {item.lineas} línea{item.lineas === 1 ? '' : 's'} de venta
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <input
                      type="text"
                      list="categorias-catalogo-list"
                      placeholder="Escribe o elige categoría"
                      value={seleccion[item.sku] || ''}
                      onChange={(e) => setSeleccion((prev) => ({ ...prev, [item.sku]: e.target.value }))}
                      className={`w-48 px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
                        isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                      }`}
                    />
                    <button
                      onClick={() => handleGuardar(item.sku)}
                      disabled={!seleccion[item.sku] || guardando[item.sku]}
                      className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-extrabold disabled:opacity-40 shrink-0"
                    >
                      {guardando[item.sku] ? '...' : 'Guardar'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <datalist id="categorias-catalogo-list">
            {catalogo.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </div>
      </div>
    </div>
  );
};
