// ============================================================
// ARCHIVO: PesoAlertaModal.tsx
// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\components\PesoAlertaModal.tsx
// ============================================================
import React, { useState, useEffect } from 'react';
import { AlertTriangle, X, Tag, CheckCircle2, Ban } from 'lucide-react';
import {
  SkuPendientePeso,
  fetchPesoPendientes,
  asignarPesoSku,
} from '../services/api';

interface PesoAlertaModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
  onCambiosGuardados?: () => void;
}

interface FormValores {
  peso: string;
  largo: string;
  ancho: string;
  alto: string;
  descontinuado: boolean;
}

const FORM_VACIO: FormValores = { peso: '', largo: '', ancho: '', alto: '', descontinuado: false };

export const PesoAlertaModal: React.FC<PesoAlertaModalProps> = ({
  isOpen, onClose, isDark, onCambiosGuardados
}) => {
  const [items, setItems] = useState<SkuPendientePeso[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<Record<string, FormValores>>({});
  const [guardando, setGuardando] = useState<Record<string, boolean>>({});

  const cargar = () => {
    setLoading(true);
    setError(null);
    fetchPesoPendientes()
      .then((res) => setItems(res.items))
      .catch((err) => setError(err?.message || 'No se pudo cargar la lista.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) cargar();
  }, [isOpen]);

  if (!isOpen) return null;

  const getForm = (sku: string): FormValores => form[sku] || FORM_VACIO;
  const setCampo = (sku: string, campo: keyof FormValores, valor: string | boolean) => {
    setForm((prev) => ({ ...prev, [sku]: { ...getForm(sku), [campo]: valor } }));
  };

  const puedeGuardar = (sku: string) => {
    const f = getForm(sku);
    if (f.descontinuado) return true;
    return !!f.peso && !!f.largo && !!f.ancho && !!f.alto;
  };

  const handleGuardar = async (sku: string) => {
    const f = getForm(sku);
    setGuardando((prev) => ({ ...prev, [sku]: true }));
    try {
      await asignarPesoSku(sku, {
        pesoKg: f.descontinuado ? undefined : parseFloat(f.peso),
        largoCm: f.descontinuado ? undefined : parseFloat(f.largo),
        anchoCm: f.descontinuado ? undefined : parseFloat(f.ancho),
        altoCm: f.descontinuado ? undefined : parseFloat(f.alto),
        descontinuado: f.descontinuado,
      });
      setItems((prev) => prev.filter((i) => i.sku !== sku));
      onCambiosGuardados?.();
    } catch (err: any) {
      setError(err?.message || `No se pudo guardar ${sku}.`);
    } finally {
      setGuardando((prev) => ({ ...prev, [sku]: false }));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className={`w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl border shadow-2xl ${
        isDark ? 'bg-[#1C1C1E] border-[#333339]' : 'bg-white border-slate-200'
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between p-5 border-b ${
          isDark ? 'border-[#333339]' : 'border-slate-200'
        }`}>
          <h2 className="text-sm font-black uppercase tracking-wider flex items-center gap-2 text-amber-500">
            <AlertTriangle className="w-5 h-5" /> SKUs Vendidos Sin Peso/Medidas ({items.length})
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-500/10">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Estos productos tuvieron ventas pero no tienen peso/dimensiones de paquete cargados.
            Se usan en Control Logístico para calcular el costo real de envío en vez de un valor
            genérico fijo. Si un producto ya no se vende, márcalo como <b>Descontinuado</b> en vez
            de llenar las medidas.
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
              <span className="text-sm font-bold">¡Todo al día! No hay SKUs vendidos sin peso/medidas.</span>
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => {
                const f = getForm(item.sku);
                return (
                  <div
                    key={item.sku}
                    className={`p-3 rounded-xl border flex flex-col gap-2.5 ${
                      isDark ? 'bg-[#232328] border-[#333339]' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-blue-500">
                          <Tag className="w-3 h-3" /> {item.sku}
                        </div>
                        <div className="text-xs font-semibold truncate">{item.producto}</div>
                        <div className="text-[10px] opacity-60">
                          ${item.ventaTotal.toLocaleString('es-CL')} · {item.lineas} línea{item.lineas === 1 ? '' : 's'} de venta
                        </div>
                      </div>

                      <label className="flex items-center gap-1.5 text-[11px] font-bold shrink-0 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={f.descontinuado}
                          onChange={(e) => setCampo(item.sku, 'descontinuado', e.target.checked)}
                          className="w-3.5 h-3.5 accent-amber-500"
                        />
                        <Ban className="w-3 h-3 text-amber-500" /> Descontinuado
                      </label>
                    </div>

                    {!f.descontinuado && (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                        <input
                          type="number" step="0.1" placeholder="Peso (kg)"
                          value={f.peso}
                          onChange={(e) => setCampo(item.sku, 'peso', e.target.value)}
                          className={`px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
                            isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                          }`}
                        />
                        <input
                          type="number" step="0.1" placeholder="Largo (cm)"
                          value={f.largo}
                          onChange={(e) => setCampo(item.sku, 'largo', e.target.value)}
                          className={`px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
                            isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                          }`}
                        />
                        <input
                          type="number" step="0.1" placeholder="Ancho (cm)"
                          value={f.ancho}
                          onChange={(e) => setCampo(item.sku, 'ancho', e.target.value)}
                          className={`px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
                            isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                          }`}
                        />
                        <input
                          type="number" step="0.1" placeholder="Alto (cm)"
                          value={f.alto}
                          onChange={(e) => setCampo(item.sku, 'alto', e.target.value)}
                          className={`px-2.5 py-1.5 text-xs font-semibold rounded-lg border outline-none ${
                            isDark ? 'bg-[#1C1C1E] border-[#383840] text-white' : 'bg-white border-slate-300'
                          }`}
                        />
                      </div>
                    )}

                    <button
                      onClick={() => handleGuardar(item.sku)}
                      disabled={!puedeGuardar(item.sku) || guardando[item.sku]}
                      className="self-end px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-extrabold disabled:opacity-40"
                    >
                      {guardando[item.sku] ? '...' : 'Guardar'}
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