// ============================================================
// ARCHIVO: KPICard.tsx
// RUTA: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\components\KPICard.tsx
// ============================================================

import React from 'react';
import { ThemeMode } from '../types';

export interface KPIRow {
  label: string;
  value: string;
  current?: number;
  target?: number;
  isPP?: boolean;
}

interface KPICardProps {
  title: string;
  mainValue: string;
  colorValue?: string;
  sparklineSvg?: string;
  rows?: KPIRow[];
  theme: ThemeMode;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  mainValue,
  colorValue = '#38BDF8',
  sparklineSvg,
  rows = [],
  theme,
}) => {
  const isDark = theme === 'dark';

  // Ajuste inteligente de tamaño de fuente según el largo del texto
  const getValueFontSize = (val: string) => {
    if (val.length > 10) return 'text-lg sm:text-xl';
    if (val.length > 7) return 'text-xl sm:text-[22px]';
    return 'text-2xl sm:text-[26px]';
  };

  return (
    <div
      className={`p-4 rounded-2xl border transition-all duration-300 hover:shadow-xl group h-full flex flex-col justify-between ${
        isDark
          ? 'bg-[#1C1C1E]/85 border-[#2C2C2E] text-white hover:border-[#48484A]'
          : 'bg-white border-slate-200 text-slate-900 hover:border-slate-300 shadow-sm'
      }`}
    >
      {/* Título de la Tarjeta (sin corte) */}
      <div className="mb-2">
        <h4 className="text-[10.5px] font-black uppercase tracking-wider text-slate-400 dark:text-zinc-400 whitespace-nowrap overflow-hidden text-ellipsis">
          {title}
        </h4>
      </div>

      {/* Cuerpo Principal: Monto + Sparkline a la izquierda | Filas WOW/YOY a la derecha */}
      <div className="grid grid-cols-12 gap-2 items-center">

        {/* Lado Izquierdo: Valor Principal y Mini Gráfico */}
        <div className="col-span-6 flex flex-col justify-center min-w-0 pr-1">
          <span
            className={`font-black tracking-tight leading-none whitespace-nowrap ${getValueFontSize(mainValue)}`}
            style={{ color: colorValue }}
            title={mainValue}
          >
            {mainValue}
          </span>

          {/* Sparkline */}
          {sparklineSvg && (
            <div
              className="mt-2 w-full max-w-[110px] h-7 overflow-visible opacity-90 group-hover:opacity-100 transition-opacity"
              dangerouslySetInnerHTML={{ __html: sparklineSvg }}
            />
          )}
        </div>

        {/* Lado Derecho: Comparativas WOW / YOY / 2YOY */}
        {rows.length > 0 && (
          <div className="col-span-6 border-l border-zinc-200 dark:border-white/10 pl-2.5 space-y-1">
            {rows.map((r, i) => {
              let diffPct = 0;
              let isPos = false;

              if (r.isPP) {
                const cur = Number(String(r.current || '').replace('%', ''));
                const tgt = Number(String(r.target || '').replace('%', ''));
                diffPct = cur - tgt;
                isPos = diffPct >= 0;
              } else if (r.current !== undefined && r.target !== undefined && r.target > 0) {
                diffPct = ((r.current - r.target) / r.target) * 100;
                isPos = diffPct >= 0;
              }

              const diffText = r.isPP
                ? `${isPos ? '+' : ''}${diffPct.toFixed(1)} pp`
                : `${isPos ? '+' : ''}${diffPct.toFixed(1)}%`;

              return (
                <div key={i} className="flex items-center justify-between text-[10.5px] leading-tight">
                  <span className="font-bold text-zinc-500 dark:text-zinc-400 text-[10px] shrink-0">
                  {r.label}
                  </span>

                <div className="flex items-center gap-1.5 shrink-0 ml-auto">
                  <span className="font-bold text-zinc-500 dark:text-zinc-400 font-mono text-[10.5px]">
                    {r.value}
                  </span>

                    <span
                      className={`font-black text-[9.5px] font-mono ${
                        isPos
                          ? isDark ? 'text-emerald-400' : 'text-emerald-600'
                          : isDark ? 'text-rose-400' : 'text-rose-600'
                      }`}
                    >
                      {diffText}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
};