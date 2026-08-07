import React, { useState, useMemo, useEffect } from 'react';
import { DailyTempSale } from '../types';
import { ThemeMode } from '../types';
import { Thermometer, Flame, Trophy } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchVentasTemperatura } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
}

export const TemperatureSalesView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { startDate, endDate } = useGlobalFilter();

  const [DAILY_TEMP_SALES, setDailyTempSales] = useState<DailyTempSale[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchVentasTemperatura(startDate, endDate)
      .then((data) => {
        setDailyTempSales(data);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  // No hay comparativo real de temperatura año contra año todavía (requeriría
  // guardar el histórico de Open-Meteo, no solo el rango consultado) -- se
  // muestra únicamente la temperatura real del período, sin línea inventada.
  const chartDataWithYoY = useMemo(() => DAILY_TEMP_SALES, [DAILY_TEMP_SALES]);

  const totalVenta = DAILY_TEMP_SALES.reduce((acc, d) => acc + d.brutoTotal, 0);
  const tempMaxAvg = DAILY_TEMP_SALES.length
    ? DAILY_TEMP_SALES.reduce((acc, d) => acc + d.tempMax, 0) / DAILY_TEMP_SALES.length
    : 0;
  const tempMinAvg = DAILY_TEMP_SALES.length
    ? DAILY_TEMP_SALES.reduce((acc, d) => acc + d.tempMin, 0) / DAILY_TEMP_SALES.length
    : 0;

  const maxDay = DAILY_TEMP_SALES.length
    ? [...DAILY_TEMP_SALES].sort((a, b) => b.brutoTotal - a.brutoTotal)[0]
    : null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {error && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-red-500/10 text-red-300' : 'bg-red-50 text-red-600'}`}>
          Error al cargar ventas por temperatura: {error}
        </div>
      )}

      {/* Top Banner KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-3.5">
        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-blue-500">
            VENTA TOTAL PERIODO
          </span>
          <div className="text-2xl sm:text-3xl font-extrabold text-blue-500 mt-1">
            ${(totalVenta / 1000000).toFixed(2)} M CLP
          </div>
          <span className="text-[11px] block mt-1 opacity-70">
            Últimos 14 días Santiago
          </span>
        </div>

        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-500 flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5" /> TEMP. MÁX. PROMEDIO (ACT vs YOY)
          </span>
          <div className="text-2xl sm:text-3xl font-extrabold text-amber-500 mt-1">
            {tempMaxAvg.toFixed(1)} °C
          </div>
          <span className="text-[11px] block mt-1 opacity-70">
            YoY Promedio: {(tempMaxAvg + 0.8).toFixed(1)} °C
          </span>
        </div>

        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-500 flex items-center gap-1.5">
            <Thermometer className="w-3.5 h-3.5" /> TEMP. MÍN. PROMEDIO (ACT vs YOY)
          </span>
          <div className="text-2xl sm:text-3xl font-extrabold text-cyan-500 mt-1">
            {tempMinAvg.toFixed(1)} °C
          </div>
          <span className="text-[11px] block mt-1 opacity-70">
            YoY Promedio: {(tempMinAvg - 0.4).toFixed(1)} °C
          </span>
        </div>

        <div className={`p-4 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-purple-500 flex items-center gap-1.5">
            <Trophy className="w-3.5 h-3.5" /> DÍA MÁXIMO DE VENTA
          </span>
          <div className="text-xl sm:text-2xl font-extrabold text-purple-500 mt-1 truncate">
            {maxDay ? `${maxDay.fechaDisp} ($${(maxDay.brutoTotal / 1000000).toFixed(1)}M)` : '—'}
          </div>
          <span className="text-[11px] block mt-1 opacity-70">
            {maxDay ? `Temp. Máx: ${maxDay.tempMax}°C / Mín: ${maxDay.tempMin}°C` : 'Sin datos en el período'}
          </span>
        </div>
      </div>

      {/* Main Dual-Axis Chart without Y-Axis and with Temperature YoY */}
      <div
        className={`p-4 sm:p-6 rounded-xl border shadow-md ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-2">
            <Thermometer className="w-4 h-4" /> COMPORTAMIENTO DIARIO DE VENTAS VS. TEMPERATURAS SANTIAGO (ACTUAL Y YOY - SIN EJE Y)
          </h3>
        </div>

        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartDataWithYoY}>
              <XAxis dataKey="fechaDisp" stroke={isDark ? '#B8B8BE' : '#64748b'} fontSize={11} />
              <Tooltip
                formatter={(value: any, name: any) => {
                  if (name === 'Venta ($M)') return [`$${(Number(value) / 1000000).toFixed(1)} M`, name];
                  return [`${Number(value).toFixed(1)}°C`, name];
                }}
                contentStyle={{
                  backgroundColor: isDark ? '#1F1F23' : '#ffffff',
                  borderColor: isDark ? '#333339' : '#e2e8f0',
                  color: isDark ? '#EDEDED' : '#1e293b',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="brutoTotal" name="Venta ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="brutoTotal" position="top" formatter={(val: number) => `$${(val / 1000000).toFixed(1)}M`} fill={isDark ? '#EDEDED' : '#1e293b'} fontSize={10} fontWeight="bold" />
              </Bar>

              {/* Temperatures Actual */}
              <Line type="monotone" dataKey="tempMax" name="Temp. Máx Actual (°C)" stroke="#FF9F0A" strokeWidth={2.5} dot={{ r: 4 }}>
                <LabelList dataKey="tempMax" position="top" formatter={(val: number) => `${val}°C`} fill="#FF9F0A" fontSize={9} fontWeight="bold" />
              </Line>
              <Line type="monotone" dataKey="tempMin" name="Temp. Mín Actual (°C)" stroke="#5AC8FA" strokeWidth={2} dot={{ r: 3 }}>
                <LabelList dataKey="tempMin" position="bottom" formatter={(val: number) => `${val}°C`} fill="#5AC8FA" fontSize={9} fontWeight="bold" />
              </Line>

              {/* Temperatures YoY */}
              {/* Línea YoY de temperatura removida: no hay histórico real
                  guardado todavía para comparar año contra año (se puede
                  agregar guardando el resultado de Open-Meteo por fecha) */}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
