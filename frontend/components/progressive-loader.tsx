"use client";

import { useEffect, useState } from "react";
import { LoaderDisplay } from "@/components/ui/loader";

interface ProgressiveLoaderProps {
  isLoading: boolean;
}

export function ProgressiveLoader({ isLoading }: ProgressiveLoaderProps) {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      return;
    }

    const t1 = setTimeout(() => setPhase(1), 15000); // 15s mark
    const t2 = setTimeout(() => setPhase(2), 30000); // 30s mark
    const t3 = setTimeout(() => setPhase(3), 90000); // 90s mark (Failsafe)

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [isLoading]);

  if (!isLoading) return null;

  const getStatusText = () => {
    switch (phase) {
      case 0:
        return "Processing clinical questionnaire responses...";
      case 1:
        return "Running Chi-Square statistical associations...";
      case 2:
        return "Finalizing demographic charts and Excel reports... (This first run takes about a minute).";
      case 3:
      default:
        return "Still working on it, hang tight...";
    }
  };

  return (
    <div className="absolute inset-0 z-50 flex flex-col items-center justify-center rounded-xl bg-background/80 backdrop-blur-md backdrop-filter transition-all duration-500 animate-in fade-in-0 zoom-in-95">
      <div className="flex flex-col items-center justify-center space-y-8 text-center p-6">
        <div className="scale-125">
          <LoaderDisplay variant="loader-dna" size="md" />
        </div>

        <div className="max-w-[280px] space-y-3">
          <h3 className="text-xl font-semibold text-foreground tracking-tight">
            Analyzing Data
          </h3>
          <p
            key={phase} // React-key creates a fresh DOM node, triggering the animate-in effect automatically on phase change
            className="text-sm font-medium text-muted-foreground animate-in fade-in-0 slide-in-from-bottom-2 duration-700 ease-out"
          >
            {getStatusText()}
          </p>
        </div>
      </div>
    </div>
  );
}
