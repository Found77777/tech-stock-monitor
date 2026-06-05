import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function SectionCard({ title, description, actions, children, className }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <Card className={cn("border-white/10 bg-slate-950/70 shadow-xl shadow-black/20", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-4 border-b border-white/5 pb-4">
        <div><CardTitle>{title}</CardTitle>{description && <CardDescription className="mt-1">{description}</CardDescription>}</div>
        {actions && <div className="shrink-0">{actions}</div>}
      </CardHeader>
      <CardContent className="pt-5">{children}</CardContent>
    </Card>
  );
}
