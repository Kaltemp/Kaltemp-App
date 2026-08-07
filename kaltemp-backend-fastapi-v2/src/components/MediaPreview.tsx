import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';

interface MediaPreviewProps {
  url: string;
  title?: string;
  className?: string;
}

export const MediaPreview: React.FC<MediaPreviewProps> = ({ url, title, className = '' }) => {
  const [hasError, setHasError] = useState(false);

  if (!url || hasError) {
    return (
      <div className={`flex flex-col items-center justify-center p-8 text-slate-400 bg-slate-100 dark:bg-[#252528] rounded-xl ${className}`}>
        <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
        <span className="text-xs font-medium">No se pudo cargar la vista previa del creativo</span>
      </div>
    );
  }

  const cleanUrl = url.toLowerCase().split('?')[0];

  // Identifica si es un archivo de video directo
  const isDirectVideo = 
    cleanUrl.endsWith('.mp4') || 
    cleanUrl.endsWith('.webm') || 
    cleanUrl.endsWith('.mov');

  if (isDirectVideo) {
    return (
      <div className={`relative overflow-hidden rounded-xl bg-black flex items-center justify-center ${className}`}>
        <video 
          src={url} 
          controls 
          autoPlay 
          muted 
          loop 
          onError={() => setHasError(true)}
          className="max-h-[450px] w-auto object-contain rounded-lg"
        >
          Tu navegador no soporta reproducción de video.
        </video>
      </div>
    );
  }

  // Renderiza imágenes o miniaturas de videos (Meta JPGs/PNGs)
  return (
    <div className={`relative overflow-hidden rounded-xl flex items-center justify-center ${className}`}>
      <img
        src={url}
        alt={title || "Vista previa del anuncio"}
        onError={() => setHasError(true)}
        className="max-h-[450px] w-auto object-contain rounded-lg shadow-md"
      />
    </div>
  );
};

export default MediaPreview;