'use client';

import { ReactNode } from 'react';
import { Inter } from 'next/font/google';
import './globals.css';
import Link from 'next/link';
import { Shield, LayoutDashboard, FileUp, ListChecks, MessageSquare, ClipboardCheck } from 'lucide-react';
import { RoleProvider, useRole, Role } from '@/hooks/use-role';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-slate-50 text-slate-900 min-h-screen">
        <RoleProvider>
          <Header />
          <main className="max-w-7xl mx-auto px-4 py-8">
            {children}
          </main>
        </RoleProvider>
      </body>
    </html>
  );
}

function Header() {
  const { role, setRole } = useRole();
  
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tight text-blue-800">
            <Shield className="w-6 h-6" />
            <span>SecureFlow</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-slate-600">
            <NavLink href="/dashboard" icon={<LayoutDashboard size={16} />} label="Dashboard" />
            <NavLink href="/intake" icon={<FileUp size={16} />} label="Intake" />
            <NavLink href="/review" icon={<ListChecks size={16} />} label="Review" />
            <NavLink href="/consultation" icon={<MessageSquare size={16} />} label="Consultation" />
            <NavLink href="/response" icon={<ClipboardCheck size={16} />} label="Response" />
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

function NavLink({ href, icon, label }: { href: string; icon: ReactNode, label: string }) {
  return (
    <Link 
      href={href} 
      className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 hover:text-blue-700 transition-colors"
    >
      {icon}
      <span>{label}</span>
    </Link>
  );
}
