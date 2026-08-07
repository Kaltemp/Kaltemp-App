import React from 'react';
import { ThemeMode } from '../types';

interface ComparisonRow {
  label: string;
  value: string;
  current: number;
  target: number;
  isPP?: boolean; // Percentage Points
}

interface KPICardProps {
  title: string;
  mainValue: string;
  colorValue?: string;
  sparklineSvg?: string;
  rows?: ComparisonRow[];
  theme: ThemeMode;
  className?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  mainValue,
  colorValue,
  sparklineSvg,
  rows = [],
  theme,
  className = ''
}) => {
  const isDark = theme === 'dark';

  const calculateDelta = (current: number, target: number, isPP: boolean = false) => {
    if (target === 0) return { pct: 0, text: '0.0%', isPositive: true };
    const diff = isPP ? current - target : ((current - target) / target) * 100;
    const isPositive = diff >= 0;
    const sign = isPositive ? '+' : '';
    const text = `${sign}${diff.toFixed(1)}${isPP ? ' pp' : '%'}`;
    return { pct: diff, text, isPositive };
  };

  return (
    <div
      className={`pbi-kpi-card p-3 sm:p-3.5 2xl:p-4 rounded-xl border transition-all flex flex-row items-center justify-between gap-2.5 sm:gap-3 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E] text-[#F5F5F7]' : 'bg-white border-slate-200/80 text-[#1D1D1F] shadow-sm'
      } ${className}`}
    >
      {/* Left Column: Title, Main Metric, Sparkline */}
      <div className="flex-1 min-w-0">
        <span className={`text-[10px] sm:text-[11px] font-bold uppercase tracking-wider block mb-0.5 truncate ${
          isDark ? 'text-[#8E8E93]' : 'text-slate-400'
        }`} title={title}>
          {title}
        </span>
        <div
          className="text-lg sm:text-2xl 2xl:text-3xl font-extrabold tracking-tight truncate leading-tight"
          style={{ color: colorValue || (isDark ? '#F5F5F7' : '#1D1D1F') }}
          title={mainValue}
        >
          {mainValue}
        </div>
        {sparklineSvg && (
          <div className="mt-1.5 opacity-90 max-w-[100px] sm:max-w-[110px]" dangerouslySetInnerHTML={{ __html: sparklineSvg }} />
        )}
      </div>

      {/* Right Column: Comparison Rows (WoW, YoY, 2YoY) */}
      {rows.length > 0 && (
        <div className={`pl-2.5 sm:pl-3 border-l flex flex-col justify-center gap-1 shrink-0 ${
          isDark ? 'border-[#2C2C2E]' : 'border-slate-200/80'
        }`}>
          {rows.map((row) => {
            const delta = calculateDelta(row.current, row.target, row.isPP);
            return (
              <div key={row.label} className="grid grid-cols-[28px_auto_auto] items-center gap-1 sm:gap-1.5 text-[10px] sm:text-[11px]">
                <span className={`font-semibold uppercase ${isDark ? 'text-[#8E8E93]' : 'text-slate-400'}`}>
                  {row.label}
                </span>
                <span className="font-bold text-right whitespace-nowrap">
                  {row.value}
                </span>
                <span className={`font-bold text-right whitespace-nowrap ${
                  delta.isPositive
                    ? isDark ? 'text-[#30D158]' : 'text-emerald-700'
                    : isDark ? 'text-[#FF453A]' : 'text-rose-700'
                }`}>
                  {delta.text}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
