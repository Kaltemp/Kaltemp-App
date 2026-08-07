import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { fetchFiltrosGlobales } from '../services/api';

// Categoría SKU y Vendedor YA NO son listas fijas: se cargan una sola vez
// desde /api/filtros con los valores REALES que existen en `ventas`
// (sincronizada 1:1 desde Bsale). Arrancan vacías; FilterProvider las
// llena al montar. Se exportan como `let` + mutación in-place (splice)
// para que los componentes que ya las importan directamente (Sidebar,
// CrossFilterBanner, etc.) vean el valor actualizado sin tener que
// migrar cada uno a leerlas del hook.
export let ALL_CATEGORIES: string[] = [];
export let ALL_REPS: string[] = [];
export let ALL_WAREHOUSES: string[] = [];

// Canal de Venta SÍ es una lista fija, definida a propósito en el código
// matriz (no viene de Bsale) -- se deja tal cual estaba, sumando los 3
// canales reales que faltaban (confirmados contra datos reales: eran
// negativos por devoluciones/notas de crédito y quedaban ocultos, lo que
// inflaba el TOTAL mostrado en pantalla).
export const ALL_CHANNELS = [
  'SHOWROOM',
  'DISTRIBUIDORES',
  'D2C',
  'FALABELLA',
  'SERVICIO TÉCNICO',
  'PARIS',
  'WALMART MKP',
  'INMOBILIARIAS',
  'MERCADOLIBRE',
  'TOM PALMER',
  'OTROS'
];

export const ALL_STATUSES = [
  '⏳ Pendiente',
  '✅ Despachado'
];

interface FilterContextType {
  // Multi-select lists
  selectedCategories: string[];
  setSelectedCategories: (cats: string[]) => void;
  selectedChannels: string[];
  setSelectedChannels: (channels: string[]) => void;
  selectedReps: string[];
  setSelectedReps: (reps: string[]) => void;
  selectedWarehouses: string[];
  setSelectedWarehouses: (bodegas: string[]) => void;
  selectedStatuses: string[];
  setSelectedStatuses: (statuses: string[]) => void;

  // Legacy single-value compatibility getters/setters
  selectedCategory: string;
  setSelectedCategory: (cat: string) => void;
  selectedChannel: string | null;
  setSelectedChannel: (channel: string | null) => void;
  selectedRep: string | null;
  setSelectedRep: (rep: string | null) => void;
  selectedWarehouse: string | null;
  setSelectedWarehouse: (bodega: string | null) => void;
  selectedStatus: string | null;
  setSelectedStatus: (status: string | null) => void;

  // Matching helpers
  matchesCategory: (cat: string) => boolean;
  matchesChannel: (channel: string) => boolean;
  matchesRep: (rep: string) => boolean;
  matchesWarehouse: (bodega: string) => boolean;
  matchesStatus: (status: string) => boolean;

  startDate: string;
  setStartDate: (date: string) => void;
  endDate: string;
  setEndDate: (date: string) => void;

  clearAllCrossFilters: () => void;
  hasActiveCrossFilters: boolean;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export const FilterProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>(ALL_CHANNELS);
  const [selectedReps, setSelectedReps] = useState<string[]>([]);
  const [selectedWarehouses, setSelectedWarehouses] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(ALL_STATUSES);
  const [filtrosCargados, setFiltrosCargados] = useState(false);

  const [startDate, setStartDate] = useState<string>('2026-07-01');
  const [endDate, setEndDate] = useState<string>('2026-07-28');

  // Carga única al montar: trae las categorías y vendedores REALES desde
  // /api/filtros (Bsale vía `ventas`), y arranca con "todos seleccionados".
  useEffect(() => {
    fetchFiltrosGlobales()
      .then(({ categorias, vendedores, bodegas }) => {
        ALL_CATEGORIES.splice(0, ALL_CATEGORIES.length, ...categorias);
        ALL_REPS.splice(0, ALL_REPS.length, ...vendedores);
        ALL_WAREHOUSES.splice(0, ALL_WAREHOUSES.length, ...(bodegas || []));
        setSelectedCategories(categorias);
        setSelectedReps(vendedores);
        setSelectedWarehouses(bodegas || []);
      })
      .catch((err) => {
        console.error('No se pudieron cargar categorías/vendedores/bodegas desde /api/filtros:', err);
      })
      .finally(() => setFiltrosCargados(true));
  }, []);

  // Matching helper methods
  const matchesCategory = (cat: string) => {
    if (!filtrosCargados) return true; // evita ocultar todo mientras carga /api/filtros
    if (!cat) return true;
    if (selectedCategories.length === 0) return false;
    return selectedCategories.some(
      (c) => c === cat || cat.toLowerCase().includes(c.toLowerCase()) || c.toLowerCase().includes(cat.toLowerCase())
    );
  };

  const matchesChannel = (channel: string) => {
    if (!channel) return true;
    if (selectedChannels.length === 0) return false;
    return selectedChannels.some(
      (ch) => ch.toUpperCase() === channel.toUpperCase() || channel.toUpperCase().includes(ch.toUpperCase())
    );
  };

  const matchesRep = (rep: string) => {
    if (!filtrosCargados) return true; // evita ocultar todo mientras carga /api/filtros
    if (!rep) return true;
    if (selectedReps.length === 0) return false;
    return selectedReps.some(
      (r) => r.toUpperCase() === rep.toUpperCase() || rep.toUpperCase().includes(r.toUpperCase())
    );
  };

  const matchesWarehouse = (bodega: string) => {
    if (!filtrosCargados) return true; // evita ocultar todo mientras carga /api/filtros
    if (!bodega) return true;
    if (selectedWarehouses.length === 0) return false;
    return selectedWarehouses.some(
      (b) => b.toUpperCase() === bodega.toUpperCase()
    );
  };

  const matchesStatus = (status: string) => {
    if (!status) return true;
    if (selectedStatuses.length === 0) return false;
    return selectedStatuses.some(
      (s) => s.toLowerCase() === status.toLowerCase() || status.toLowerCase().includes(s.toLowerCase())
    );
  };

  // Compatibility properties
  const selectedCategory =
    selectedCategories.length === ALL_CATEGORIES.length
      ? 'Todas'
      : selectedCategories.length === 1
      ? selectedCategories[0]
      : selectedCategories.length === 0
      ? 'Ninguna'
      : `Parcial (${selectedCategories.length})`;

  const setSelectedCategory = (cat: string) => {
    if (cat === 'Todas') {
      setSelectedCategories(ALL_CATEGORIES);
    } else {
      setSelectedCategories([cat]);
    }
  };

  const selectedChannel =
    selectedChannels.length === ALL_CHANNELS.length
      ? null
      : selectedChannels.length === 1
      ? selectedChannels[0]
      : `Parcial (${selectedChannels.length})`;

  const setSelectedChannel = (channel: string | null) => {
    if (channel === null || channel === 'Todos') {
      setSelectedChannels(ALL_CHANNELS);
    } else {
      setSelectedChannels([channel]);
    }
  };

  const selectedRep =
    selectedReps.length === ALL_REPS.length
      ? null
      : selectedReps.length === 1
      ? selectedReps[0]
      : `Parcial (${selectedReps.length})`;

  const setSelectedRep = (rep: string | null) => {
    if (rep === null || rep === 'Todos') {
      setSelectedReps(ALL_REPS);
    } else {
      setSelectedReps([rep]);
    }
  };

  const selectedWarehouse =
    selectedWarehouses.length === ALL_WAREHOUSES.length
      ? null
      : selectedWarehouses.length === 1
      ? selectedWarehouses[0]
      : `Parcial (${selectedWarehouses.length})`;

  const setSelectedWarehouse = (bodega: string | null) => {
    if (bodega === null || bodega === 'Todas') {
      setSelectedWarehouses(ALL_WAREHOUSES);
    } else {
      setSelectedWarehouses([bodega]);
    }
  };

  const selectedStatus =
    selectedStatuses.length === ALL_STATUSES.length
      ? null
      : selectedStatuses.length === 1
      ? selectedStatuses[0]
      : `Parcial (${selectedStatuses.length})`;

  const setSelectedStatus = (status: string | null) => {
    if (status === null || status === 'Todos') {
      setSelectedStatuses(ALL_STATUSES);
    } else {
      setSelectedStatuses([status]);
    }
  };

  const clearAllCrossFilters = () => {
    setSelectedCategories(ALL_CATEGORIES);
    setSelectedChannels(ALL_CHANNELS);
    setSelectedReps(ALL_REPS);
    setSelectedWarehouses(ALL_WAREHOUSES);
    setSelectedStatuses(ALL_STATUSES);
  };

  const hasActiveCrossFilters =
    selectedCategories.length < ALL_CATEGORIES.length ||
    selectedChannels.length < ALL_CHANNELS.length ||
    selectedReps.length < ALL_REPS.length ||
    selectedWarehouses.length < ALL_WAREHOUSES.length ||
    selectedStatuses.length < ALL_STATUSES.length;

  return (
    <FilterContext.Provider
      value={{
        selectedCategories,
        setSelectedCategories,
        selectedChannels,
        setSelectedChannels,
        selectedReps,
        setSelectedReps,
        selectedWarehouses,
        setSelectedWarehouses,
        selectedStatuses,
        setSelectedStatuses,
        selectedCategory,
        setSelectedCategory,
        selectedChannel,
        setSelectedChannel,
        selectedRep,
        setSelectedRep,
        selectedWarehouse,
        setSelectedWarehouse,
        selectedStatus,
        setSelectedStatus,
        matchesCategory,
        matchesChannel,
        matchesRep,
        matchesWarehouse,
        matchesStatus,
        startDate,
        setStartDate,
        endDate,
        setEndDate,
        clearAllCrossFilters,
        hasActiveCrossFilters
      }}
    >
      {children}
    </FilterContext.Provider>
  );
};

export const useGlobalFilter = () => {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error('useGlobalFilter must be used within a FilterProvider');
  }
  return context;
};

