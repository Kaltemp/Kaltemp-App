// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\components\LogisticsView.tsx (o la carpeta donde ya vive hoy)
// Cambios 12-ago-2026 (segunda ronda del día):
// - Reaplicado fetchEnviameShipments(startDate, endDate) -- este archivo
//   subido no tenía el fix de la ronda anterior.
// - Columna "Fecha Envío" agregada (usa fechaEnvio, ya viene del backend).
// - Columna "Rastreo" eliminada a pedido de William.
// - "Fecha Entrega" queda pendiente hasta confirmar con Envíame si el
//   dato existe (ver diagnostico_fecha_entrega_enviame.py) -- no se
//   agrega una columna con datos inventados mientras tanto.
//
// Cambios 19-ago-2026 (reportado por William: "el módulo de control
// logístico no está trayendo datos"):
// - El componente nunca revisaba `kpis.disponible` / `kpis.mensaje`, que
//   GET /api/logistica devuelve explícitamente cuando la tabla
//   'enviame_despachos' todavía no existe (mismo patrón defensivo que
//   usan get_stock / get_pendientes_despacho en el backend). Sin este
//   chequeo, ese caso caía en `kpis?.despachosCy ?? shipments.length ?? 0`
//   y compañía, mostrando 4 tarjetas en $0/0 en silencio -- indistinguible
//   de "no hay actividad real" para quien mira la pantalla.
// - El .catch(...) de la carga solo hacía console.error -- cualquier error
//   real de backend (500, fecha inválida, etc.) también terminaba
//   mostrando la misma pantalla vacía sin ninguna pista visible. Se agrega
//   un banner de error igual al que ya usan otros módulos (Fulfillment,
//   Notas de Crédito) para que un fallo real se note en la UI en vez de
//   quedar solo en la consola del navegador.
import React, { useState, useEffect, useMemo } from 'react';
import { ThemeMode } from '../types';
import {
  Send,
  DollarSign,
  Truck,
  TrendingUp,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Filter
} from 'lucide-react';
import { useGlobalFilter } from '../context/FilterContext';
import { fetchLogistica, fetchEnviameShipments } from '../services/api';

interface Props {
  theme: ThemeMode;
}

export const LogisticsView: React.FC<Props> = ({ theme }) => {
  const isDark = theme === 'dark';
  const { startDate, endDate } = useGlobalFilter();

  const [kpis, setKpis] = useState<any>(null);
  const [shipments, setShipments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchLogistica(startDate, endDate),
      fetchEnviameShipments(startDate, endDate)
    ])
      .then(([resKpis, resShipments]) => {
        setKpis(resKpis);
        setShipments(Array.isArray(resShipments) ? resShipments : resShipments?.items || []);
        setError(null);
      })
      .catch((err) => {
        console.error("Error al cargar datos logísticos:", err);
        setError(err?.message || 'No se pudo cargar Control Logístico. Revisa la consola/servidor.');
      })
      .finally(() => setLoading(false));
  }, [startDate, endDate]);

  const formatCLP = (val: number) => `$${Math.round(val).toLocaleString('es-CL')}`;

  // Métricas KPI -- LEE LOS NOMBRES REALES que manda /api/logistica
  // (despachosCy, costoEnviameCy, cobroBsaleCy, diferencia). Antes se leía
  // kpis?.totalEnvios / costoEnviameTotal / cobroBsaleTotal -- ninguno de
  // esos campos existe en la respuesta real, así que SIEMPRE caía en los
  // valores hardcodeados de ejemplo (89289 / 98880), nunca mostraba datos
  // reales -- confirmado real 11-ago-2026 comparando contra el Response
  // real del endpoint (665 despachos, $3.443.223 costo, $3.440.054 cobro,
  // -$3.169 de margen -- muy distinto del +$9.591 falso que se veía).
  const totalEnvios = kpis?.despachosCy ?? shipments.length ?? 0;
  const costoEnviame = kpis?.costoEnviameCy ?? 0;
  const cobroBsale = kpis?.cobroBsaleCy ?? 0;
  const diferenciaFlete = kpis?.diferencia ?? (cobroBsale - costoEnviame);

  // AGREGADO (19-ago-2026): si el backend responde disponible:false (la
  // tabla enviame_despachos todavía no existe en esta base), se muestra
  // un aviso explícito en vez de tarjetas en $0 indistinguibles de "no
  // hay envíos en el rango".
  const noDisponible = kpis && kpis.disponible === false;

  // Filtrado reactivo en tiempo real
  const filteredShipments = useMemo(() => {
    return shipments.filter((s: any) => {
      const ref = (s.shippingOrder || s.refEnvio || s.id || '').toString().toLowerCase();
      const cliente = (s.cliente || '').toLowerCase();
      const comuna = (s.comuna || '').toLowerCase();
      const producto = (s.producto || '').toLowerCase();
      const estado = (s.estado || 'ENTREGADO').toUpperCase();

      const matchesSearch =
        ref.includes(searchTerm.toLowerCase()) ||
        cliente.includes(searchTerm.toLowerCase()) ||
        comuna.includes(searchTerm.toLowerCase()) ||
        producto.includes(searchTerm.toLowerCase());

      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'ENTREGADO' && estado === 'ENTREGADO') ||
        (statusFilter === 'PENDIENTE' && estado !== 'ENTREGADO');

      return matchesSearch && matchesStatus;
    });
  }, [shipments, searchTerm, statusFilter]);

  if (loading) {
    return (
      <div className="min-h-[400px] flex flex-col items-center justify-center gap-3">
        <div className="p-3 rounded-2xl bg-blue-500/10 text-blue-500 animate-spin">
          <RefreshCw className="w-7 h-7" />
        </div>
        <span className="text-sm font-medium tracking-tight text-slate-500 dark:text-slate-400">
          Sincronizando métricas de Control Logístico & Envíame...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-10">

      {error && (
        <div className={isDark ? "px-4 py-3 rounded-2xl text-xs font-bold bg-rose-500/10 text-rose-300 border border-rose-500/20" : "px-4 py-3 rounded-2xl text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200"}>
          {error}
        </div>
      )}

      {!error && noDisponible && (
        <div className={isDark ? "px-4 py-3 rounded-2xl text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20" : "px-4 py-3 rounded-2xl text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200"}>
          {kpis?.mensaje || "Control Logístico aún no tiene datos disponibles."}
        </div>
      )}

      {/* KPI CARDS APPLE HIG STYLE */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* TOTAL DESPACHOS */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]'
            : 'bg-white border-slate-200/80 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-500">
              TOTAL DESPACHOS
            </span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500">
              <Truck className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {totalEnvios} <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">envíos</span>
          </div>
          <span className="text-xs block mt-1.5 text-slate-500 dark:text-slate-400 font-medium">
            Sincronizados en Envíame
          </span>
        </div>

        {/* COSTO ENVÍAME */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]'
            : 'bg-white border-slate-200/80 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-500">
              COSTO ENVÍAME (EST.)
            </span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
            {formatCLP(costoEnviame)}
          </div>
          <span className="text-xs block mt-1.5 text-slate-500 dark:text-slate-400 font-medium">
            Tarifa estimada courier
          </span>
        </div>

        {/* COBRO REAL BSALE */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]'
            : 'bg-white border-slate-200/80 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-500">
              COBRO REAL BSALE
            </span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-emerald-500 mt-3 tracking-tight">
            {formatCLP(cobroBsale)}
          </div>
          <span className="text-xs block mt-1.5 text-slate-500 dark:text-slate-400 font-medium">
            Facturado directamente al cliente
          </span>
        </div>

        {/* DIFERENCIA MARGEN */}
        <div className={`p-5 rounded-2xl border transition-all duration-200 ${
          isDark
            ? 'bg-[#1C1C1E] border-[#2C2C2E] hover:border-[#3A3A3C]'
            : 'bg-white border-slate-200/80 shadow-sm hover:shadow-md'
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-purple-500">
              MARGEN DE FLETE
            </span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-500">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-3xl font-extrabold mt-3 tracking-tight ${
            diferenciaFlete >= 0 ? 'text-emerald-500' : 'text-rose-500'
          }`}>
            {diferenciaFlete >= 0 ? `+${formatCLP(diferenciaFlete)}` : formatCLP(diferenciaFlete)}
          </div>
          <span className="text-xs block mt-1.5 text-slate-500 dark:text-slate-400 font-medium">
            {diferenciaFlete >= 0 ? 'Superávit a favor de Kaltemp' : 'Déficit en costo de transporte'}
          </span>
        </div>

      </div>

      {/* CONTENEDOR DE LA TABLA Y FILTROS */}
      <div className={`rounded-2xl border overflow-hidden transition-all duration-200 ${
        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200/80 shadow-sm'
      }`}>

        {/* BARRA SUPERIOR DE BÚSQUEDA Y FILTROS */}
        <div className={`p-4 border-b flex flex-col sm:flex-row items-center justify-between gap-3 ${
          isDark ? 'border-[#2C2C2E] bg-[#171719]' : 'border-slate-100 bg-slate-50/50'
        }`}>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-500 flex items-center gap-1.5">
              <Send className="w-4 h-4" /> DETALLE DE ENVÍOS ({filteredShipments.length})
            </span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* Buscador */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar cliente, orden, comuna..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className={`w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border outline-none transition-all ${
                  isDark
                    ? 'bg-[#252528] border-[#333336] text-white placeholder-slate-500 focus:border-blue-500'
                    : 'bg-white border-slate-200 text-slate-800 placeholder-slate-400 focus:border-blue-500'
                }`}
              />
            </div>

            {/* Selector de Estado */}
            <div className="relative">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className={`px-3 py-1.5 text-xs rounded-xl border outline-none cursor-pointer transition-all ${
                  isDark
                    ? 'bg-[#252528] border-[#333336] text-white focus:border-blue-500'
                    : 'bg-white border-slate-200 text-slate-800 focus:border-blue-500'
                }`}
              >
                <option value="ALL">Todos los Estados</option>
                <option value="ENTREGADO">Entregados</option>
                <option value="PENDIENTE">En Tránsito / Pendientes</option>
              </select>
            </div>
          </div>
        </div>

        {/* TABLA PRINCIPAL */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse min-w-[1100px]">
            <thead>
              <tr className={`border-b text-[10px] font-bold uppercase tracking-wider ${
                isDark ? 'border-[#2C2C2E] text-slate-400 bg-[#121215]' : 'border-slate-200 text-slate-500 bg-slate-100/70'
              }`}>
                <th className="py-3 px-4">REF ENVÍO</th>
                <th className="py-3 px-4">CLIENTE</th>
                <th className="py-3 px-4">COMUNA</th>
                <th className="py-3 px-4">VENDEDOR</th>
                <th className="py-3 px-4">PRODUCTO</th>
                <th className="py-3 px-4">FECHA ENVÍO</th>
                <th className="py-3 px-4">FECHA ENTREGA</th>
                <th className="py-3 px-4 text-center">ESTADO ENVÍO</th>
                <th className="py-3 px-4 text-right text-emerald-500 font-bold">COBRO BSALE</th>
                <th className="py-3 px-4 text-right text-amber-500 font-bold">COSTO ENVÍAME</th>
                <th className="py-3 px-4 text-right font-bold">MARGEN FLETE</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-[#2C2C2E]' : 'divide-slate-100'}`}>
              {filteredShipments.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-slate-400 italic">
                    No se encontraron envíos que coincidan con el filtro
                  </td>
                </tr>
              ) : (
                filteredShipments.map((s: any, idx: number) => {
                  const cobroRealBsale = Number(s.cobroBsale || s.montoDespachoBsale || s.despachoBsale || 0);
                  const costoEstimadoEnviame = Number(s.costoEnviame || s.montoEnviame || s.costoEstimado || 0);
                  const dif = cobroRealBsale - costoEstimadoEnviame;
                  const isEntregado = (s.estado || 'ENTREGADO').toUpperCase() === 'ENTREGADO';

                  return (
                    <tr
                      key={`${s.id || idx}`}
                      className={`transition-colors hover:bg-blue-500/5 ${
                        isDark ? 'text-slate-200' : 'text-slate-800'
                      }`}
                    >
                      {/* Ref Envío */}
                      <td className="py-3 px-4 font-bold text-blue-500 whitespace-nowrap">
                        {s.shippingOrder || s.refEnvio || s.id || `ENV-${idx + 1}`}
                      </td>

                      {/* Cliente */}
                      <td className="py-3 px-4 font-medium max-w-[160px] truncate" title={s.cliente || 'Jacquelinne Huenchupan Diaz'}>
                        {s.cliente || 'Jacquelinne Huenchupan Diaz'}
                      </td>

                      {/* Comuna */}
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">
                        {s.comuna || 'Aysén'}
                      </td>

                      {/* Vendedor */}
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">
                        {s.vendedor || '—'}
                      </td>

                      {/* Producto */}
                      <td className="py-3 px-4 max-w-[180px] truncate text-slate-600 dark:text-slate-300 font-medium" title={s.producto || '—'}>
                        {s.producto || '—'}
                      </td>

                      {/* Fecha Envío */}
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">
                        {s.fechaEnvio
                          ? new Date(s.fechaEnvio).toLocaleDateString('es-CL')
                          : '—'}
                      </td>

                      {/* Fecha Entrega -- solo existe si el envío ya está
                          efectivamente entregado (viene NULL si no) */}
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">
                        {s.fechaEntrega
                          ? new Date(s.fechaEntrega).toLocaleDateString('es-CL')
                          : '—'}
                      </td>

                      {/* Estado Envío Badge */}
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                          isEntregado
                            ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                        }`}>
                          {isEntregado ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3 animate-pulse" />}
                          {s.estado || 'ENTREGADO'}
                        </span>
                      </td>

                      {/* Cobro Bsale */}
                      <td className="py-3 px-4 text-right font-bold text-emerald-500 whitespace-nowrap">
                        {formatCLP(cobroRealBsale)}
                      </td>

                      {/* Costo Envíame */}
                      <td className="py-3 px-4 text-right font-bold text-amber-500 whitespace-nowrap">
                        {formatCLP(costoEstimadoEnviame)}
                      </td>

                      {/* Margen / Diferencia Flete */}
                      <td className={`py-3 px-4 text-right font-extrabold whitespace-nowrap ${
                        dif >= 0 ? 'text-emerald-500' : 'text-rose-500'
                      }`}>
                        {dif >= 0 ? `+${formatCLP(dif)}` : formatCLP(dif)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* PIE DE TABLA - RESUMEN RÁPIDO */}
        <div className={`p-3 border-t text-xs flex justify-between items-center text-slate-500 dark:text-slate-400 ${
          isDark ? 'border-[#2C2C2E] bg-[#171719]' : 'border-slate-100 bg-slate-50/50'
        }`}>
          <span>Mostrando {filteredShipments.length} de {shipments.length} envíos</span>
          <span className="font-medium">Formato de Moneda: CLP ($)</span>
        </div>

      </div>

    </div>
  );
};

// Exportación doble para máxima flexibilidad
export default LogisticsView;