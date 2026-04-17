import { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Link, NavLink as RouterNavLink } from 'react-router-dom';
import { Shield, LayoutDashboard, FileUp, ListChecks, MessageSquare, ClipboardCheck } from 'lucide-react';
import { RoleProvider, useRole, Role } from '@/hooks/use-role';
import HomePage from '@/pages/HomePage';
import DashboardPage from '@/pages/DashboardPage';
import IntakePage from '@/pages/IntakePage';
import ReviewPage from '@/pages/ReviewPage';
import DocumentDetailPage from '@/pages/DocumentDetailPage';
import ConsultationPage from '@/pages/ConsultationPage';
import ResponsePage from '@/pages/ResponsePage';

export default function App() {
  return (
    <BrowserRouter>
      <RoleProvider>
        <div className="bg-slate-50 text-slate-900 min-h-screen" style={{ fontFamily: 'system-ui, sans-serif' }}>
          <Header />
          <main className="max-w-7xl mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/intake" element={<IntakePage />} />
              <Route path="/review" element={<ReviewPage />} />
              <Route path="/documents/:id" element={<DocumentDetailPage />} />
              <Route path="/consultation" element={<ConsultationPage />} />
              <Route path="/response" element={<ResponsePage />} />
            </Routes>
          </main>
        </div>
      </RoleProvider>
    </BrowserRouter>
  );
}

function Header() {
  const { role, setRole } = useRole();

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 font-bold text-xl tracking-tight text-blue-800">
            <Shield className="w-6 h-6" />
            <span>SecureFlow</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-slate-600">
            <NavLink to="/dashboard" icon={<LayoutDashboard size={16} />} label="Dashboard" />
            <NavLink to="/intake" icon={<FileUp size={16} />} label="Intake" />
            <NavLink to="/review" icon={<ListChecks size={16} />} label="Review" />
            <NavLink to="/consultation" icon={<MessageSquare size={16} />} label="Consultation" />
            <NavLink to="/response" icon={<ClipboardCheck size={16} />} label="Response" />
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Active Role</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="bg-slate-100 border-none rounded-md px-2 py-1 text-xs font-semibold focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <option>Intake Clerk</option>
              <option>Department Reviewer</option>
              <option>Consultant</option>
              <option>Supervisor</option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}

function NavLink({ to, icon, label }: { to: string; icon: ReactNode; label: string }) {
  return (
    <RouterNavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
          isActive
            ? 'bg-blue-50 text-blue-700 shadow-sm ring-1 ring-blue-100'
            : 'hover:bg-slate-100 hover:text-blue-700'
        }`
      }
    >
      {icon}
      <span>{label}</span>
    </RouterNavLink>
  );
}
