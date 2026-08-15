// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\components\AbandonedCartsView.tsx (o la carpeta donde ya vive hoy)
import React, { useState, useEffect } from 'react';
import { ThemeMode, BrandMode} from '../types';
import { getBrandTokens } from '../theme/brandTokens';
import { ShoppingCart, DollarSign, RefreshCw, Percent, TrendingDown, ArrowUpRight } from 'lucide-react';
import { useGlobalFilter, ALL_CATEGORIES, ALL_CHANNELS, ALL_REPS, ALL_WAREHOUSES } from '../context/FilterContext';
import { fetchAbandonedCarts } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';

interface Props {
  theme: ThemeMode;
  brandMode: BrandMode;
}

export const AbandonedCartsView: React.FC<Props> = ({ theme, brandMode }) => {
  const isDark = theme === 'dark';
  const brandTokens = getBrandTokens(brandMode, isDark);

  const { 
    startDate, 
    endDate, 
    selectedCategories, 
    selectedChannels, 
    selectedReps, 
    selectedWarehouses 
  } = useGlobalFilter();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const catParam = (selectedCategories && selectedCategories.length < ALL_CATEGORIES.length) ? selectedCategories.join(',') : null;
    const chanParam = (selectedChannels && selectedChannels.length < ALL_CHANNELS.length) ? selectedChannels.join(',') : null;
    const repParam = (selectedReps && selectedReps.length < ALL_REPS.length) ? selectedReps.join(',') : null;
    const whParam = (selectedWarehouses && selectedWarehouses.length < ALL_WAREHOUSES.length) ? selectedWarehouses.join(',') : null;

    fetchAbandonedCarts(startDate, endDate, catParam, chanParam, repParam, whParam)
      .then((res) => {
        if (isMounted) setData(res && typeof res === 'object' ? res : null);
      })
      .catch((err) => {
        console.error("Error al cargar carros abandonados:", err);
        if (isMounted) setData(null);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [
    startDate, 
    endDate, 
    JSON.stringify(selectedCategories), 
    JSON.stringify(selectedChannels), 
    JSON.stringify(selectedReps), 
    JSON.stringify(selectedWarehouses)
  ]);

  const totalCarritos = data?.totalCarritos ?? 0;
  const oportunidadPerdida = data?.oportunidadPerdida ?? 0;
  const recuperados = data?.carritosRecuperados ?? 0;
  const tasaRecuperacion = data?.tasaRecuperacion ?? 0;
  const topProductos = Array.isArray(data?.topProductos) ? data.topProductos : [];

  const formatCLP = (val: number) => `$${Math.round(val || 0).toLocaleString('es-CL')}`;

  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleRed = isDark ? "text-red-400" : "text-red-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const titleAmber = isDark ? "text-amber-400" : "text-amber-800";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-red-600" />
        <span className={`text-sm font-semibold ${subtextColor}`}>Cargando Carros Abandonados Shopify...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5" style={{ color: brandTokens.accent }}>
          <ShoppingCart className="w-7 h-7" style={{ color: brandTokens.accent }} /> Carros Abandonados Shopify
        </h1>
      </div>

      {/* Top KPI Cards Estilo Apple HIG */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1: Carros Abandonados */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleRed}`}>
              <ShoppingCart className="w-4 h-4" /> CARROS ABANDONADOS
            </span>
            <span className="p-1.5 rounded-lg bg-red-500/10 text-red-500">
              <TrendingDown className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleRed}`}>{totalCarritos}</span>
            <span className="text-[10px] font-bold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">
              Checkouts
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Checkouts no finalizados en Shopify</span>
          </div>
        </div>

        {/* KPI 2: Oportunidad Perdida */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleAmber}`}>
              <DollarSign className="w-4 h-4" /> OPORTUNIDAD PERDIDA
            </span>
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-500">
              <DollarSign className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleAmber}`}>{formatCLP(oportunidadPerdida)}</span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Monto total acumulado en carritos</span>
          </div>
        </div>

        {/* KPI 3: Carros Recuperados */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleEmerald}`}>
              <RefreshCw className="w-4 h-4" /> CARROS RECUPERADOS
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500">
              <ArrowUpRight className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleEmerald}`}>{recuperados}</span>
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              Convertidos
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Ventas rescatadas post-mkt</span>
          </div>
        </div>

        {/* KPI 4: Tasa de Recuperación */}
        <div className={`p-5 rounded-2xl border transition-all hover:shadow-md ${panelBg}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${titleBlue}`}>
              <Percent className="w-4 h-4" /> TASA DE RECUPERACIÓN
            </span>
            <span className="p-1.5 rounded-lg bg-blue-500/10 text-blue-500">
              <Percent className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={`text-3xl font-black tracking-tight ${titleBlue}`}>{tasaRecuperacion}%</span>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-[#2C2C2E] flex justify-between text-xs font-medium">
            <span className={subtextColor}>Efectividad de correos / Klaviyo</span>
          </div>
        </div>

      </div>

      {/* Tabla Top Productos Abandonados */}
      <div className={`p-6 rounded-2xl border shadow-sm ${panelBg}`}>
        <h3 className={`text-xs font-black uppercase tracking-wider mb-4 flex items-center gap-2 ${titleBlue}`}>
          <TrendingDown className="w-4 h-4" /> TOP PRODUCTOS MÁS ABANDONADOS ({topProductos.length})
        </h3>

        <div className="overflow-auto max-h-[480px] rounded-lg border border-slate-200/60 dark:border-[#2C2C2E]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className={`sticky top-0 z-10 ${isDark ? 'bg-[#17171A]' : 'bg-slate-50'}`}>
              <tr className={`border-b text-[11px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
                <th className="p-3">PRODUCTO</th>
                <th className="p-3 text-center">CARRITOS</th>
                <th className="p-3 text-right">PRECIO REF.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#2C2C2E]">
              {topProductos.length === 0 ? (
                <tr>
                  <td colSpan={3} className="p-6 text-center text-slate-400 italic">
                    Sin carritos abandonados en este rango de fechas
                  </td>
                </tr>
              ) : (
                topProductos.map((p: any, idx: number) => (
                  <tr key={idx} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-3 font-extrabold">{p.producto}</td>
                    <td className={`p-3 text-center font-black ${titleRed}`}>{p.carritos} u.</td>
                    <td className={`p-3 text-right font-black ${titleEmerald}`}>{formatCLP(p.precioRef || 0)}</td>
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

export default AbandonedCartsView;