import React, { useState, useMemo, useEffect } from 'react';
import { DailyTempSale, ThemeMode, BrandMode} from '../types';
import { getBrandTokens } from '../theme/brandTokens';
import { Thermometer, Flame, Trophy } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchVentasTemperatura } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LabelList
} from 'recharts';

interface ExtendedDailyTempSale extends DailyTempSale {
  tempMaxYoY?: number;
  tempMinYoY?: number;
}

interface Props {
  theme: ThemeMode;
  brandMode: BrandMode;
}

export const TemperatureSalesView: React.FC<Props> = ({ theme, brandMode }) => {
  const isDark = theme === 'dark';
  const brandTokens = getBrandTokens(brandMode, isDark);
  const { startDate, endDate } = useGlobalFilter();

  const [DAILY_TEMP_SALES, setDailyTempSales] = useState<ExtendedDailyTempSale[]>([]);
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

  const totalVenta = DAILY_TEMP_SALES.reduce((acc, d) => acc + d.brutoTotal, 0);

  const tempMaxAvg = DAILY_TEMP_SALES.length
    ? DAILY_TEMP_SALES.reduce((acc, d) => acc + d.tempMax, 0) / DAILY_TEMP_SALES.length
    : 0;

  const tempMaxAvgYoY = DAILY_TEMP_SALES.length
    ? DAILY_TEMP_SALES.reduce((acc, d) => acc + (d.tempMaxYoY ?? 0), 0) / DAILY_TEMP_SALES.length
    : 0;

  const tempMinAvg = DAILY_TEMP_SALES.length
    ? DAILY_TEMP_SALES.reduce((acc, d) => acc + d.tempMin, 0) / DAILY_TEMP_SALES.length
    : 0;

  const tempMinAvgYoY = DAILY_TEMP_SALES.length
    ? DAILY_TEMP_SALES.reduce((acc, d) => acc + (d.tempMinYoY ?? 0), 0) / DAILY_TEMP_SALES.length
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
          <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: brandTokens.accent }}>
            VENTA TOTAL PERIODO
          </span>
          <div className="text-2xl sm:text-3xl font-extrabold mt-1" style={{ color: brandTokens.accent }}>
            ${(totalVenta / 1000000).toFixed(2)} M CLP
          </div>
          <span className="text-[11px] block mt-1 opacity-70">
            Venta acumulada del período
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
            YoY Promedio: {tempMaxAvgYoY.toFixed(1)} °C
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
            YoY Promedio: {tempMinAvgYoY.toFixed(1)} °C
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

        <div className="h-[480px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={DAILY_TEMP_SALES} margin={{ top: 25, right: 15, left: 15, bottom: 10 }}>
              <XAxis dataKey="fechaDisp" stroke={isDark ? '#B8B8BE' : '#64748b'} fontSize={12} fontWeight="bold" />

              {/* Eje Y1 Oculto para Ventas ($ Millions) */}
              <YAxis yAxisId="left" hide={true} />

              {/* Eje Y2 Oculto para Temperaturas (°C) */}
              <YAxis
                yAxisId="right"
                hide={true}
                domain={[(dataMin: number) => Math.floor(dataMin - 3), (dataMax: number) => Math.ceil(dataMax + 5)]}
              />

              <Tooltip
                formatter={(value: any, name: any) => {
                  if (name === 'Venta ($M)') return [`$${(Number(value) / 1000000).toFixed(1)} M`, name];
                  return [`${Number(value).toFixed(1)} °C`, name];
                }}
                contentStyle={{
                  backgroundColor: isDark ? '#1F1F23' : '#ffffff',
                  borderColor: isDark ? '#333339' : '#e2e8f0',
                  color: isDark ? '#EDEDED' : '#1e293b',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}
              />

              <Legend
                verticalAlign="top"
                height={36}
                wrapperStyle={{ fontSize: '12px', fontWeight: 'bold', paddingBottom: '10px' }}
              />

              {/* Barras de Ventas */}
              <Bar yAxisId="left" dataKey="brutoTotal" name="Venta ($M)" fill="#0A84FF" radius={[4, 4, 0, 0]}>
                <LabelList
                  dataKey="brutoTotal"
                  position="top"
                  offset={10}
                  formatter={(val: number) => `$${(val / 1000000).toFixed(1)}M`}
                  fill={isDark ? '#EDEDED' : '#0F172A'}
                  fontSize={12}
                  fontWeight="bold"
                />
              </Bar>

              {/* Temperaturas Actuales (Líneas Sólidas con etiquetas más grandes) */}
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="tempMax"
                name="Temp. Máx Actual (°C)"
                stroke="#FF9F0A"
                strokeWidth={2.8}
                dot={{ r: 4.5 }}
              >
                <LabelList
                  dataKey="tempMax"
                  position="top"
                  offset={10}
                  formatter={(val: number) => `${val}°C`}
                  fill="#D97706"
                  fontSize={11}
                  fontWeight="bold"
                />
              </Line>

              <Line
                yAxisId="right"
                type="monotone"
                dataKey="tempMin"
                name="Temp. Mín Actual (°C)"
                stroke="#5AC8FA"
                strokeWidth={2.2}
                dot={{ r: 4 }}
              >
                <LabelList
                  dataKey="tempMin"
                  position="bottom"
                  offset={10}
                  formatter={(val: number) => `${val}°C`}
                  fill="#0284C7"
                  fontSize={11}
                  fontWeight="bold"
                />
              </Line>

              {/* Temperaturas YoY Año Anterior (Líneas Punteadas) */}
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="tempMaxYoY"
                name="Temp. Máx YoY (°C)"
                stroke="#D97706"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 3 }}
              />

              <Line
                yAxisId="right"
                type="monotone"
                dataKey="tempMinYoY"
                name="Temp. Mín YoY (°C)"
                stroke="#0284C7"
                strokeWidth={1.8}
                strokeDasharray="4 4"
                dot={{ r: 3 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};