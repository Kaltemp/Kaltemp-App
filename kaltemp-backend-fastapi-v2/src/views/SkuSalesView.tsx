import React, { useState, useMemo, useEffect } from 'react';
import { ThemeMode, SkuNode, SellerNode, DocumentNode, ClientNode } from '../types';
import { ChevronRight, ChevronDown, Package, User, FileText, Building2, CheckCircle2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';
import { useGlobalFilter, ALL_REPS, ALL_CHANNELS, ALL_CATEGORIES } from '../context/FilterContext';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';
import { fetchSkuProductos, fetchSkuVendedores, fetchSkuDocumentos, fetchSkuClientes, fetchSkuCategoriaResumen, fetchSkuCanalResumen } from '../services/api';

interface Props {
  theme: ThemeMode;
  selectedCategory?: string;
  onCategoryChange?: (cat: string) => void;
}

interface ChannelItem {
  canal: string;
  venta: number;
  yoy: number | null;
  yoyPct: number;
}

export const SkuSalesView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';

  const {
    selectedCategories,
    selectedChannels,
    selectedReps,
    startDate,
    endDate
  } = useGlobalFilter();

  const [selectedCategory, setSelectedCategory] = useState<string>('Todas');
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);

  const [expandedP, setExpandedP] = useState<Record<string, boolean>>({});
  const [expandedV, setExpandedV] = useState<Record<string, boolean>>({});
  const [expandedD, setExpandedD] = useState<Record<string, boolean>>({});

  const [productos, setProductos] = useState<SkuNode[]>([]);
  const [loadingProductos, setLoadingProductos] = useState(true);
  const [vendedoresPorProducto, setVendedoresPorProducto] = useState<Record<string, SellerNode[]>>({});
  const [documentosPorVendedor, setDocumentosPorVendedor] = useState<Record<string, DocumentNode[]>>({});
  const [clientesPorDocumento, setClientesPorDocumento] = useState<Record<string, ClientNode[]>>({});

  const vendedoresParaBackend = selectedReps.length < ALL_REPS.length ? selectedReps : undefined;
  const canalesBaseGlobal = selectedChannels.length < ALL_CHANNELS.length ? selectedChannels : undefined;
  const canalesParaBackend = selectedChannel ? [selectedChannel] : canalesBaseGlobal;
  const categoriasBaseGlobal = selectedCategories.length < ALL_CATEGORIES.length ? selectedCategories : undefined;
  const categoriasParaBackend = (selectedCategory && selectedCategory !== 'Todas') ? [selectedCategory] : categoriasBaseGlobal;

  useEffect(() => {
    setLoadingProductos(true);
    fetchSkuProductos(startDate, endDate, vendedoresParaBackend, canalesParaBackend)
      .then((res) => setProductos(Array.isArray(res) ? res : []))
      .catch(() => setProductos([]))
      .finally(() => setLoadingProductos(false));

    setExpandedP({});
    setExpandedV({});
    setExpandedD({});
    setVendedoresPorProducto({});
    setDocumentosPorVendedor({});
    setClientesPorDocumento({});
  }, [startDate, endDate, JSON.stringify(vendedoresParaBackend), JSON.stringify(canalesParaBackend)]);

  const [sortKey, setSortKey] = useState<string>('ventaCy');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const [chanSortKey, setChanSortKey] = useState<string>('venta');
  const [chanSortDir, setChanSortDir] = useState<'asc' | 'desc'>('desc');

  const [channelsData, setChannelsData] = useState<ChannelItem[]>([]);
  const [categoryChartData, setCategoryChartData] = useState<{ name: string; value: number; color?: string }[]>([]);

  const CHART_COLORS = ['#0A84FF', '#30D158', '#FF9F0A', '#BF5AF2', '#FF453A', '#64D2FF', '#FFD60A', '#FF6482'];

  useEffect(() => {
    fetchSkuCanalResumen(startDate, endDate, vendedoresParaBackend, categoriasParaBackend)
      .then((data) =>
        setChannelsData(Array.isArray(data) ? data.map((d: any) => ({ canal: d.canal, venta: d.venta, yoy: d.yoy, yoyPct: d.yoyPct })) : [])
      )
      .catch(() => setChannelsData([]));

    fetchSkuCategoriaResumen(startDate, endDate, vendedoresParaBackend, canalesParaBackend)
      .then((data) => setCategoryChartData(Array.isArray(data) ? data.map((d, i) => ({ ...d, color: CHART_COLORS[i % CHART_COLORS.length] })) : []))
      .catch(() => setCategoryChartData([]));
  }, [startDate, endDate, JSON.stringify(vendedoresParaBackend), JSON.stringify(canalesParaBackend), JSON.stringify(categoriasParaBackend)]);

  const toggleExpandP = (p: SkuNode) => {
    const willExpand = !expandedP[p.id];
    setExpandedP((prev) => ({ ...prev, [p.id]: willExpand }));
    if (willExpand && !vendedoresPorProducto[p.id]) {
      fetchSkuVendedores(p.nombre, startDate, endDate).then((data) => {
        setVendedoresPorProducto((prev) => ({ ...prev, [p.id]: Array.isArray(data) ? data : [] }));
      });
    }
  };

  const toggleExpandV = (p: SkuNode, v: SellerNode) => {
    const willExpand = !expandedV[v.id];
    setExpandedV((prev) => ({ ...prev, [v.id]: willExpand }));
    if (willExpand && !documentosPorVendedor[v.id]) {
      fetchSkuDocumentos(p.nombre, v.nombre, startDate, endDate).then((data) => {
        setDocumentosPorVendedor((prev) => ({ ...prev, [v.id]: Array.isArray(data) ? data : [] }));
      });
    }
  };

  const toggleExpandD = (p: SkuNode, v: SellerNode, d: DocumentNode) => {
    const willExpand = !expandedD[d.id];
    setExpandedD((prev) => ({ ...prev, [d.id]: willExpand }));
    if (willExpand && !clientesPorDocumento[d.id]) {
      fetchSkuClientes(p.nombre, v.nombre, d.nombre, startDate, endDate).then((data) => {
        setClientesPorDocumento((prev) => ({ ...prev, [d.id]: Array.isArray(data) ? data : [] }));
      });
    }
  };

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const handleChanSort = (key: string) => {
    if (chanSortKey === key) {
      setChanSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setChanSortKey(key);
      setChanSortDir('desc');
    }
  };

  const filteredTree = useMemo(() => {
    let result = (productos || []).filter((item) => {
      if (selectedCategory && selectedCategory !== 'Todas') {
        const cleanCatFilter = selectedCategory.replace(/[🔥♨️🚿🏊]/g, '').trim().toLowerCase();
        if (!item.categoria.toLowerCase().includes(cleanCatFilter)) {
          return false;
        }
      }
      return true;
    });

    return [...result].sort((a: any, b: any) => {
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
  }, [productos, selectedCategory, sortKey, sortDir]);

  const sortedChannels = useMemo(() => {
    return [...(channelsData || [])].sort((a: any, b: any) => {
      let aVal = a[chanSortKey];
      let bVal = b[chanSortKey];
      if (aVal === undefined || aVal === null) aVal = -999999;
      if (bVal === undefined || bVal === null) bVal = -999999;
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (aVal < bVal) return chanSortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return chanSortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [channelsData, chanSortKey, chanSortDir]);

  const handleChannelClick = (canalName: string) => {
    if (selectedChannel === canalName) {
      setSelectedChannel(null);
    } else {
      setSelectedChannel(canalName);
    }
  };

  const handleBarClick = (entry: any) => {
    if (selectedCategory === entry.name) {
      setSelectedCategory('Todas');
    } else {
      setSelectedCategory(entry.name);
    }
  };

  const formatM = (val?: number) => {
    if (val === undefined || val === null) return '-';
    return `$ ${(val / 1000000).toFixed(1)} M`;
  };

  const formatPrice = (val?: number) => {
    if (val === undefined || val === null) return '-';
    return `$ ${Math.round(val).toLocaleString('es-CL')}`;
  };

  const formatPct = (val?: number) => {
    if (val === undefined || val === null) return '-';
    return `${val.toFixed(1)}%`;
  };

  // Estilos de Apple HIG para Fondos y Títulos
  const panelBg = isDark ? "bg-[#1C1C1E] border-[#2C2C2E]" : "bg-white border-slate-200/80 shadow-sm";
  const titleBlue = isDark ? "text-blue-400" : "text-blue-700";
  const titleEmerald = isDark ? "text-emerald-400" : "text-emerald-700";
  const subtextColor = isDark ? "text-[#8E8E93]" : "text-slate-500";
  const tableHeaderClass = isDark ? "border-[#2C2C2E] text-[#8E8E93] bg-[#121214]" : "border-slate-200 text-slate-600 bg-slate-50";

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {/* Main Expandable Tree Table */}
      <div className={`p-5 rounded-2xl border overflow-x-auto ${panelBg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className={`text-xs font-black uppercase tracking-wider flex items-center gap-2 ${titleBlue}`}>
              <Package className="w-4 h-4" /> VENTA POR SKU Y ÁRBOL DESPLEGABLE
            </h3>
          </div>
          <span className="text-[10px] px-2.5 py-1 rounded-xl font-bold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 self-start sm:self-auto flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> Origen: Bsale Matrix ERP (Ordenable)
          </span>
        </div>

        <table className="w-full text-left text-xs border-collapse min-w-[1280px]">
          <thead>
            <tr className={`border-b text-[10px] font-black uppercase tracking-wider ${tableHeaderClass}`}>
              <SortableTh label="DESCRIPCIÓN" sortKey="nombre" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} className="min-w-[280px]" />
              <SortableTh label="CANTIDAD" sortKey="cantCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" className="bg-slate-500/5" />
              <SortableTh label="CANTIDAD WOW" sortKey="cantWow" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
              <SortableTh label="CANTIDAD YOY" sortKey="cantYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
              <SortableTh label="VENTA" sortKey="ventaCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={`${titleBlue} bg-blue-500/5 font-black`} />
              <SortableTh label="WOW" sortKey="ventaWow" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="YOY" sortKey="ventaYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="P. PROMEDIO (ACTUAL)" sortKey="pPromCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className="bg-amber-500/5" />
              <SortableTh label="P. PROMEDIO (WOW)" sortKey="pPromWow" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="P. PROMEDIO (YOY)" sortKey="pPromYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" />
              <SortableTh label="M. FRONTAL" sortKey="margenCy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={`${titleEmerald} bg-emerald-500/5`} />
              <SortableTh label="M. FRONTAL (YOY)" sortKey="margenYoy" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="right" className={titleEmerald} />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-[#2C2C2E]">
            {loadingProductos ? (
              <tr>
                <td colSpan={12} className="p-6 text-center text-xs font-semibold text-slate-400">
                  Cargando árbol de SKUs...
                </td>
              </tr>
            ) : filteredTree.length === 0 ? (
              <tr>
                <td colSpan={12} className="p-6 text-center text-xs text-slate-400 italic">
                  Sin SKUs registrados para este filtro
                </td>
              </tr>
            ) : (
              filteredTree.map((p) => {
                const isPExpanded = !!expandedP[p.id];
                return (
                  <React.Fragment key={p.id}>
                    {/* LEVEL 1: SKU Row */}
                    <tr
                      onClick={() => toggleExpandP(p)}
                      className={`cursor-pointer font-extrabold transition-colors ${
                        isDark ? 'bg-[#121214] hover:bg-[#2C2C2E]' : 'bg-slate-100 hover:bg-slate-200/80 text-slate-900'
                      }`}
                    >
                      <td className="p-2.5 flex items-center gap-2 min-w-[280px]">
                        {isPExpanded ? <ChevronDown className="w-4 h-4 shrink-0 text-blue-500" /> : <ChevronRight className="w-4 h-4 shrink-0 text-blue-500" />}
                        <span className="px-2 py-0.5 rounded-md text-[10px] bg-blue-500/10 text-blue-700 dark:text-blue-400 font-mono font-black shrink-0">
                          N1
                        </span>
                        <span className={`truncate ${titleBlue}`}>[{p.sku}] {p.nombre}</span>
                      </td>
                      <td className="p-2 text-center font-black">{p.cantCy}</td>
                      <td className="p-2 text-center opacity-70">{p.cantWow}</td>
                      <td className="p-2 text-center opacity-70">{p.cantYoy}</td>
                      <td className={`p-2 text-right font-black ${titleBlue}`}>{formatM(p.ventaCy)}</td>
                      <td className="p-2 text-right opacity-70">{formatM(p.ventaWow)}</td>
                      <td className="p-2 text-right opacity-70">{formatM(p.ventaYoy)}</td>
                      <td className="p-2 text-right font-black">{formatPrice(p.pPromCy)}</td>
                      <td className="p-2 text-right opacity-70">{formatPrice(p.pPromWow)}</td>
                      <td className="p-2 text-right opacity-70">{formatPrice(p.pPromYoy)}</td>
                      <td className={`p-2 text-right font-black ${titleEmerald}`}>{formatPct(p.margenCy)}</td>
                      <td className={`p-2 text-right font-bold ${titleEmerald}`}>{formatPct(p.margenYoy)}</td>
                    </tr>

                    {/* LEVEL 2: Seller Rows */}
                    {isPExpanded &&
                      (vendedoresPorProducto[p.id] || []).map((v) => {
                        const isVExpanded = !!expandedV[v.id];
                        return (
                          <React.Fragment key={v.id}>
                            <tr
                              onClick={() => toggleExpandV(p, v)}
                              className={`cursor-pointer text-[11px] transition-colors ${
                                isDark ? 'bg-[#1F1F23] hover:bg-[#2C2C2E]' : 'bg-slate-50 hover:bg-slate-100 text-slate-800'
                              }`}
                            >
                              <td className="p-2 pl-8 font-extrabold flex items-center gap-2 min-w-[280px]">
                                {isVExpanded ? <ChevronDown className="w-3.5 h-3.5 text-amber-500 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-400 font-mono font-black shrink-0">
                                  N2 Vendedor
                                </span>
                                <User className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                                <span>{v.nombre}</span>
                              </td>
                              <td className="p-2 text-center font-bold">{v.cantCy}</td>
                              <td className="p-2 text-center opacity-60">{v.cantWow ?? '-'}</td>
                              <td className="p-2 text-center opacity-60">{v.cantYoy ?? '-'}</td>
                              <td className={`p-2 text-right font-black ${titleBlue}`}>{formatM(v.ventaCy)}</td>
                              <td className="p-2 text-right opacity-60">{formatM(v.ventaWow)}</td>
                              <td className="p-2 text-right opacity-60">{formatM(v.ventaYoy)}</td>
                              <td className="p-2 text-right font-bold">{formatPrice(v.pPromCy)}</td>
                              <td className="p-2 text-right opacity-60">{formatPrice(v.pPromWow ?? v.pPromCy)}</td>
                              <td className="p-2 text-right opacity-60">{formatPrice(v.pPromYoy ?? v.pPromCy)}</td>
                              <td className={`p-2 text-right font-black ${titleEmerald}`}>{formatPct(v.margenCy)}</td>
                              <td className={`p-2 text-right font-bold ${titleEmerald}`}>{formatPct(v.margenYoy ?? (v.margenCy - 1.0))}</td>
                            </tr>

                            {/* LEVEL 3: Document Rows */}
                            {isVExpanded &&
                              (documentosPorVendedor[v.id] || []).map((d) => {
                                const isDExpanded = !!expandedD[d.id];
                                return (
                                  <React.Fragment key={d.id}>
                                    <tr
                                      onClick={() => toggleExpandD(p, v, d)}
                                      className={`cursor-pointer text-[11px] transition-colors ${
                                        isDark ? 'bg-[#17171A] hover:bg-[#222226]' : 'bg-slate-100/60 hover:bg-slate-100 text-slate-800'
                                      }`}
                                    >
                                      <td className="p-2 pl-14 font-semibold flex items-center gap-2 min-w-[280px]">
                                        {isDExpanded ? <ChevronDown className="w-3 h-3 text-emerald-500 shrink-0" /> : <ChevronRight className="w-3 h-3 text-emerald-500 shrink-0" />}
                                        <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-mono font-bold shrink-0">
                                          N3 Doc
                                        </span>
                                        <FileText className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                                        <span>{d.nombre}</span>
                                      </td>
                                      <td className="p-2 text-center font-bold">{d.cantCy}</td>
                                      <td className="p-2 text-center opacity-50">{d.cantWow ?? '-'}</td>
                                      <td className="p-2 text-center opacity-50">{d.cantYoy ?? '-'}</td>
                                      <td className={`p-2 text-right font-black ${titleEmerald}`}>{formatM(d.ventaCy)}</td>
                                      <td className="p-2 text-right opacity-50">{formatM(d.ventaWow)}</td>
                                      <td className="p-2 text-right opacity-50">{formatM(d.ventaYoy)}</td>
                                      <td className="p-2 text-right opacity-80">{formatPrice(d.pPromCy)}</td>
                                      <td className="p-2 text-right opacity-50">{formatPrice(d.pPromWow ?? d.pPromCy)}</td>
                                      <td className="p-2 text-right opacity-50">{formatPrice(d.pPromYoy ?? d.pPromCy)}</td>
                                      <td className={`p-2 text-right font-black ${titleEmerald}`}>{formatPct(d.margenCy)}</td>
                                      <td className={`p-2 text-right font-bold ${titleEmerald}`}>{formatPct(d.margenYoy ?? (d.margenCy - 1.0))}</td>
                                    </tr>

                                    {/* LEVEL 4: Client Rows */}
                                    {isDExpanded &&
                                      (clientesPorDocumento[d.id] || []).map((c) => (
                                        <tr
                                          key={c.id}
                                          className={`text-[10px] ${
                                            isDark ? 'bg-[#121214] text-slate-400' : 'bg-slate-200/50 text-slate-700'
                                          }`}
                                        >
                                          <td className="p-1.5 pl-20 font-bold flex items-center gap-2 min-w-[280px]">
                                            <span className="px-1 py-0.2 rounded text-[9px] bg-purple-500/10 text-purple-700 dark:text-purple-400 font-mono font-bold shrink-0">
                                              N4 Cliente
                                            </span>
                                            <Building2 className="w-3 h-3 text-purple-500 shrink-0" />
                                            <span className="font-extrabold text-purple-700 dark:text-purple-300">{c.nombre}</span>
                                          </td>
                                          <td className="p-1.5 text-center font-bold">{c.cantCy}</td>
                                          <td className="p-1.5 text-center opacity-40">{c.cantWow ?? '-'}</td>
                                          <td className="p-1.5 text-center opacity-40">{c.cantYoy ?? '-'}</td>
                                          <td className="p-1.5 text-right font-black text-purple-700 dark:text-purple-400">{formatM(c.ventaCy)}</td>
                                          <td className="p-1.5 text-right opacity-40">{formatM(c.ventaWow)}</td>
                                          <td className="p-1.5 text-right opacity-40">{formatM(c.ventaYoy)}</td>
                                          <td className="p-1.5 text-right font-medium">{formatPrice(c.pPromCy)}</td>
                                          <td className="p-1.5 text-right opacity-40">{formatPrice(c.pPromWow ?? c.pPromCy)}</td>
                                          <td className="p-1.5 text-right opacity-40">{formatPrice(c.pPromYoy ?? c.pPromCy)}</td>
                                          <td className={`p-1.5 text-right font-bold ${titleEmerald}`}>{formatPct(c.margenCy)}</td>
                                          <td className={`p-1.5 text-right font-bold ${titleEmerald}`}>{formatPct(c.margenYoy ?? (c.margenCy - 1.0))}</td>
                                        </tr>
                                      ))}
                                  </React.Fragment>
                                );
                              })}
                          </React.Fragment>
                        );
                      })}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Grid: Bar Chart on Left + Canal Summary Table on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Left Column: Bar Chart */}
        <div className={`p-5 rounded-2xl border shadow-sm flex flex-col justify-between ${panelBg}`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className={`text-xs font-black uppercase tracking-wider ${titleBlue}`}>
              🏷️ VENTA TOTAL POR CATEGORÍA ($ MILLONES)
            </h3>
            <span className={`text-[10px] font-medium ${subtextColor}`}>Haz clic en una barra para filtro cruzado</span>
          </div>

          <div className="w-full" style={{ height: Math.max(256, categoryChartData.length * 38) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={categoryChartData} margin={{ left: 8, right: 28 }}>
                <XAxis type="number" stroke={isDark ? '#8E8E93' : '#64748b'} fontSize={10} unit="M" tickLine={false} />
                <YAxis dataKey="name" type="category" stroke={isDark ? '#F5F5F7' : '#1e293b'} fontSize={10} width={150} interval={0} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#1C1C1E' : '#ffffff',
                    borderColor: isDark ? '#2C2C2E' : '#e2e8f0',
                    color: isDark ? '#F5F5F7' : '#1e293b',
                    borderRadius: '12px'
                  }}
                />
                <Bar
                  dataKey="value"
                  name="Venta ($M)"
                  radius={[0, 4, 4, 0]}
                  className="cursor-pointer"
                >
                  {categoryChartData.map((entry, index) => {
                    const isSelected = selectedCategory === entry.name;
                    return (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.color}
                        opacity={selectedCategory !== 'Todas' ? (isSelected ? 1 : 0.35) : 1}
                        stroke={isSelected ? '#ffffff' : undefined}
                        strokeWidth={isSelected ? 2 : 0}
                        onClick={() => handleBarClick(entry)}
                        style={{ cursor: 'pointer' }}
                      />
                    );
                  })}
                  <LabelList dataKey="value" position="right" fill={isDark ? '#EDEDED' : '#1e293b'} fontSize={10} fontWeight="bold" formatter={(val: number) => `$${val.toFixed(1)} M`} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Column: Venta por Canal Table */}
        <div className={`p-5 rounded-2xl border shadow-sm flex flex-col ${panelBg}`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className={`text-xs font-black uppercase tracking-wider ${titleBlue}`}>
              🏬 VENTA POR CANAL
            </h3>
            <span className={`text-[10px] font-medium ${subtextColor}`}>Haz clic para filtro cruzado u ordenamiento</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className={`border-b text-[10px] font-black uppercase ${tableHeaderClass}`}>
                  <SortableTh label="CANAL" sortKey="canal" currentSortKey={chanSortKey} sortDirection={chanSortDir} onSort={handleChanSort} />
                  <SortableTh label="VENTA" sortKey="venta" currentSortKey={chanSortKey} sortDirection={chanSortDir} onSort={handleChanSort} align="right" />
                  <SortableTh label="YOY" sortKey="yoy" currentSortKey={chanSortKey} sortDirection={chanSortDir} onSort={handleChanSort} align="right" />
                  <SortableTh label="YOY %" sortKey="yoyPct" currentSortKey={chanSortKey} sortDirection={chanSortDir} onSort={handleChanSort} align="right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-[#2C2C2E] font-medium">
                {sortedChannels.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-4 text-center text-slate-400 italic">
                      Sin datos de canales para esta selección
                    </td>
                  </tr>
                ) : (
                  sortedChannels.map((c) => {
                    const isSelected = selectedChannel === c.canal;
                    const isPositive = c.yoyPct !== null && c.yoyPct >= 0;

                    const rowBg = isSelected
                      ? (isDark ? 'bg-blue-600/30 font-bold border-l-4 border-l-blue-400' : 'bg-blue-50 font-bold border-l-4 border-l-blue-600')
                      : (isDark ? 'hover:bg-[#2C2C2E] text-[#F5F5F7]' : 'hover:bg-slate-50 text-slate-800');

                    return (
                      <tr
                        key={c.canal}
                        onClick={() => handleChannelClick(c.canal)}
                        className={`cursor-pointer transition-colors ${rowBg}`}
                      >
                        <td className={`p-2.5 font-black uppercase flex items-center gap-1.5 ${titleBlue}`}>
                          {isSelected && <span className="w-2 h-2 rounded-full bg-blue-500" />}
                          {c.canal}
                        </td>
                        <td className="p-2.5 text-right font-black">
                          $ {c.venta.toFixed(1).replace('.', ',')} M
                        </td>
                        <td className={`p-2.5 text-right font-semibold ${subtextColor}`}>
                          {c.yoy !== null ? `$ ${c.yoy.toFixed(1).replace('.', ',')} M` : '—'}
                        </td>
                        <td className={`p-2.5 text-right font-black ${
                          c.yoyPct === null 
                            ? subtextColor 
                            : isPositive 
                            ? (isDark ? 'text-emerald-400' : 'text-emerald-700') 
                            : (isDark ? 'text-rose-400' : 'text-rose-700')
                        }`}>
                          {c.yoyPct === null ? 'Sin dato AA' : `${c.yoyPct.toFixed(1).replace('.', ',')}%`}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SkuSalesView;