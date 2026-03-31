import React, { Fragment } from "react";
import type { LogisticRegressionResult } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface LogisticRegressionTableProps {
  results: LogisticRegressionResult[];
}

export function LogisticRegressionTable({
  results,
}: LogisticRegressionTableProps) {
  if (!results || results.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        No logistic regression results available.
      </div>
    );
  }

  /** Null-safe number formatter — returns "—" for null/undefined values */
  const fmt = (v: number | null | undefined, decimals: number) =>
    v != null ? v.toFixed(decimals) : "—";

  return (
    <div className="rounded-md border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-[200px] font-bold text-foreground">
              Demographic Factor
            </TableHead>
            <TableHead className="font-bold text-foreground">
              Category (vs Reference)
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              β
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              OR
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              95% CI
            </TableHead>
            <TableHead className="text-right font-bold text-foreground">
              p-value
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((model, mIdx) => {
            const hasError = model.predictors.length === 0 && model.note;

            return (
              <Fragment key={`model-${mIdx}`}>
                {/* MODEL HEADER ROW */}
                <TableRow className="bg-primary/5 border-t-2 border-primary/20">
                  <TableCell
                    colSpan={6}
                    className="font-bold text-base text-primary py-3"
                  >
                    {model.outcome}
                    {model.n != null && (
                      <span className="ml-3 text-xs font-normal text-muted-foreground">
                        n={model.n}
                      </span>
                    )}
                    {model.pseudo_r2 != null && (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        Pseudo R²={fmt(model.pseudo_r2, 4)}
                      </span>
                    )}
                  </TableCell>
                </TableRow>

                {hasError ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="text-muted-foreground text-sm pl-6"
                    >
                      {model.note}
                    </TableCell>
                  </TableRow>
                ) : (
                  model.predictors.map((pred, pIdx) => {
                    const isSignificant = pred.significant;
                    return (
                      <TableRow
                        key={`pred-${mIdx}-${pIdx}`}
                        className={isSignificant ? "bg-emerald-500/5" : ""}
                      >
                        <TableCell className="pl-6 text-sm font-medium border-r border-muted/30">
                          {pred.variable}
                        </TableCell>
                        <TableCell className="text-sm border-r border-muted/30">
                          {pred.category}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {fmt(pred.coef, 4)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm font-semibold">
                          {fmt(pred.odds_ratio, 3)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm text-muted-foreground">
                          {fmt(pred.ci_lower, 3)}–{fmt(pred.ci_upper, 3)}
                        </TableCell>
                        <TableCell
                          className={`text-right font-mono text-sm font-bold ${
                            isSignificant
                              ? "text-emerald-600 dark:text-emerald-400"
                              : ""
                          }`}
                        >
                          {fmt(pred.p_value, 4)}
                          {isSignificant && "*"}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
