/** Type definitions for the KAP Study analysis API responses. */

export interface AnalysisResult {
  session_id: string;
  summary: AnalysisSummary;
}

export interface AnalysisSummary {
  total_respondents: number;
  total_submissions: number;
  excluded: number;

  sociodemographics: Record<string, Record<string, number>>;

  constructs: {
    knowledge_menopause: ConstructScoreData;
    knowledge_hrt: ConstructScoreData;
    attitude_menopause: ConstructScoreData;
    attitude_hrt: ConstructScoreData;
  };

  hrt_practices: {
    currently_using: number;
    previously_used: number;
    never_used: number;
  };

  chi_square: ChiSquareResult[];
  logistic_regression?: LogisticRegressionResult[];
}

export interface ConstructScoreData {
  good_n?: number;
  good_pct?: number;
  poor_n?: number;
  poor_pct?: number;
  positive_n?: number;
  positive_pct?: number;
  negative_n?: number;
  negative_pct?: number;
}

export interface ChiSquareResult {
  demographic: string;
  outcome: string;
  chi2: number | null;
  df: number | null;
  p_value: number | null;
  fisher_p_value?: number | null;
  significant: boolean;
  note: string;
  crosstab?: Record<string, Record<string, number>>;
}

export interface LogisticPredictor {
  variable: string;
  category: string;
  coef: number;
  odds_ratio: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
  significant: boolean;
}

export interface LogisticRegressionResult {
  outcome: string;
  predictors: LogisticPredictor[];
  n?: number;
  pseudo_r2?: number;
  note?: string;
}
