import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function Badge({ children, className, variant = "default" }: { children: React.ReactNode; className?: string; variant?: "default" | "outline" | "secondary" }) {
  const variants = {
    default: "bg-blue-600 text-white",
    outline: "border border-slate-200 text-slate-900",
    secondary: "bg-slate-100 text-slate-900"
  };
  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold", variants[variant], className)}>
      {children}
    </span>
  );
}
