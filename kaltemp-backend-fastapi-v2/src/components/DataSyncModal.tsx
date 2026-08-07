import React, { useState, useEffect } from 'react';
import { Database, HardDrive, RefreshCw, UploadCloud, CheckCircle2, AlertCircle, FileText, ExternalLink, X, Table, Key, ShieldCheck, ChevronDown, ChevronUp, Play, Clock } from 'lucide-react';

interface DataSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
}

interface TableInfo {
  name: string;
  count: number;
}

interface DbStatus {
  exists: boolean;
  sizeMb?: string;
  lastUpdated?: string;
  tables?: TableInfo[];
  message?: string;
  error?: string;
}

interface ServiceAccountStatus {
  configured: boolean;
  clientEmail?: string;
  projectId?: string;
}

interface SyncStatus {
  corriendo: boolean;
  modo: string | null;
  paso_actual: string | null;
  pct_paso: number;
  mensaje: string;
  iniciado_en: string | null;
  terminado_en: string | null;
  resultados: Record<string, string>;
}

export const DataSyncModal: React.FC<DataSyncModalProps> = ({ isOpen, onClose, isDark }) => {
  const [driveUrl, setDriveUrl] = useState('https://drive.google.com/file/d/1E4T34DnWqzmqZily6RResbulPAxJRJ9Y/view?usp=drive_link');
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null);
  const [serviceAccount, setServiceAccount] = useState<ServiceAccountStatus | null>(null);
  const [jsonKeyInput, setJsonKeyInput] = useState('');
  const [showSaConfig, setShowSaConfig] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [diasHistorico, setDiasHistorico] = useState('1825');

  const fetchSyncStatus = async () => {
    try {
      const res = await fetch('/api/sync/status');
      const data = await res.json();
      setSyncStatus(data);
    } catch {
      // silencioso -- el polling reintenta solo en el próximo ciclo
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    fetchSyncStatus();
    const intervalo = setInterval(fetchSyncStatus, 3000);
    return () => clearInterval(intervalo);
  }, [isOpen]);

  const handleIniciarIncremental = async () => {
    setActionMessage(null);
    try {
      const res = await fetch('/api/sync/incremental', { method: 'POST' });
      const data = await res.json();
      if (data.iniciado) {
        setActionMessage({ type: 'info', text: 'Motor de actualización iniciado (últimos 30 días, todas las tablas).' });
        fetchSyncStatus();
      } else {
        setActionMessage({ type: 'error', text: data.error || 'No se pudo iniciar la sincronización.' });
      }
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err?.message || 'Error al iniciar la sincronización' });
    }
  };

  const handleIniciarHistorico = async () => {
    setActionMessage(null);
    const dias = parseInt(diasHistorico, 10);
    if (!dias || dias < 1) {
      setActionMessage({ type: 'error', text: 'Ingresa un número de días válido.' });
      return;
    }
    try {
      const res = await fetch('/api/sync/historico', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dias }),
      });
      const data = await res.json();
      if (data.iniciado) {
        setActionMessage({ type: 'info', text: `Carga histórica iniciada (${dias} días) -- puede tardar horas, puedes cerrar este modal y seguir usando la app.` });
        fetchSyncStatus();
      } else {
        setActionMessage({ type: 'error', text: data.error || 'No se pudo iniciar la carga histórica.' });
      }
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err?.message || 'Error al iniciar la carga histórica' });
    }
  };

  const fetchStatus = async () => {
    try {
      setIsLoading(true);
      const [resDb, resSa] = await Promise.all([
        fetch('/api/db/status'),
        fetch('/api/db/service-account')
      ]);
      const dataDb = await resDb.json();
      const dataSa = await resSa.json();
      setDbStatus(dataDb);
      setServiceAccount(dataSa);
    } catch (err: any) {
      setDbStatus({ exists: false, error: 'No se pudo verificar el estado del servidor de datos' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setActionMessage(null);
    }
  }, [isOpen]);

  const handleSaveServiceAccount = async () => {
    if (!jsonKeyInput.trim()) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/db/service-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonKey: jsonKeyInput.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setActionMessage({
          type: 'success',
          text: `¡Cuenta de Servicio ${data.clientEmail} configurada correctamente en el servidor!`,
        });
        setJsonKeyInput('');
        setShowSaConfig(false);
        fetchStatus();
      } else {
        setActionMessage({ type: 'error', text: data.error || 'Error al guardar la cuenta de servicio' });
      }
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err?.message || 'Error al enviar credenciales' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleJsonFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string;
      if (text) setJsonKeyInput(text);
    };
    reader.readAsText(file);
  };

  const handleDriveSync = async () => {
    if (!driveUrl) return;
    setIsLoading(true);
    setActionMessage({
      type: 'info',
      text: serviceAccount?.configured
        ? `Descargando vía Google Drive API con la Cuenta de Servicio (${serviceAccount.clientEmail})...`
        : 'Conectando con Google Drive y descargando kaltemp_matrix.duckdb...',
    });

    try {
      const res = await fetch('/api/db/sync-drive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ driveUrl }),
      });
      const data = await res.json();

      if (data.success) {
        setActionMessage({ type: 'success', text: data.message || '¡Base de datos kaltemp_matrix.duckdb sincronizada con éxito!' });
        fetchStatus();
      } else {
        setActionMessage({
          type: 'error',
          text: data.error || 'No se pudo sincronizar el archivo de Google Drive.',
        });
      }
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err?.message || 'Error al comunicar con la API de sincronización' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsLoading(true);
    setActionMessage({ type: 'info', text: 'Subiendo archivo kaltemp_matrix.duckdb al servidor...' });

    const formData = new FormData();
    formData.append('database', selectedFile);

    try {
      const res = await fetch('/api/db/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.success) {
        setActionMessage({ type: 'success', text: '¡Archivo de base de datos local cargado correctamente!' });
        setSelectedFile(null);
        fetchStatus();
      } else {
        setActionMessage({ type: 'error', text: data.error || 'Error al subir el archivo' });
      }
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err?.message || 'Error de conexión durante la subida' });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className={`relative max-w-2xl w-full rounded-2xl p-6 shadow-2xl border ${
        isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-200 text-slate-900'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-[#2C2C2E] mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-black tracking-tight">Conexión de Datos (kaltemp_matrix.duckdb)</h3>
              <p className="text-xs text-slate-400">Integración con Google Drive & Motor de Base de Datos DuckDB</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-slate-200/50 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Current Database Status */}
        <div className={`p-4 rounded-xl border mb-5 ${
          isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <HardDrive className="w-4 h-4 text-blue-500" /> Estado de Base de Datos Servidor
            </span>
            <button
              onClick={fetchStatus}
              disabled={isLoading}
              className="text-xs font-bold text-blue-500 hover:text-blue-400 flex items-center gap-1 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Actualizar
            </button>
          </div>

          {dbStatus?.exists ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-emerald-500 text-xs font-extrabold">
                <CheckCircle2 className="w-4 h-4" /> Archivo kaltemp_matrix.duckdb Activo ({dbStatus.sizeMb} MB)
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                Última modificación: {dbStatus.lastUpdated ? new Date(dbStatus.lastUpdated).toLocaleString('es-CL') : 'N/A'}
              </p>

              {dbStatus.tables && dbStatus.tables.length > 0 && (
                <div className="mt-2">
                  <p className="text-[11px] font-bold text-slate-300 mb-1.5 flex items-center gap-1">
                    <Table className="w-3.5 h-3.5 text-purple-400" /> Tablas detectadas en DuckDB:
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {dbStatus.tables.map((tbl) => (
                      <div key={tbl.name} className={`px-2.5 py-1.5 rounded-lg border text-[11px] font-mono flex items-center justify-between ${
                        isDark ? 'bg-[#1C1C1E] border-[#2C2C2E]' : 'bg-white border-slate-200'
                      }`}>
                        <span className="font-bold truncate">{tbl.name}</span>
                        <span className="text-blue-500 font-black ml-1">{tbl.count.toLocaleString('es-CL')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-amber-500 text-xs font-bold">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{dbStatus?.message || 'Pendiente de sincronización inicial del archivo kaltemp_matrix.duckdb'}</span>
            </div>
          )}
        </div>

        {/* Action Alert Message */}
        {actionMessage && (
          <div className={`p-3 rounded-xl border mb-4 text-xs font-bold flex items-start gap-2 ${
            actionMessage.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : actionMessage.type === 'error'
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              : 'bg-blue-500/10 border-blue-500/30 text-blue-400'
          }`}>
            {actionMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />}
            <div className="flex-1">{actionMessage.text}</div>
          </div>
        )}

        {/* Service Account Banner & Setup */}
        <div className={`p-4 rounded-xl border mb-5 ${
          serviceAccount?.configured
            ? (isDark ? 'bg-emerald-950/20 border-emerald-500/30' : 'bg-emerald-50 border-emerald-200')
            : (isDark ? 'bg-amber-950/20 border-amber-500/30' : 'bg-amber-50 border-amber-200')
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className={`w-5 h-5 ${serviceAccount?.configured ? 'text-emerald-500' : 'text-amber-500'}`} />
              <div>
                <h4 className="text-xs font-bold">Autenticación por Cuenta de Servicio GCP</h4>
                <p className="text-[11px] text-slate-400">
                  {serviceAccount?.configured
                    ? `Activa: ${serviceAccount.clientEmail}`
                    : 'Permite saltar restricciones de Google Workspace Enterprise en Drive'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowSaConfig(!showSaConfig)}
              className="text-xs font-bold text-blue-500 hover:text-blue-400 flex items-center gap-1 py-1 px-2.5 rounded-lg border border-blue-500/20 hover:bg-blue-500/10 transition-colors"
            >
              <Key className="w-3.5 h-3.5" />
              {serviceAccount?.configured ? 'Cambiar Clave JSON' : 'Configurar Clave JSON'}
              {showSaConfig ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          {showSaConfig && (
            <div className="mt-4 pt-4 border-t border-slate-200/40 dark:border-slate-800 space-y-3 animate-in fade-in duration-150">
              <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[11px] text-slate-300 space-y-1">
                <p className="font-extrabold text-blue-400">Paso 1: Compartir en Google Drive</p>
                <p>
                  En Google Drive, comparte el archivo <code className="font-mono text-white bg-black/40 px-1 py-0.5 rounded">kaltemp_matrix.duckdb</code> con el correo:
                </p>
                <p className="font-mono font-bold text-emerald-400 select-all bg-emerald-950/40 p-1.5 rounded border border-emerald-500/30 text-[11px]">
                  kaltemp-bot@kaltemp-data-app.iam.gserviceaccount.com
                </p>
                <p className="font-extrabold text-blue-400 pt-1">Paso 2: Cargar Clave JSON de GCP</p>
                <p>Carga el archivo .json descargado desde Google Cloud Console (Cuentas de Servicio &gt; Claves):</p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <label className={`flex-1 p-2 rounded-lg border border-dashed flex items-center justify-center gap-2 cursor-pointer text-xs font-bold ${
                    isDark ? 'border-slate-700 bg-[#1C1C1E] hover:border-blue-500' : 'border-slate-300 bg-white hover:border-blue-500'
                  }`}>
                    <FileText className="w-4 h-4 text-blue-400" />
                    <span>Subir archivo .json de la clave</span>
                    <input type="file" accept=".json" onChange={handleJsonFileUpload} className="hidden" />
                  </label>
                </div>

                <textarea
                  rows={4}
                  value={jsonKeyInput}
                  onChange={(e) => setJsonKeyInput(e.target.value)}
                  placeholder='O pega aquí el contenido JSON de la clave (ej: { "type": "service_account", "client_email": "kaltemp-bot@...", ... })'
                  className={`w-full text-[11px] font-mono p-2.5 rounded-lg border outline-none resize-none ${
                    isDark ? 'bg-[#1C1C1E] border-[#333339] text-white focus:border-blue-500' : 'bg-white border-slate-300 focus:border-blue-500'
                  }`}
                />

                <button
                  onClick={handleSaveServiceAccount}
                  disabled={isLoading || !jsonKeyInput.trim()}
                  className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-emerald-600/20"
                >
                  <ShieldCheck className="w-3.5 h-3.5" /> Guardar Credenciales de Cuenta de Servicio
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Motor de Actualización -- corre los sync directo desde la app */}
        <div className={`p-4 rounded-xl border mb-5 ${
          isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <RefreshCw className={`w-4 h-4 text-emerald-500 ${syncStatus?.corriendo ? 'animate-spin' : ''}`} />
            <h4 className="text-xs font-bold uppercase tracking-wider">Motor de Actualización</h4>
          </div>

          {syncStatus?.corriendo && (
            <div className="mb-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center justify-between text-[11px] font-bold mb-1.5">
                <span className="flex items-center gap-1.5 text-blue-400">
                  <Clock className="w-3.5 h-3.5" /> {syncStatus.paso_actual || 'Procesando...'}
                </span>
                <span className="text-blue-400">{syncStatus.pct_paso}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-blue-950/40 overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${syncStatus.pct_paso}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5">{syncStatus.mensaje}</p>
            </div>
          )}

          {!syncStatus?.corriendo && syncStatus?.resultados && Object.keys(syncStatus.resultados).length > 0 && (
            <div className="mb-3 p-3 rounded-lg bg-slate-500/10 border border-slate-500/20 space-y-1">
              <p className="text-[11px] font-bold text-slate-300">Última corrida ({syncStatus.modo}):</p>
              {Object.entries(syncStatus.resultados).map(([paso, estado]) => (
                <div key={paso} className="flex items-center gap-1.5 text-[11px]">
                  {estado === 'OK'
                    ? <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                    : <AlertCircle className="w-3 h-3 text-rose-500 shrink-0" />}
                  <span className="font-mono">{paso}</span>
                  {estado !== 'OK' && <span className="text-rose-400 truncate">— {estado}</span>}
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={handleIniciarIncremental}
              disabled={!!syncStatus?.corriendo}
              className="py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-emerald-600/20"
            >
              <Play className="w-3.5 h-3.5" /> Actualizar Ahora (últimos 30 días)
            </button>

            <div className="flex items-center gap-1.5">
              <input
                type="number"
                min={1}
                max={3650}
                value={diasHistorico}
                onChange={(e) => setDiasHistorico(e.target.value)}
                disabled={!!syncStatus?.corriendo}
                className={`w-20 text-xs font-mono p-2 rounded-lg border outline-none disabled:opacity-50 ${
                  isDark ? 'bg-[#1C1C1E] border-[#333339] text-white' : 'bg-white border-slate-300'
                }`}
              />
              <button
                onClick={handleIniciarHistorico}
                disabled={!!syncStatus?.corriendo}
                className="flex-1 py-2 px-3 rounded-lg bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-purple-600/20"
              >
                Carga Histórica (días)
              </button>
            </div>
          </div>
          <p className="text-[10px] text-slate-500 mt-2">
            "Actualizar Ahora" corre ventas + stock + pendientes + notas de crédito + falabella + envíame (30 días).
            "Carga Histórica" solo re-sincroniza ventas, en la ventana de días que indiques -- úsalo una vez para el historial completo.
          </p>
        </div>

        {/* Sync Options Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Option A: Google Drive Link */}
          <div className={`p-4 rounded-xl border ${
            isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <ExternalLink className="w-4 h-4 text-blue-500" />
              <h4 className="text-xs font-bold uppercase tracking-wider">Opción 1: Google Drive</h4>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Conecta el enlace compartido de Google Drive de tu cuenta empresa Kaltemp.
            </p>

            <div className="space-y-2.5">
              <input
                type="text"
                value={driveUrl}
                onChange={(e) => setDriveUrl(e.target.value)}
                placeholder="https://drive.google.com/file/d/.../view"
                className={`w-full text-xs font-mono p-2.5 rounded-lg border outline-none transition-all ${
                  isDark ? 'bg-[#1C1C1E] border-[#333339] text-white focus:border-blue-500' : 'bg-white border-slate-300 focus:border-blue-500'
                }`}
              />
              <button
                onClick={handleDriveSync}
                disabled={isLoading || !driveUrl}
                className="w-full py-2 px-3 rounded-lg bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-blue-500/20"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Sincronizar Google Drive
              </button>
            </div>
          </div>

          {/* Option B: Direct Local Upload */}
          <div className={`p-4 rounded-xl border ${
            isDark ? 'bg-[#121214] border-[#2C2C2E]' : 'bg-slate-50 border-slate-200'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <UploadCloud className="w-4 h-4 text-purple-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider">Opción 2: Carga Directa</h4>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Carga tu archivo <code className="text-blue-400 font-mono">kaltemp_matrix.duckdb</code> desde tu computador.
            </p>

            <form onSubmit={handleFileUpload} className="space-y-2.5">
              <label className={`w-full p-2.5 rounded-lg border border-dashed flex items-center justify-center gap-2 cursor-pointer transition-colors ${
                isDark ? 'border-slate-700 hover:border-blue-500 bg-[#1C1C1E]' : 'border-slate-300 hover:border-blue-500 bg-white'
              }`}>
                <FileText className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-bold truncate max-w-[170px]">
                  {selectedFile ? selectedFile.name : 'Seleccionar .duckdb'}
                </span>
                <input
                  type="file"
                  accept=".duckdb,.db"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>

              <button
                type="submit"
                disabled={isLoading || !selectedFile}
                className="w-full py-2 px-3 rounded-lg bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-purple-600/20"
              >
                <UploadCloud className="w-3.5 h-3.5" /> Subir a Servidor
              </button>
            </form>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-5 pt-3 border-t border-slate-200/60 dark:border-[#2C2C2E] flex items-center justify-between text-[11px] text-slate-400">
          <span>⚡ Carga ultra-rápida asistida por DuckDB en servidor Cloud Run</span>
          <button onClick={onClose} className="font-bold hover:underline">Cerrar</button>
        </div>
      </div>
    </div>
  );
};
