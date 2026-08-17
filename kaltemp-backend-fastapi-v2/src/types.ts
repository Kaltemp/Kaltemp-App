// ============================================================
// ARCHIVO: types.ts
// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\types.ts
// (Respaldar el archivo actual antes de reemplazar: Copy-Item types.ts types.ts.bak)
// ============================================================

export type ThemeMode = 'dark' | 'light';

export type ModuleId =
  | 'resumen'
  | 'principal'
  | 'ventas_sku'
  | 'stock'
  | 'pendientes_despacho'
  | 'notas_credito'
  | 'fulfillment'
  | 'control_logistico'
  | 'leads'
  | 'carros_abandonados'
  | 'indicadores_d2c'
  | 'campanas_mkt'
  | 'distribuidores'
  | 'inmobiliaria'
  | 'ventas_temperatura'
  | 'cumplimiento_ventas';

export interface ChannelSale {
  canal: string;
  bsale: number;
  full: number;
  totalBruto: number;
  contribucion: number;
  neto: number;
  txs: number;
  tkp: number;
  wow: number;
  yoy: number;
  twoYoy: number;
  wowPct: number;
  yoyPct: number;
  twoYoyPct: number;
  margenFrontal: number;
  share: number;
}

export interface SkuNode {
  id: string;
  nombre: string;
  sku: string;
  cantCy: number;
  cantWow: number;
  cantYoy: number;
  ventaCy: number;
  ventaWow: number;
  ventaYoy: number;
  netoCy: number;
  netoYoy?: number;
  contriCy: number;
  contriYoy?: number;
  pPromCy: number;
  pPromWow: number;
  pPromYoy: number;
  margenCy: number;
  margenYoy: number;
  categoria: string;
  vendedores?: SellerNode[];
}

export interface SellerNode {
  id: string;
  nombre: string;
  cantCy: number;
  cantWow?: number;
  cantYoy?: number;
  ventaCy: number;
  ventaWow?: number;
  ventaYoy?: number;
  netoCy?: number;
  contriCy?: number;
  pPromCy: number;
  pPromWow?: number;
  pPromYoy?: number;
  margenCy: number;
  margenYoy?: number;
  documentos?: DocumentNode[];
}

export interface DocumentNode {
  id: string;
  nombre: string;
  cantCy: number;
  cantWow?: number;
  cantYoy?: number;
  ventaCy: number;
  ventaWow?: number;
  ventaYoy?: number;
  netoCy?: number;
  contriCy?: number;
  pPromCy: number;
  pPromWow?: number;
  pPromYoy?: number;
  margenCy: number;
  margenYoy?: number;
  clientes?: ClientNode[];
}

export interface ClientNode {
  id: string;
  nombre: string;
  cantCy: number;
  cantWow?: number;
  cantYoy?: number;
  ventaCy: number;
  ventaWow?: number;
  ventaYoy?: number;
  netoCy?: number;
  contriCy?: number;
  pPromCy: number;
  pPromWow?: number;
  pPromYoy?: number;
  margenCy: number;
  margenYoy?: number;
}

export interface StockItem {
  sku: string;
  producto: string;
  categoria: string;
  bodegas: Record<string, number>;
  totalStock: number;
  venta14d: number;
  ventaDiariaProm: number;
  diasCobertura: number;
  estado: '🔴 QUIEBRE' | '🔴' | '🟡' | '🟢';
}

export interface PendingDispatchItem {
  id: string;
  sku: string;
  producto: string;
  categoria: string;
  bodega: string;
  cantidadReservada: number;
}

export interface PendingDispatchDocItem {
  id: string;
  sku: string;
  descripcion: string;
  documento: string;
  tipoDocumento: string;
  cliente: string;
  vendedor: string;
  bodega: string;
  fechaEmision: string;
  diasPendiente: number;
  montoDocumento: number;
  cantidad: number;
  pedidoNumero: string | null;
  pedidoOrigen: string | null;
  estadoEnvio: string | null;
}

export interface CreditNoteItem {
  id: string;
  documento: string;
  cliente: string;
  vendedor?: string;
  documentoOriginal?: string | null;
  descripcionProducto?: string | null;
  fechaEmision: string;
  fechaCaida: string;
  fechaGeneracion?: string | null;
  diasDesfase: number;
  monto: number;
  alerta: boolean;
}

export interface FulfillmentProgram {
  codigo: 'FBF' | 'FBM' | 'FBP' | 'FBR';
  canal: 'FALABELLA' | 'MERCADOLIBRE' | 'PARIS' | 'RIPLEY';
  nombre: string;
  monto: number;
  color: string;
}

export interface EnviameShipment {
  id: string;
  ref: string;
  cliente: string;
  telefono: string;
  comuna: string;
  direccion: string;
  courier: string;
  estado: string;
  costoEnvio: number;
  trackingNumber: string;
  trackingUrl: string;
  esIncidencia: boolean;
  fechaCreacion: string;
}

export interface LeadItem {
  id: string;
  fecha: string;
  semana: number;
  semanaLbl: string;
  mesNum: number;
  mesLbl: string;
  fuente: 'Google' | 'Facebook' | 'Instagram' | 'kaltemp.cl' | 'ChatGPT' | 'Copilot';
  canal: 'WhatsApp' | 'Chat Web';
  estado: 'NUEVO' | 'EN PROGRESO' | 'CON VENTA' | 'SIN VENTA';
  vendedor: string;
  calificacion: number;
  calificacionLbl: string;
  comuna: string;
  categoriaInteres: string;
  nombre: string;
}

export interface AbandonedCart {
  id: string;
  fecha: string;
  fechaDia: string;
  producto: string;
  sku: string;
  categoria: string;
  precioUnitario: number;
  totalPrice: number;
  estado: 'ABANDONADO' | 'RECUPERADO';
  cliente: string;
}

export interface D2CCategoryPerf {
  categoria: string;
  inversion: number;
  inversionYoy: number;
  venta: number;
  ventaYoy: number;
  ordenes: number;
  ordenesYoy: number;
  tkp: number;
  tkpYoy: number;
  tacos: number;
  tacosYoy: number;
}

export interface CampaignItem {
  id: string;
  campana: string;
  plataforma: 'Meta' | 'Google';
  gastoCy: number;
  gastoWow: number;
  gastoYoy: number;
  impresionesCy: number;
  impresionesWow: number;
  impresionesYoy: number;
  clicsCy: number;
  clicsWow: number;
  clicsYoy: number;
  ctrCy: number;
  ctrWow: number;
  ctrYoy: number;
  roasCy: number;
  roasWow: number;
  roasYoy: number;
  valorComprasCy: number;
}

export interface DistributorItem {
  id: string;
  cliente: string;
  categoria: string;
  producto: string;
  v2024: number;
  c2024: number;
  v2025: number;
  c2025: number;
  v2026: number;
  c2026: number;
  yoyPct: number;
}

export interface DailyTempSale {
  fechaStr: string;
  fechaDisp: string;
  brutoTotal: number;
  tempMax: number;
  tempMin: number;
}