import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ResponsiveLayout as Layout } from './components/ResponsiveLayout';
import { HonestCockpit as Cockpit } from './pages/HonestCockpit';
import { Today as Dashboard } from './pages/Today';
import { Settings } from './pages/Settings';
import { TriageModern as Triage } from './pages/TriageModern';
import { TasksModern as Tasks } from './pages/TasksModern';
import { CalendarHonest as Calendar } from './pages/CalendarHonest';
import { ProjectsView, WaitingOnOthers } from './pages/OperationalViews';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="cockpit" element={<Cockpit />} />
          <Route path="triage" element={<Triage />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="calendar" element={<Calendar />} />
          <Route path="settings" element={<Settings />} />
          <Route path="waiting" element={<WaitingOnOthers />} />
          <Route path="projects" element={<ProjectsView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
