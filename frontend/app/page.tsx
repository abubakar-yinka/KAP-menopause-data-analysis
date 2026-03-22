"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { UploadZone } from "@/components/upload-zone";
import { Dashboard } from "@/components/dashboard";
import { analyzeFile } from "@/lib/api";
import { Activity } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Home() {
  const mutation = useMutation({
    mutationFn: analyzeFile,
    onError: (error: Error) => {
      toast.error(error.message || "Failed to analyze dataset.");
    },
    onSuccess: () => {
      toast.success("Dataset successfully analyzed!");
    },
  });

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
        <div className="container mx-auto flex h-14 items-center justify-between md:px-0 px-4">
          <div className="flex items-center gap-2 font-semibold text-primary flex-1">
            <Activity className="h-5 w-5" />
            <span>Menopause & HRT Study</span>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="container mx-auto flex-1 p-4 md:p-8">
        <div className="mx-auto max-w-[1200px]">
          {!mutation.data ? (
            <div className="mx-auto max-w-2xl text-center mt-12">
              <h1 className="text-3xl font-bold tracking-tight mb-2">
                Knowledge & Attitudes Analysis
              </h1>
              <p className="text-muted-foreground mb-8">
                Upload your raw KoboToolbox dataset to instantly generate
                processed statistics, categorizations, and publication-ready
                tables.
              </p>
              <UploadZone
                onUpload={async (file) => {
                  mutation.mutate(file);
                }}
                isLoading={mutation.isPending}
              />
            </div>
          ) : (
            <Dashboard
              data={mutation.data}
              onUpload={async (file) => {
                mutation.mutate(file);
              }}
              isLoading={mutation.isPending}
            />
          )}
        </div>
      </main>

      <footer className="py-6 md:px-8 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row shadow-sm">
          <p className="text-balance text-center text-sm leading-loose text-muted-foreground md:text-left">
            Built for clinical research data analysis.
          </p>
        </div>
      </footer>
    </div>
  );
}
