import * as React from 'react';

function cn(...args: (string | undefined | false)[]) {
  return args.filter(Boolean).join(' ');
}

export function Card({
  children,
  className,
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={cn('bg-white rounded-2xl border border-slate-200 overflow-hidden', className)}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className,
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...rest} className={cn('p-6 pb-4', className)}>
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className,
  ...rest
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 {...rest} className={cn('text-xl font-bold leading-none tracking-tight', className)}>
      {children}
    </h3>
  );
}

export function CardDescription({
  children,
  className,
  ...rest
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p {...rest} className={cn('text-sm text-slate-500', className)}>
      {children}
    </p>
  );
}

export function CardContent({
  children,
  className,
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...rest} className={cn('p-6 pt-0', className)}>
      {children}
    </div>
  );
}
