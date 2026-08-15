import React, { useState, useMemo, useEffect } from 'react';
import { KPICard } from '../components/KPICard';
import { ThemeMode, BrandMode} from '../types';
import { getBrandTokens } from '../theme/brandTokens';
import { ChannelSale } from '../types';
import { fetchChannels, fetchTendenciaMensual, fetchAcumuladoYtd } from '../services/api';
import { useGlobalFilter, ALL_REPS, ALL_CATEGORIES, ALL_CHANNELS } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import {
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
  brandMode: BrandMode;
}

const CustomMonthlyTooltip = ({ active, payload, label, theme }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload || {};
    const isDark = theme === 'dark';

    const cardBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E] text-[#F5F5F7]" : "bg-white border-slate-200 text-slate-900";
    const headerText = isDark ? "text-white" : "text-slate-900";
    const cyText = isDark ? "text-blue-400" : "text-blue-700";
    const yoyText = isDark ? "text-emerald-400" : "text-emerald-700";

    return (
      <div className={`p-3.5 rounded-2xl border shadow-2xl text-xs space-y-2 min-w-[170px] ${cardBg}`}>
        <p className={`font-extrabold border-b pb-1.5 border-slate-200 dark:border-[#2C2C2E] text-sm ${headerText}`}>
          {label}
        </p>
        <div className="flex items-center justify-between gap-3">
          <span className={`flex items-center gap-1.5 font-bold ${cyText}`}>
            <span className="w-2.5 h-2.5 rounded-full bg-[#0A84FF]" />
            Año Actual:
          </span>
          <span className={`font-extrabold ${cyText}`}>
            ${(data.cy || 0).toFixed(1)} M
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-1.5 font-bold text-slate-500 dark:text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-400 dark:bg-[#545458]" />
            Año Anterior:
          </span>
          <span className="font-bold text-slate-700 dark:text-slate-300">${(data.ly || 0).toFixed(1)} M</span>
        </div>
        {data.cy > 0 && data.yoy !== null && data.yoy !== undefined && (
          <div className="flex items-center justify-between gap-3 pt-1.5 border-t border-slate-200 dark:border-[#2C2C2E]">
            <span className={`flex items-center gap-1.5 font-bold ${yoyText}`}>
              <span className="w-2.5 h-2.5 rounded-full bg-[#30D158]" />
              VAR YoY%:
            </span>
            <span className={`font-black ${yoyText}`}>
              {data.yoy >= 0 ? '+' : ''}{data.yoy}%
            </span>
          </div>
        )}
      </div>
    );
  }
  return null;
};

// Componente inteligente para posicionar las etiquetas de la línea verde
const CustomLineLabel = (props: any) => {
  const { x, y, index, data, theme } = props;
  const item = (data && data[index]) ? data[index] : (props.payload || {});

  // Si no hay año actual o cy <= 0 (meses futuros), NO mostrar etiqueta
  if (!item || !item.cy || item.cy <= 0) {
    return null;
  }

  const yoyVal = item.yoy;
  if (yoyVal === undefined || yoyVal === null) return null;

  const isPositive = yoyVal >= 0;
  const isDark = theme === 'dark';

  const fillColor = isPositive
    ? (isDark ? '#30D158' : '#15803D')
    : (isDark ? '#FF453A' : '#DC2626');

  const textLabel = `${isPositive ? '+' : ''}${Number(yoyVal).toFixed(1)}%`;

  // Si el punto del pico está muy pegado arriba (y < 22), se dibuja justo debajo del punto
  const labelY = y < 22 ? y + 18 : y - 10;

  return (
    <text
      x={x}
      y={labelY}
      fill={fillColor}
      textAnchor="middle"
      fontSize={12}
      fontWeight="900"
    >
      {textLabel}
    </text>
  );
};

export const MainExecutiveView: React.FC<Props> = ({ theme, brandMode }) => {
  const isDark = theme === 'dark';
  const brandTokens = getBrandTokens(brandMode, isDark);
  const {
    selectedChannels,
    matchesChannel,
    selectedReps,
    selectedCategories,
    startDate,
    endDate,
  } = useGlobalFilter();

  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string>('totalBruto');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const [CHANNELS_DATA_RAW, setChannelsData] = useState<ChannelSale[]>([]);

  const vendedoresParaBackend = selectedReps.length < ALL_REPS.length ? selectedReps : undefined;
  const categoriasParaBackend = selectedCategories.length < ALL_CATEGORIES.length ? selectedCategories : undefined;
  const canalesBaseGlobal = selectedChannels.length < ALL_CHANNELS.length ? selectedChannels : undefined;
  const canalesParaBackend = selectedChannel ? [selectedChannel] : canalesBaseGlobal;

  const [MONTHS_DATA, setMonthsData] = useState<{ month: string; cy: number; ly: number; yoy: number }[]>([]);
  const [ytd, setYtd] = useState<{ actual: number; yoy: number; proyeccion: number; yoyPct: number } | null>(null);

  useEffect(() => {
    fetchChannels(startDate, endDate, vendedoresParaBackend, categoriasParaBackend)
      .then((data) => setChannelsData(Array.isArray(data) ? data : []))
      .catch((err) => {
        console.error(err);
        setChannelsData([]);
      });

    fetchTendenciaMensual(endDate, vendedoresParaBackend, categoriasParaBackend, canalesParaBackend)
      .then((res) => setMonthsData(Array.isArray(res) ? res : []))
      .catch(() => setMonthsData([]));

    fetchAcumuladoYtd(endDate, vendedoresParaBackend, categoriasParaBackend, canalesParaBackend)
      .then((res) => setYtd(res && typeof res === 'object' ? res : null))
      .catch(() => setYtd(null));
  }, [
    startDate,
    endDate,
    JSON.stringify(vendedoresParaBackend),
    JSON.stringify(categoriasParaBackend),
    JSON.stringify(canalesParaBackend),
  ]);

  const processedMonthsData = useMemo(() => {
    return (MONTHS_DATA || []).map((m) => {
      const hasCy = m && typeof m.cy === 'number' && m.cy > 0;
      return {
        ...m,
        yoy: hasCy ? m.yoy : null
      };
    });
  }, [MONTHS_DATA]);

  const rawChannelsList = useMemo(() => (Array.isArray(CHANNELS_DATA_RAW) ? CHANNELS_DATA_RAW : []), [CHANNELS_DATA_RAW]);

  const CHANNELS_DATA = useMemo(
    () => rawChannelsList.filter(
      (ch) => ch && matchesChannel(ch.canal) && (!selectedChannel || ch.canal === selectedChannel)
    ),
    [rawChannelsList, selectedChannels, selectedChannel, matchesChannel]
  );

  const strokeContriColor = isDark ? '#EDEDED' : '#1D1D1F';

  const sparkVenta = '<svg width="110" height="32" viewBox="0 0 110 32"><polygon points="3.0,32 3.0,22.0 12.7,20.0 22.5,17.0 32.2,14.0 41.9,8.0 51.6,4.0 61.4,3.0 71.1,6.0 80.8,12.0 90.5,16.0 100.2,18.0 107.0,15.0 107.0,32" fill="#0A84FF" opacity="0.15"/><polyline points="3.0,22.0 12.7,20.0 22.5,17.0 32.2,14.0 41.9,8.0 51.6,4.0 61.4,6.0 80.8,12.0 90.5,16.0 100.2,18.0 107.0,15.0" fill="none" stroke="#0A84FF" stroke-width="2.5" stroke-linejoin="round"/><circle cx="107.0" cy="15.0" r="3" fill="#0A84FF"/></svg>';
  const sparkContri = `<svg width="110" height="32" viewBox="0 0 110 32"><polygon points="3.0,32 3.0,24.0 12.7,22.0 22.5,18.0 32.2,15.0 41.9,9.0 51.6,5.0 61.4,4.0 71.1,7.0 80.8,13.0 90.5,17.0 100.2,19.0 107.0,16.0 107.0,32" fill="${strokeContriColor}" opacity="0.15"/><polyline points="3.0,24.0 12.7,22.0 22.5,18.0 32.2,15.0 41.9,9.0 51.6,5.0 61.4,4.0 71.1,7.0 80.8,13.0 90.5,17.0 100.2,19.0 107.0,16.0" fill="none" stroke="${strokeContriColor}" stroke-width="2.5" stroke-linejoin="round"/><circle cx="107.0" cy="16.0" r="3" fill="${strokeContriColor}"/></svg>`;
  const sparkMargen = '<svg width="110" height="32" viewBox="0 0 110 32"><polygon points="3.0,32 3.0,10.0 12.7,11.0 22.5,9.0 32.2,8.0 41.9,6.0 51.6,4.0 61.4,5.0 71.1,7.0 80.8,8.0 90.5,9.0 100.2,10.0 107.0,8.0 107.0,32" fill="#30D158" opacity="0.15"/><polyline points="3.0,10.0 12.7,11.0 22.5,9.0 32.2,8.0 41.9,6.0 51.6,4.0 61.4,5.0 71.1,7.0 80.8,8.0 90.5,9.0 100.2,10.0 107.0,8.0" fill="none" stroke="#30D158" stroke-width="2.5" stroke-linejoin="round"/><circle cx="107.0" cy="8.0" r="3" fill="#30D158"/></svg>';
  const sparkTkp = '<svg width="110" height="32" viewBox="0 0 110 32"><polygon points="3.0,32 3.0,26.0 12.7,23.0 22.5,20.0 32.2,17.0 41.9,13.0 51.6,10.0 61.4,7.0 71.1,9.0 80.8,12.0 90.5,8.0 100.2,5.0 107.0,4.0 107.0,32" fill="#FF9F0A" opacity="0.15"/><polyline points="3.0,26.0 12.7,23.0 22.5,20.0 32.2,17.0 41.9,13.0 51.6,10.0 61.4,7.0 71.1,9.0 80.8,12.0 90.5,8.0 100.2,5.0 107.0,4.0" fill="none" stroke="#FF9F0A" stroke-width="2.5" stroke-linejoin="round"/><circle cx="107.0" cy="4.0" r="3" fill="#FF9F0A"/></svg>';

  // Totales
  const totalBruto = CHANNELS_DATA.reduce((acc, c) => acc + (c.totalBruto || 0), 0);
  const totalContri = CHANNELS_DATA.reduce((acc, c) => acc + (c.contribucion || 0), 0);
  const totalNeto = CHANNELS_DATA.reduce((acc, c) => acc + (c.neto || 0), 0);
  const totalTxs = CHANNELS_DATA.reduce((acc, c) => acc + (c.txs || 0), 0);
  const totalBsale = CHANNELS_DATA.reduce((acc, c) => acc + (c.bsale || 0), 0);
  const totalFull = CHANNELS_DATA.reduce((acc, c) => acc + (c.full || 0), 0);
  const totalWow = CHANNELS_DATA.reduce((acc, c) => acc + (c.wow || 0), 0);
  const totalYoy = CHANNELS_DATA.reduce((acc, c) => acc + (c.yoy || 0), 0);
  const total2Yoy = CHANNELS_DATA.reduce((acc, c) => acc + (c.twoYoy || 0), 0);

  const totalMargen = totalNeto ? (totalContri / totalNeto) * 100 : 0;
  const totalTkp = totalTxs ? totalBruto / totalTxs : 0;

  const totalWowPct = totalWow ? ((totalBruto - totalWow) / totalWow) * 100 : 0;
  const totalYoyPct = totalYoy ? ((totalBruto - totalYoy) / totalYoy) * 100 : 0;
  const total2YoyPct = total2Yoy ? ((totalBruto - total2Yoy) / total2Yoy) * 100 : 0;

  // Históricos para tarjetas
  const totalContriWow = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.contribucionWow || 0), 0);
  const totalContriYoy = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.contribucionYoy || 0), 0);
  const totalContri2Yoy = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.contribucionTwoYoy || 0), 0);
  const totalNetoWow = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.netoWow || 0), 0);
  const totalNetoYoy = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.netoYoy || 0), 0);
  const totalNeto2Yoy = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.netoTwoYoy || 0), 0);
  const totalTxsWow = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.txsWow || 0), 0);
  const totalTxsYoy = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.txsYoy || 0), 0);
  const totalTxs2Yoy = CHANNELS_DATA.reduce((acc, c: any) => acc + (c.txsTwoYoy || 0), 0);

  const totalMargenWow = totalNetoWow ? (totalContriWow / totalNetoWow) * 100 : 0;
  const totalMargenYoy = totalNetoYoy ? (totalContriYoy / totalNetoYoy) * 100 : 0;
  const totalMargen2Yoy = totalNeto2Yoy ? (totalContri2Yoy / totalNeto2Yoy) * 100 : 0;
  const totalTkpWow = totalTxsWow ? totalWow / totalTxsWow : 0;
  const totalTkpYoy = totalTxsYoy ? totalYoy / totalTxsYoy : 0;
  const totalTkp2Yoy = totalTxs2Yoy ? total2Yoy / totalTxs2Yoy : 0;

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sortedChannels = useMemo(() => {
    return [...CHANNELS_DATA].sort((a: any, b: any) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];
      if (aVal === undefined || aVal === null) aVal = '';
      if (bVal === undefined || bVal === null) bVal = '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [sortKey, sortDir, CHANNELS_DATA]);

  const handleRowClick = (canalName: string) => {
    if (selectedChannel === canalName) {
      setSelectedChannel(null);
    } else {
      setSelectedChannel(canalName);
    }
  };

  const formatM = (val: number) => `$${((val || 0) / 1000000).toFixed(1)} M`;
  const formatClp = (val: number) => `$${Math.round(val || 0).toLocaleString('es-CL')}`;

  const yoyPctFormatted = (ytd && typeof ytd.yoyPct === 'number' && !isNaN(ytd.yoyPct))
    ? `${ytd.yoyPct >= 0 ? '+' : ''}${ytd.yoyPct.toFixed(1)}% YTD YoY`
    : '—';

  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleColor = isDark ? "text-blue-400" : "text-blue-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {/* Hero KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard
          title="VENTA TOTAL (BRUTO)"
          mainValue={formatM(totalBruto)}
          colorValue={brandTokens.accent}
          sparklineSvg={sparkVenta}
          theme={theme}
          rows={[
            { label: 'WOW', value: formatM(totalWow), current: totalBruto, target: totalWow },
            { label: 'YOY', value: formatM(totalYoy), current: totalBruto, target: totalYoy },
            { label: '2YOY', value: formatM(total2Yoy), current: totalBruto, target: total2Yoy }
          ]}
        />

        <KPICard
          title="CONTRIBUCIÓN ($)"
          mainValue={formatM(totalContri)}
          colorValue={isDark ? '#F5F5F7' : '#0F172A'}
          sparklineSvg={sparkContri}
          theme={theme}
          rows={[
            { label: 'WOW', value: formatM(totalContriWow), current: totalContri, target: totalContriWow },
            { label: 'YOY', value: formatM(totalContriYoy), current: totalContri, target: totalContriYoy },
            { label: '2YOY', value: formatM(totalContri2Yoy), current: totalContri2Yoy, target: totalContri2Yoy }
          ]}
        />

        <KPICard
          title="MARGEN FRONTAL (%)"
          mainValue={`${totalMargen.toFixed(1)}%`}
          colorValue={isDark ? '#30D158' : '#15803D'}
          sparklineSvg={sparkMargen}
          theme={theme}
          rows={[
            { label: 'WOW', value: `${totalMargenWow.toFixed(1)}%`, current: totalMargen, target: totalMargenWow },
            { label: 'YOY', value: `${totalMargenYoy.toFixed(1)}%`, current: totalMargen, target: totalMargenYoy },
            { label: '2YOY', value: `${totalMargen2Yoy.toFixed(1)}%`, current: totalMargen, target: totalMargen2Yoy }
          ]}
        />

        <KPICard
          title="TICKET PROMEDIO (TKP)"
          mainValue={formatClp(totalTkp)}
          colorValue={isDark ? '#FF9F0A' : '#B45309'}
          sparklineSvg={sparkTkp}
          theme={theme}
          rows={[
            { label: 'WOW', value: formatClp(totalTkpWow), current: totalTkp, target: totalTkpWow },
            { label: 'YOY', value: formatClp(totalTkpYoy), current: totalTkp, target: totalTkpYoy },
            { label: '2YOY', value: formatClp(totalTkp2Yoy), current: totalTkp, target: totalTkp2Yoy }
          ]}
        />
      </div>

      {/* Matriz de Canales */}
      <div className={`p-5 rounded-2xl border overflow-x-auto ${panelBg}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={`text-xs font-black uppercase tracking-wider ${titleColor}`}>
            📊 MATRIZ DE CANALES CON DESGLOSE Y SHARE
          </h3>
          <span className={`text-[11px] font-medium ${subtextColor}`}>
            Haz clic en un canal para filtro cruzado | Clic en encabezado para ordenar
          </span>
        </div>

        <table className="w-full text-left text-xs border-collapse min-w-[1200px]">
          <thead>
            <tr className={`border-b text-[11px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
              <SortableTh label="CANAL" sortKey="canal" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
              <SortableTh label="BSALE" sortKey="bsale" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="FULL" sortKey="full" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="TOTAL" sortKey="totalBruto" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={isDark ? 'text-blue-400 font-black' : 'text-blue-700 font-black'} />
              <SortableTh label="CONTRIBUCIÓN" sortKey="contribucion" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="TKP" sortKey="tkp" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="WOW $" sortKey="wow" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className="opacity-70" />
              <SortableTh label="WOW %" sortKey="wowPct" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="YOY $" sortKey="yoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className="opacity-70" />
              <SortableTh label="YOY %" sortKey="yoyPct" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="2YOY $" sortKey="twoYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className="opacity-70" />
              <SortableTh label="2YOY %" sortKey="twoYoyPct" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="MARGEN %" sortKey="margenFrontal" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="SHARE %" sortKey="share" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-[#2C2C2E] font-medium">
            {sortedChannels.length === 0 ? (
              <tr>
                <td colSpan={14} className="p-4 text-center text-slate-400 italic">
                  Sin datos de canales para esta selección
                </td>
              </tr>
            ) : (
              sortedChannels.map((ch) => {
                const isSelected = selectedChannel === ch.canal;
                const wowPct = ch.wowPct || 0;
                const yoyPct = ch.yoyPct || 0;
                const twoYoyPct = ch.twoYoyPct || 0;
                const margenFrontal = ch.margenFrontal || 0;
                const share = ch.share || 0;

                const rowHighlight = isSelected
                  ? (isDark ? 'bg-blue-600/30 font-bold border-l-4 border-l-blue-400' : 'bg-blue-50 font-bold border-l-4 border-l-blue-600')
                  : (isDark ? 'hover:bg-[#2C2C2E] text-[#F5F5F7]' : 'hover:bg-slate-50 text-slate-800');

                return (
                  <tr
                    key={ch.canal}
                    onClick={() => handleRowClick(ch.canal)}
                    className={`cursor-pointer transition-colors ${rowHighlight}`}
                  >
                    <td className="p-2.5 font-bold flex items-center gap-1.5">
                      {isSelected && <span className="w-2 h-2 rounded-full bg-blue-500" />}
                      {ch.canal}
                    </td>
                    <td className="p-2.5 text-right">{formatM(ch.bsale)}</td>
                    <td className="p-2.5 text-right">{formatM(ch.full)}</td>
                    <td className={`p-2.5 text-right font-black ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>{formatM(ch.totalBruto)}</td>
                    <td className="p-2.5 text-right">{formatM(ch.contribucion)}</td>
                    <td className="p-2.5 text-right">${Math.round(ch.tkp || 0).toLocaleString('es-CL')}</td>
                    <td className="p-2.5 text-right opacity-70">{formatM(ch.wow || 0)}</td>
                    <td className={`p-2.5 text-right font-black ${wowPct >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-700') : (isDark ? 'text-red-400' : 'text-red-700')}`}>
                      {wowPct >= 0 ? '+' : ''}{wowPct.toFixed(1)}%
                    </td>
                    <td className="p-2.5 text-right opacity-70">{formatM(ch.yoy || 0)}</td>
                    <td className={`p-2.5 text-right font-black ${yoyPct >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-700') : (isDark ? 'text-red-400' : 'text-red-700')}`}>
                      {yoyPct >= 0 ? '+' : ''}{yoyPct.toFixed(1)}%
                    </td>
                    <td className="p-2.5 text-right opacity-70">{formatM(ch.twoYoy || 0)}</td>
                    <td className={`p-2.5 text-right font-black ${twoYoyPct >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-700') : (isDark ? 'text-red-400' : 'text-red-700')}`}>
                      {twoYoyPct >= 0 ? '+' : ''}{twoYoyPct.toFixed(1)}%
                    </td>
                    <td className="p-2.5 text-right font-bold">
                      <div className="flex items-center justify-end gap-1.5">
                        <span>{margenFrontal.toFixed(1)}%</span>
                        <div className={`w-12 h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-200'}`}>
                          <div
                            className="h-full bg-emerald-500 rounded-full"
                            style={{ width: `${Math.min(100, margenFrontal)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-2.5 text-right font-bold">
                      <div className="flex items-center justify-end gap-1.5">
                        <span>{share.toFixed(1)}%</span>
                        <div className={`w-12 h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-200'}`}>
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${Math.min(100, share * 3)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
          <tfoot>
            <tr className={`border-t-2 font-black text-xs ${
              isDark ? 'border-[#2C2C2E] bg-[#121214] text-[#F5F5F7]' : 'border-slate-300 bg-slate-100 text-slate-900'
            }`}>
              <td className="p-2.5">TOTAL</td>
              <td className="p-2.5 text-right">{formatM(totalBsale)}</td>
              <td className="p-2.5 text-right">{formatM(totalFull)}</td>
              <td className={`p-2.5 text-right ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>{formatM(totalBruto)}</td>
              <td className="p-2.5 text-right">{formatM(totalContri)}</td>
              <td className="p-2.5 text-right">${Math.round(totalTkp).toLocaleString('es-CL')}</td>
              <td className="p-2.5 text-right opacity-70">{formatM(totalWow)}</td>
              <td className={`p-2.5 text-right ${totalWowPct >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-700') : (isDark ? 'text-red-400' : 'text-red-700')}`}>
                {totalWowPct >= 0 ? '+' : ''}{totalWowPct.toFixed(1)}%
              </td>
              <td className="p-2.5 text-right opacity-70">{formatM(totalYoy)}</td>
              <td className={`p-2.5 text-right ${totalYoyPct >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-700') : (isDark ? 'text-red-400' : 'text-red-700')}`}>
                {totalYoyPct >= 0 ? '+' : ''}{totalYoyPct.toFixed(1)}%
              </td>
              <td className="p-2.5 text-right opacity-70">{formatM(total2Yoy)}</td>
              <td className={`p-2.5 text-right ${total2YoyPct >= 0 ? (isDark ? 'text-emerald-400' : 'text-emerald-700') : (isDark ? 'text-red-400' : 'text-red-700')}`}>
                {total2YoyPct >= 0 ? '+' : ''}{total2YoyPct.toFixed(1)}%
              </td>
              <td className={`p-2.5 text-right ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>{totalMargen.toFixed(1)}%</td>
              <td className="p-2.5 text-right">100.0%</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Tendencia Mensual */}
        <div className={`lg:col-span-3 p-5 rounded-2xl border ${panelBg}`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={`text-xs font-black uppercase tracking-wider ${titleColor}`}>
              📈 TENDENCIA MENSUAL - VENTA BRUTA ($ M) VS YOY %
            </h3>
            <span className={`text-xs font-extrabold ${
              isDark ? 'text-emerald-400' : 'text-emerald-700'
            }`}>
              {yoyPctFormatted}
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={processedMonthsData} margin={{ top: 28, right: 15, left: 15, bottom: 5 }}>
                <XAxis dataKey="month" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={11} tickLine={false} />
                <YAxis yAxisId="left" hide />
                <YAxis yAxisId="right" hide domain={['dataMin - 15', 'dataMax + 25']} />
                <Tooltip content={<CustomMonthlyTooltip theme={theme} />} />
                <Bar yAxisId="left" dataKey="ly" name="Año Anterior" fill={isDark ? '#2C2C2E' : '#cbd5e1'} radius={[4, 4, 0, 0]} />
                <Bar yAxisId="left" dataKey="cy" name="Año Actual" fill="#0A84FF" radius={[4, 4, 0, 0]} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="yoy"
                  name="VAR YoY%"
                  stroke="#30D158"
                  strokeWidth={2.5}
                  connectNulls={false}
                  dot={(dotProps: any) => {
                    const { cx, cy, payload } = dotProps;
                    if (!payload || !payload.cy || payload.cy <= 0) return <React.Fragment key={dotProps.index} />;
                    return <circle key={dotProps.index} cx={cx} cy={cy} r={4.5} fill="#30D158" />;
                  }}
                >
                  <LabelList
                    dataKey="yoy"
                    content={<CustomLineLabel theme={theme} data={processedMonthsData} />}
                  />
                </Line>
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Acumulado YTD */}
        <div className={`p-5 rounded-2xl border flex flex-col justify-between ${panelBg}`}>
          <div>
            <h3 className={`text-xs font-black uppercase tracking-wider mb-1 ${titleColor}`}>
              🎯 ACUMULADO YTD
            </h3>
            <p className={`text-xs font-medium ${subtextColor}`}>
              Venta acumulada Ene-{new Date(endDate).toLocaleDateString('es-CL', { month: 'short' })}
            </p>
          </div>

          <div className="space-y-3.5 my-4">
            {(ytd
              ? [
                  { name: 'Actual', value: ytd.actual || 0, color: '#0A84FF' },
                  { name: 'YoY', value: ytd.yoy || 0, color: isDark ? '#8E8E93' : '#64748b' },
                  { name: 'Proy. (est.)', value: ytd.proyeccion || 0, color: '#30D158' }
                ]
              : []
            ).map((item) => (
              <div key={item.name} className="space-y-1">
                <div className="flex items-center justify-between text-xs font-bold">
                  <span className={isDark ? 'text-[#F5F5F7]' : 'text-slate-800'}>{item.name}</span>
                  <span className="font-extrabold">${(item.value || 0).toFixed(1)} M</span>
                </div>
                <div className={`w-full h-2 rounded-full overflow-hidden ${isDark ? 'bg-[#2C2C2E]' : 'bg-slate-200'}`}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${ytd ? (item.value / Math.max(ytd.actual || 1, ytd.yoy || 1, ytd.proyeccion || 1, 1)) * 100 : 0}%`,
                      backgroundColor: item.color
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className={`p-3 rounded-xl border text-xs text-center font-bold ${
            isDark ? 'bg-[#121214] border-[#2C2C2E] text-emerald-400' : 'bg-emerald-50 border-emerald-200 text-emerald-800'
          }`}>
            Proyección Cierre {new Date(endDate).getFullYear()} (est.): <strong>${ytd ? (ytd.proyeccion || 0).toFixed(1) : '—'} M</strong>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainExecutiveView;