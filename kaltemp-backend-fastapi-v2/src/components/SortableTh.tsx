import React from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

interface Props {
  label: React.ReactNode;
  sortKey: string;
  currentSortKey: string | null;
  sortDirection: 'asc' | 'desc' | null;
  onSort: (key: string) => void;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export const SortableTh: React.FC<Props> = ({
  label,
  sortKey,
  currentSortKey,
  sortDirection,
  onSort,
  align = 'left',
  className = ''
}) => {
  const isActive = currentSortKey === sortKey;

  const getAlignClass = () => {
    if (align === 'center') return 'justify-center text-center';
    if (align === 'right') return 'justify-end text-right';
    return 'justify-start text-left';
  };

  return (
    <th
      onClick={() => onSort(sortKey)}
      className={`p-2.5 cursor-pointer select-none group transition-colors hover:bg-slate-500/10 ${className}`}
      title={`Hacer clic para ordenar por ${typeof label === 'string' ? label : sortKey}`}
    >
      <div className={`flex items-center gap-1 ${getAlignClass()}`}>
        <span>{label}</span>
        <span className="opacity-60 group-hover:opacity-100 transition-opacity">
          {isActive ? (
            sortDirection === 'asc' ? (
              <ArrowUp className="w-3.5 h-3.5 text-blue-500 font-bold" />
            ) : (
              <ArrowDown className="w-3.5 h-3.5 text-blue-500 font-bold" />
            )
          ) : (
            <ArrowUpDown className="w-3 h-3 text-slate-400 opacity-40 group-hover:opacity-80" />
          )}
        </span>
      </div>
    </th>
  );
};
