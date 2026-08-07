import React, { useState, useMemo, useRef, useEffect } from 'react';
import { StockItem, ThemeMode } from '../types';
import { Search, X } from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchStock } from '../services/api';
import { CrossFilterBanner } from '../components/CrossFilterBanner';
import { SortableTh } from '../components/SortableTh';

interface Props {
  theme: ThemeMode;
}

export const StockView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { selectedCategory } = useGlobalFilter();
  const [search, setSearch] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const [STOCK_DATA, setStockData] = useState<StockItem[]>([]);
  const [disponible, setDisponible] = useState(true);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchStock()
      .then((res) => {
        setDisponible(res.disponible);
        setMensaje(res.mensaje);
        setStockData(res.items as StockItem[]);
      })
      .catch((err) => {
        setDisponible(false);
        setMensaje(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  // Nombres reales de bodega
  const bodegasReales = useMemo(() => {
    const set = new Set<string>();
    STOCK_DATA.forEach((item) => Object.keys(item.bodegas || {}).forEach((b) => set.add(b)));
    return Array.from(set).sort();
  }, [STOCK_DATA]);

  // Todas las categorías reales disponibles
  const todasLasCategorias = useMemo(() => {
    const map: Record<string, number> = {};
    STOCK_DATA.forEach((item) => {
      if (item.totalStock > 0) {
        map[item.categoria] = (map[item.categoria] || 0) + 1;
      }
    });
    return Object.entries(map)
      .map(([categoria, count]) => ({ categoria, count }))
      .sort((a, b) => b.count - a.count);
  }, [STOCK_DATA]);

  // Selección única para la tabla superior "por categoría"
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState<string>('');

  // Estado de ordenamiento propio para la tabla "Stock por Categoría"
  const [sortKeyCategoria, setSortKeyCategoria] = useState<string>('totalStock');
  const [sortDirCategoria, setSortDirCategoria] = useState<'asc' | 'desc'>('desc');
  
  const handleSortCategoria = (key: string) => {
    if (sortKeyCategoria === key) {
      setSortDirCategoria((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKeyCategoria(key);
      setSortDirCategoria('desc');
    }
  };

  useEffect(() => {
    if (todasLasCategorias.length > 0 && !categoriaSeleccionada) {
      setCategoriaSeleccionada(todasLasCategorias[0].categoria);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [todasLasCategorias]);

  const itemsCategoriaSeleccionada = useMemo(() => {
    const filtrados = STOCK_DATA.filter((i) => i.categoria === categoriaSeleccionada && i.totalStock > 0);
    return [...filtrados].sort((a: any, b: any) => {
      let aVal = a[sortKeyCategoria];
      let bVal = b[sortKeyCategoria];
      if (aVal === undefined || aVal === null) aVal = '';
      if (bVal === undefined || bVal === null) bVal = '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();

      if (aVal < bVal) return sortDirCategoria === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirCategoria === 'asc' ? 1 : -1;
      return 0;
    });
  }, [STOCK_DATA, categoriaSeleccionada, sortKeyCategoria, sortDirCategoria]);

  // Table sorting state
  const [sortKey, setSortKey] = useState<string>('totalStock');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const suggestions = useMemo(() => {
    if (!search.trim()) return [];
    const q = search.trim().toLowerCase();
    return STOCK_DATA.filter(
      (item) => item.sku.toLowerCase().includes(q) || item.producto.toLowerCase().includes(q)
    ).slice(0, 6);
  }, [search, STOCK_DATA]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const filteredStock = useMemo(() => {
    let list = STOCK_DATA.filter((item) => {
      if (selectedCategory && selectedCategory !== 'Todas') {
        if (item.categoria !== selectedCategory) return false;
      }
      if (search.trim()) {
        const query = search.toLowerCase();
        return item.sku.toLowerCase().includes(query) || item.producto.toLowerCase().includes(query);
      }
      return true;
    });

    return [...list].sort((a: any, b: any) => {
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
  }, [STOCK_DATA, selectedCategory, search, sortKey, sortDir]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <CrossFilterBanner theme={theme} />

      {!disponible && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-amber-500/10 text-amber-300' : 'bg-amber-50 text-amber-700'}`}>
          {mensaje}
        </div>
      )}
      {loading && (
        <div className={`px-4 py-2.5 rounded-xl text-[12.5px] ${isDark ? 'bg-white/5 text-white/50' : 'bg-black/5 text-black/50'}`}>
          Cargando stock...
        </div>
      )}

      {/* 1 selector + tabla por categoría */}
      <div
        className={`p-4 rounded-xl border shadow-md space-y-3 ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500">
            📍 STOCK POR CATEGORÍA
          </h3>
          <select
            value={categoriaSeleccionada}
            onChange={(e) => setCategoriaSeleccionada(e.target.value)}
            className={`text-xs font-bold px-3 py-1.5 rounded-lg border outline-none ${
              isDark ? 'bg-[#17171A] border-[#333339] text-blue-400' : 'bg-slate-50 border-slate-200 text-blue-600'
            }`}
          >
            {todasLasCategorias.length === 0 && <option value="">Cargando...</option>}
            {todasLasCategorias.map((cat) => (
              <option key={cat.categoria} value={cat.categoria}>
                {cat.categoria} ({cat.count})
              </option>
            ))}
          </select>
        </div>

        <div className="overflow-auto max-h-[320px] rounded-lg border border-slate-200/60 dark:border-[#2C2C2E]">
          <table className="w-full text-left text-xs border-collapse min-w-[900px]">
            <thead className={`sticky top-0 z-10 ${isDark ? 'bg-[#17171A]' : 'bg-slate-50'}`}>
              <tr className={`border-b text-[11px] font-bold ${
                isDark ? 'border-[#333339] text-[#B8B8BE]' : 'border-slate-200 text-slate-500'
              }`}>
                <SortableTh label="SKU" sortKey="sku" currentSortKey={sortKeyCategoria} sortDirection={sortDirCategoria} onSort={handleSortCategoria} />
                <SortableTh label="PRODUCTO" sortKey="producto" currentSortKey={sortKeyCategoria} sortDirection={sortDirCategoria} onSort={handleSortCategoria} />
                {bodegasReales.map((bodega) => (
                  <th key={bodega} className="p-2 text-center whitespace-nowrap">{bodega.toUpperCase()}</th>
                ))}
                <SortableTh label="TOTAL STOCK" sortKey="totalStock" currentSortKey={sortKeyCategoria} sortDirection={sortDirCategoria} onSort={handleSortCategoria} align="center" className="font-extrabold text-blue-500" />
                <SortableTh label="VENTA 14D" sortKey="venta14d" currentSortKey={sortKeyCategoria} sortDirection={sortDirCategoria} onSort={handleSortCategoria} align="center" />
                <SortableTh label="DÍAS COB." sortKey="diasCobertura" currentSortKey={sortKeyCategoria} sortDirection={sortDirCategoria} onSort={handleSortCategoria} align="center" />
                <SortableTh label="ESTADO" sortKey="estado" currentSortKey={sortKeyCategoria} sortDirection={sortDirCategoria} onSort={handleSortCategoria} align="center" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {itemsCategoriaSeleccionada.length === 0 ? (
                <tr>
                  <td colSpan={4 + bodegasReales.length} className="p-4 text-center text-xs text-slate-400 italic">
                    Sin SKUs en esta categoría
                  </td>
                </tr>
              ) : (
                itemsCategoriaSeleccionada.map((item) => (
                  <tr key={item.sku} className={`hover:bg-blue-500/10 transition-colors ${
                    isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                  }`}>
                    <td className="p-2 font-bold text-blue-500">{item.sku}</td>
                    <td className="p-2 font-semibold max-w-xs truncate">{item.producto}</td>
                    {bodegasReales.map((bodega) => (
                      <td key={bodega} className="p-2 text-center">{item.bodegas?.[bodega] ?? 0}</td>
                    ))}
                    <td className="p-2 text-center font-extrabold text-blue-500">{item.totalStock}</td>
                    <td className="p-2 text-center">{item.venta14d}</td>
                    <td className="p-2 text-center font-bold">{item.diasCobertura.toFixed(1)}d</td>
                    <td className="p-2 text-center font-bold">{item.estado}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Consolidado de Stock */}
      <div
        className={`p-4 rounded-xl border shadow-md space-y-4 ${
          isDark ? 'bg-[#1F1F23] border-[#333339]' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-blue-500">
            📊 CONSOLIDADO DE STOCK (TODAS LAS BODEGAS BSALE)
          </h3>

          <div ref={searchRef} className="relative w-full sm:w-80">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all ${
              isDark ? 'bg-[#17171A] border-[#333339] focus-within:border-blue-500' : 'bg-slate-50 border-slate-200 focus-within:border-blue-500'
            }`}>
              <Search className="w-3.5 h-3.5 text-blue-500 shrink-0" />
              <input
                type="text"
                placeholder="Búsqueda predictiva SKU / Producto..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                className="bg-transparent focus:outline-none w-full"
              />
              {search && (
                <button
                  onClick={() => {
                    setSearch('');
                    setShowSuggestions(false);
                  }}
                  className="p-0.5 hover:opacity-75 text-slate-400"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {showSuggestions && suggestions.length > 0 && (
              <div className={`absolute top-full left-0 right-0 mt-1.5 rounded-xl border shadow-2xl z-50 overflow-hidden text-xs animate-in fade-in slide-in-from-top-1 duration-150 ${
                isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-200 text-slate-800'
              }`}>
                <div className="p-2 border-b border-slate-200 dark:border-[#2C2C2E] flex items-center justify-between text-[10px] text-blue-500 font-bold uppercase tracking-wider">
                  <span>Sugerencias Predictivas</span>
                  <span className="text-slate-400 font-normal">Coincidencias ({suggestions.length})</span>
                </div>
                <div className="max-h-60 overflow-y-auto divide-y divide-slate-100 dark:divide-[#2C2C2E]">
                  {suggestions.map((item) => (
                    <button
                      key={item.sku}
                      onClick={() => {
                        setSearch(item.sku);
                        setShowSuggestions(false);
                      }}
                      className="w-full text-left p-2.5 hover:bg-blue-500/10 flex items-center justify-between transition-colors group"
                    >
                      <div className="truncate pr-2">
                        <div className="flex items-center gap-1.5">
                          <span className="font-extrabold text-blue-500">{item.sku}</span>
                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-600'}`}>
                            {item.categoria}
                          </span>
                        </div>
                        <div className="text-[11px] opacity-80 truncate mt-0.5 group-hover:text-blue-400">
                          {item.producto}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="font-bold block text-blue-500">{item.totalStock} u.</span>
                        <span className="text-[10px] opacity-60">{item.estado}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="overflow-auto max-h-[480px] rounded-lg border border-slate-200/60 dark:border-[#2C2C2E]">
          <table className="w-full text-left text-xs border-collapse min-w-[900px]">
            <thead className={`sticky top-0 z-10 ${isDark ? 'bg-[#17171A]' : 'bg-slate-50'}`}>
              <tr className={`border-b text-[11px] font-bold ${
                isDark ? 'border-[#333339] text-[#B8B8BE]' : 'border-slate-200 text-slate-500'
              }`}>
                <SortableTh label="SKU" sortKey="sku" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="PRODUCTO" sortKey="producto" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                <SortableTh label="CATEGORÍA" sortKey="categoria" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} />
                {bodegasReales.map((bodega) => (
                  <th key={bodega} className="p-2 text-center whitespace-nowrap">{bodega.toUpperCase()}</th>
                ))}
                <SortableTh label="TOTAL STOCK" sortKey="totalStock" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" className="font-extrabold text-blue-500" />
                <SortableTh label="VENTA 14D" sortKey="venta14d" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                <SortableTh label="DÍAS COB." sortKey="diasCobertura" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
                <SortableTh label="ESTADO" sortKey="estado" currentSortKey={sortKey} sortDirection={sortDir} onSort={handleSort} align="center" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-[#333339]">
              {filteredStock.map((item) => (
                <tr key={item.sku} className={`hover:bg-blue-500/10 transition-colors ${
                  isDark ? 'text-[#EDEDED]' : 'text-slate-800'
                }`}>
                  <td className="p-2 font-bold text-blue-500">{item.sku}</td>
                  <td className="p-2 font-semibold max-w-xs truncate">{item.producto}</td>
                  <td className="p-2 text-[11px] opacity-80">{item.categoria}</td>
                  {bodegasReales.map((bodega) => (
                    <td key={bodega} className="p-2 text-center">{item.bodegas?.[bodega] ?? 0}</td>
                  ))}
                  <td className="p-2 text-center font-extrabold text-blue-500">{item.totalStock}</td>
                  <td className="p-2 text-center">{item.venta14d}</td>
                  <td className="p-2 text-center font-bold">{item.diasCobertura.toFixed(1)}d</td>
                  <td className="p-2 text-center font-bold">{item.estado}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};