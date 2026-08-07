import React from 'react';
import { useGlobalFilter, ALL_CATEGORIES, ALL_CHANNELS, ALL_REPS, ALL_STATUSES } from '../context/FilterContext';
import { Filter, X } from 'lucide-react';
import { ThemeMode } from '../types';

interface Props {
  theme: ThemeMode;
}

export const CrossFilterBanner: React.FC<Props> = ({ theme }) => {
  const {
    selectedCategories,
    setSelectedCategories,
    selectedChannels,
    setSelectedChannels,
    selectedReps,
    setSelectedReps,
    selectedStatuses,
    setSelectedStatuses,
    clearAllCrossFilters,
    hasActiveCrossFilters
  } = useGlobalFilter();

  if (!hasActiveCrossFilters) return null;

  const isDark = theme === 'dark';

  const isCatPartial = selectedCategories.length < ALL_CATEGORIES.length;
  const isChanPartial = selectedChannels.length < ALL_CHANNELS.length;
  const isRepPartial = selectedReps.length < ALL_REPS.length;
  const isStatPartial = selectedStatuses.length < ALL_STATUSES.length;

  return (
    <div
      className={`p-3 rounded-xl border flex flex-wrap items-center justify-between gap-2 text-xs font-bold transition-all animate-in fade-in ${
        isDark
          ? 'bg-blue-950/40 border-blue-500/40 text-blue-300'
          : 'bg-blue-50 border-blue-200 text-blue-900'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="w-4 h-4 text-blue-500 animate-pulse" />
        <span>🎯 <strong>Filtro Cruzado Activo (Power BI):</strong></span>

        {isCatPartial && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
            Categoría: {selectedCategories.length === 1 ? selectedCategories[0] : `${selectedCategories.length}/${ALL_CATEGORIES.length}`}
            <button
              onClick={() => setSelectedCategories(ALL_CATEGORIES)}
              className="hover:text-white cursor-pointer ml-1"
              title="Restablecer todas las categorías"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        )}

        {isChanPartial && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            Canal: {selectedChannels.length === 1 ? selectedChannels[0] : `${selectedChannels.length}/${ALL_CHANNELS.length}`}
            <button
              onClick={() => setSelectedChannels(ALL_CHANNELS)}
              className="hover:text-white cursor-pointer ml-1"
              title="Restablecer todos los canales"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        )}

        {isRepPartial && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
            Vendedor: {selectedReps.length === 1 ? selectedReps[0] : `${selectedReps.length}/${ALL_REPS.length}`}
            <button
              onClick={() => setSelectedReps(ALL_REPS)}
              className="hover:text-white cursor-pointer ml-1"
              title="Restablecer todos los vendedores"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        )}

        {isStatPartial && (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
            Estado: {selectedStatuses.length === 1 ? selectedStatuses[0] : `${selectedStatuses.length}/${ALL_STATUSES.length}`}
            <button
              onClick={() => setSelectedStatuses(ALL_STATUSES)}
              className="hover:text-white cursor-pointer ml-1"
              title="Restablecer todos los estados"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        )}
      </div>

      <button
        onClick={clearAllCrossFilters}
        className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 transition-all cursor-pointer font-bold text-[11px]"
      >
        <X className="w-3.5 h-3.5" /> Limpiar Filtro Cruzado
      </button>
    </div>
  );
};

