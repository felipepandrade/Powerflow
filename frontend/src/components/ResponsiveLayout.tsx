import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Activity, Calendar, CheckSquare, FolderKanban, Inbox, Menu, Settings, Users, X } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { name: 'Hoje', path: '/', icon: Activity },
  { name: 'Triagem', path: '/triage', icon: Inbox },
  { name: 'Tarefas', path: '/tasks', icon: CheckSquare },
  { name: 'Aguardando', path: '/waiting', icon: Users },
  { name: 'Projetos', path: '/projects', icon: FolderKanban },
  { name: 'Calendario', path: '/calendar', icon: Calendar },
  { name: 'Cockpit', path: '/cockpit', icon: Activity },
  { name: 'Ajustes', path: '/settings', icon: Settings },
];

export const ResponsiveLayout = () => {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileNavRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const menuTrigger = menuButtonRef.current;
    const firstLink = mobileNavRef.current?.querySelector<HTMLAnchorElement>('a[href]');
    firstLink?.focus();
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
      menuTrigger?.focus();
    };
  }, [menuOpen]);

  const navigation = (
    <nav aria-label="Navegacao principal" className="flex h-full flex-col">
      <div className="border-b border-surface2 p-6">
        <Link
          to="/"
          onClick={() => setMenuOpen(false)}
          className="inline-block text-xl font-bold uppercase tracking-tight text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
        >
          Power<span className="text-accent">flow</span>
        </Link>
      </div>
      <ul className="flex flex-1 flex-col gap-1 p-4">
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          return (
            <li key={item.path}>
              <Link
                to={item.path}
                onClick={() => setMenuOpen(false)}
                aria-current={active ? 'page' : undefined}
                className={clsx(
                  'flex min-h-11 items-center gap-3 rounded px-4 py-3 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent',
                  active ? 'bg-accent/10 font-semibold text-white' : 'text-muted hover:bg-surface2 hover:text-white',
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                {item.name}
                {active ? <span className="ml-auto h-2 w-2 rounded-full bg-accent" aria-hidden="true" /> : null}
              </Link>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-surface2 p-5 text-xs leading-relaxed text-muted">
        Diagnostico do fluxo do gestor. Nao avalia desempenho individual.
      </p>
    </nav>
  );

  return (
    <div className="min-h-screen bg-base text-text lg:flex">
      <a
        href="#main-content"
        className="fixed left-3 top-3 z-[70] -translate-y-20 rounded bg-accent px-4 py-2 font-semibold text-white transition-transform focus:translate-y-0"
      >
        Ir para o conteudo principal
      </a>

      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-surface2 bg-base/95 px-4 backdrop-blur lg:hidden">
        <Link to="/" className="font-bold uppercase text-white">Power<span className="text-accent">flow</span></Link>
        <button
          ref={menuButtonRef}
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          className="rounded p-2 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          aria-expanded={menuOpen}
          aria-controls="mobile-navigation"
          aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
        >
          {menuOpen ? <X className="h-6 w-6" aria-hidden="true" /> : <Menu className="h-6 w-6" aria-hidden="true" />}
        </button>
      </header>

      {menuOpen ? (
        <button
          type="button"
          className="fixed inset-0 top-16 z-40 bg-black/70 lg:hidden"
          onClick={() => setMenuOpen(false)}
          aria-label="Fechar menu"
        />
      ) : null}
      <aside
        ref={mobileNavRef}
        inert={!menuOpen}
        id="mobile-navigation"
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-72 border-r border-surface2 bg-base transition-transform lg:hidden',
          menuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-hidden={!menuOpen}
      >
        {navigation}
      </aside>

      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-surface2 bg-surface/50 lg:block">
        {navigation}
      </aside>

      <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 p-4 sm:p-6 lg:p-10 xl:p-12">
        <Outlet />
      </main>
    </div>
  );
};
