import React, { useState, useRef, useEffect } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, ChevronDown, RotateCcw } from 'lucide-react';
import { ThemeMode } from '../types';

interface DateRangePickerProps {
  startDate: string; // YYYY-MM-DD
  endDate: string;   // YYYY-MM-DD
  onSelectRange: (start: string, end: string) => void;
  theme: ThemeMode;
}

type PresetType =
  | 'Hoy'
  | 'Ayer'
  | 'Esta semana'
  | 'Semana anterior'
  | 'Este mes'
  | 'Mes anterior'
  | 'Este año'
  | 'Año anterior';

const toIso = (d: Date): string => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return y + '-' + m + '-' + day;
};

const addDays = (d: Date, days: number): Date => {
  const copia = new Date(d);
  copia.setDate(copia.getDate() + days);
  return copia;
};

const lunesDeLaSemana = (d: Date): Date => {
  const copia = new Date(d);
  const diaSemana = (copia.getDay() + 6) % 7;
  return addDays(copia, -diaSemana);
};

const calcularRangoPreset = (preset: PresetType): { start: string; end: string } => {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);

  switch (preset) {
    case 'Hoy':
      return { start: toIso(hoy), end: toIso(hoy) };
    case 'Ayer': {
      const ayer = addDays(hoy, -1);
      return { start: toIso(ayer), end: toIso(ayer) };
    }
    case 'Esta semana': {
      const lunes = lunesDeLaSemana(hoy);
      return { start: toIso(lunes), end: toIso(hoy) };
    }
    case 'Semana anterior': {
      const lunesEstaSemana = lunesDeLaSemana(hoy);
      const lunesAnterior = addDays(lunesEstaSemana, -7);
      const domingoAnterior = addDays(lunesEstaSemana, -1);
      return { start: toIso(lunesAnterior), end: toIso(domingoAnterior) };
    }
    case 'Este mes': {
      const inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
      return { start: toIso(inicio), end: toIso(hoy) };
    }
    case 'Mes anterior': {
      const inicio = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
      const fin = new Date(hoy.getFullYear(), hoy.getMonth(), 0);
      return { start: toIso(inicio), end: toIso(fin) };
    }
    case 'Este año': {
      const inicio = new Date(hoy.getFullYear(), 0, 1);
      return { start: toIso(inicio), end: toIso(hoy) };
    }
    case 'Año anterior': {
      const inicio = new Date(hoy.getFullYear() - 1, 0, 1);
      const fin = new Date(hoy.getFullYear() - 1, 11, 31);
      return { start: toIso(inicio), end: toIso(fin) };
    }
  }
};

const formatDateDisplay = (iso: string | null) => {
  if (!iso) return '';
  const parts = iso.split('-');
  if (parts.length !== 3) return iso;
  return parts[2] + '/' + parts[1] + '/' + parts[0];
};

const parseDisplayToIso = (display: string): string | null => {
  const clean = display.replace(/[^0-9/]/g, '');
  const parts = clean.split('/');
  if (parts.length !== 3) return null;
  const day = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10);
  const year = parseInt(parts[2], 10);

  if (isNaN(day) || isNaN(month) || isNaN(year)) return null;
  if (month < 1 || month > 12) return null;
  if (day < 1 || day > 31) return null;
  if (parts[2].length !== 4) return null;

  const mStr = String(month).padStart(2, '0');
  const dStr = String(day).padStart(2, '0');
  return year + '-' + mStr + '-' + dStr;
};

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  startDate,
  endDate,
  onSelectRange,
  theme
}) => {
  const isDark = theme === 'dark';
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const [activePreset, setActivePreset] = useState<PresetType | null>(null);

  const fechaInicial = startDate ? new Date(startDate + 'T00:00:00') : new Date();
  const [currentYear, setCurrentYear] = useState<number>(fechaInicial.getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(fechaInicial.getMonth());

  const [selectionStep, setSelectionStep] = useState<'selecting_start' | 'selecting_end'>('selecting_start');
  const [tempStart, setTempStart] = useState<string>(startDate);
  const [tempEnd, setTempEnd] = useState<string | null>(endDate);
  const [hoverIso, setHoverIso] = useState<string | null>(null);

  const [startInputText, setStartInputText] = useState<string>(formatDateDisplay(startDate));
  const [endInputText, setEndInputText] = useState<string>(formatDateDisplay(endDate));

  useEffect(() => {
    if (!isOpen) {
      setTempStart(startDate);
      setTempEnd(endDate);
      setStartInputText(formatDateDisplay(startDate));
      setEndInputText(formatDateDisplay(endDate));
      setSelectionStep('selecting_start');
    }
  }, [isOpen, startDate, endDate]);

  useEffect(() => {
    setStartInputText(formatDateDisplay(tempStart));
  }, [tempStart]);

  useEffect(() => {
    setEndInputText(formatDateDisplay(tempEnd));
  }, [tempEnd]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const applyPreset = (preset: PresetType) => {
    setActivePreset(preset);
    const { start, end } = calcularRangoPreset(preset);
    const fechaRef = new Date(start + 'T00:00:00');
    setCurrentYear(fechaRef.getFullYear());
    setCurrentMonth(fechaRef.getMonth());
    setTempStart(start);
    setTempEnd(end);
    setSelectionStep('selecting_start');
    onSelectRange(start, end);
  };

  const monthNamesEs = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  const prevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  const nextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  const handleDayClick = (dayNum: number, isCurrentMonth: boolean, targetIso?: string) => {
    let clickedIso = targetIso;

    if (!clickedIso) {
      const mStr = String(currentMonth + 1).padStart(2, '0');
      const dStr = String(dayNum).padStart(2, '0');
      clickedIso = currentYear + '-' + mStr + '-' + dStr;
    }

    setActivePreset(null);

    if (selectionStep === 'selecting_start' || !tempStart) {
      setTempStart(clickedIso);
      setTempEnd(null);
      setSelectionStep('selecting_end');
    } else {
      if (clickedIso < tempStart) {
        setTempStart(clickedIso);
        setTempEnd(tempStart);
        setSelectionStep('selecting_start');
      } else {
        setTempEnd(clickedIso);
        setSelectionStep('selecting_start');
      }
    }
  };

  const handleDayMouseEnter = (iso: string) => {
    if (selectionStep === 'selecting_end' && tempStart) {
      setHoverIso(iso);
    }
  };

  const handleApply = () => {
    const finalStart = tempStart;
    const finalEnd = tempEnd || tempStart;
    if (finalStart && finalEnd) {
      if (finalStart <= finalEnd) {
        onSelectRange(finalStart, finalEnd);
      } else {
        onSelectRange(finalEnd, finalStart);
      }
    }
    setIsOpen(false);
  };

  const renderCalendarDays = () => {
    const firstDay = new Date(currentYear, currentMonth, 1);
    let startDayOfWeek = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const daysInPrevMonth = new Date(currentYear, currentMonth, 0).getDate();

    const weeks: Array<Array<{ day: number; isCurrentMonth: boolean; iso: string }>> = [];
    let currentWeek: Array<{ day: number; isCurrentMonth: boolean; iso: string }> = [];

    const prevMonthNum = currentMonth === 0 ? 11 : currentMonth - 1;
    const prevYearNum = currentMonth === 0 ? currentYear - 1 : currentYear;
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const day = daysInPrevMonth - i;
      const mStr = String(prevMonthNum + 1).padStart(2, '0');
      const dStr = String(day).padStart(2, '0');
      currentWeek.push({ day, isCurrentMonth: false, iso: prevYearNum + '-' + mStr + '-' + dStr });
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const mStr = String(currentMonth + 1).padStart(2, '0');
      const dStr = String(day).padStart(2, '0');
      const iso = currentYear + '-' + mStr + '-' + dStr;

      currentWeek.push({ day, isCurrentMonth: true, iso });
      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    }

    let nextDay = 1;
    const nextMonthNum = currentMonth === 11 ? 0 : currentMonth + 1;
    const nextYearNum = currentMonth === 11 ? currentYear + 1 : currentYear;
    while (weeks.length < 5 || (weeks.length === 5 && currentWeek.length > 0)) {
      while (currentWeek.length < 7) {
        const mStr = String(nextMonthNum + 1).padStart(2, '0');
        const dStr = String(nextDay).padStart(2, '0');
        currentWeek.push({ day: nextDay++, isCurrentMonth: false, iso: nextYearNum + '-' + mStr + '-' + dStr });
      }
      weeks.push(currentWeek);
      currentWeek = [];
    }

    const effectiveEnd = tempEnd || (selectionStep === 'selecting_end' ? hoverIso : tempStart);

    return weeks.map((week, wIdx) => (
      <div key={wIdx} className="grid grid-cols-7 gap-y-1 my-0.5 relative">
        {week.map((cell, dIdx) => {
          const isStart = cell.iso === tempStart;
          const isEnd = effectiveEnd ? cell.iso === effectiveEnd : false;

          let isInRange = false;
          if (tempStart && effectiveEnd) {
            const minIso = tempStart < effectiveEnd ? tempStart : effectiveEnd;
            const maxIso = tempStart > effectiveEnd ? tempStart : effectiveEnd;
            isInRange = cell.iso >= minIso && cell.iso <= maxIso;
          }

          let stripClass = '';
          if (isInRange) {
            if (isStart && isEnd) {
              stripClass = 'bg-transparent';
            } else if (isStart) {
              stripClass = 'bg-[#8ED9F1]/80 rounded-l-full';
            } else if (isEnd) {
              stripClass = 'bg-[#8ED9F1]/80 rounded-r-full';
            } else {
              stripClass = 'bg-[#8ED9F1]/80';
            }
          }

          const dayTextClass = isInRange
            ? 'text-slate-900 font-semibold z-10'
            : isDark
            ? 'text-slate-200 hover:text-white'
            : 'text-slate-700 hover:text-black';

          const opacityClass = !cell.isCurrentMonth ? ' opacity-40' : '';

          return (
            <div
              key={dIdx}
              onClick={() => handleDayClick(cell.day, cell.isCurrentMonth, cell.iso)}
              onMouseEnter={() => handleDayMouseEnter(cell.iso)}
              className={'h-9 flex items-center justify-center cursor-pointer text-xs relative select-none font-medium transition-colors ' + stripClass + opacityClass}
            >
              {isStart && (
                <div className="w-8 h-8 rounded-full bg-[#0099D8] text-white font-bold flex items-center justify-center z-10 shadow-md">
                  {cell.day}
                </div>
              )}
              {isEnd && !isStart && (
                <div className="w-8 h-8 rounded-full bg-[#0099D8] text-white font-bold flex items-center justify-center z-10 shadow-md">
                  {cell.day}
                </div>
              )}
              {!isStart && !isEnd && (
                <span className={dayTextClass}>
                  {cell.day}
                </span>
              )}
            </div>
          );
        })}
      </div>
    ));
  };

  const presetsList: PresetType[] = [
    'Hoy',
    'Ayer',
    'Esta semana',
    'Semana anterior',
    'Este mes',
    'Mes anterior',
    'Este año',
    'Año anterior'
  ];

  const currentActualYear = new Date().getFullYear();
  const yearsList = Array.from({ length: 7 }, (_, i) => currentActualYear - 5 + i);

  const mainBtnTheme = isOpen
    ? 'border-[#0099D8] ring-2 ring-[#0099D8]/20 bg-[#0099D8]/5 text-[#0099D8]'
    : isDark
    ? 'bg-[#121214] border-[#2C2C2E] text-[#F5F5F7] hover:border-[#0099D8]'
    : 'bg-slate-50 border-slate-200 text-slate-800 hover:border-[#0099D8] shadow-sm';

  const modalTheme = isDark
    ? 'bg-[#1C1C1E] border-[#2C2C2E] text-white shadow-black/80'
    : 'bg-white border-slate-200 text-slate-800 shadow-slate-400/30';

  const sidebarTheme = isDark ? 'border-[#2C2C2E] bg-[#121214]' : 'border-slate-100 bg-slate-50/80';
  const rangeDisplayTheme = isDark ? 'bg-[#121214] border-[#2C2C2E] text-[#0099D8]' : 'bg-slate-100 border-slate-200 text-[#0099D8]';
  const inputTheme = isDark ? 'border-slate-600 bg-[#121214] focus-within:border-[#0099D8]' : 'border-slate-300 bg-white focus-within:border-[#0099D8]';
  const selectTheme = isDark ? 'border-slate-700 text-white bg-[#121214]' : 'border-slate-200 text-slate-800 bg-slate-50';
  const optionTheme = isDark ? 'bg-[#1C1C1E]' : 'bg-white';

  const chevronClass = 'w-4 h-4 transition-transform duration-200 text-slate-400 ' + (isOpen ? 'rotate-180' : '');

  return (
    <div className="relative w-full" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={'w-full flex items-center justify-between p-2.5 rounded-xl border text-xs font-semibold transition-all ' + mainBtnTheme}
      >
        <div className="flex items-center gap-2 truncate">
          <CalendarIcon className="w-4 h-4 text-[#0099D8] shrink-0" />
          <div className="flex flex-col text-left truncate">
            <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">
              Rango de Fecha
            </span>
            <span className="text-xs font-bold text-[#0099D8] truncate">
              {formatDateDisplay(startDate)} - {formatDateDisplay(endDate)}
            </span>
          </div>
        </div>
        <ChevronDown className={chevronClass} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-[998] bg-black/20 backdrop-blur-[1px]"
            onClick={() => setIsOpen(false)}
          />

          <div
            className={'fixed left-4 right-4 top-16 md:left-[280px] md:top-20 z-[999] rounded-2xl border shadow-2xl flex flex-col md:flex-row overflow-hidden w-auto md:w-[580px] animate-in fade-in zoom-in-95 duration-150 ' + modalTheme}
          >
            {/* Presets */}
            <div className={'w-full md:w-40 p-3.5 border-b md:border-b-0 md:border-r space-y-1 shrink-0 ' + sidebarTheme}>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 mb-1.5 hidden md:block">
                Rangos Rápidos
              </div>
              <div className="grid grid-cols-2 md:grid-cols-1 gap-1">
                {presetsList.map((preset) => {
                  const isActive = activePreset === preset;
                  const btnPresetClass = isActive
                    ? 'text-[#0099D8] font-bold bg-[#0099D8]/15'
                    : isDark
                    ? 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50';

                  return (
                    <button
                      key={preset}
                      onClick={() => applyPreset(preset)}
                      className={'w-full text-left text-xs font-medium py-1.5 px-2.5 rounded-lg transition-all ' + btnPresetClass}
                    >
                      {preset}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Calendario e Inputs */}
            <div className="flex-1 p-4 md:p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-[#2C2C2E] pb-2">
                <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  Filtro de Fechas
                </span>
                <button
                  onClick={() => applyPreset('Este mes')}
                  className="flex items-center gap-1 text-[11px] font-semibold text-[#0099D8] hover:underline"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Restablecer</span>
                </button>
              </div>

              {/* Rango Seleccionado Display */}
              <div className={'p-2 rounded-xl text-center text-xs font-bold flex items-center justify-center gap-2 border ' + rangeDisplayTheme}>
                <CalendarIcon className="w-3.5 h-3.5" />
                <span>{formatDateDisplay(tempStart)} - {formatDateDisplay(tempEnd || tempStart)}</span>
              </div>

              {/* Inputs Manuales con Escritura Teclado Habilitada */}
              <div className="grid grid-cols-2 gap-3">
                <div className="relative">
                  <fieldset className={'border rounded-xl px-3 py-1 text-xs transition-colors ' + inputTheme}>
                    <legend className="px-1 text-[10px] text-slate-400 font-medium">Desde</legend>
                    <input
                      type="text"
                      value={startInputText}
                      onChange={(e) => {
                        const val = e.target.value;
                        setStartInputText(val);
                        const iso = parseDisplayToIso(val);
                        if (iso) {
                          setTempStart(iso);
                          const d = new Date(iso + 'T00:00:00');
                          setCurrentYear(d.getFullYear());
                          setCurrentMonth(d.getMonth());
                        }
                      }}
                      className="w-full bg-transparent font-bold text-xs focus:outline-none py-0.5 text-slate-800 dark:text-slate-100"
                      placeholder="DD/MM/YYYY"
                    />
                  </fieldset>
                </div>

                <div className="relative">
                  <fieldset className={'border rounded-xl px-3 py-1 text-xs transition-colors ' + inputTheme}>
                    <legend className="px-1 text-[10px] text-slate-400 font-medium">Hasta</legend>
                    <input
                      type="text"
                      value={endInputText}
                      onChange={(e) => {
                        const val = e.target.value;
                        setEndInputText(val);
                        const iso = parseDisplayToIso(val);
                        if (iso) {
                          setTempEnd(iso);
                        }
                      }}
                      className="w-full bg-transparent font-bold text-xs focus:outline-none py-0.5 text-slate-800 dark:text-slate-100"
                      placeholder="DD/MM/YYYY"
                    />
                  </fieldset>
                </div>
              </div>

              {/* Cabecera del Calendario con Desplegable de Mes y Año */}
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-1.5">
                  <select
                    value={currentMonth}
                    onChange={(e) => setCurrentMonth(parseInt(e.target.value, 10))}
                    className={'text-xs font-bold rounded-lg p-1 bg-transparent border cursor-pointer focus:outline-none ' + selectTheme}
                  >
                    {monthNamesEs.map((m, idx) => (
                      <option key={m} value={idx} className={optionTheme}>
                        {m}
                      </option>
                    ))}
                  </select>

                  <select
                    value={currentYear}
                    onChange={(e) => setCurrentYear(parseInt(e.target.value, 10))}
                    className={'text-xs font-bold rounded-lg p-1 bg-transparent border cursor-pointer focus:outline-none ' + selectTheme}
                  >
                    {yearsList.map((y) => (
                      <option key={y} value={y} className={optionTheme}>
                        {y}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={prevMonth}
                    className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-[#2C2C2E] text-slate-500 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={nextMonth}
                    className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-[#2C2C2E] text-slate-500 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Días de la semana */}
              <div className="grid grid-cols-7 text-center text-xs font-bold text-slate-400 my-1">
                <span>L</span>
                <span>M</span>
                <span>X</span>
                <span>J</span>
                <span>V</span>
                <span>S</span>
                <span>D</span>
              </div>

              {/* Días del Mes */}
              <div>
                {renderCalendarDays()}
              </div>

              {/* Botón Aplicar */}
              <div className="flex items-center justify-end pt-2 border-t border-slate-100 dark:border-[#2C2C2E]">
                <button
                  onClick={handleApply}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-[#0099D8] text-white hover:bg-[#0082B8] shadow-sm transition-all cursor-pointer"
                >
                  Aplicar
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};