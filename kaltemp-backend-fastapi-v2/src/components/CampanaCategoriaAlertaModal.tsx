import React, { useState, useEffect } from 'react';
import { Megaphone, X, Tag, CheckCircle2 } from 'lucide-react';
import {
  CampanaPendienteCategoria,
  fetchCampanasPendientes,
  fetchCategoriasCatalogo,
  asignarCategoriaCampana,
} from '../services/api';

interface CampanaCategoriaAlertaModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
  onCambiosGuardados?: () => void;
}

export const CampanaCategoriaAlertaModal: React.FC<CampanaCategoriaAlertaModalProps> = ({
  isOpen, onClose, isDark, onCambiosGuardados
}) => {
  const [items, setItems] = useState<CampanaPendienteCategoria[]>([]);
  const [catalogo, setCatalogo] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [seleccion, setSeleccion] = useState<Record<string, string>>({});
  const [guardando, setGuardando] = useState<Record<string, boolean>>({});

  const cargar = () => {
    setLoading(true);
    setError(null);
    Promise.all([fetchCampanasPendientes(), fetchCategoriasCatalogo()])
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

  const handleGuardar = async (item: CampanaPendienteCategoria) => {
    const categoria = (seleccion[item.campana] || '').trim();
    if (!categoria) return;
    setGuardando((prev) => ({ ...prev, [item.campana]: true }));
    try {
      await asignarCategoriaCampana(item.campana, item.plataforma, categoria);
      setItems((prev) => prev.filter((i) => i.campana !== item.campana));
      onCambiosGuardados?.();
    } catch (err: any) {
      setError(err?.message || `No se pudo guardar la categoría para ${item.campana}.`);
    } finally {
      setGuardando((prev) => ({ ...prev, [item.campana]: false }));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className={`w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border shadow-2xl ${
        isDark ? 'bg-[#1C1C1E] border-[#333339]' : 'bg-white border-slate-200'
      }`}>
        <div className={`flex items-center justify-between p-5 border-b ${
          isDark ? 'border-[#333339]' : 'border-slate-200'
        }`}>
          <h2 className="text-sm font-black uppercase tracking-wider flex items-center gap-2 text-amber-500">
            <Megaphone className="w-5 h-5" /> Campañas Sin Categoría ({items.length})
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-500/10">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Estas campañas de Meta/Google tuvieron inversión pero no tienen una categoría de
            producto asignada -- por eso no aparecen repartidas en "Performance por Categoría"
            de Indicadores D2C. Asígnales una -- se aplica de inmediato, sin esperar ningún sync.
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
              <span className="text-sm font-bold">¡Todo al día! No hay campañas sin categoría.</span>
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.campana}
                  className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center gap-2.5 ${
                    isDark ? 'bg-[#232328] border-[#333339]' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-blue-500 uppercase">
                      <Tag className="w-3 h-3" /> {item.plataforma} · {item.marca}
                    </div>
                    <div className="text-xs font-semibold truncate">{item.campana}</div>
                    <div className="text-[10px] opacity-60">
                      ${item.gastoTotal.toLocaleString('es-CL')} invertidos
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <input
                      type="text"
                      list="categorias-catalogo-list-campanas"
                      placeholder="Escribe o elige categoría"
                      value={seleccion[item.campana] || ''}
                      onChange={(e) => setSeleccion((prev) => ({ ...prev, [item.campana]: e.target.value }))}
                      className={`w-48 px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
                        isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                      }`}
                    />
                    <button
                      onClick={() => handleGuardar(item)}
                      disabled={!seleccion[item.campana] || guardando[item.campana]}
                      className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-extrabold disabled:opacity-40 shrink-0"
                    >
                      {guardando[item.campana] ? '...' : 'Guardar'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <datalist id="categorias-catalogo-list-campanas">
            {catalogo.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </div>
      </div>
    </div>
  );
};
