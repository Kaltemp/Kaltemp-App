// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\views\MarketingCampaignsView.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { ThemeMode } from '../types';
import { getBrandTokens } from '../theme/brandTokens';
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
  ChevronDown,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import { fetchMarketingCampaigns, fetchDatosManuales, DatoManual, fetchMarketingCampaignAnuncios, AnuncioCampana } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Line,
  CartesianGrid,
  Legend,
  LabelList,
  AreaChart,
  Area,
  YAxis
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

  // EXCEPCIÓN (ver theme/brandTokens.ts): Marketing nunca recibe el
  // selector global de modo de marca -- resuelve el suyo propio a
  // partir de marcaFilter. 'ALL' (Todas las Marcas) cae en 'standard'
  // porque ahí sí conviven ambas marcas a la vez en la misma vista.
  const brandTokens = getBrandTokens(
    marcaFilter === 'Kaltemp' ? 'kaltemp' : marcaFilter === 'Tom Palmer' ? 'tompalmer' : 'standard',
    isDark
  );

  const [previewAd, setPreviewAd] = useState<{ name: string; url: string; platform: string } | null>(null);

  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [anunciosPorCampana, setAnunciosPorCampana] = useState<Record<string, AnuncioCampana[]>>({});
  const [loadingAnunciosKey, setLoadingAnunciosKey] = useState<string | null>(null);
  const [previewAnuncio, setPreviewAnuncio] = useState<{ name: string; url: string } | null>(null);

  const [CAMPAIGNS_DATA, setCampaignsData] = useState<any[]>([]);
  const [loadingCampaigns, setLoadingCampaigns] = useState(true);
  const [datosManuales, setDatosManuales] = useState<DatoManual[]>([]);

  // Tendencia Semanal (Semanas 1 a 52)
  const [weeklyTrendData, setWeeklyTrendData] = useState<any[]>([]);
  const [loadingWeekly, setLoadingWeekly] = useState<boolean>(true);

  useEffect(() => {
    fetchDatosManuales()
      .then((data) => setDatosManuales(Array.isArray(data) ? data : []))
      .catch((err) => {
        console.error('Error al cargar presupuesto de marketing:', err);
        setDatosManuales([]);
      });
  }, []);

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

  // Carga tendencia semanal de inversión
  useEffect(() => {
    setLoadingWeekly(true);
    const marcaQuery = marcaFilter === 'ALL' ? '' : `?marca=${encodeURIComponent(marcaFilter)}`;
    fetch(`/api/marketing/weekly-trend${marcaQuery}`)
      .then((res) => res.json())
      .then((data) => setWeeklyTrendData(Array.isArray(data) ? data : []))
      .catch((err) => {
        console.error('Error al cargar tendencia semanal de inversión:', err);
        setWeeklyTrendData([]);
      })
      .finally(() => setLoadingWeekly(false));
  }, [marcaFilter]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const handleToggleExpand = (c: any) => {
    const plataforma = getPlataforma(c);
    const isGoogle = plataforma.toLowerCase().includes('google');
    if (isGoogle) return;

    const nombreCampana = getCampanaName(c);
    const marcaCampana = c.marca || 'Kaltemp';
    const key = `${plataforma}__${nombreCampana}__${marcaCampana}`;

    if (expandedKey === key) {
      setExpandedKey(null);
      return;
    }

    setExpandedKey(key);

    if (!anunciosPorCampana[key]) {
      setLoadingAnunciosKey(key);
      fetchMarketingCampaignAnuncios(nombreCampana, startDate, endDate, marcaCampana)
        .then((anuncios) => {
          setAnunciosPorCampana((prev) => ({ ...prev, [key]: Array.isArray(anuncios) ? anuncios : [] }));
        })
        .catch((err) => {
          console.error('Error al cargar anuncios de la campaña:', err);
          setAnunciosPorCampana((prev) => ({ ...prev, [key]: [] }));
        })
        .finally(() => setLoadingAnunciosKey(null));
    }
  };

  const getCampanaName = (c: any) => c.campana || c.nombre || c.name || c.campaign_name || 'Sin Nombre';
  const getPlataforma = (c: any) => c.plataforma || c.platform || c.origen || 'Meta';
  const getGasto = (c: any) => c.gastoCy ?? c.gasto ?? c.inversion ?? c.cost ?? 0;
  const getClics = (c: any) => c.clicsCy ?? c.clics ?? c.clicks ?? 0;
  const getImpresiones = (c: any) => c.impresionesCy ?? c.impresiones ?? c.impressions ?? 0;
  const getCtr = (c: any) => c.ctrCy ?? c.ctr ?? (getImpresiones(c) > 0 ? (getClics(c) / getImpresiones(c)) * 100 : 0);
  const getRoas = (c: any) => c.roasCy ?? c.roas ?? 0;

  const fmtMoney = (val: number) => `$${Math.round(val || 0).toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;

  // Color consistente para variaciones %: negativo = rojo, positivo (o cero) = verde.
  // Se usa en TODAS las tarjetas KPI y en el comparativo Google/Meta.
  const pctColor = (pct: number) =>
    pct >= 0
      ? (isDark ? 'text-emerald-400 font-bold' : 'text-emerald-600 font-bold')
      : (isDark ? 'text-rose-400 font-bold' : 'text-rose-600 font-bold');

  // Color consistente para valores de referencia (YoY/WoW) vs el valor actual: si el
  // actual está por debajo de la referencia = rojo (bajó), si está igual o por encima = verde.
  // Si no hay referencia (0/null/undefined) se muestra en gris neutro, sin semáforo engañoso.
  const varClass = (current: number, reference: number | null | undefined) => {
    if (!reference) return isDark ? 'text-slate-500' : 'text-slate-400';
    return current >= reference
      ? (isDark ? 'text-emerald-400 font-bold' : 'text-emerald-600 font-bold')
      : (isDark ? 'text-rose-400 font-bold' : 'text-rose-600 font-bold');
  };

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

  const pptoMarketing = useMemo(() => {
    if (!startDate || !endDate) return 0;

    const [anioIni, mesIni, diaIni] = startDate.split('-').map(Number);
    const [anioFin, mesFin, diaFin] = endDate.split('-').map(Number);
    if (!anioIni || !mesIni || !diaIni || !anioFin || !mesFin || !diaFin) return 0;

    const rangoInicio = new Date(anioIni, mesIni - 1, diaIni);
    const rangoFin = new Date(anioFin, mesFin - 1, diaFin);

    return datosManuales
      .filter((d) => d.tipo === 'presupuesto_marketing')
      .filter((d) => /^\d{4}-\d{2}$/.test(d.periodo))
      .filter((d) => marcaFilter === 'ALL' || d.marca === marcaFilter)
      .reduce((acc, d) => {
        const [anioP, mesP] = d.periodo.split('-').map(Number);
        const mesInicioDate = new Date(anioP, mesP - 1, 1);
        const mesFinDate = new Date(anioP, mesP, 0);
        const diasDelMes = mesFinDate.getDate();

        const solapInicio = mesInicioDate > rangoInicio ? mesInicioDate : rangoInicio;
        const solapFin = mesFinDate < rangoFin ? mesFinDate : rangoFin;
        if (solapInicio > solapFin) return acc;

        const diasSolapados = Math.round((solapFin.getTime() - solapInicio.getTime()) / 86400000) + 1;
        const proporcion = diasSolapados / diasDelMes;

        return acc + (d.monto || 0) * proporcion;
      }, 0);
  }, [datosManuales, startDate, endDate, marcaFilter]);

  const gastoVarPptoPct = pptoMarketing ? ((totalGasto - pptoMarketing) / pptoMarketing) * 100 : 0;

  const impVarYoyPct = totalImpresionesYoy ? ((totalImpresiones - totalImpresionesYoy) / totalImpresionesYoy) * 100 : 0;
  const impVarWowPct = totalImpresionesWow ? ((totalImpresiones - totalImpresionesWow) / totalImpresionesWow) * 100 : 0;
  const clicsVarYoyPct = totalClicsYoy ? ((totalClics - totalClicsYoy) / totalClicsYoy) * 100 : 0;
  const clicsVarWowPct = totalClicsWow ? ((totalClics - totalClicsWow) / totalClicsWow) * 100 : 0;

  const ctrVarYoyPct = ctrPromedioYoy ? ((ctrPromedio - ctrPromedioYoy) / ctrPromedioYoy) * 100 : 0;
  const ctrVarWowPct = ctrPromedioWow ? ((ctrPromedio - ctrPromedioWow) / ctrPromedioWow) * 100 : 0;
  const roasVarYoyPct = roasPromedioYoy ? ((roasPromedio - roasPromedioYoy) / roasPromedioYoy) * 100 : 0;
  const roasVarWowPct = roasPromedioWow ? ((roasPromedio - roasPromedioWow) / roasPromedioWow) * 100 : 0;

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
              <span className={pctColor(gastoVarYoyPct)}>
                {gastoVarYoyPct >= 0 ? '+' : ''}{gastoVarYoyPct.toFixed(1)}%
              </span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: ${(totalGastoWow / 1000000).toFixed(1)}M 
              <span className={pctColor(gastoVarWowPct)}>{gastoVarWowPct >= 0 ? '+' : ''}{gastoVarWowPct.toFixed(1)}%</span>
            </span>
            {pptoMarketing > 0 ? (
              <span
                className="text-amber-600 dark:text-amber-400 flex items-center justify-between"
                title="Presupuesto prorrateado por día según el rango de fechas filtrado"
              >
                Ppto: ${(pptoMarketing / 1000000).toFixed(1)}M
                <span className={pctColor(gastoVarPptoPct)}>
                  {gastoVarPptoPct >= 0 ? '+' : ''}{gastoVarPptoPct.toFixed(1)}%
                </span>
              </span>
            ) : (
              <span className="text-slate-400 dark:text-slate-500 flex items-center justify-between italic">
                Ppto: sin cargar
              </span>
            )}
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
              <span className={pctColor(impVarYoyPct)}>
                {impVarYoyPct >= 0 ? '+' : ''}{impVarYoyPct.toFixed(1)}%
              </span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: {(totalImpresionesWow / 1000).toFixed(0)}K 
              <span className={pctColor(impVarWowPct)}>{impVarWowPct >= 0 ? '+' : ''}{impVarWowPct.toFixed(1)}%</span>
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
              <span className={pctColor(clicsVarYoyPct)}>
                {clicsVarYoyPct >= 0 ? '+' : ''}{clicsVarYoyPct.toFixed(1)}%
              </span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: {(totalClicsWow / 1000).toFixed(1)}K 
              <span className={pctColor(clicsVarWowPct)}>{clicsVarWowPct >= 0 ? '+' : ''}{clicsVarWowPct.toFixed(1)}%</span>
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
              YoY: {ctrPromedioYoy.toFixed(2)}%
              <span className={pctColor(ctrVarYoyPct)}>{ctrVarYoyPct >= 0 ? '+' : ''}{ctrVarYoyPct.toFixed(1)}%</span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: {ctrPromedioWow.toFixed(2)}%
              <span className={pctColor(ctrVarWowPct)}>{ctrVarWowPct >= 0 ? '+' : ''}{ctrVarWowPct.toFixed(1)}%</span>
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
              YoY: {roasPromedioYoy.toFixed(2)}x
              <span className={pctColor(roasVarYoyPct)}>{roasVarYoyPct >= 0 ? '+' : ''}{roasVarYoyPct.toFixed(1)}%</span>
            </span>
            <span className="text-blue-600 dark:text-blue-400 flex items-center justify-between">
              WoW: {roasPromedioWow.toFixed(2)}x
              <span className={pctColor(roasVarWowPct)}>{roasVarWowPct >= 0 ? '+' : ''}{roasVarWowPct.toFixed(1)}%</span>
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
                  <span className={`text-xs block ${pctColor(googleVarPct)}`}>
                    {googleVarPct >= 0 ? '+' : ''}{googleVarPct.toFixed(1)}% VAR
                  </span>
                  <span className="text-[10px] text-slate-600 dark:text-slate-400 font-semibold">
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
                  <span className={`text-xs block ${pctColor(metaVarPct)}`}>
                    {metaVarPct >= 0 ? '+' : ''}{metaVarPct.toFixed(1)}% VAR
                  </span>
                  <span className="text-[10px] text-slate-600 dark:text-slate-400 font-semibold">
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

      {/* NUEVO GRÁFICO: TENDENCIA SEMANAL DE INVERSIÓN (SEMANAS 1 A 52: 2026 VS 2025 VS 2024) */}
      <div className={`p-5 rounded-2xl border transition-all duration-200 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className={`text-xs font-bold uppercase tracking-wider flex items-center gap-2 ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
              <TrendingUp className="w-4 h-4" /> TENDENCIA SEMANAL DE INVERSIÓN (SEMANAS 1 A 52)
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
              Comportamiento histórico de inversión publicitaria comparando 2026 vs 2025 y 2024
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-bold whitespace-nowrap">
            <span className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
              <span className="w-3 h-3 rounded-full bg-blue-600 dark:bg-blue-400 inline-block"></span> 2026 Actual
            </span>
            <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <span className="w-3 h-0.5 bg-slate-500 dark:bg-slate-400 inline-block border-t border-dashed"></span> 2025 YoY
            </span>
            <span className="flex items-center gap-1.5 text-purple-600 dark:text-purple-400">
              <span className="w-3 h-0.5 bg-purple-500 dark:bg-purple-400 inline-block border-t border-dotted"></span> 2024 2YoY
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          {loadingWeekly ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400 gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-500" /> Cargando gráfico semanal...
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={weeklyTrendData} margin={{ top: 10, right: 15, left: 10, bottom: 5 }}>
                <defs>
                  <linearGradient id="invGrad2026" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0A84FF" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#0A84FF" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="invGrad2025" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8E8E93" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#8E8E93" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? '#2C2C2E' : '#E2E8F0'} />
                <XAxis dataKey="semana" stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} interval={3} tickLine={false} fontWeight="bold" />
                <YAxis stroke={isDark ? '#8E8E93' : '#64748B'} fontSize={10} tickLine={false} axisLine={false} tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ backgroundColor: isDark ? '#1F1F23' : '#FFFFFF', borderColor: isDark ? '#333339' : '#E2E8F0', color: isDark ? '#EDEDED' : '#1E293B', borderRadius: '12px' }} formatter={(val: any, name: string) => [val != null ? fmtMoney(Number(val)) : 'Sin datos', name === 'actual2026' ? '2026 Actual' : name === 'yoy2025' ? '2025 YoY' : '2024 2YoY']} />
                <Area type="monotone" dataKey="actual2026" name="2026 Actual" stroke="#0A84FF" strokeWidth={3} fill="url(#invGrad2026)" connectNulls={false} />
                <Area type="monotone" dataKey="yoy2025" name="2025 YoY" stroke="#8E8E93" strokeWidth={1.5} strokeDasharray="3 3" fill="url(#invGrad2025)" />
                <Area type="monotone" dataKey="yoy2024" name="2024 2YoY" stroke="#BF5AF2" strokeWidth={1.5} strokeDasharray="2 2" fill="none" />
              </AreaChart>
            </ResponsiveContainer>
          )}
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
                <th className="py-3 px-2 text-center w-8"></th>
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
                  <td colSpan={8} className="py-12 text-center text-slate-500 dark:text-slate-400 italic">
                    Sin campañas registradas que coincidan con la búsqueda o filtros activos
                  </td>
                </tr>
              ) : (
                filteredCampaigns.map((c, idx) => {
                  const imgUrl = c.imagenUrl || c.imagen || c.piezagrafica || c.urlAnuncio;
                  const isGoogle = getPlataforma(c).toLowerCase().includes('google');
                  const nombreCampana = getCampanaName(c);
                  const marcaCampana = c.marca || 'Kaltemp';
                  const rowKey = `${getPlataforma(c)}__${nombreCampana}__${marcaCampana}`;
                  const isExpanded = expandedKey === rowKey;
                  const isLoadingAnuncios = loadingAnunciosKey === rowKey;
                  const anuncios = anunciosPorCampana[rowKey];

                  return (
                    <React.Fragment key={c.id || idx}>
                    <tr 
                      className={`transition-colors hover:bg-blue-500/5 ${
                        isDark ? 'text-slate-200' : 'text-slate-900'
                      } ${!isGoogle ? 'cursor-pointer' : ''}`}
                      onClick={() => handleToggleExpand(c)}
                    >
                      <td className="py-3 px-2 text-center">
                        {!isGoogle && (
                          isLoadingAnuncios ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400 mx-auto" />
                          ) : isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400 mx-auto" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400 mx-auto" />
                          )
                        )}
                      </td>
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
                            onClick={(e) => { e.stopPropagation(); setPreviewAd({ name: nombreCampana, url: imgUrl, platform: getPlataforma(c) }); }}
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
                        <span className="text-[10px] block font-medium">
                          <span className={varClass(getGasto(c), c.gastoYoy ?? 0)}>YoY: {fmtMoney(c.gastoYoy ?? 0)}</span>
                          <span className={isDark ? 'text-slate-600' : 'text-slate-300'}> | </span>
                          <span className={varClass(getGasto(c), c.gastoWow ?? 0)}>WoW: {fmtMoney(c.gastoWow ?? 0)}</span>
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right font-semibold whitespace-nowrap">
                        <span>{getClics(c).toLocaleString('es-CL')}</span>
                        <span className="text-[10px] block font-medium">
                          <span className={varClass(getClics(c), c.clicsYoy ?? 0)}>YoY: {(c.clicsYoy ?? 0).toLocaleString('es-CL')}</span>
                          <span className={isDark ? 'text-slate-600' : 'text-slate-300'}> | </span>
                          <span className={varClass(getClics(c), c.clicsWow ?? 0)}>WoW: {(c.clicsWow ?? 0).toLocaleString('es-CL')}</span>
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right font-semibold whitespace-nowrap">
                        <span>{getCtr(c).toFixed(1)}%</span>
                        <span className="text-[10px] block font-medium">
                          <span className={varClass(getCtr(c), c.ctrYoy ?? 0)}>YoY: {(c.ctrYoy ?? 0).toFixed(1)}%</span>
                          <span className={isDark ? 'text-slate-600' : 'text-slate-300'}> | </span>
                          <span className={varClass(getCtr(c), c.ctrWow ?? 0)}>WoW: {(c.ctrWow ?? 0).toFixed(1)}%</span>
                        </span>
                      </td>

                      <td className={`py-3 px-4 text-right font-extrabold whitespace-nowrap ${isDark ? 'text-purple-400' : 'text-purple-700'}`}>
                        <span>{getRoas(c).toFixed(2)}x</span>
                        <span className="text-[10px] block font-medium">
                          <span className={varClass(getRoas(c), c.roasYoy ?? 0)}>YoY: {(c.roasYoy ?? 0).toFixed(2)}x</span>
                          <span className={isDark ? 'text-slate-600' : 'text-slate-300'}> | </span>
                          <span className={varClass(getRoas(c), c.roasWow ?? 0)}>WoW: {(c.roasWow ?? 0).toFixed(2)}x</span>
                        </span>
                      </td>
                    </tr>

                                        {/* SECCIÓN EXPANDIDA: FILAS DIRECTAS ALINEADAS PÍXEL A PÍXEL CON LA TABLA PRINCIPAL */}
                    {isExpanded && !isGoogle && (
                      isLoadingAnuncios ? (
                        <tr className={isDark ? "bg-[#121215]" : "bg-slate-50"}>
                          <td colSpan={8} className="py-4 px-6 text-center text-xs text-slate-500 dark:text-slate-400">
                            <div className="flex items-center justify-center gap-2">
                              <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                              <span>Cargando anuncios de {nombreCampana}...</span>
                            </div>
                          </td>
                        </tr>
                      ) : !anuncios || anuncios.length === 0 ? (
                        <tr className={isDark ? "bg-[#121215]" : "bg-slate-50"}>
                          <td colSpan={8} className="py-3 px-6 text-center text-xs text-slate-500 dark:text-slate-400 italic">
                            Sin anuncios individuales registrados para esta campaña en el rango seleccionado.
                          </td>
                        </tr>
                      ) : (
                        <>
                          {/* Subcabecera de detalle de anuncios */}
                          <tr className={isDark ? "bg-[#18181B] border-t border-b border-blue-500/20" : "bg-blue-50/70 border-t border-b border-blue-200"}>
                            <td colSpan={8} className="py-2 px-6">
                              <div className="flex items-center justify-between">
                                <span className={`text-[11px] font-bold uppercase tracking-wider ${isDark ? "text-blue-400" : "text-blue-700"}`}>
                                  ↳ Detalle de Anuncios Meta ({anuncios.length}) — {nombreCampana}
                                </span>
                                <span className="text-[10px] text-slate-500 dark:text-slate-400 italic font-medium">
                                  Alineación exacta por columna
                                </span>
                              </div>
                            </td>
                          </tr>

                          {/* Filas directas de Anuncios */}
                          {anuncios.map((a: any) => {
                            const adImg = a.imagenUrl || a.imagen_url || a.imagen || a.piezagrafica || a.urlAnuncio;
                            const adName = a.anuncio || a.ad_name || "Anuncio sin nombre";
                            const adId = a.ad_id || a.adId || a.id;

                            return (
                              <tr
                                key={a.id || adId}
                                className={`border-b transition-colors ${
                                  isDark
                                    ? "bg-[#141417] hover:bg-[#1E1E22] border-[#2A2A2E] text-slate-200"
                                    : "bg-slate-50/60 hover:bg-slate-100 border-slate-200 text-slate-900"
                                }`}
                              >
                                {/* Col 1: Indentador */}
                                <td className="py-2.5 px-2 text-center w-8">
                                  <span className="text-slate-400 dark:text-slate-600 text-xs font-mono">└</span>
                                </td>

                                {/* Col 2: Origen Badge */}
                                <td className="py-2.5 px-4 text-center">
                                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold border ${
                                    isDark ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-blue-100 text-blue-800 border-blue-200"
                                  }`}>
                                    Meta Ad
                                  </span>
                                </td>

                                {/* Col 3: Pieza Gráfica */}
                                <td className="py-2.5 px-4 text-center">
                                  {adImg ? (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setPreviewAnuncio({ name: adName, url: adImg });
                                      }}
                                      className="group relative inline-flex items-center justify-center w-10 h-10 overflow-hidden rounded-xl border border-slate-300 dark:border-slate-700 shadow-sm bg-white focus:outline-none transition-transform hover:scale-105 cursor-pointer"
                                      title="Ver anuncio completo"
                                    >
                                      <img src={adImg} alt={adName} className="max-w-full max-h-full w-auto h-auto object-contain" />
                                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                        <Eye className="w-3.5 h-3.5 text-white" />
                                      </div>
                                    </button>
                                  ) : (
                                    <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-slate-100 dark:bg-[#252528] border border-slate-200 dark:border-slate-800">
                                      <ImageIcon className="w-4 h-4 text-slate-400 opacity-60" />
                                    </span>
                                  )}
                                </td>

                                {/* Col 4: Nombre, ID y Compras */}
                                <td className="py-2.5 px-4 font-bold max-w-[280px] truncate" title={adName}>
                                  <span className="text-xs font-bold text-slate-900 dark:text-white block truncate">{adName}</span>
                                  <div className="flex items-center gap-2 mt-0.5">
                                    {adId && <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono font-medium">ID: {adId}</span>}
                                    {(a.comprasCy || 0) > 0 ? (
                                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300">
                                        {a.comprasCy} compras · CPA: {fmtMoney(a.costoCompraCy || 0)}
                                      </span>
                                    ) : (
                                      <span className="text-[9px] text-slate-500 dark:text-slate-400 font-medium">0 compras</span>
                                    )}
                                  </div>
                                </td>

                                {/* Col 5: Inversión */}
                                <td className={`py-2.5 px-4 text-right font-bold whitespace-nowrap ${isDark ? "text-blue-400" : "text-blue-600"}`}>
                                  <span className="text-xs">{fmtMoney(a.gastoCy || 0)}</span>
                                  <span className="text-[10px] block font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                                    YoY: <span className="font-bold text-slate-900 dark:text-slate-100">{fmtMoney(a.gastoYoy || 0)}</span> | WoW: <span className="font-bold text-slate-900 dark:text-slate-100">{fmtMoney(a.gastoWow || 0)}</span>
                                  </span>
                                </td>

                                {/* Col 6: Clics & CPC */}
                                <td className="py-2.5 px-4 text-right font-semibold whitespace-nowrap">
                                  <span className="text-xs">{(a.clicsCy || 0).toLocaleString("es-CL")} clics</span>
                                  <span className="text-[10px] block font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                                    CPC: <span className="font-bold text-slate-900 dark:text-slate-100">{fmtMoney(a.cpcCy || 0)}</span>
                                  </span>
                                </td>

                                {/* Col 7: CTR */}
                                <td className="py-2.5 px-4 text-right font-semibold whitespace-nowrap">
                                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold">{(a.ctrCy || 0).toFixed(1)}%</span>
                                  <span className="text-[10px] block font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                                    YoY: <span className="font-bold text-slate-900 dark:text-slate-100">{(a.ctrYoy || 0).toFixed(1)}%</span>
                                  </span>
                                </td>

                                {/* Col 8: ROAS */}
                                <td className={`py-2.5 px-4 text-right font-extrabold whitespace-nowrap ${(a.roasCy || 0) > 0 ? (isDark ? "text-purple-400" : "text-purple-700") : "text-slate-500"}`}>
                                  <span className="text-xs">{(a.roasCy || 0) > 0 ? `${(a.roasCy).toFixed(2)}x` : "0.00x"}</span>
                                  <span className="text-[10px] block font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                                    WoW: <span className="font-bold text-slate-900 dark:text-slate-100">{(a.roasWow || 0) > 0 ? `${(a.roasWow).toFixed(2)}x` : "0.00x"}</span>
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </>
                      )
                    )}
                    </React.Fragment>
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

      {previewAnuncio && (
        <div
          className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setPreviewAnuncio(null)}
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
                  Anuncio Individual · Meta
                </span>
                <h4 className="text-base font-bold truncate max-w-xs mt-0.5">{previewAnuncio.name}</h4>
              </div>
              <button
                onClick={() => setPreviewAnuncio(null)}
                className="p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-[#2C2C2E] text-slate-400 hover:text-slate-200 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-[#2C2C2E] bg-black/5 flex items-center justify-center h-[450px] w-full">
              <img
                src={previewAnuncio.url}
                alt={previewAnuncio.name}
                className="w-full h-full object-contain rounded-xl shadow-md"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setPreviewAnuncio(null)}
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