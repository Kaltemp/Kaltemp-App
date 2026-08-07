import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, X, CheckSquare, Square } from 'lucide-react';
import { ThemeMode } from '../types';

export interface MultiSelectOption {
  id: string;
  label: string;
}

interface MultiSelectDropdownProps {
  label?: string;
  options: (MultiSelectOption | string)[];
  selectedValues: string[];
  onChange: (newValues: string[]) => void;
  placeholder?: string;
  theme?: ThemeMode;
  className?: string;
  compact?: boolean;
}

export const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  label,
  options,
  selectedValues,
  onChange,
  placeholder = 'Todos',
  theme = 'dark',
  className = '',
  compact = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDark = theme === 'dark';

  // Normalize options to { id, label }
  const normalizedOptions: MultiSelectOption[] = options.map((opt) =>
    typeof opt === 'string' ? { id: opt, label: opt } : opt
  );

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const allSelected =
    normalizedOptions.length > 0 && selectedValues.length === normalizedOptions.length;
  const noneSelected = selectedValues.length === 0;

  const handleToggleOption = (id: string) => {
    if (selectedValues.includes(id)) {
      onChange(selectedValues.filter((v) => v !== id));
    } else {
      onChange([...selectedValues, id]);
    }
  };

  const handleSelectAll = () => {
    onChange(normalizedOptions.map((o) => o.id));
  };

  const handleDeselectAll = () => {
    onChange([]);
  };

  // Label to render on the trigger button
  const getDisplayText = () => {
    if (allSelected) return `${placeholder} (${normalizedOptions.length})`;
    if (noneSelected) return 'Ninguno seleccionado';
    if (selectedValues.length === 1) {
      const match = normalizedOptions.find((o) => o.id === selectedValues[0]);
      return match ? match.label : selectedValues[0];
    }
    return `${selectedValues.length} de ${normalizedOptions.length} sel.`;
  };

  return (
    <div ref={containerRef} className={`relative inline-block w-full ${className}`}>
      {label && (
        <label className={`block text-[10px] font-extrabold uppercase tracking-wider mb-1 ${
          isDark ? 'text-[#8E8E93]' : 'text-slate-400'
        }`}>
          {label}
        </label>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between text-left border rounded-xl font-bold transition-all ${
          compact ? 'px-2.5 py-1 text-xs' : 'px-3 py-2 text-xs'
        } ${
          isDark
            ? 'bg-[#121214] border-[#2C2C2E] text-white hover:border-blue-500/50'
            : 'bg-white border-slate-200 text-slate-800 hover:border-blue-400'
        } ${isOpen ? 'ring-2 ring-blue-500/30 border-blue-500' : ''}`}
      >
        <span className="truncate mr-2 font-semibold text-xs">
          {getDisplayText()}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          {!allSelected && !noneSelected && (
            <span className="text-[10px] px-1.5 py-0.2 rounded font-bold bg-blue-500/20 text-blue-400">
              {selectedValues.length}
            </span>
          )}
          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-blue-500' : 'opacity-60'
          }`} />
        </div>
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className={`absolute z-50 left-0 top-full mt-1.5 w-full min-w-[220px] rounded-xl border shadow-xl p-2 animate-in fade-in zoom-in-95 duration-150 ${
          isDark ? 'bg-[#1C1C1E] border-[#2C2C2E] text-white' : 'bg-white border-slate-200 text-slate-900'
        }`}>
          {/* Header Actions */}
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-[#2C2C2E] text-[11px] font-bold">
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-blue-500 hover:text-blue-400 flex items-center gap-1 cursor-pointer"
            >
              <CheckSquare className="w-3.5 h-3.5" />
              Seleccionar Todos
            </button>
            <button
              type="button"
              onClick={handleDeselectAll}
              className="text-rose-500 hover:text-rose-400 flex items-center gap-1 cursor-pointer"
            >
              <Square className="w-3.5 h-3.5" />
              Desmarcar
            </button>
          </div>

          {/* Options List */}
          <div className="max-h-56 overflow-y-auto space-y-0.5 pr-1 [scrollbar-width:thin]">
            {normalizedOptions.map((opt) => {
              const isChecked = selectedValues.includes(opt.id);
              return (
                <label
                  key={opt.id}
                  onClick={(e) => {
                    e.preventDefault();
                    handleToggleOption(opt.id);
                  }}
                  className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold cursor-pointer select-none transition-colors ${
                    isChecked
                      ? isDark
                        ? 'bg-blue-500/15 text-blue-400'
                        : 'bg-blue-50 text-blue-700'
                      : isDark
                      ? 'hover:bg-[#2C2C2E] text-slate-300'
                      : 'hover:bg-slate-100 text-slate-700'
                  }`}
                >
                  <div className={`w-4 h-4 rounded flex items-center justify-center shrink-0 border transition-all ${
                    isChecked
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : isDark
                      ? 'border-[#3C3C3E] bg-[#121214]'
                      : 'border-slate-300 bg-white'
                  }`}>
                    {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
                  </div>
                  <span className="truncate text-[12px]">{opt.label}</span>
                </label>
              );
            })}
          </div>

          {/* Footer Done button */}
          <div className="pt-2 mt-2 border-t border-slate-200 dark:border-[#2C2C2E] flex justify-end">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-sm"
            >
              Listo
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
