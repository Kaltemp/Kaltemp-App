import React from 'react';
import * as LucideIcons from 'lucide-react';
import { resolveAvatarImageUrl } from '../services/api';

interface AvatarBadgeProps {
  nombre: string;
  avatarColor: string;
  avatarIcon?: string | null;
  avatarImageUrl?: string | null;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE_MAP: Record<string, { box: string; icon: string; text: string }> = {
  xs: { box: 'w-5 h-5', icon: 'w-2.5 h-2.5', text: 'text-[9px]' },
  sm: { box: 'w-8 h-8', icon: 'w-4 h-4', text: 'text-xs' },
  md: { box: 'w-10 h-10', icon: 'w-5 h-5', text: 'text-sm' },
  lg: { box: 'w-16 h-16', icon: 'w-7 h-7', text: 'text-xl' },
};

/**
 * Avatar de usuario, en orden de prioridad:
 *   1. Foto propia subida (avatarImageUrl)
 *   2. Ícono del catálogo (avatarIcon) sobre avatarColor
 *   3. Inicial del nombre sobre avatarColor (comportamiento original)
 */
export const AvatarBadge: React.FC<AvatarBadgeProps> = ({
  nombre,
  avatarColor,
  avatarIcon,
  avatarImageUrl,
  size = 'md',
  className = '',
}) => {
  const dims = SIZE_MAP[size] || SIZE_MAP.md;
  const resolvedImageUrl = resolveAvatarImageUrl(avatarImageUrl);

  if (resolvedImageUrl) {
    return (
      <img
        src={resolvedImageUrl}
        alt={nombre}
        className={`${dims.box} rounded-full object-cover shadow shrink-0 ${className}`}
      />
    );
  }

  const IconComponent = avatarIcon ? (LucideIcons as unknown as Record<string, React.FC<any>>)[avatarIcon] : null;

  return (
    <div
      className={`${dims.box} rounded-full flex items-center justify-center font-black text-white shadow shrink-0 ${dims.text} ${className}`}
      style={{ backgroundColor: avatarColor }}
    >
      {IconComponent ? (
        <IconComponent className={dims.icon} />
      ) : (
        nombre.charAt(0).toUpperCase()
      )}
    </div>
  );
};
