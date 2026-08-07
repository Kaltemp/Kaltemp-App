// avatarCatalog.ts — Catálogo fijo de avatares (ícono + color) para elegir
// en vez de solo iniciales sobre un color. Colócalo junto a
// UserManagementModal.tsx (o donde vivan tus otros componentes).
//
// Los nombres de "icon" deben existir como export en lucide-react (se
// resuelven dinámicamente en AvatarBadge.tsx / AvatarPickerModal.tsx vía
// `(LucideIcons as any)[icon]`).

export interface AvatarOption {
  id: string;
  icon: string; // nombre exacto del ícono en lucide-react
  color: string;
  label: string;
}

export const AVATAR_CATALOG: AvatarOption[] = [
  { id: 'flame', icon: 'Flame', color: '#DC2626', label: 'Calefacción' },
  { id: 'snowflake', icon: 'Snowflake', color: '#0EA5E9', label: 'Aire Acondicionado' },
  { id: 'sun', icon: 'Sun', color: '#F59E0B', label: 'Energía' },
  { id: 'wind', icon: 'Wind', color: '#06B6D4', label: 'Ventilación' },
  { id: 'droplet', icon: 'Droplet', color: '#2563EB', label: 'Agua Sanitaria' },
  { id: 'zap', icon: 'Zap', color: '#CA8A04', label: 'Generadores' },
  { id: 'waves', icon: 'Waves', color: '#0891B2', label: 'Piscina' },
  { id: 'thermometer', icon: 'Thermometer', color: '#DB2777', label: 'Temperatura' },
  { id: 'wrench', icon: 'Wrench', color: '#475569', label: 'Herramientas' },
  { id: 'lightbulb', icon: 'Lightbulb', color: '#D97706', label: 'Iluminación' },
  { id: 'home', icon: 'Home', color: '#7C3AED', label: 'Hogar' },
  { id: 'shield', icon: 'ShieldCheck', color: '#059669', label: 'Seguridad' },
  { id: 'star', icon: 'Star', color: '#EAB308', label: 'Destacado' },
  { id: 'crown', icon: 'Crown', color: '#B91C1C', label: 'Administrador' },
  { id: 'rocket', icon: 'Rocket', color: '#4F46E5', label: 'Ventas' },
  { id: 'heart', icon: 'Heart', color: '#E11D48', label: 'Favorito' },
  { id: 'sparkles', icon: 'Sparkles', color: '#9333EA', label: 'Marketing' },
  { id: 'fan', icon: 'Fan', color: '#0D9488', label: 'Climatización' },
];

// Paleta para el modo "solo iniciales" (sin ícono), para quien prefiera
// mantenerlo simple.
export const INITIALS_COLOR_PALETTE: string[] = [
  '#CC0000', '#2563EB', '#059669', '#D97706',
  '#7C3AED', '#DB2777', '#0891B2', '#475569',
];
