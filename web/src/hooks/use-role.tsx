import { useState, createContext, useContext, ReactNode } from 'react';

export type Role = 'Intake Clerk' | 'Department Reviewer' | 'Consultant' | 'Supervisor';

interface RoleContextType {
  role: Role;
  setRole: (role: Role) => void;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export const RoleProvider = ({ children }: { children: ReactNode }) => {
  const [role, setRole] = useState<Role>(() => {
    const saved = localStorage.getItem('activeRole') as Role;
    return saved || 'Intake Clerk';
  });

  const handleSetRole = (newRole: Role) => {
    setRole(newRole);
    localStorage.setItem('activeRole', newRole);
  };

  return (
    <RoleContext.Provider value={{ role, setRole: handleSetRole }}>
      {children}
    </RoleContext.Provider>
  );
};

export const useRole = () => {
  const context = useContext(RoleContext);
  if (!context) throw new Error('useRole must be used within RoleProvider');
  return context;
};
