import React, { Fragment } from "react";
import type { ChiSquareResult } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface DetailedChiSquareTableProps {
  results: ChiSquareResult[];
}

export function DetailedChiSquareTable({
  results,
}: DetailedChiSquareTableProps) {
  if (!results || results.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        No statistical results available.
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-[300px] font-bold text-foreground">
              Variable / Category
            </TableHead>
            <TableHead className="font-bold text-foreground">
              Outcome Measure
            </TableHead>
            <TableHead className="font-bold text-foreground">
              Result 1 n(%)
            </TableHead>
            <TableHead className="font-bold text-foreground">
              Result 2 n(%)
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              Chi-Square (χ²)
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              df
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              p-value
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((result, idx) => {
            const { demographic, outcome, chi2, df, p_value, crosstab } =
              result;

            const hasError = crosstab && "error" in crosstab;

            // If no crosstab, just render a single error/note row
            if (!crosstab || hasError) {
              const errorMessage = hasError
                ? String((crosstab as { error?: unknown }).error)
                : result.note || "Insufficient data";

              return (
                <TableRow key={`err-${idx}`} className="border-b">
                  <TableCell className="font-bold">{demographic}</TableCell>
                  <TableCell>{outcome}</TableCell>
                  <TableCell
                    colSpan={2}
                    className="text-muted-foreground text-sm"
                  >
                    {errorMessage}
                  </TableCell>
                  <TableCell className="text-right">-</TableCell>
                  <TableCell className="text-right">-</TableCell>
                  <TableCell className="text-right">-</TableCell>
                </TableRow>
              );
            }

            // Extract the child categories, ignoring 'Total'
            const outcomeLabels = Object.keys(crosstab).filter(
              (k) => k !== "Total",
            );

            // Assume the first outcome column's keys are the demographic tiers
            const demographicLabels = Object.keys(
              crosstab[outcomeLabels[0]] || {},
            ).filter((k) => k !== "Total");

            const isSignificant =
              result.significant || (p_value !== null && p_value < 0.05);

            return (
              <Fragment key={`parent-${idx}`}>
                {/* PARENT ROW */}
                <TableRow className="bg-muted/10">
                  <TableCell className="font-bold text-base border-r border-muted/30">
                    {demographic}
                  </TableCell>
                  <TableCell className="font-semibold text-primary/80 border-r border-muted/30">
                    {outcome}
                  </TableCell>

                  {/* Provide label hints in the parent row so we know what Result 1 and 2 mean */}
                  <TableCell className="text-xs text-muted-foreground align-bottom pb-1">
                    {outcomeLabels[0]}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground align-bottom pb-1 border-r border-muted/30">
                    {outcomeLabels.length > 1 ? outcomeLabels[1] : ""}
                  </TableCell>

                  <TableCell className="text-right font-mono">
                    {chi2?.toFixed(3) ?? "-"}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {df ?? "-"}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono font-bold ${
                      isSignificant
                        ? "text-emerald-600 dark:text-emerald-400"
                        : ""
                    }`}
                  >
                    {p_value !== null ? p_value.toFixed(4) : "-"}
                    {isSignificant && "*"}
                  </TableCell>
                </TableRow>

                {/* CHILD ROWS (Sub-categories) */}
                {demographicLabels.map((catLabel) => {
                  const out1Val = crosstab[outcomeLabels[0]]?.[catLabel] || 0;
                  const totalVal = crosstab["Total"]?.[catLabel] || 0;
                  const out1Pct = totalVal > 0 ? (out1Val / totalVal) * 100 : 0;

                  let out2Str = "-";
                  if (outcomeLabels.length > 1) {
                    const out2Val = crosstab[outcomeLabels[1]]?.[catLabel] || 0;
                    const out2Pct =
                      totalVal > 0 ? (out2Val / totalVal) * 100 : 0;
                    out2Str = `${out2Val} (${out2Pct.toFixed(1)}%)`;
                  }

                  return (
                    <TableRow key={`child-${idx}-${catLabel}`}>
                      <TableCell className="pl-6 text-sm border-r border-muted/30">
                        {catLabel}
                      </TableCell>
                      <TableCell className="border-r border-muted/30"></TableCell>
                      <TableCell className="text-sm">
                        {out1Val} ({out1Pct.toFixed(1)}%)
                      </TableCell>
                      <TableCell className="text-sm border-r border-muted/30">
                        {out2Str}
                      </TableCell>
                      <TableCell className="text-right"></TableCell>
                      <TableCell className="text-right"></TableCell>
                      <TableCell className="text-right"></TableCell>
                    </TableRow>
                  );
                })}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
