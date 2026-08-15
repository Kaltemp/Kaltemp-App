// ============================================================
// ARCHIVO: App.tsx
// GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\src\App.tsx
// (Respaldar el archivo actual antes de reemplazar: Copy-Item App.tsx App.tsx.bak)
// ============================================================

import React, { useState, useEffect } from 'react';
import { ModuleId, ThemeMode, BrandMode } from './types';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { KpiReviewModal } from './components/KpiReviewModal';
import { LoginView } from './components/LoginView';
import { RestrictedModuleView } from './components/RestrictedModuleView';
import { UserManagementModal } from './components/UserManagementModal';
import { useUser } from './context/UserContext';
import { useGlobalFilter } from './context/FilterContext';

import { MainExecutiveView } from './views/MainExecutiveView';
import { ResumenView } from './views/ResumenView';
import { SkuSalesView } from './views/SkuSalesView';
import { StockView } from './views/StockView';
import { PendingDispatchView } from './views/PendingDispatchView';
import { CreditNotesView } from './views/CreditNotesView';
import { FulfillmentView } from './views/FulfillmentView';
import { LogisticsView } from './views/LogisticsView';
import { LeadsView } from './views/LeadsView';
import { AbandonedCartsView } from './views/AbandonedCartsView';
import { D2CPerformanceView } from './views/D2CPerformanceView';
import { MarketingCampaignsView } from './views/MarketingCampaignsView';
import { DistributorsView } from './views/DistributorsView';
import { RealEstateView } from './views/RealEstateView';
import { TemperatureSalesView } from './views/TemperatureSalesView';
import { SalesTargetCumplimientoView } from './views/SalesTargetCumplimientoView';

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>('light');
  // Selector global de modo de marca (Standard/Kaltemp/Tom Palmer) --
  // ver theme/brandTokens.ts para la paleta y las reglas de excepción.
  // Persistido igual que 'theme' para que se recuerde entre sesiones.
  const [brandMode, setBrandMode] = useState<BrandMode>(() => {
    const guardado = localStorage.getItem('kaltemp_brand_mode');
    return guardado === 'kaltemp' || guardado === 'tompalmer' ? guardado : 'standard';
  });
  const [activeModule, setActiveModule] = useState<ModuleId>('principal');
  const { startDate, setStartDate, endDate, setEndDate } = useGlobalFilter();
  const [selectedCategory, setSelectedCategory] = useState<string>('Todas');
  const [isKpiModalOpen, setIsKpiModalOpen] = useState<boolean>(false);
  const [isUserModalOpen, setIsUserModalOpen] = useState<boolean>(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);

  const { isModuleAllowed, currentUser, isLoadingSession, logout } = useUser();

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((prev) => !prev);
  };

  const handleThemeToggle = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleBrandModeChange = (mode: BrandMode) => {
    setBrandMode(mode);
    localStorage.setItem('kaltemp_brand_mode', mode);
  };

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const renderActiveModule = () => {
    if (!isModuleAllowed(activeModule)) {
      return (
        <RestrictedModuleView
          moduleId={activeModule}
          theme={theme}
          onGoBack={() => setActiveModule('principal')}
          onOpenUserModal={() => setIsUserModalOpen(true)}
        />
      );
    }

    switch (activeModule) {
      case 'resumen': return <ResumenView theme={theme} onSelectModule={setActiveModule} />;
      case 'principal': return <MainExecutiveView theme={theme} brandMode={brandMode} />;
      case 'ventas_sku': return <SkuSalesView theme={theme} brandMode={brandMode} selectedCategory={selectedCategory} onCategoryChange={setSelectedCategory} />;
      case 'stock': return <StockView theme={theme} brandMode={brandMode} />;
      case 'pendientes_despacho': return <PendingDispatchView theme={theme} brandMode={brandMode} />;
      case 'notas_credito': return <CreditNotesView theme={theme} brandMode={brandMode} />;
      case 'fulfillment': return <FulfillmentView theme={theme} brandMode={brandMode} />;
      case 'control_logistico': return <LogisticsView theme={theme} brandMode={brandMode} />;
      case 'leads': return <LeadsView theme={theme} brandMode={brandMode} />;
      case 'carros_abandonados': return <AbandonedCartsView theme={theme} brandMode={brandMode} />;
      // indicadores_d2c y campanas_mkt NO reciben brandMode a propósito --
      // resuelven su propio modo de marca a partir de su selector interno
      // (ver D2CPerformanceView.tsx / MarketingCampaignsView.tsx), ignorando
      // el selector global. Ver theme/brandTokens.ts para la regla completa.
      case 'indicadores_d2c': return <D2CPerformanceView theme={theme} />;
      case 'campanas_mkt': return <MarketingCampaignsView theme={theme} />;
      case 'distribuidores': return <DistributorsView theme={theme} brandMode={brandMode} />;
      case 'inmobiliaria': return <RealEstateView theme={theme} brandMode={brandMode} />;
      case 'ventas_temperatura': return <TemperatureSalesView theme={theme} brandMode={brandMode} />;
      case 'cumplimiento_ventas': return <SalesTargetCumplimientoView theme={theme} />;
      default: return <MainExecutiveView theme={theme} />;
    }
  };

  const isDark = theme === 'dark';

  // Mientras se valida un token guardado contra el backend (GET /api/auth/me)
  if (isLoadingSession) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${
        isDark ? 'bg-[#000000] text-[#F5F5F7]' : 'bg-[#F2F2F7] text-[#1D1D1F]'
      }`}>
        <span className="text-sm font-semibold opacity-60">Verificando sesión...</span>
      </div>
    );
  }

  // Si no hay sesión válida, presenta la pantalla de Login
  if (!currentUser) {
    return (
      <LoginView
        theme={theme}
        onThemeToggle={handleThemeToggle}
      />
    );
  }

  return (
    <div className={`min-h-screen flex flex-col font-sans transition-colors ${
      isDark ? 'bg-[#000000] text-[#F5F5F7]' : 'bg-[#F2F2F7] text-[#1D1D1F]'
    }`}>
      {/* Main Body */}
      <div className="flex flex-1 overflow-hidden w-full mx-auto h-screen">
        {/* Sidebar */}
        <Sidebar
          activeModule={activeModule}
          onSelectModule={setActiveModule}
          theme={theme}
          onThemeToggle={handleThemeToggle}
          brandMode={brandMode}
          onBrandModeChange={handleBrandModeChange}
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          onOpenKpiReview={() => setIsKpiModalOpen(true)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
          userEmail={currentUser.email}
          userName={currentUser.nombre}
          onLogout={logout}
        />

        {/* Main Content Area with Header + Module View */}
        <div className="flex-1 flex flex-col h-screen overflow-hidden">
          <Header
            theme={theme}
            activeModule={activeModule}
          />

          <main className="flex-1 p-4 sm:p-6 overflow-y-auto">
            {renderActiveModule()}
          </main>
        </div>
      </div>

      {/* KPI Review Modal */}
      <KpiReviewModal
        isOpen={isKpiModalOpen}
        onClose={() => setIsKpiModalOpen(false)}
        theme={theme}
      />

      {/* User Management & RBAC Modal */}
      <UserManagementModal
        isOpen={isUserModalOpen}
        onClose={() => setIsUserModalOpen(false)}
        isDark={isDark}
      />
    </div>
  );
}