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

// 5. NOTAS DE CRÉDITO — sin parámetros (sync_dependent.py)
export async function fetchCreditNotes(): Promise<any> {
  return apiGet<any>('/api/notas-credito');
}

// Alias en español usado por CreditNotesView.tsx
export async function fetchNotasCredito(): Promise<any> {
  return fetchCreditNotes();
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
// (sin parámetros -- sync_dependent.py trae hasta 2000 registros más recientes)
export async function fetchEnviameShipments(): Promise<any> {
  return apiGet<any>('/api/enviame-shipments');
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

// 13. CANAL INMOBILIARIA
export async function fetchRealEstate(
  fechaInicio?: string, fechaFin?: string
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  return apiGet<any>(`/api/real-estate?${params.toString()}`);
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
  vendedores?: string[]
): Promise<any> {
  const params = new URLSearchParams();
  if (fechaInicio) params.append('fecha_inicio', fechaInicio);
  if (fechaFin) params.append('fecha_fin', fechaFin);
  if (vendedores && vendedores.length > 0) {
    params.append('vendedores', vendedores.join(','));
  }
  return apiGet<any>(`/api/cumplimiento?${params.toString()}`);
}

// 16. FILTROS GLOBALES
// NOTA: filtros.py devuelve claves en español: {categorias, vendedores, bodegas}
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
// ⚠️ PENDIENTE DE CONFIRMAR: no hay router "/api/kpi-review" en los routers
// vistos hasta ahora (channels, sku, tendencia, abandoned_carts, marketing,
// leads, cumplimiento, fulfillment, distributors, temperatura_ventas,
// sync_dependent, filtros, db_sync, sync_admin). Es probable que viva en
// sync_dependent.py -- confirmar cuando se revise ese archivo.
export async function fetchKpiReview(): Promise<any> {
  return apiGet<any>('/api/kpi-review');
}

// 18. DISPARADOR DE SINCRONIZACIÓN DE DATOS
// sync_admin.py NO tiene POST /api/sync/run -- expone /api/sync/incremental
// (ventas 30 días + stock + pendientes + notas de crédito + envíame) y
// /api/sync/historico (con {dias} en el body, para carga histórica inicial).
export async function runDataSync(): Promise<any> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${baseUrl}/api/sync/incremental`, { method: 'POST' });
  if (!response.ok) throw new Error('Error al sincronizar datos');
  return response.json();
}

// Consulta el progreso de una sincronización en curso (polling)
export async function fetchSyncStatus(): Promise<any> {
  return apiGet<any>('/api/sync/status');
}

// 19. AUTENTICACIÓN Y GESTIÓN DE USUARIOS (RBAC)
// Reemplaza la validación 100% client-side que vivía en UserContext.tsx
// (con las contraseñas de todos los usuarios en texto plano en el bundle).
// El backend valida contra un hash bcrypt y devuelve un token de sesión.
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

// La API guarda avatarImageUrl como ruta relativa (/static/avatars/xxx.jpg)
// -- hay que anteponerle la base URL del backend para poder mostrarla en un <img>.
export function resolveAvatarImageUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;
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
  avatarColor?: string; avatarIcon?: string | null;
  blockedModules?: string[]; allowedModulesOnly?: string[];
}): Promise<AuthUser> {
  return apiSend('/api/auth/users', 'POST', user);
}

export async function updateUserRequest(userId: string, changes: {
  nombre?: string; rol?: string; avatarColor?: string;
  // '' (string vacío) le pide al backend borrar el ícono y volver a solo
  // iniciales -- undefined/omitido significa "no tocar este campo".
  avatarIcon?: string;
  blockedModules?: string[]; allowedModulesOnly?: string[];
}): Promise<AuthUser> {
  return apiSend(`/api/auth/users/${userId}`, 'PATCH', changes);
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

// Subir/quitar foto propia de avatar -- multipart, no puede usar apiSend
// (ese fuerza Content-Type: application/json).
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
    const msg = await parseErrorMessage(response, `Error al subir la imagen (${response.status})`);
    throw new Error(msg);
  }
  return response.json();
}

export async function removeAvatarImageRequest(userId: string): Promise<AuthUser> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const response = await fetch(`${baseUrl}/api/auth/users/${userId}/avatar-image`, {
    method: 'DELETE',
    headers: { ...authHeaders() },
  });
  if (!response.ok) {
    const msg = await parseErrorMessage(response, `Error al quitar la imagen (${response.status})`);
    throw new Error(msg);
  }
  return response.json();
}

// 20. ALERTA DE CATEGORÍA FALTANTE
// SKUs que se vendieron pero no tienen categoría real asignada -- ver
// routers/categorias.py. Asignar una categoría acá no recalcula ventas
// pasadas al instante: se aplica en la próxima sincronización.
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

// 21. ALERTA DE CATEGORÍA FALTANTE -- CAMPAÑAS (usa el mismo catálogo
// de categorías que la alerta de SKUs, fetchCategoriasCatalogo)
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
// Distinto al resto: el backend devuelve un archivo binario (StreamingResponse),
// no JSON -- hay que pedirlo como blob y disparar la descarga manualmente.
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

  // Por si el backend devolvió un error 200 con JSON en vez del archivo
  // (el endpoint atrapa excepciones y responde {"error": "..."} con
  // status 200 en vez de un código de error real).
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const data = await response.json();
    throw new Error(data?.error || 'El backend no pudo generar el archivo Excel.');
  }

  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);

  // Nombre de archivo desde el header Content-Disposition si viene, si no un default.
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