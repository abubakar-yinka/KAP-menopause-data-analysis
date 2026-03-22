"use client";

import { useState, useCallback, useRef } from "react";
import { UploadCloud, FileSpreadsheet, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>;
  isLoading: boolean;
}

export function UploadZone({ onUpload, isLoading }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const processFile = useCallback(
    (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext !== "xlsx" && ext !== "csv") {
        toast.error(
          "Invalid file type. Please upload a .xlsx or .csv dataset.",
        );
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error("File is too large. Maximum size is 10 MB.");
        return;
      }
      onUpload(file);
    },
    [onUpload],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        processFile(e.dataTransfer.files[0]);
      }
    },
    [processFile],
  );

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
    e.target.value = "";
  };

  const handleCardClick = () => {
    if (!isLoading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <Card
      onClick={handleCardClick}
      className={`cursor-pointer overflow-hidden relative mt-8 rounded-xl border-2 border-dashed transition-all duration-200 ease-in-out ${
        isDragging
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center justify-center space-y-4 px-6 py-20 text-center">
        <div className="rounded-full bg-primary/10 p-4">
          {isLoading ? (
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          ) : (
            <UploadCloud className="h-8 w-8 text-primary" />
          )}
        </div>

        <div className="space-y-1">
          <h3 className="text-xl font-semibold tracking-tight">
            {isLoading
              ? "Analyzing Dataset..."
              : "Upload RAW KoboToolbox Dataset"}
          </h3>
          <p className="text-sm text-muted-foreground pointer-events-none">
            {isLoading
              ? "Running data cleaning, composite scoring, and chi-square tests."
              : "Drag and drop your .xlsx or .csv file here, or click anywhere to browse."}
          </p>
        </div>

        <div className="pt-4">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".xlsx, .csv"
            onChange={handleFileChange}
            disabled={isLoading}
          />
          <Button
            disabled={isLoading}
            variant="secondary"
            className="cursor-pointer"
          >
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            Select File
          </Button>
        </div>
      </div>
    </Card>
  );
}
