import type { ReactNode } from 'react';

interface MainLayoutProps {
  header?: ReactNode;
  sidebar?: ReactNode;
  children: ReactNode;
}

export function MainLayout({ header, sidebar, children }: MainLayoutProps) {
  return (
    <div className="relative h-screen flex flex-col bg-void mesh-gradient noise-overlay">
      {/* Global Header - needs overflow-visible for dropdown menu */}
      <div className="relative z-50">
        {header}
      </div>

      {/* Main container with sidebar and content - z-0 to stay below header dropdown */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative z-0">
        {/* Sidebar */}
        {sidebar}

        {/* Main content area */}
        <main className="flex-1 flex flex-col min-w-0 relative z-0">
          {/* Decorative gradient orbs */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute -top-1/4 -right-1/4 w-1/2 h-1/2 bg-nebula/5 rounded-full blur-3xl" />
            <div className="absolute -bottom-1/4 -left-1/4 w-1/2 h-1/2 bg-glow/5 rounded-full blur-3xl" />
          </div>

          {/* Content */}
          <div className="relative flex-1 flex flex-col min-h-0 overflow-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export default MainLayout;
