import { Link, Outlet, useLocation } from 'react-router-dom';
import { Activity, CheckSquare, Settings, Calendar, Inbox } from 'lucide-react';
import clsx from 'clsx';

export const Layout = () => {
  const location = useLocation();

  const navItems = [
    { name: 'Cockpit', path: '/cockpit', icon: Activity },
    { name: 'Triagem', path: '/triage', icon: Inbox },
    { name: 'Hoje', path: '/', icon: Activity },
    { name: 'Tarefas', path: '/tasks', icon: CheckSquare },
    { name: 'Calendário', path: '/calendar', icon: Calendar },
    { name: 'Ajustes', path: '/settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-base text-text flex">
      {/* Sidebar fina e geométrica */}
      <nav className="w-64 border-r border-surface2 bg-surface/50 flex flex-col justify-between">
        <div>
          <div className="p-8 border-b border-surface2">
            <h1 className="text-xl font-bold tracking-tight text-white uppercase">
              Task<span className="text-accent">Flow</span>
            </h1>
          </div>
          <ul className="flex flex-col mt-6 space-y-1 px-4">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-3 transition-all duration-200 group relative overflow-hidden',
                      isActive ? 'text-accent font-semibold' : 'text-muted hover:text-white hover:bg-surface2'
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-0 bottom-0 w-1 bg-accent shadow-[0_0_8px_rgba(69,162,158,0.5)]" />
                    )}
                    <item.icon className="w-5 h-5 z-10" />
                    <span className="z-10">{item.name}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
        <div className="p-6 border-t border-surface2 text-xs text-surface2">
          v1.0.0
        </div>
      </nav>

      {/* Conteúdo Principal com espaço negativo */}
      <main className="flex-1 overflow-auto bg-base p-12">
        <Outlet />
      </main>
    </div>
  );
};
