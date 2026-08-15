// ============================================================
// ARCHIVO: brandTokens.ts
// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\theme\brandTokens.ts
// ============================================================
/**
 * theme/brandTokens.ts — Fuente única de verdad para los colores del
 * modo de marca (Standard / Kaltemp / Tom Palmer), cruzados con
 * claro/oscuro.
 *
 * IMPORTANTE (15-ago-2026): el azul que se usaba antes para Tom Palmer
 * en Sidebar.tsx (#1D6FA5, #4FA8DE, #0F4C81, #58C6E5) NO corresponde al
 * manual de marca real de Tom Palmer -- ese manual define coral
 * (#FF8F7D) + navy (#133874) + durazno claro (#FFD7CB). Este archivo
 * usa los colores reales del manual. Kaltemp: rojo (#CC0000) + rojo
 * oscuro (#800404) + gris claro (#CCCCCC), también del manual real.
 *
 * REGLA DE USO ("esencia, no copia fiel" -- ver conversación): el color
 * de marca se usa en ACENTOS (hairline, ítem activo, número de KPI
 * destacado, botones primarios) y en un TINTE PASTEL DE TARJETA SOLO EN
 * MODO CLARO (el manual no define un modo oscuro propio para ninguna
 * marca, así que en oscuro el chrome se queda neutro para las dos --
 * solo cambia el acento). Nunca se usa como color de fondo saturado de
 * pantalla completa: el rojo Kaltemp también es el color de alerta/
 * peligro en toda la app (stock en quiebre, margen negativo, notas de
 * crédito) -- un fondo rojo haría que esas alertas dejen de destacar.
 */

export type BrandMode = 'standard' | 'kaltemp' | 'tompalmer';

export interface BrandTokens {
  /** Color de acento principal: hairline, borde de ítem activo, íconos activos, botones primarios. */
  accent: string;
  /** Variante oscura del acento -- texto sobre fondos con tinte pastel en modo claro. */
  accentStrong: string;
  /** Background CSS (sólido o gradiente) para el filete de 3px superior del sidebar (horizontal). */
  hairline: string;
  /** Background CSS para la barra de 3px del ítem de nav activo (vertical). */
  activeBar: string;
  /** Tinte pastel de tarjeta -- SOLO se aplica en modo claro. En oscuro, usar el bg neutro normal del componente. */
  cardTintLight: string | null;
  /** Borde a juego con cardTintLight, modo claro. */
  cardBorderLight: string | null;
}

const KALTEMP_ROJO = '#CC0000';
const KALTEMP_ROJO_OSCURO = '#800404';
const KALTEMP_TINTE_CLARO = '#FBEAEA';
const KALTEMP_BORDE_CLARO = '#E8CCCC';

const TOMPALMER_CORAL = '#FF8F7D';
const TOMPALMER_NAVY = '#133874';
const TOMPALMER_TINTE_CLARO = '#FFEDE8';
const TOMPALMER_BORDE_CLARO = '#F5D6CC';

const STANDARD_GRADIENTE = `linear-gradient(90deg, ${KALTEMP_ROJO} 0%, ${TOMPALMER_CORAL} 100%)`;
const STANDARD_GRADIENTE_VERTICAL = `linear-gradient(180deg, ${KALTEMP_ROJO}, ${TOMPALMER_CORAL})`;

/**
 * Devuelve los tokens de color para el modo de marca + apariencia
 * (claro/oscuro) dados. Los componentes NUNCA deben hardcodear estos
 * hex directamente -- siempre a través de esta función, para que un
 * cambio de paleta futuro (ej. si Kaltemp actualiza su manual) se
 * propague desde un solo lugar.
 */
export function getBrandTokens(mode: BrandMode, isDark: boolean): BrandTokens {
  if (mode === 'kaltemp') {
    return {
      accent: KALTEMP_ROJO,
      accentStrong: KALTEMP_ROJO_OSCURO,
      hairline: KALTEMP_ROJO,
      activeBar: KALTEMP_ROJO,
      cardTintLight: isDark ? null : KALTEMP_TINTE_CLARO,
      cardBorderLight: isDark ? null : KALTEMP_BORDE_CLARO,
    };
  }
  if (mode === 'tompalmer') {
    return {
      accent: TOMPALMER_CORAL,
      accentStrong: TOMPALMER_NAVY,
      hairline: TOMPALMER_CORAL,
      activeBar: TOMPALMER_CORAL,
      cardTintLight: isDark ? null : TOMPALMER_TINTE_CLARO,
      cardBorderLight: isDark ? null : TOMPALMER_BORDE_CLARO,
    };
  }
  // 'standard' -- degradado de ambas marcas, sin tinte de tarjeta.
  return {
    accent: KALTEMP_ROJO,
    accentStrong: KALTEMP_ROJO_OSCURO,
    hairline: STANDARD_GRADIENTE,
    activeBar: STANDARD_GRADIENTE_VERTICAL,
    cardTintLight: null,
    cardBorderLight: null,
  };
}

/**
 * Módulos con EXCEPCIÓN fija a 'standard', sin importar el selector
 * global (Resumen y Cumplimiento de Ventas muestran ambas marcas a la
 * vez o un total general -- ver conversación 15-ago-2026). Se listan
 * acá para que cualquier componente pueda preguntar
 * `MODULOS_SIEMPRE_STANDARD.has(activeModule)` en vez de hardcodear la
 * excepción en varios lugares.
 *
 * 'indicadores_d2c' y 'campanas_mkt' NO están en esta lista a propósito
 * -- esos dos módulos resuelven su propio modo de marca internamente,
 * a partir de su selector interno (ver D2CPerformanceView.tsx y
 * MarketingCampaignsView.tsx), y deben ignorar tanto esta lista como el
 * selector global.
 */
export const MODULOS_SIEMPRE_STANDARD = new Set(['resumen', 'cumplimiento_ventas']);