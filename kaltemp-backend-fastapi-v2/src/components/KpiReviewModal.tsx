import React from 'react';
import { X, CheckCircle2, AlertTriangle, TrendingUp, HelpCircle, Lightbulb, BarChart3, ShieldCheck } from 'lucide-react';
import { ThemeMode } from '../types';

interface KpiReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  theme: ThemeMode;
}

export const KpiReviewModal: React.FC<KpiReviewModalProps> = ({ isOpen, onClose, theme }) => {
  if (!isOpen) return null;

  const isDark = theme === 'dark';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className={`relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl border ${
          isDark ? 'bg-[#1C1C1E] border-[#2C2C2E] text-[#F5F5F7]' : 'bg-white border-slate-200/80 text-[#1D1D1F]'
        } p-6 sm:p-8`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-4 mb-6 border-slate-200 dark:border-[#2C2C2E]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-extrabold tracking-tight">
                Auditoría & Recomendación de KPIs - Kaltemp
              </h2>
              <p className={`text-xs ${isDark ? 'text-[#8E8E93]' : 'text-slate-500'}`}>
                Revisión técnica de métricas actuales y recomendaciones estratégicas
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-2 rounded-lg transition-colors ${
              isDark ? 'hover:bg-[#2C2C2E] text-[#8E8E93]' : 'hover:bg-slate-100 text-slate-500'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Verdict Badge */}
        <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold text-emerald-500">
              Diagnóstico General: Los KPIs actuales son sólidos y están bien estructurados.
            </h4>
            <p className="text-xs mt-1 leading-relaxed opacity-90">
              La arquitectura de métricas actual cubre de forma equilibrada la perspectiva financiera
              (Contribución/Margen Frontal), logística (Cobertura/Despachos), ventas (Canales/SKU)
              y marketing (TACOS/ROAS). A continuación verás la confirmación de aciertos y 4 mejoras clave recomendadas.
            </p>
          </div>
        </div>

        {/* Section 1: Validated Strengths */}
        <div className="space-y-4 mb-8">
          <h3 className="text-sm font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> 1. KPIs Confirmados (Muy bien implementados)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-[#333339]' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div className="font-semibold text-xs text-emerald-500 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Venta Bruta, Contribución y Margen Frontal
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                Excelente triada ejecutiva. El cálculo de <code>Margen Frontal % = (Contribución / Venta Neta) * 100</code> previene distorsiones causadas por IVA o descuentos comerciales masivos.
              </p>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-[#333339]' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div className="font-semibold text-xs text-emerald-500 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> TACOS Global (Total Advertising Cost of Sales)
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                <code>TACOS = (Inversión MKT / Venta D2C) * 100</code>. Es mucho mejor indicador de rentabilidad real que el ROAS de las plataformas de anuncios, las cuales suelen sobre-atribuir compras.
              </p>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-[#333339]' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div className="font-semibold text-xs text-emerald-500 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Cobertura de Stock (Días de Inventario)
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                <code>Stock / Venta Diaria Promedio (14d)</code> con alertas de color (🔴 Quiebre &lt; 7d) para Casa Matriz y Bodega Full es el estándar óptimo de la industria HVAC.
              </p>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-[#333339]' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div className="font-semibold text-xs text-emerald-500 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Auditoría de Notas de Crédito y Pendientes
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                Calcular el desfase entre la fecha de emisión y la caída real al libro RCOF evita diferencias contables y asegura que las ventas no despachadas estén bajo control.
              </p>
            </div>
          </div>
        </div>

        {/* Section 2: Strategic Recommendations */}
        <div className="space-y-4 mb-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-500 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> 2. Recomendaciones de Mejora Aplicadas
          </h3>

          <div className="space-y-3">
            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-emerald-500/30' : 'bg-emerald-50/50 border-emerald-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-bold text-xs text-emerald-500 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 1. Ticket Promedio (TKP) Promovido al Hero Principal
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-500 font-bold">
                  ✅ APLICADO
                </span>
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                Incorporado en la fila Hero Ejecutiva (Principal). Permite analizar de inmediato el comportamiento de compra de los clientes con comparativas WOW, YOY y 2YOY.
              </p>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-emerald-500/30' : 'bg-emerald-50/50 border-emerald-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-bold text-xs text-emerald-500 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 2. Tasa de Conversión de Leads a Venta (%)
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-500 font-bold">
                  ✅ APLICADO
                </span>
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                Destacado en el módulo de Leads con desglose de tasa de conversión por cada ejecutivo comercial (William, Alexis, Diana, Andesgear).
              </p>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-emerald-500/30' : 'bg-emerald-50/50 border-emerald-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-bold text-xs text-emerald-500 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 3. Aging Buckets para Despachos Pendientes
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-500 font-bold">
                  ✅ APLICADO
                </span>
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                Implementado en el módulo de Auditoría Bsale dividiendo el backlog en 3 tramos: <code>1-3 días (normal)</code>, <code>4-7 días (atención)</code> y <code>&gt;7 días (crítico)</code> con gráfico acumulativo de avance.
              </p>
            </div>

            <div
              className={`p-4 rounded-xl border ${
                isDark ? 'bg-[#17171A] border-emerald-500/30' : 'bg-emerald-50/50 border-emerald-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-bold text-xs text-emerald-500 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 4. Margen Neto Fulfillment vs. Venta Directa Bsale
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-500 font-bold">
                  ✅ APLICADO
                </span>
              </div>
              <p className="text-xs opacity-80 leading-relaxed">
                Añadido al módulo de Fulfillment comparando el 42.1% de margen neto directo Bsale versus el 33.2% de consolas Fulfillment tras comisiones (-8.9% de impacto).
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-200 dark:border-[#333339] flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition-colors shadow-lg shadow-blue-500/25"
          >
            Entendido, cerrar revisión
          </button>
        </div>
      </div>
    </div>
  );
};
