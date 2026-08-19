// ============================================================
// Archivo: api.ts
// Ruta:    src/services/api.ts
// ============================================================

// --- SERVICIO DE API CENTRALIZADO Y MAESTRO (Kaltemp Dashboard) ---

const AUTH_TOKEN_KEY = 'kaltemp_auth_token';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
    else localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    // localStorage puede fallar en modo incógnito estricto -- la sesión
    // simplemente no persiste entre recargas, no es un error fatal.
  }
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    return data?.detail || fallback;
  } catch {
    return fallback;
  }
}

async function apiGet<T>(endpoint: string): Promise<T> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = `${baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  const response = await fetch(url, { headers: { ...authHeaders() } });
  if (!response.ok) {
    throw new Error(`Error en API (${response.status}): ${response.statusText}`);
  }
  return response.json();
}

async function apiSend<T>(endpoint: string, method: 'POST' | 'PATCH' | 'DELETE', body?: any): Promise<T> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = `${baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const msg = await parseErrorMessage(response, `Error en API (${response.status}): ${response.statusText}`);
    throw new Error(msg);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

// 1. VISTA PRINCIPAL EJECUTIVA & CANALES
export async function fetchExecutiveSummary(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (categorias && categorias.length > 0) params.append('categorias', categorias.join(','));
  return apiGet<any>(`/api/channels?${params.toString()}`);
}

export async function fetchChannels(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[]
): Promise<any> {
  return fetchExecutiveSummary(fechaInicio, fechaFin, vendedores, categorias);
}

// NOTA: MainExecutiveView.tsx llama a estas dos con un solo parámetro de
// fecha (endDate = "a la fecha de corte"), no con un rango fechaInicio/fechaFin.
export async function fetchAcumuladoYtd(
  fecha?: string,
  vendedores?: string[], categorias?: string[], canales?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fecha) params.append('fecha', fecha);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (categorias && categorias.length > 0) params.append('categorias', categorias.join(','));
  if (canales && canales.length > 0) params.append('canales', canales.join(','));
  return apiGet<any>(`/api/acumulado-ytd?${params.toString()}`);
}

export async function fetchTendenciaMensual(
  fecha?: string,
  vendedores?: string[], categorias?: string[], canales?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fecha) params.append('fecha', fecha);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (categorias && categorias.length > 0) params.append('categorias', categorias.join(','));
  if (canales && canales.length > 0) params.append('canales', canales.join(','));
  return apiGet<any>(`/api/tendencia-mensual?${params.toString()}`);
}

// 2. VENTAS POR SKU
export async function fetchSkuSales(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string, categorias?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores) params.append('vendedores', vendedores);
  if (categorias) params.append('categorias', categorias);
  return apiGet<any>(`/api/sku-sales?${params.toString()}`);
}

export async function fetchSkuCanalResumen(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (categorias && categorias.length > 0) params.append('categorias', categorias.join(','));
  return apiGet<any>(`/api/sku/canal-resumen?${params.toString()}`);
}

// 2b. ÁRBOL DE DRILL-DOWN: Producto -> Vendedor -> Documento -> Cliente
// NOTA: sku.py tiene prefix="/api/sku" (no "/api"), por eso todas estas
// rutas van con /api/sku/... y no /api/sku-...
export async function fetchSkuProductos(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], canales?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (canales && canales.length > 0) params.append('canales', canales.join(','));
  return apiGet<any>(`/api/sku/productos?${params.toString()}`);
}

export async function fetchSkuVendedores(
  producto: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('producto', producto);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/sku/vendedores?${params.toString()}`);
}

export async function fetchSkuDocumentos(
  producto: string, vendedor: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('producto', producto);
  params.append('vendedor', vendedor);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/sku/documentos?${params.toString()}`);
}

export async function fetchSkuClientes(
  producto: string, vendedor: string, documento: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('producto', producto);
  params.append('vendedor', vendedor);
  params.append('documento', documento);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/sku/clientes?${params.toString()}`);
}

export async function fetchSkuCategoriaParticipacion(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/sku-categoria-participacion?${params.toString()}`);
}

export async function fetchSkuCategoriaResumen(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], canales?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (canales && canales.length > 0) params.append('canales', canales.join(','));
  return apiGet<any>(`/api/sku/categoria-resumen?${params.toString()}`);
}

export async function fetchSkuDetalle(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/sku-detalle?${params.toString()}`);
}

// 3. CONSOLIDADO DE STOCK — /api/stock no recibe parámetros (sync_dependent.py)
export async function fetchStock(): Promise<any> {
  return apiGet<any>('/api/stock');
}

// 4. PENDIENTES POR DESPACHAR — sin parámetros (sync_dependent.py)
export async function fetchPendingDispatch(): Promise<any> {
  return apiGet<any>('/api/pendientes-despacho');
}

// Alias en español usado por PendingDispatchView.tsx
export async function fetchPendientesDespacho(): Promise<any> {
  return fetchPendingDispatch();
}

// Vista de detalle por documento dentro de Pendientes por Despachar
export async function fetchPendientesDespachoDocumentos(): Promise<any> {
  return apiGet<any>('/api/pendientes-despacho-documentos');
}

// 5. NOTAS DE CRÉDITO — ahora acepta rango de fechas (sync_dependent.py)
export async function fetchCreditNotes(fechaInicio?: string, fechaFin?: string): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  const qs = params.toString();
  return apiGet<any>(`/api/notas-credito${qs ? `?${qs}` : ''}`);
}

// Alias en español usado por CreditNotesView.tsx
export async function fetchNotasCredito(fechaInicio?: string, fechaFin?: string): Promise<any> {
  return fetchCreditNotes(fechaInicio, fechaFin);
}

// 6. DETALLE FULFILLMENT
export async function fetchFulfillment(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/fulfillment?${params.toString()}`);
}

export async function fetchFulfillmentPorProducto(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/fulfillment-por-producto?${params.toString()}`);
}

// 7. CONTROL LOGÍSTICO — /api/logistica (KPIs, requiere fecha_inicio/fecha_fin)
export async function fetchLogistics(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/logistica?${params.toString()}`);
}

// Alias en español usado por LogisticsView.tsx (KPIs de control logístico)
export async function fetchLogistica(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  return fetchLogistics(fechaInicio, fechaFin);
}

// Envíos individuales desde Envíame, usados en la tabla detallada de LogisticsView.tsx
export async function fetchEnviameShipments(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/enviame-shipments?${params.toString()}`);
}

// 8. CRM LEADS (CLIENGO)
export async function fetchLeads(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/leads?${params.toString()}`);
}

// 9. CARROS ABANDONADOS (SHOPIFY)
export async function fetchAbandonedCarts(
  fechaInicio?: string, fechaFin?: string,
  categoria?: string | null, canal?: string | null,
  vendedor?: string | null, bodega?: string | null
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (categoria) params.append('categoria', categoria);
  if (canal) params.append('canal', canal);
  if (vendedor) params.append('vendedor', vendedor);
  if (bodega) params.append('bodega', bodega);
  return apiGet<any>(`/api/abandoned-carts?${params.toString()}`);
}

// 10. CAMPAÑAS DE MARKETING DIGITAL
export async function fetchMarketingCampaigns(
  fechaInicio?: string, fechaFin?: string, marca?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (marca) params.append('marca', marca);
  return apiGet<any>(`/api/marketing-campaigns?${params.toString()}`);
}

// 10b. ANUNCIOS INDIVIDUALES DE UNA CAMPAÑA (drill-down por campaña)
export interface AnuncioCampana {
  id: string;
  adId: string;
  anuncio: string;
  imagenUrl: string;
  imagen: string;
  gastoCy: number;
  clicsCy: number;
  impresionesCy: number;
  ctrCy: number;
}

export async function fetchMarketingCampaignAnuncios(
  campana: string, fechaInicio?: string, fechaFin?: string, marca?: string
): Promise<AnuncioCampana[]> {
  const params = new URLSearchParams();
  params.append('campana', campana);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (marca) params.append('marca', marca);
  return apiGet<AnuncioCampana[]>(`/api/marketing-campaigns/anuncios?${params.toString()}`);
}

// 10c. TOP/BOTTOM ANUNCIOS DESTACADOS
export interface AnuncioTop {
  adId: string;
  anuncio: string;
  imagen: string;
  gastoCy: number;
  clicsCy: number;
  impresionesCy: number;
  ctrCy: number;
  roasCy: number;
}

export async function fetchMarketingTopAnuncios(
  fechaInicio?: string, fechaFin?: string, marca?: string, limite: number = 3
): Promise<{ mejores: AnuncioTop[]; peores: AnuncioTop[] }> {
  try {
    const params = new URLSearchParams();
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);
    if (marca) params.append('marca', marca);
    params.append('limite', String(limite));
    return await apiGet<{ mejores: AnuncioTop[]; peores: AnuncioTop[] }>(`/api/marketing-campaigns/top-anuncios?${params.toString()}`);
  } catch (e) {
    // Si el endpoint aún no está implementado en el backend, responde vacío sin romper
    return { mejores: [], peores: [] };
  }
}

// 11. INDICADORES D2C PERFORMANCE
export async function fetchD2CPerformance(
  fechaInicio?: string, fechaFin?: string,
  categoria?: string | null, canal?: string | null,
  vendedor?: string | null, bodega?: string | null,
  marca?: string | null
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (categoria) params.append('categoria', categoria);
  if (canal) params.append('canal', canal);
  if (vendedor) params.append('vendedor', vendedor);
  if (bodega) params.append('bodega', bodega);
  if (marca) params.append('marca', marca);
  return apiGet<any>(`/api/indicadores-d2c?${params.toString()}`);
}

// 12. CANAL DISTRIBUIDORES (B2B) — distributors.py NO acepta parámetro "tipo":
// el filtro a distribuidores (CANAL LIKE '%DISTRIBUIDOR%' / vendedores fijos)
// está hardcodeado en el propio backend. Solo recibe fechas.
export async function fetchDistributors(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/distributors?${params.toString()}`);
}

// 12b. DISTRIBUIDORES -- ACORDEÓN TABLA 1 (18-ago-2026): Categoría -> Producto
// -> Cliente. Nivel 1 (categoría) ya viene en distribucionCategoria dentro
// de fetchDistributors(); estos 2 endpoints son niveles 2 y 3, se piden
// perezosamente (lazy-load) solo cuando el usuario despliega una fila,
// igual que el árbol Producto->Vendedor->Documento->Cliente de sku.py.
export async function fetchDistributorsProductosPorCategoria(
  categoria: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('categoria', categoria);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/distributors/productos-por-categoria?${params.toString()}`);
}

export async function fetchDistributorsClientesPorProducto(
  producto: string, categoria: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('producto', producto);
  params.append('categoria', categoria);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/distributors/clientes-por-producto?${params.toString()}`);
}

// 13. CANAL INMOBILIARIA
export async function fetchRealEstate(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/real-estate?${params.toString()}`);
}

// 13b. INMOBILIARIA -- ACORDEÓN TABLA 1 (18-ago-2026): Categoría -> Producto
// -> Proyecto/Cliente. Mismo patrón que 12b, sobre /api/real-estate.
export async function fetchRealEstateProductosPorCategoria(
  categoria: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('categoria', categoria);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/real-estate/productos-por-categoria?${params.toString()}`);
}

export async function fetchRealEstateClientesPorProducto(
  producto: string, categoria: string, fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  params.append('producto', producto);
  params.append('categoria', categoria);
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/real-estate/clientes-por-producto?${params.toString()}`);
}

// 14. VENTAS VS TEMPERATURA
export async function fetchTemperatureSales(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/ventas-temperatura?${params.toString()}`);
}

// Alias en español usado por TemperatureSalesView.tsx
export async function fetchVentasTemperatura(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  return fetchTemperatureSales(fechaInicio, fechaFin);
}

// 15. CUMPLIMIENTO VENTAS
export async function fetchCumplimiento(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[], canales?: string[], bodegas?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) {
    params.append('vendedores', vendedores.join(','));
  }
  if (categorias && categorias.length > 0) {
    params.append('categorias', categorias.join(','));
  }
  if (canales && canales.length > 0) {
    params.append('canales', canales.join(','));
  }
  if (bodegas && bodegas.length > 0) {
    params.append('bodegas', bodegas.join(','));
  }
  return apiGet<any>(`/api/cumplimiento?${params.toString()}`);
}

// 15b. RECOMENDACIONES DE PRECIO & STOCK (YoY) — Cumplimiento Ventas
export async function fetchRecomendacionesPrecioStock(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[], canales?: string[], bodegas?: string[],
  limite?: number
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) {
    params.append('vendedores', vendedores.join(','));
  }
  if (categorias && categorias.length > 0) {
    params.append('categorias', categorias.join(','));
  }
  if (canales && canales.length > 0) {
    params.append('canales', canales.join(','));
  }
  if (bodegas && bodegas.length > 0) {
    params.append('bodegas', bodegas.join(','));
  }
  if (limite) params.append('limite', String(limite));
  return apiGet<any>(`/api/cumplimiento/recomendaciones-precio-stock?${params.toString()}`);
}

// 15c. COMPARATIVO HISTÓRICO ANUAL — Cumplimiento Ventas
export async function fetchHistoricoAnual(): Promise<{ anios: any[] }> {
  return apiGet<{ anios: any[] }>('/api/cumplimiento/historico-anual');
}

// 15c-bis. TOP PRODUCTOS DEL PERÍODO ACTUAL — Cumplimiento Ventas
export async function fetchProductosActual(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[], canales?: string[], bodegas?: string[],
  topN?: number
): Promise<{ productos: any[] }> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (categorias && categorias.length > 0) params.append('categorias', categorias.join(','));
  if (canales && canales.length > 0) params.append('canales', canales.join(','));
  if (bodegas && bodegas.length > 0) params.append('bodegas', bodegas.join(','));
  if (topN) params.append('top_n', String(topN));
  return apiGet<{ productos: any[] }>(`/api/cumplimiento/productos-actual?${params.toString()}`);
}

// 15c-ter. DETALLE COMPLETO DE SKUs — Cumplimiento Ventas
export async function fetchSkuDetalleCumplimiento(
  fechaInicio?: string, fechaFin?: string,
  vendedores?: string[], categorias?: string[], canales?: string[], bodegas?: string[]
): Promise<{ skus: any[]; totalUnidades: number; totalVenta: number; totalContribucion: number }> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) params.append('vendedores', vendedores.join(','));
  if (categorias && categorias.length > 0) params.append('categorias', categorias.join(','));
  if (canales && canales.length > 0) params.append('canales', canales.join(','));
  if (bodegas && bodegas.length > 0) params.append('bodegas', bodegas.join(','));
  return apiGet(`/api/cumplimiento/sku-detalle?${params.toString()}`);
}

// 15d. DATOS MANUALES
export interface DatoManual {
  periodo: string;
  tipo: string;
  marca: string;
  monto: number;
  notas?: string | null;
  actualizado_por?: string | null;
  actualizado_en?: string;
}

export interface TipoDatoManual {
  tipo: string;
  etiqueta: string;
}

export async function fetchTiposDatosManuales(): Promise<TipoDatoManual[]> {
  return apiGet<TipoDatoManual[]>('/api/datos-manuales/tipos');
}

export async function fetchMarcasDatosManuales(): Promise<string[]> {
  return apiGet<string[]>('/api/datos-manuales/marcas');
}

export async function fetchDatosManuales(): Promise<DatoManual[]> {
  return apiGet<DatoManual[]>('/api/datos-manuales/metas');
}

export async function guardarDatoManual(dato: {
  periodo: string; tipo: string; marca: string; monto: number; notas?: string; actualizado_por?: string;
}): Promise<{ success: boolean; message: string }> {
  return apiSend('/api/datos-manuales/metas', 'POST', dato);
}

export async function eliminarDatoManual(periodo: string, tipo: string, marca: string): Promise<{ success: boolean; message: string }> {
  return apiSend('/api/datos-manuales/metas/eliminar', 'POST', { periodo, tipo, marca });
}

// 16. FILTROS GLOBALES
export async function fetchFiltrosGlobales(): Promise<any> {
  try {
    return await apiGet<any>('/api/filtros');
  } catch (e) {
    return {
      categorias: [],
      vendedores: [],
      bodegas: []
    };
  }
}

// 17. AUDITORÍA KPI REVIEW
export async function fetchKpiReview(): Promise<any> {
  return apiGet<any>('/api/kpi-review');
}

// 18. DISPARADOR DE SINCRONIZACIÓN DE DATOS
export async function runDataSync(): Promise<any> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${baseUrl}/api/sync/incremental`, { method: 'POST' });
  if (!response.ok) throw new Error('Error al sincronizar datos');
  return response.json();
}

export async function fetchSyncStatus(): Promise<any> {
  return apiGet<any>('/api/sync/status');
}

// 19. AUTENTICACIÓN Y GESTIÓN DE USUARIOS (RBAC)
export function resolveAvatarImageUrl(avatarImageUrl?: string | null): string | null {
  if (!avatarImageUrl) return null;
  if (/^https?:\/\//i.test(avatarImageUrl)) return avatarImageUrl;
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${avatarImageUrl.startsWith('/') ? '' : '/'}${avatarImageUrl}`;
}

export interface AuthUser {
  id: string;
  email: string;
  nombre: string;
  rol: string;
  avatarColor: string;
  avatarIcon: string | null;
  avatarImageUrl: string | null;
  blockedModules: string[];
  allowedModulesOnly: string[] | null;
}

export async function loginRequest(email: string, password: string): Promise<{ token: string; user: AuthUser }> {
  return apiSend('/api/auth/login', 'POST', { email, password });
}

export async function logoutRequest(): Promise<void> {
  await apiSend('/api/auth/logout', 'POST');
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return apiGet<AuthUser>('/api/auth/me');
}

export async function fetchUsers(): Promise<AuthUser[]> {
  return apiGet<AuthUser[]>('/api/auth/users');
}

export async function createUserRequest(user: {
  email: string; nombre: string; rol: string; password: string;
  avatarColor?: string; avatarIcon?: string; blockedModules?: string[]; allowedModulesOnly?: string[];
}): Promise<AuthUser> {
  return apiSend('/api/auth/users', 'POST', user);
}

export async function updateUserRequest(userId: string, changes: {
  nombre?: string; rol?: string; avatarColor?: string; avatarIcon?: string;
  blockedModules?: string[]; allowedModulesOnly?: string[];
}): Promise<AuthUser> {
  return apiSend(`/api/auth/users/${userId}`, 'PATCH', changes);
}

export async function uploadAvatarImageRequest(userId: string, file: File): Promise<AuthUser> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${baseUrl}/api/auth/users/${userId}/avatar-image`, {
    method: 'POST',
    headers: { ...authHeaders() },
    body: formData,
  });

  if (!response.ok) {
    const msg = await parseErrorMessage(response, `Error al subir la imagen (${response.status}).`);
    throw new Error(msg);
  }
  return response.json();
}

export async function removeAvatarImageRequest(userId: string): Promise<AuthUser> {
  return apiSend(`/api/auth/users/${userId}/avatar-image`, 'DELETE');
}

export async function resetPasswordRequest(userId: string, newPassword: string): Promise<void> {
  await apiSend(`/api/auth/users/${userId}/reset-password`, 'POST', { newPassword });
}

export async function deleteUserRequest(userId: string): Promise<void> {
  await apiSend(`/api/auth/users/${userId}`, 'DELETE');
}

export async function impersonateRequest(targetUserId: string): Promise<{ token: string; user: AuthUser }> {
  return apiSend('/api/auth/impersonate', 'POST', { targetUserId });
}

// 20. ALERTA DE CATEGORÍA FALTANTE (SKUs)
export interface SkuPendienteCategoria {
  sku: string;
  producto: string;
  ventaTotal: number;
  lineas: number;
}

export async function fetchCategoriasPendientes(): Promise<{ total: number; items: SkuPendienteCategoria[] }> {
  return apiGet('/api/categorias/pendientes');
}

export async function fetchCategoriasCatalogo(): Promise<string[]> {
  return apiGet('/api/categorias/catalogo');
}

export async function asignarCategoriaSku(sku: string, categoria: string): Promise<{ success: boolean; message: string }> {
  return apiSend('/api/categorias/asignar', 'POST', { sku, categoria });
}

// 21. ALERTA DE CATEGORÍA FALTANTE (CAMPAÑAS)
export interface CampanaPendienteCategoria {
  campana: string;
  plataforma: string;
  marca: string;
  gastoTotal: number;
}

export async function fetchCampanasPendientes(): Promise<{ total: number; items: CampanaPendienteCategoria[] }> {
  return apiGet('/api/categorias/campanas-pendientes');
}

export async function asignarCategoriaCampana(campana: string, plataforma: string, categoria: string): Promise<{ success: boolean; message: string }> {
  return apiSend('/api/categorias/campanas-asignar', 'POST', { campana, plataforma, categoria });
}

// 22. EXPORTAR EXCEL CONSOLIDADO DE VENTAS
export async function downloadVentasExcel(
  fechaInicio?: string, fechaFin?: string,
  canal?: string | null, categoria?: string | null
): Promise<void> {
  const baseUrl = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';
  const params = new URLSearchParams();
  if (fechaInicio) params.append('start_date', fechaInicio);
  if (fechaFin) params.append('end_date', fechaFin);
  if (canal) params.append('canal', canal);
  if (categoria) params.append('categoria', categoria);

  const url = `${baseUrl}/api/export/ventas-excel?${params.toString()}`;
  const response = await fetch(url, { headers: { ...authHeaders() } });

  if (!response.ok) {
    const msg = await parseErrorMessage(response, `Error al generar el Excel (${response.status}).`);
    throw new Error(msg);
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const data = await response.json();
    throw new Error(data?.error || 'El backend no pudo generar el archivo Excel.');
  }

  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);

  const disposition = response.headers.get('content-disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `Ventas_Consolidadas_Kaltemp.xlsx`;

  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

// RESUMEN EJECUTIVO -- acepta rango de fechas opcional
export async function fetchResumen(fechaInicio?: string, fechaFin?: string): Promise<Record<string, any>> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  const qs = params.toString();
  return apiGet<Record<string, any>>(`/api/resumen${qs ? `?${qs}` : ''}`);
}

// 23. ALERTA DE PESO/MEDIDAS FALTANTE (Control Logístico)
export interface SkuPendientePeso {
  sku: string;
  producto: string;
  ventaTotal: number;
  lineas: number;
}

export interface AsignarPesoPayload {
  pesoKg?: number;
  largoCm?: number;
  anchoCm?: number;
  altoCm?: number;
  descontinuado: boolean;
}

export async function fetchPesoPendientes(): Promise<{ total: number; items: SkuPendientePeso[] }> {
  return apiGet('/api/peso-productos/pendientes');
}

export async function asignarPesoSku(sku: string, payload: AsignarPesoPayload): Promise<{ success: boolean; message: string }> {
  return apiSend('/api/peso-productos/asignar', 'POST', { sku, ...payload });
}