"use client";

import React, { useRef } from "react";
import { toast } from "sonner";
import {
  DownloadCloud,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
} from "lucide-react";
import { LogisticRegressionTable } from "@/components/logistic-regression-table";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

import type { AnalysisResult } from "@/lib/types";
import { DetailedChiSquareTable } from "@/components/detailed-chi-square";
import { getDownloadUrl } from "@/lib/api";

const COLORS = ["#0d9488", "#14b8a6", "#5eead4", "#99f6e4", "#ccfbf1"];
const KNOWLEDGE_COLORS = ["#0d9488", "#ef4444"]; // Teal for Good, Red for Poor
const ATTITUDE_COLORS = ["#0d9488", "#eab308"]; // Teal for Positive, Yellow for Negative

interface DashboardProps {
  data: AnalysisResult;
  onUpload?: (file: File) => Promise<void>;
  isLoading?: boolean;
}

export function Dashboard({ data, onUpload, isLoading }: DashboardProps) {
  const { summary, session_id } = data;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDownload = (type: "results" | "cleaned") => {
    window.open(getDownloadUrl(type, session_id), "_blank");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
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
      onUpload?.(file);
    }
    e.target.value = "";
  };

  // Prepare chart data format
  const knowledgeMenoData = [
    {
      name: "Good",
      value: summary.constructs.knowledge_menopause.good_pct || 0,
      count: summary.constructs.knowledge_menopause.good_n || 0,
    },
    {
      name: "Poor",
      value: summary.constructs.knowledge_menopause.poor_pct || 0,
      count: summary.constructs.knowledge_menopause.poor_n || 0,
    },
  ];
  const knowledgeHrtData = [
    {
      name: "Good",
      value: summary.constructs.knowledge_hrt.good_pct || 0,
      count: summary.constructs.knowledge_hrt.good_n || 0,
    },
    {
      name: "Poor",
      value: summary.constructs.knowledge_hrt.poor_pct || 0,
      count: summary.constructs.knowledge_hrt.poor_n || 0,
    },
  ];

  const attMenoData = [
    {
      name: "Positive",
      value: summary.constructs.attitude_menopause.positive_pct || 0,
      count: summary.constructs.attitude_menopause.positive_n || 0,
    },
    {
      name: "Negative",
      value: summary.constructs.attitude_menopause.negative_pct || 0,
      count: summary.constructs.attitude_menopause.negative_n || 0,
    },
  ];
  const attHrtData = [
    {
      name: "Positive",
      value: summary.constructs.attitude_hrt.positive_pct || 0,
      count: summary.constructs.attitude_hrt.positive_n || 0,
    },
    {
      name: "Negative",
      value: summary.constructs.attitude_hrt.negative_pct || 0,
      count: summary.constructs.attitude_hrt.negative_n || 0,
    },
  ];

  const hrtData = [
    { name: "Currently Using", value: summary.hrt_practices.currently_using },
    { name: "Previously Used", value: summary.hrt_practices.previously_used },
    { name: "Never Used", value: summary.hrt_practices.never_used },
  ];

  // Prepare socio chart data wrapper
  const transformSocio = (obj: Record<string, number>) => {
    return Object.entries(obj).map(([name, value]) => ({ name, value }));
  };

  return (
    <div className="space-y-8 mt-6">
      {/* Header section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-primary">
            Analysis Dashboard
          </h2>
          <p className="text-muted-foreground mt-1">
            Processed {summary.total_submissions} responses ({summary.excluded}{" "}
            excluded due to lack of consent).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".xlsx, .csv"
            onChange={handleFileChange}
            disabled={isLoading}
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            variant="outline"
            disabled={isLoading}
            className="cursor-pointer border-dashed border-2"
          >
            {isLoading ? "Analyzing..." : "Upload New Dataset"}
          </Button>

          <Button
            onClick={() => handleDownload("results")}
            variant="default"
            className="cursor-pointer"
          >
            <DownloadCloud className="mr-2 h-4 w-4" />
            Results (Excel)
          </Button>
          <Button
            onClick={() => handleDownload("cleaned")}
            variant="secondary"
            className="cursor-pointer"
          >
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            Cleaned Data
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Analyzed Participants
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.total_respondents}
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              Consented out of {summary.total_submissions} total
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Good Knowledge (Menopause)
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.constructs.knowledge_menopause.good_pct}%
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              {summary.constructs.knowledge_menopause.good_n} subjects
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Good Knowledge (HRT)
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.constructs.knowledge_hrt.good_pct}%
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              {summary.constructs.knowledge_hrt.good_n} subjects
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Positive Attitude (Menopause)
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.constructs.attitude_menopause.positive_pct}%
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              {summary.constructs.attitude_menopause.positive_n} subjects
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Positive Attitude (HRT)
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.constructs.attitude_hrt.positive_pct}%
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              {summary.constructs.attitude_hrt.positive_n} subjects
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">HRT Usage</CardTitle>
            <AlertCircle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(
                (summary.hrt_practices.currently_using /
                  summary.total_respondents) *
                100
              ).toFixed(1)}
              %
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              Currently using ({summary.hrt_practices.currently_using} women)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="knowledge" className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5 lg:w-[850px] mb-8 h-auto! gap-1 p-1">
          <TabsTrigger
            value="sociodemographics"
            className="cursor-pointer whitespace-normal h-auto! py-2 lg:py-1"
          >
            Sociodemographics
          </TabsTrigger>
          <TabsTrigger
            value="knowledge"
            className="cursor-pointer whitespace-normal h-auto! py-2 lg:py-1"
          >
            Knowledge
          </TabsTrigger>
          <TabsTrigger
            value="attitudes"
            className="cursor-pointer whitespace-normal h-auto! py-2 lg:py-1"
          >
            Attitudes
          </TabsTrigger>
          <TabsTrigger
            value="hrt"
            className="cursor-pointer whitespace-normal h-auto! py-2 lg:py-1"
          >
            HRT Practices
          </TabsTrigger>
          <TabsTrigger
            value="chisquare"
            className="cursor-pointer whitespace-normal h-auto! py-2 lg:py-1"
          >
            Statistical Tests
          </TabsTrigger>
          <TabsTrigger
            value="logistic"
            className="cursor-pointer whitespace-normal h-auto! py-2 lg:py-1"
          >
            Logistic Regression
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: Knowledge */}
        <TabsContent value="knowledge" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="col-span-1 border-muted">
              <CardHeader>
                <CardTitle>Knowledge of Menopause</CardTitle>
                <CardDescription>
                  Percentage of Good vs Poor knowledge
                </CardDescription>
              </CardHeader>
              <CardContent className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={knowledgeMenoData}
                    layout="vertical"
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis
                      type="number"
                      dataKey="value"
                      unit="%"
                      domain={[0, 100]}
                    />
                    <YAxis type="category" dataKey="name" />
                    <Tooltip
                      formatter={(value, name, props) => [
                        `${value}% (${props.payload.count} subjects)`,
                        "Result",
                      ]}
                    />
                    <Bar dataKey="value" name="Percentage">
                      {knowledgeMenoData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            KNOWLEDGE_COLORS[index % KNOWLEDGE_COLORS.length]
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="col-span-1 border-muted">
              <CardHeader>
                <CardTitle>Knowledge of HRT</CardTitle>
                <CardDescription>
                  Percentage of Good vs Poor knowledge
                </CardDescription>
              </CardHeader>
              <CardContent className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={knowledgeHrtData}
                    layout="vertical"
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis
                      type="number"
                      dataKey="value"
                      unit="%"
                      domain={[0, 100]}
                    />
                    <YAxis type="category" dataKey="name" />
                    <Tooltip
                      formatter={(value, name, props) => [
                        `${value}% (${props.payload.count} subjects)`,
                        "Result",
                      ]}
                    />
                    <Bar dataKey="value" name="Percentage">
                      {knowledgeHrtData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            KNOWLEDGE_COLORS[index % KNOWLEDGE_COLORS.length]
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* TAB: Attitudes */}
        <TabsContent value="attitudes" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="col-span-1 border-muted">
              <CardHeader>
                <CardTitle>Attitude towards Menopause</CardTitle>
                <CardDescription>
                  Percentage of Positive vs Negative attitude
                </CardDescription>
              </CardHeader>
              <CardContent className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={attMenoData}
                    layout="vertical"
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis
                      type="number"
                      dataKey="value"
                      unit="%"
                      domain={[0, 100]}
                    />
                    <YAxis type="category" dataKey="name" />
                    <Tooltip
                      formatter={(value, name, props) => [
                        `${value}% (${props.payload.count} subjects)`,
                        "Result",
                      ]}
                    />
                    <Bar dataKey="value" name="Percentage">
                      {attMenoData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={ATTITUDE_COLORS[index % ATTITUDE_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="col-span-1 border-muted">
              <CardHeader>
                <CardTitle>Attitude towards HRT</CardTitle>
                <CardDescription>
                  Percentage of Positive vs Negative attitude
                </CardDescription>
              </CardHeader>
              <CardContent className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={attHrtData}
                    layout="vertical"
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis
                      type="number"
                      dataKey="value"
                      unit="%"
                      domain={[0, 100]}
                    />
                    <YAxis type="category" dataKey="name" />
                    <Tooltip
                      formatter={(value, name, props) => [
                        `${value}% (${props.payload.count} subjects)`,
                        "Result",
                      ]}
                    />
                    <Bar dataKey="value" name="Percentage">
                      {attHrtData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={ATTITUDE_COLORS[index % ATTITUDE_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 2: Sociodemographics */}
        <TabsContent value="sociodemographics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {["Age Group", "Education Level", "Marital Status"].map(
              (demoName) => (
                <Card key={demoName} className="border-muted">
                  <CardHeader>
                    <CardTitle className="text-lg">{demoName}</CardTitle>
                  </CardHeader>
                  <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={transformSocio(
                            summary.sociodemographics[demoName] || {},
                          )}
                          cx="50%"
                          cy="45%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {transformSocio(
                            summary.sociodemographics[demoName] || {},
                          ).map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={COLORS[index % COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value, name) => [
                            `${value} participants`,
                            name,
                          ]}
                        />
                        <Legend verticalAlign="bottom" height={36} />
                      </PieChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              ),
            )}
          </div>
        </TabsContent>

        {/* TAB 3: HRT Practices */}
        <TabsContent value="hrt" className="space-y-4">
          <Card className="border-muted">
            <CardHeader>
              <CardTitle>Hormone Replacement Therapy (HRT) Practice</CardTitle>
              <CardDescription>
                Breakdown of respondents by HRT history
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={hrtData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(1)}%`
                    }
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {hrtData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [`${value} participants`, "Count"]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: Chi-Square Tests */}
        <TabsContent value="chisquare" className="space-y-4">
          <Card className="border-muted">
            <CardHeader>
              <CardTitle>
                Detailed Statistical Associations (Chi-Square)
              </CardTitle>
              <CardDescription>
                Inferential analysis of demographic factors associated with
                Menopause and HRT outcomes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DetailedChiSquareTable results={summary.chi_square} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 5: Logistic Regression */}
        <TabsContent value="logistic" className="space-y-4">
          <Card className="border-muted">
            <CardHeader>
              <CardTitle>Binary Logistic Regression</CardTitle>
              <CardDescription>
                Identifies specific sociodemographic sub-categories that are
                statistically significant predictors of knowledge and attitude
                outcomes. Odds Ratios (OR) &gt; 1 indicate higher likelihood; OR
                &lt; 1 indicate lower likelihood relative to the reference
                category.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LogisticRegressionTable
                results={summary.logistic_regression ?? []}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
