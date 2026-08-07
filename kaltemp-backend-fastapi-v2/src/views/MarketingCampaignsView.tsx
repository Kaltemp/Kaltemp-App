import React, { useState, useEffect, useMemo } from 'react';
import { ThemeMode } from '../types';
import { 
  Megaphone, 
  Layers, 
  Facebook, 
  Search, 
  Image as ImageIcon, 
  Eye, 
  X,
  TrendingUp,
  DollarSign,
  Target,
  Sparkles,
  RefreshCw,
  BarChart3
} from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import { fetchMarketingCampaigns } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Line,
  CartesianGrid,
  LabelList
} from 'recharts';

interface Props {
  theme: ThemeMode;
}

export const MarketingCampaignsView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { selectedChannel, startDate, endDate } = useGlobalFilter();

  const [sortKey, setSortKey] = useState<string>('gastoCy');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [platformFilter, setPlatformFilter] = useState<string>('ALL');
  const [marcaFilter, setMarcaFilter] = useState<string>('ALL');

  const [previewAd, setPreviewAd] = useState<{ name: string; url: string; platform: string } | null>(null);

  const [CAMPAIGNS_DATA, setCampaignsData] = useState<any[]>([]);
  const [loadingCampaigns, setLoadingCampaigns] = useState(true);

  useEffect(() => {
    setLoadingCampaigns(true);
    fetchMarketingCampaigns(startDate, endDate, marcaFilter === 'ALL' ? undefined : marcaFilter)
      .then((data: any[]) => setCampaignsData(Array.isArray(data) ? data : []))
      .catch((err) => {
        console.error("Error al cargar campañas:", err);
        setCampaignsData([]);
      })
      .finally(() => setLoadingCampaigns(false));
  }, [startDate, endDate, marcaFilter]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const getCampanaName = (c: any) => c.campana || c.nombre || c.name || c.campaign_name || 'Sin Nombre';
  const getPlataforma = (c: any) => c.plataforma || c.platform || c.origen || 'Meta';
  const getGasto = (c: any) => c.gastoCy ?? c.gasto ?? c.inversion ?? c.cost ?? 0;
  const getClics = (c: any) => c.clicsCy ?? c.clics ?? c.clicks ?? 0;
  const getImpresiones = (c: any) => c.impresionesCy ?? c.impresiones ?? c.impressions ?? 0;
  const getCtr = (c: any) => c.ctrCy ?? c.ctr ?? (getImpresiones(c) > 0 ? (getClics(c) / getImpresiones(c)) * 100 : 0);
  const getRoas = (c: any) => c.roasCy ?? c.roas ?? 0;

  // Formateador sin decimales para pesos ($)
  const fmtMoney = (val: number) => `$${Math.round(val).toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;

  const filteredCampaigns = useMemo(() => {
    let list = CAMPAIGNS_DATA;

    if (selectedChannel && typeof selectedChannel === 'string' && selectedChannel.trim() !== '') {
      const channelLower = selectedChannel.toLowerCase();
      if (!channelLower.includes('todos') && !channelLower.includes('all')) {
        const matchesAny = list.some(c => 
          getPlataforma(c).toLowerCase().includes(channelLower) ||
          getCampanaName(c).toLowerCase().includes(channelLower)
        );
        if (matchesAny) {
          list = list.filter((c) => 
            getPlataforma(c).toLowerCase().includes(channelLower) || 
            getCampanaName(c).toLowerCase().includes(channelLower)
          );
        }
      }
    }

    if (platformFilter !== 'ALL') {
      list = list.filter((c) => getPlataforma(c).toLowerCase().includes(platformFilter.toLowerCase()));
    }

    if (searchTerm.trim() !== '') {
      const term = searchTerm.toLowerCase();
      list = list.filter((c) => 
        getCampanaName(c).toLowerCase().includes(term) ||
        getPlataforma(c).toLowerCase().includes(term)
      );
    }

    return [...list].sort((a: any, b: any) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];

      if (sortKey === 'gastoCy') { aVal = getGasto(a); bVal = getGasto(b); }
      if (sortKey === 'clicsCy') { aVal = getClics(a); bVal = getClics(b); }
      if (sortKey === 'ctrCy') { aVal = getCtr(a); bVal = getCtr(b); }
      if (sortKey === 'roasCy') { aVal = getRoas(a); bVal = getRoas(b); }
      if (sortKey === 'campana') { aVal = getCampanaName(a); bVal = getCampanaName(b); }

      if (aVal === undefined || aVal === null) aVal = '';
      if (bVal === undefined || bVal === null) bVal = '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [CAMPAIGNS_DATA, selectedChannel, platformFilter, searchTerm, sortKey, sortDir]);

  const totalGasto = CAMPAIGNS_DATA.reduce((acc, c) => acc + getGasto(c), 0);
  const totalGastoWow = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.gastoWow ?? 0), 0);
  const totalGastoYoy = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.gastoYoy ?? 0), 0);

  const totalImpresiones = CAMPAIGNS_DATA.reduce((acc, c) => acc + getImpresiones(c), 0);
  const totalImpresionesWow = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.impresionesWow ?? 0), 0);
  const totalImpresionesYoy = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.impresionesYoy ?? 0), 0);

  const totalClics = CAMPAIGNS_DATA.reduce((acc, c) => acc + getClics(c), 0);
  const totalClicsWow = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.clicsWow ?? 0), 0);
  const totalClicsYoy = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.clicsYoy ?? 0), 0);

  const totalValorCompras = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.valorComprasCy ?? (getRoas(c) * getGasto(c)) ?? 0), 0);

  const ctrPromedio = totalImpresiones ? (totalClics / totalImpresiones) * 100 : 0;
  const ctrPromedioWow = totalImpresionesWow ? (totalClicsWow / totalImpresionesWow) * 100 : 0;
  const ctrPromedioYoy = totalImpresionesYoy ? (totalClicsYoy / totalImpresionesYoy) * 100 : 0;

  const roasPromedio = totalGasto ? totalValorCompras / totalGasto : 0;
  const totalValorComprasWow = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.roasWow || 0) * (c.gastoWow || 0), 0);
  const totalValorComprasYoy = CAMPAIGNS_DATA.reduce((acc, c) => acc + (c.roasYoy || 0) * (c.gastoYoy || 0), 0);
  const roasPromedioWow = totalGastoWow ? totalValorComprasWow / totalGastoWow : 0;
  const roasPromedioYoy = totalGastoYoy ? totalValorComprasYoy / totalGastoYoy : 0;

  const gastoVarYoyPct = totalGastoYoy ? ((totalGasto - totalGastoYoy) / totalGastoYoy) * 100 : 0;
  const gastoVarWowPct = totalGastoWow ? ((totalGasto - totalGastoWow) / totalGastoWow) * 100 : 0;
  const impVarYoyPct = totalImpresionesYoy ? ((totalImpresiones - totalImpresionesYoy) / totalImpresionesYoy) * 100 : 0;
  const impVarWowPct = totalImpresionesWow ? ((totalImpresiones - totalImpresionesWow) / totalImpresionesWow) * 100 : 0;
  const clicsVarYoyPct = totalClicsYoy ? ((totalClics - totalClicsYoy) / totalClicsYoy) * 100 : 0;
  const clicsVarWowPct = totalClicsWow ? ((totalClics - totalClicsWow) / totalClicsWow) * 100 : 0;

  const spendPorPlataforma = useMemo(() => {
    const acc: Record<string, { actual: number; yoy: number }> = { Google: { actual: 0, yoy: 0 }, Meta: { actual: 0, yoy: 0 } };
    CAMPAIGNS_DATA.forEach((c) => {
      const plat = getPlataforma(c).toLowerCase().includes('google') ? 'Google' : 'Meta';
      if (!acc[plat]) acc[plat] = { actual: 0, yoy: 0 };
      acc[plat].actual += getGasto(c);
      acc[plat].yoy += c.gastoYoy || 0;
    });
    return acc;
  }, [CAMPAIGNS_DATA]);

  const googleSpendActual = spendPorPlataforma.Google?.actual || 0;
  const googleSpendYoy = spendPorPlataforma.Google?.yoy || 0;
  const googleVarPct = googleSpendYoy ? ((googleSpendActual - googleSpendYoy) / googleSpendYoy) * 100 : 0;

  const metaSpendActual = spendPorPlataforma.Meta?.actual || 0;
  const metaSpendYoy = spendPorPlataforma.Meta?.yoy || 0;
  const metaVarPct = metaSpendYoy ? ((metaSpendActual - metaSpendYoy) / metaSpendYoy) * 100 : 0;

  const totalSpendActual = metaSpendActual + googleSpendActual || 1;
  const totalSpendYoy = metaSpendYoy + googleSpendYoy || 1;

  const compareSpendData = [
    {
      plataforma: 'Google Ads',
      actual: googleSpendActual,
      yoy: googleSpendYoy,
      share: ((googleSpendActual / totalSpendActual) * 100).toFixed(1),
      yoyShare: ((googleSpendYoy / totalSpendYoy) * 100).toFixed(1)
    },
    {
      plataforma: 'Meta Ads',
      actual: metaSpendActual,
      yoy: metaSpendYoy,
      share: ((metaSpendActual / totalSpendActual) * 100).toFixed(1),
      yoyShare: ((metaSpendYoy / totalSpendYoy) * 100).toFixed(1)
    }
  ];

  const monthlyTrendData = [
    { mes: 'Ene', gasto: 18200000, roas: 3.8 },
    { mes: 'Feb', gasto: 22400000, roas: 4.1 },
    { mes: 'Mar', gasto: 28900000, roas: 4.3 },
    { mes: 'Abr', gasto: 31200000, roas: 4.2 },
    { mes: 'May', gasto: 34500000, roas: 4.5 },
    { mes: 'Jun', gasto: 38200000, roas: 4.6 },
    { mes: 'Jul', gasto: 34950000, roas: 4.5 }
  ];

  if (loadingCampaigns) {
    return (
      <div className="min-h-[400px] flex flex-col items-center justify-center gap-3">
        <div className="p-3 rounded-2xl bg-blue-500/10 text-blue-500 animate-spin">
          <RefreshCw className="w-7 h-7" />
        </div>
        <span className="text-sm font-medium tracking-tight text-slate-500 dark:text-slate-400">
          Cargando rendimiento de Campañas de Marketing...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-10">
      <CrossFilterBanner theme={theme} />

      {/* TARJETAS KPI */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        
        {/* INVERSIÓN TOTAL */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark 
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]' 
            : 'bg-white border-slate-200 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
              INVERSIÓN TOTAL
            </span>
            <div className={`p-2 rounded-xl ${isDark ? 'bg-blue-500/10 text-blue-400' : 'bg-blue-50 text-blue-600'}`}>
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
            ${(totalGasto / 1000000).toFixed(1)}M
          </div>
          <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-[#2C2C2E] flex flex-col gap-1 text-[11px] font-semibold">
            <span className="text-slate-600 dark:text-slate-400 flex items-center justify-between">
              YoY: ${(totalGastoYoy / 1000000).toFixed(1)}M 
              <span className={gastoVarYoyPct <= 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-600 dark:text-rose-400 font-bold'}>
                {gastoVarYoyPct >= 0 ? '+' : ''}{gastoVarYoyPct.toFixed(1)}%
              </span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: ${(totalGastoWow / 1000000).toFixed(1)}M 
              <span>{gastoVarWowPct >= 0 ? '+' : ''}{gastoVarWowPct.toFixed(1)}%</span>
            </span>
          </div>
        </div>

        {/* IMPRESIONES */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark 
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]' 
            : 'bg-white border-slate-200 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isDark ? 'text-purple-400' : 'text-purple-700'}`}>
              IMPRESIONES
            </span>
            <div className={`p-2 rounded-xl ${isDark ? 'bg-purple-500/10 text-purple-400' : 'bg-purple-50 text-purple-700'}`}>
              <Eye className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {(totalImpresiones / 1000000).toFixed(2)}M
          </div>
          <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-[#2C2C2E] flex flex-col gap-1 text-[11px] font-semibold">
            <span className="text-slate-600 dark:text-slate-400 flex items-center justify-between">
              YoY: {(totalImpresionesYoy / 1000000).toFixed(2)}M 
              <span className={impVarYoyPct >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-slate-500 dark:text-slate-400'}>
                {impVarYoyPct >= 0 ? '+' : ''}{impVarYoyPct.toFixed(1)}%
              </span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: {(totalImpresionesWow / 1000).toFixed(0)}K 
              <span>{impVarWowPct >= 0 ? '+' : ''}{impVarWowPct.toFixed(1)}%</span>
            </span>
          </div>
        </div>

        {/* CLICS TOTALES */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark 
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]' 
            : 'bg-white border-slate-200 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>
              CLICS TOTALES
            </span>
            <div className={`p-2 rounded-xl ${isDark ? 'bg-amber-500/10 text-amber-400' : 'bg-amber-50 text-amber-700'}`}>
              <Target className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {(totalClics / 1000).toFixed(1)}K
          </div>
          <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-[#2C2C2E] flex flex-col gap-1 text-[11px] font-semibold">
            <span className="text-slate-600 dark:text-slate-400 flex items-center justify-between">
              YoY: {(totalClicsYoy / 1000).toFixed(1)}K 
              <span className={clicsVarYoyPct >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-slate-500 dark:text-slate-400'}>
                {clicsVarYoyPct >= 0 ? '+' : ''}{clicsVarYoyPct.toFixed(1)}%
              </span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: {(totalClicsWow / 1000).toFixed(1)}K 
              <span>{clicsVarWowPct >= 0 ? '+' : ''}{clicsVarWowPct.toFixed(1)}%</span>
            </span>
          </div>
        </div>

        {/* CTR PROMEDIO */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark 
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]' 
            : 'bg-white border-slate-200 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
              CTR PROMEDIO
            </span>
            <div className={`p-2 rounded-xl ${isDark ? 'bg-emerald-500/10 text-emerald-400' : 'bg-emerald-50 text-emerald-700'}`}>
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
            {ctrPromedio.toFixed(2)}%
          </div>
          <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-[#2C2C2E] flex flex-col gap-1 text-[11px] font-semibold">
            <span className="text-slate-600 dark:text-slate-400 flex items-center justify-between">
              YoY: <span>{ctrPromedioYoy.toFixed(2)}%</span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: <span>{ctrPromedioWow.toFixed(2)}%</span>
            </span>
          </div>
        </div>

        {/* ROAS PROMEDIO */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark 
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]' 
            : 'bg-white border-slate-200 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className={`text-[11px] font-bold uppercase tracking-wider ${isDark ? 'text-purple-400' : 'text-purple-800'}`}>
              ROAS PROMEDIO
            </span>
            <div className={`p-2 rounded-xl ${isDark ? 'bg-purple-500/10 text-purple-400' : 'bg-purple-50 text-purple-800'}`}>
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-purple-400' : 'text-purple-700'}`}>
            {roasPromedio.toFixed(2)}x
          </div>
          <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-[#2C2C2E] flex flex-col gap-1 text-[11px] font-semibold">
            <span className="text-slate-600 dark:text-slate-400 flex items-center justify-between">
              YoY: <span>{roasPromedioYoy.toFixed(2)}x</span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: <span>{roasPromedioWow.toFixed(2)}x</span>
            </span>
          </div>
        </div>

      </div>

      {/* COMPARATIVO DE INVERSIÓN: GOOGLE ADS VS META ADS */}
      <div className={`p-5 rounded-2xl border transition-all duration-200 space-y-4 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-xs font-bold uppercase tracking-wider flex items-center gap-2 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
            <Megaphone className="w-4 h-4" /> COMPARATIVO DE INVERSIÓN: GOOGLE ADS VS META ADS (ACTUAL VS YOY &amp; SHARE %)
          </h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-5 space-y-3">
            <div className={`p-4 rounded-xl border transition-all ${
              isDark ? 'bg-[#171719] border-[#2C2C2E]' : 'bg-amber-50/70 border-amber-200'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-lg ${isDark ? 'bg-amber-500/10 text-amber-400' : 'bg-amber-100 text-amber-800'}`}>
                    <Search className="w-5 h-5" />
                  </div>
                  <div>
                    <span className={`font-extrabold text-xs block tracking-wide ${isDark ? 'text-amber-400' : 'text-amber-800'}`}>
                      GOOGLE ADS
                    </span>
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Inversión: {fmtMoney(googleSpendActual)}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-black block ${
                    googleVarPct <= 0 
                      ? (isDark ? 'text-emerald-400' : 'text-emerald-700') 
                      : (isDark ? 'text-rose-400' : 'text-rose-700')
                  }`}>
                    {googleVarPct >= 0 ? '+' : ''}{googleVarPct.toFixed(1)}% VAR
                  </span>
                  <span className="text-[10px] text-slate-600 dark:text-slate-400 font-medium">
                    YoY: {fmtMoney(googleSpendYoy)}
                  </span>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl border transition-all ${
              isDark ? 'bg-[#171719] border-[#2C2C2E]' : 'bg-blue-50/70 border-blue-200'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-lg ${isDark ? 'bg-blue-500/10 text-blue-400' : 'bg-blue-100 text-blue-700'}`}>
                    <Facebook className="w-5 h-5" />
                  </div>
                  <div>
                    <span className={`font-extrabold text-xs block tracking-wide ${isDark ? 'text-blue-400' : 'text-blue-700'}`}>
                      META ADS (FB + IG)
                    </span>
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Inversión: {fmtMoney(metaSpendActual)}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-black block ${
                    metaVarPct <= 0 
                      ? (isDark ? 'text-emerald-400' : 'text-emerald-700') 
                      : (isDark ? 'text-rose-400' : 'text-rose-700')
                  }`}>
                    {metaVarPct >= 0 ? '+' : ''}{metaVarPct.toFixed(1)}% VAR
                  </span>
                  <span className="text-[10px] text-slate-600 dark:text-slate-400 font-medium">
                    YoY: {fmtMoney(metaSpendYoy)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={compareSpendData} margin={{ top: 25, right: 30, left: 10, bottom: 5 }}>
                <XAxis 
                  dataKey="plataforma" 
                  stroke={isDark ? '#94A3B8' : '#334155'} 
                  fontSize={11} 
                  fontWeight="bold"
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: isDark ? '#1C1C1E' : '#FFFFFF',
                    borderColor: isDark ? '#2C2C2E' : '#CBD5E1',
                    borderRadius: '12px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                    color: isDark ? '#FFF' : '#0F172A',
                    fontSize: '12px'
                  }}
                  formatter={(val: number) => [fmtMoney(val), 'Inversión']}
                />
                <Bar dataKey="actual" name="Inversión Actual ($)" fill={isDark ? '#0A84FF' : '#2563EB'} radius={[6, 6, 0, 0]}>
                  <LabelList 
                    dataKey="share" 
                    position="top" 
                    formatter={(val: string) => `${val}% Share`} 
                    fill={isDark ? '#EDEDED' : '#0F172A'} 
                    fontSize={10} 
                    fontWeight="bold" 
                  />
                </Bar>
                <Bar dataKey="yoy" name="Inversión YoY ($)" fill={isDark ? '#8E8E93' : '#64748B'} radius={[6, 6, 0, 0]}>
                  <LabelList 
                    dataKey="yoyShare" 
                    position="top" 
                    formatter={(val: string) => `${val}% Share YoY`} 
                    fill={isDark ? '#EDEDED' : '#0F172A'} 
                    fontSize={10} 
                    fontWeight="bold" 
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* TENDENCIA MENSUAL DE GASTO Y ROAS */}
      <div className={`p-5 rounded-2xl border transition-all duration-200 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <h3 className={`text-xs font-bold uppercase tracking-wider mb-4 flex items-center gap-2 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
          <BarChart3 className="w-4 h-4" /> TENDENCIA MENSUAL DE GASTO Y ROAS (HISTÓRICO)
        </h3>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={monthlyTrendData} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#2C2C2E' : '#E2E8F0'} vertical={false} />
              <XAxis dataKey="mes" stroke={isDark ? '#94A3B8' : '#334155'} fontSize={11} axisLine={false} tickLine={false} fontWeight="bold" />
              <Tooltip 
                contentStyle={{
                  backgroundColor: isDark ? '#1C1C1E' : '#FFFFFF',
                  borderColor: isDark ? '#2C2C2E' : '#CBD5E1',
                  borderRadius: '12px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                  fontSize: '12px'
                }}
              />
              <Bar dataKey="gasto" name="Inversión ($)" fill={isDark ? '#0A84FF' : '#2563EB'} radius={[6, 6, 0, 0]}>
                <LabelList 
                  dataKey="gasto" 
                  position="top" 
                  formatter={(val: number) => `$${(val / 1000000).toFixed(1)}M`} 
                  fill={isDark ? '#EDEDED' : '#0F172A'} 
                  fontSize={10} 
                  fontWeight="bold" 
                />
              </Bar>
              <Line 
                type="monotone" 
                dataKey="roas" 
                name="ROAS (x)" 
                stroke={isDark ? '#BF5AF2' : '#7E22CE'} 
                strokeWidth={3} 
                dot={{ r: 5, fill: isDark ? '#BF5AF2' : '#7E22CE' }}
              >
                <LabelList 
                  dataKey="roas" 
                  position="top" 
                  formatter={(val: number) => `${val}x`} 
                  fill={isDark ? '#BF5AF2' : '#7E22CE'} 
                  fontSize={10} 
                  fontWeight="bold" 
                />
              </Line>
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* TABLA RANKING DE CAMPAÑAS */}
      <div className={`rounded-2xl border overflow-hidden transition-all duration-200 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        
        <div className={`p-4 border-b flex flex-col sm:flex-row items-center justify-between gap-3 ${
          isDark ? 'border-[#2C2C2E] bg-[#171719]' : 'border-slate-200 bg-slate-50'
        }`}>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <span className={`text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
              <Layers className="w-4 h-4" /> RANKING DE CAMPAÑAS ({filteredCampaigns.length})
            </span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar campaña o plataforma..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className={`w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border outline-none transition-all ${
                  isDark 
                    ? 'bg-[#252528] border-[#333336] text-white placeholder-slate-500 focus:border-blue-500' 
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400 focus:border-blue-500'
                }`}
              />
            </div>

            <div className="relative">
              <select
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                className={`px-3 py-1.5 text-xs rounded-xl border outline-none cursor-pointer transition-all ${
                  isDark 
                    ? 'bg-[#252528] border-[#333336] text-white focus:border-blue-500' 
                    : 'bg-white border-slate-300 text-slate-900 focus:border-blue-500'
                }`}
              >
                <option value="ALL">Todas las Plataformas</option>
                <option value="Google">Google Ads</option>
                <option value="Meta">Meta Ads</option>
              </select>
            </div>

            <div className="relative">
              <select
                value={marcaFilter}
                onChange={(e) => setMarcaFilter(e.target.value)}
                className={`px-3 py-1.5 text-xs rounded-xl border outline-none cursor-pointer transition-all ${
                  isDark 
                    ? 'bg-[#252528] border-[#333336] text-white focus:border-blue-500' 
                    : 'bg-white border-slate-300 text-slate-900 focus:border-blue-500'
                }`}
              >
                <option value="ALL">Todas las Marcas</option>
                <option value="Kaltemp">Kaltemp</option>
                <option value="Tom Palmer">Tom Palmer</option>
              </select>
            </div>
          </div>
        </div>

        {/* TABLA PRINCIPAL */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse min-w-[1100px]">
            <thead>
              <tr className={`border-b text-[10px] font-bold uppercase tracking-wider ${
                isDark ? 'border-[#2C2C2E] text-slate-400 bg-[#121215]' : 'border-slate-200 text-slate-600 bg-slate-100'
              }`}>
                <th className="py-3 px-4 text-center">ORIGEN</th>
                <th className="py-3 px-4 text-center">PIEZA GRÁFICA</th>
                <SortableTh label="CAMPAÑA" sortKey="campana" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="INVERSIÓN (ACT | YoY | WoW)" sortKey="gastoCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={isDark ? 'text-blue-400 font-bold' : 'text-blue-600 font-bold'} />
                <SortableTh label="CLICS (ACT | YoY | WoW)" sortKey="clicsCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="CTR (ACT | YoY | WoW)" sortKey="ctrCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
                <SortableTh label="ROAS (ACT | YoY | WoW)" sortKey="roasCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={isDark ? 'text-purple-400 font-bold' : 'text-purple-700 font-bold'} />
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-[#2C2C2E]' : 'divide-slate-200'}`}>
              {filteredCampaigns.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 dark:text-slate-400 italic">
                    Sin campañas registradas que coincidan con la búsqueda o filtros activos
                  </td>
                </tr>
              ) : (
                filteredCampaigns.map((c, idx) => {
                  const imgUrl = c.imagenUrl || c.imagen || c.piezagrafica || c.urlAnuncio;
                  const isGoogle = getPlataforma(c).toLowerCase().includes('google');
                  const nombreCampana = getCampanaName(c);

                  return (
                    <tr 
                      key={c.id || idx} 
                      className={`transition-colors hover:bg-blue-500/5 ${
                        isDark ? 'text-slate-200' : 'text-slate-900'
                      }`}
                    >
                      <td className="py-3 px-4 text-center">
                        {isGoogle ? (
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                            isDark ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-amber-100 text-amber-800 border-amber-200'
                          }`}>
                            <Search className="w-3 h-3" /> Google
                          </span>
                        ) : (
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                            isDark ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-blue-100 text-blue-800 border-blue-200'
                          }`}>
                            <Facebook className="w-3 h-3" /> Meta
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-center">
                        {imgUrl ? (
                          <button
                            onClick={() => setPreviewAd({ name: nombreCampana, url: imgUrl, platform: getPlataforma(c) })}
                            className="group relative inline-flex items-center justify-center w-10 h-10 overflow-hidden rounded-xl border border-slate-300 dark:border-slate-700 shadow-sm bg-white focus:outline-none transition-transform hover:scale-105"
                            title="Ver anuncio completo"
                          >
                            <img
                              src={imgUrl}
                              alt={nombreCampana}
                              className="max-w-full max-h-full w-auto h-auto object-contain"
                            />
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                              <Eye className="w-3.5 h-3.5 text-white" />
                            </div>
                          </button>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 dark:text-slate-400 font-medium px-2 py-1 bg-slate-100 dark:bg-[#252528] rounded-lg">
                            <ImageIcon className="w-3 h-3 opacity-60" /> Sin Imagen
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 font-semibold max-w-[220px] truncate" title={nombreCampana}>
                        {nombreCampana}
                      </td>

                      {/* Inversión sin decimales */}
                      <td className={`py-3 px-4 text-right font-bold whitespace-nowrap ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                        <span>{fmtMoney(getGasto(c))}</span>
                        <span className="text-[10px] block text-slate-500 dark:text-slate-400 font-normal">
                          YoY: {fmtMoney(c.gastoYoy ?? 0)} | WoW: {fmtMoney(c.gastoWow ?? 0)}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right font-semibold whitespace-nowrap">
                        <span>{getClics(c).toLocaleString('es-CL')}</span>
                        <span className={`text-[10px] block font-medium ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
                          YoY: {(c.clicsYoy ?? 0).toLocaleString('es-CL')} | WoW: {(c.clicsWow ?? 0).toLocaleString('es-CL')}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right font-semibold whitespace-nowrap">
                        <span>{getCtr(c).toFixed(1)}%</span>
                        <span className={`text-[10px] block font-medium ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
                          YoY: {(c.ctrYoy ?? 0).toFixed(1)}% | WoW: {(c.ctrWow ?? 0).toFixed(1)}%
                        </span>
                      </td>

                      <td className={`py-3 px-4 text-right font-extrabold whitespace-nowrap ${isDark ? 'text-purple-400' : 'text-purple-700'}`}>
                        <span>{getRoas(c).toFixed(2)}x</span>
                        <span className={`text-[10px] block font-medium ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
                          YoY: {(c.roasYoy ?? 0).toFixed(2)}x | WoW: {(c.roasYoy ?? 0).toFixed(2)}x
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {previewAd && (
        <div
          className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setPreviewAd(null)}
        >
          <div
            className={`relative max-w-xl w-full rounded-3xl border p-6 shadow-2xl space-y-4 ${
              isDark ? 'bg-[#1C1C1E] border-[#2C2C2E] text-white' : 'bg-white border-slate-200 text-slate-900'
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b pb-3 border-slate-200 dark:border-[#2C2C2E]">
              <div>
                <span className={`text-[10px] font-bold uppercase tracking-wider ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                  Pieza Gráfica del Anuncio · {previewAd.platform}
                </span>
                <h4 className="text-base font-bold truncate max-w-xs mt-0.5">{previewAd.name}</h4>
              </div>
              <button
                onClick={() => setPreviewAd(null)}
                className="p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-[#2C2C2E] text-slate-400 hover:text-slate-200 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-[#2C2C2E] bg-black/5 flex items-center justify-center h-[450px] w-full">
              <img
                src={previewAd.url}
                alt={previewAd.name}
                className="w-full h-full object-contain rounded-xl shadow-md"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setPreviewAd(null)}
                className="px-6 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white hover:bg-blue-700 transition-all shadow-md cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default MarketingCampaignsView;