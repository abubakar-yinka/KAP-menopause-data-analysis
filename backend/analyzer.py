"""
analyzer.py — In-memory analysis pipeline for the KAP Study web app.

This is a refactored version of the standalone analysis.py script.
Instead of reading/writing files on disk, it:
  - Accepts a pd.DataFrame as input
  - Returns a JSON-serializable summary dict + two BytesIO Excel buffers
"""

import io
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# =============================================================================
# COLUMN DEFINITIONS & ANSWER KEYS
# (Identical to the standalone script — these are the data contracts)
# =============================================================================

SOCIO_COLS = {
    "age": "_1_Age_in_years",
    "education": "_2_Education_level",
    "occupation": "_3_What_is_your_profession",
    "marital": "_4_Marital_status",
    "income": "_5_Average_monthly_income",
    "insurance": "_6_Enrolled_in_health_insurance",
    "children": "_7_Number_of_children",
    "sex": "_8_Have_you_had_any_in_the_last_3_months",
}

SOCIO_LABELS = {
    "_1_Age_in_years": {
        5: "40 - 44",
        4: "45 - 49",
        3: "50 - 54",
        2: "55 - 59",
        1: "≥ 60",
    },
    "_2_Education_level": {0: "None", 1: "Primary", 2: "Secondary", 3: "Tertiary"},
    "_3_What_is_your_profession": {
        0: "Health Professional",
        1: "Non-Health Professional",
    },
    "_4_Marital_status": {0: "Single", 1: "Married", 2: "Divorced", 3: "Widowed"},
    "_5_Average_monthly_income": {
        1: "< ₦10,000",
        2: "₦10,000 – ₦30,000",
        3: "₦30,000 – ₦50,000",
        4: "> ₦50,000",
    },
    "_6_Enrolled_in_health_insurance": {1: "Yes", 0: "No"},
    "_7_Number_of_children": {0: "None", 1: "1-2", 2: "3-4", 3: "≥ 5"},
    "_8_Have_you_had_any_in_the_last_3_months": {1: "Yes", 0: "No"},
}

SOCIO_DISPLAY_NAMES = {
    "age": "Age Group",
    "education": "Education Level",
    "occupation": "Occupation",
    "marital": "Marital Status",
    "income": "Average Monthly Income",
    "insurance": "Health Insurance",
    "children": "Number of Children",
    "sex": "Sexual Activity in Last 3 Months",
}

KNOWLEDGE_COLS = [
    "_25_Menopause_is_a_natural_bio",
    "_27_Regular_exercise_menopausal_symptoms",
    "_28_Balance_diet_ric_lth_during_menopause",
    "_29_Some_plant_based_menopausal_symptoms",
    "_30_At_the_time_of_m_ation_stops_suddenly",
    "_31_Women_become_men_e_age_of_45_55_years",
    "_32_Family_History_a_an_reaches_menopause",
    "_33_Menopause_occurs_reasing_sex_hormones",
    "_34_Slim_people_become_menopausal_sooner",
    "_35_Most_women_exper_menopause_occurrence",
    "_36_Most_of_the_wome_the_menopause_period",
    "_37_Menopause_in_wo_s_genital_infections",
    "_38_Menopause_in_wom_s_weight_and_obesity",
    "_39_Menopause_sympt_ventable_and_curable",
    "_40_Menopause_decrea_ar_diseases_in_women",
    "_41_Menopause_make_w_weak_and_soft_bones",
    "_42_Menopause_causes_to_wrinkle_in_women",
    "_43_Menopause_causes_s_of_cancer_in_women",
    "_44_Sexual_urge_dec_in_menopausal_women",
    "_45_Smoking_delays_e_onset_of_menopause",
    "_46_Smoking_does_not_cations_of_menopause",
    "_47_Menopause_incre_hair_on_women_s_face",
    "_48_Menopause_causes_l_sexual_intercourse",
    "_49_Menopause_cause_g_when_passing_urine",
    "_50_Smoking_and_usin_teomalacia_in_women",
    "_51_Regular_physical_in_menopausal_women",
    "_52_Menopause_affect_and_memory_of_women",
    "_53_The_frequency_an_en_increases_by_time",
    "_54_The_level_of_str_in_menopausal_women",
    "_55_During_1_year_af_vention_is_necessary",
    "_56_Menopausal_sympt_and_after_menopause",
    "_57_Menopause_is_a_n_women_aged_40_to_59",
    "_58_The_primary_cause_that_occurs_with_age",
    "_59_HRT_can_be_taken_r_used_in_the_vagina",
    "_60_HRT_can_alleviat_hes_and_night_sweats",
    "_61_HRT_can_help_kee_bones_and_fractures",
    "_62_HRT_can_help_red_ion_more_comfortable",
    "_63_HRT_can_help_red_lood_vessel_diseases",
    "_64_HRT_may_help_red_r_of_the_womb_uterus",
    "_66_HRT_may_lead_to_weight_gain",
    "_67_HRT_may_increase_isk_of_breast_cancer",
    "_68_HRT_may_reduce_t_risk_of_colon_cancer",
    "_69_HRT_can_improve_ity_during_menopause",
    "_70_HRT_risks_are_hi_story_of_blood_clots",
    "_71_Estrogen_only_HR_men_without_a_uterus",
    "_72_HRT_should_be_us_st_duration_possible",
]

CORRECT_ANSWER_KEY = {
    "_25_Menopause_is_a_natural_bio": "2",
    "_27_Regular_exercise_menopausal_symptoms": "1_1",
    "_28_Balance_diet_ric_lth_during_menopause": "1_1",
    "_29_Some_plant_based_menopausal_symptoms": "1_1",
    "_30_At_the_time_of_m_ation_stops_suddenly": "1",
    "_31_Women_become_men_e_age_of_45_55_years": "1_1",
    "_32_Family_History_a_an_reaches_menopause": "1_1",
    "_33_Menopause_occurs_reasing_sex_hormones": "1",
    "_34_Slim_people_become_menopausal_sooner": "1_1",
    "_35_Most_women_exper_menopause_occurrence": "1_1",
    "_36_Most_of_the_wome_the_menopause_period": "1_1",
    "_37_Menopause_in_wo_s_genital_infections": "1",
    "_38_Menopause_in_wom_s_weight_and_obesity": "1_1",
    "_39_Menopause_sympt_ventable_and_curable": "1",
    "_40_Menopause_decrea_ar_diseases_in_women": "1",
    "_41_Menopause_make_w_weak_and_soft_bones": "1_1",
    "_42_Menopause_causes_to_wrinkle_in_women": "1",
    "_43_Menopause_causes_s_of_cancer_in_women": "1",
    "_44_Sexual_urge_dec_in_menopausal_women": "0_1",
    "_45_Smoking_delays_e_onset_of_menopause": "1",
    "_46_Smoking_does_not_cations_of_menopause": "1",
    "_47_Menopause_incre_hair_on_women_s_face": "1_1",
    "_48_Menopause_causes_l_sexual_intercourse": "1_1",
    "_49_Menopause_cause_g_when_passing_urine": "1_1",
    "_50_Smoking_and_usin_teomalacia_in_women": "1_1",
    "_51_Regular_physical_in_menopausal_women": "1_1",
    "_52_Menopause_affect_and_memory_of_women": "1_1",
    "_53_The_frequency_an_en_increases_by_time": "1",
    "_54_The_level_of_str_in_menopausal_women": "1_1",
    "_55_During_1_year_af_vention_is_necessary": "1_1",
    "_56_Menopausal_sympt_and_after_menopause": "1_1",
    "_57_Menopause_is_a_n_women_aged_40_to_59": "1_1",
    "_58_The_primary_cause_that_occurs_with_age": "1_1",
    "_59_HRT_can_be_taken_r_used_in_the_vagina": "1_1",
    "_60_HRT_can_alleviat_hes_and_night_sweats": "1_1",
    "_61_HRT_can_help_kee_bones_and_fractures": "1_1",
    "_62_HRT_can_help_red_ion_more_comfortable": "1_1",
    "_63_HRT_can_help_red_lood_vessel_diseases": "1_1",
    "_64_HRT_may_help_red_r_of_the_womb_uterus": "1_1",
    "_66_HRT_may_lead_to_weight_gain": "1_1",
    "_67_HRT_may_increase_isk_of_breast_cancer": "1_1",
    "_68_HRT_may_reduce_t_risk_of_colon_cancer": "1_1",
    "_69_HRT_can_improve_ity_during_menopause": "1_1",
    "_70_HRT_risks_are_hi_story_of_blood_clots": "2",
    "_71_Estrogen_only_HR_men_without_a_uterus": "1_1",
    "_72_HRT_should_be_us_st_duration_possible": "1_1",
}

ATTITUDE_COLS = [
    "_73_Menopause_is_a_p_liness_for_the_woman",
    "_74_Menopause_is_the_preventing_pregnancy",
    "_75_Every_menopausa_d_necessary_tendency",
    "_76_Sexual_activitie_ble_during_menopause",
    "_77_Menopause_is_the_f_women_s_disability",
    "_78_In_the_postmeno_er_husband_decreases",
    "_79_Menopause_in_wo_exual_desire_for_her",
    "_80_A_woman_s_life_han_before_menopause",
    "_81_Menopause_decre_he_beauty_of_a_woman",
    "_82_Menopause_is_a_on_in_a_woman_s_life",
    "_Menopause_the_beginning_of_an",
    "_84_At_menopause_th_an_becomes_different",
    "_85_At_menopause_th_loses_her_womanhood",
    "_86_Menopause_is_a_t_from_monthly_periods",
    "_87_I_have_a_full_un_imenopausal_syndrome",
    "_88_HRT_will_signifi_y_physical_condition",
    "_89_HRT_will_improve_chological_condition",
    "_90_HRT_can_improve_my_quality_of_life",
    "_91_I_have_full_unde_associated_with_HRT",
    "_92_I_am_concerned_about_the_risk_of_HRT",
    "_93_I_would_consider_menopausal_symptoms",
    "_94_The_benefits_of_ghs_the_risks_for_me",
    "_95_I_am_willing_to_menopausal_symptoms",
    "_96_I_trust_my_healt_ider_s_advice_on_HRT",
    "_97_I_m_open_to_tryi_rapies_for_menopause",
    "_98_I_feel_confident_l_symptoms_on_my_own",
]

REVERSE_SCORED = [
    "_73_Menopause_is_a_p_liness_for_the_woman",
    "_77_Menopause_is_the_f_women_s_disability",
    "_78_In_the_postmeno_er_husband_decreases",
    "_79_Menopause_in_wo_exual_desire_for_her",
    "_81_Menopause_decre_he_beauty_of_a_woman",
    "_84_At_menopause_th_an_becomes_different",
    "_85_At_menopause_th_loses_her_womanhood",
    "_92_I_am_concerned_about_the_risk_of_HRT",
    "_98_I_feel_confident_l_symptoms_on_my_own",
]

PRACTICE_COLS = {
    "aware_treatment": "_12_Are_you_aware_of_any_treat",
    "aware_hrt": "_13_Are_you_aware_of_acement_Therapy_HRT",
    "ever_used_hrt": "_14_Have_you_ever_used_any_HRT",
    "currently_use": "_15_Do_you_currently_use_HRT",
    "on_hrt": "_126_Are_you_on_hormone_replac",
    "discussed_hcp": "_112_Have_you_discus_healthcare_provider",
    "want_to_know": "_113_Would_you_like_replacement_therapy",
}

SYMPTOM_COLS = {
    "Genital symptoms": "_111_Genital_symptoms",
    "Vaginal dryness": "_112_Vaginal_dryness",
    "Reduced lubrication": "_113_Reduced_lubrication",
    "Dyspareunia": "_114_Dyspareunia",
    "Irritation/burning/itching": "_115_Irritation_burning_itchin",
    "Post-coital bleeding": "_116_Post_coital_bleeding",
    "Stress incontinence": "_117_Stress_incontinence",
    "Urge incontinence": "_118_Urge_incontinence",
    "UTI (past 12 months)": "_119_Have_you_been_treated_for",
    "Dysuria": "_120_Dysuria",
    "Urgency": "_121_Urgency",
}

MANAGEMENT_COLS = {
    "Lifestyle changes": "_123_How_do_you_manage_your_sy/1",
    "HRT": "_123_How_do_you_manage_your_sy/2",
    "Alternative therapy": "_123_How_do_you_manage_your_sy/3",
    "Others": "_123_How_do_you_manage_your_sy/4",
}

# Required columns — at least some of these must be present in uploaded data
REQUIRED_COLS_SAMPLE = [
    "Do_you_consent_to_this_study",
    "_1_Age_in_years",
    "_25_Menopause_is_a_natural_bio",
    "_73_Menopause_is_a_p_liness_for_the_woman",
]


# =============================================================================
# PIPELINE FUNCTIONS (adapted from analysis.py to work in-memory)
# =============================================================================


def validate_dataframe(df: pd.DataFrame) -> None:
    """Raise ValueError if the DataFrame doesn't look like valid KAP data."""
    missing = [c for c in REQUIRED_COLS_SAMPLE if c not in df.columns]
    if len(missing) == len(REQUIRED_COLS_SAMPLE):
        raise ValueError(
            f"The uploaded file doesn't appear to be a valid KAP questionnaire dataset. "
            f"Expected columns like {REQUIRED_COLS_SAMPLE[:3]} but none were found. "
            f"Found columns: {list(df.columns[:10])}..."
        )


def filter_consent(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Filter to only consented participants. Returns (df, n_total, n_excluded)."""
    n_total = len(df)
    consent_col = "Do_you_consent_to_this_study"
    if consent_col in df.columns:
        df = df[df[consent_col] == 1].reset_index(drop=True)
        df = df.drop(columns=[consent_col])
    n_excluded = n_total - len(df)
    return df, n_total, n_excluded


def drop_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Drop system/metadata columns and all-NaN note columns."""
    meta_cols = [
        "start",
        "end",
        "_id",
        "_uuid",
        "_submission_time",
        "_validation_status",
        "_notes",
        "_status",
        "_submitted_by",
        "__version__",
        "_tags",
        "meta/rootUuid",
        "_index",
    ]
    note_cols = [c for c in df.columns if df[c].isna().all() and c not in meta_cols]

    version_col = df["__version__"].copy() if "__version__" in df.columns else None

    drop_cols = [c for c in meta_cols + note_cols if c in df.columns]
    df = df.drop(columns=drop_cols, errors="ignore")

    if version_col is not None:
        df["__version__"] = version_col

    return df


def coalesce_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Merge duplicate columns from different form versions."""
    seen: dict[str, int] = {}
    cols_to_drop: list[int] = []
    for idx, col in enumerate(df.columns):
        if col in seen and col != "__version__":
            primary_idx = seen[col]
            df.iloc[:, primary_idx] = df.iloc[:, primary_idx].combine_first(
                df.iloc[:, idx]
            )
            cols_to_drop.append(idx)
        else:
            seen[col] = idx

    if cols_to_drop:
        df = df.drop(df.columns[cols_to_drop], axis=1)

    df = df.drop(columns=["__version__"], errors="ignore")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Fix malformed values, coerce types, map labels."""
    df = df.copy()

    # Fix backtick and apostrophe artifacts in attitude columns
    for col in ATTITUDE_COLS:
        if col in df.columns:
            df[col] = df[col].replace("`", 1)
            df[col] = df[col].apply(
                lambda x: str(x).replace("'", "").strip() if isinstance(x, str) else x
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Clean knowledge columns
    for col in KNOWLEDGE_COLS:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(x).replace("'", "").strip() if isinstance(x, str) else x
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Map sociodemographic codes to labels
    for col_key, col_name in SOCIO_COLS.items():
        if col_name in df.columns and col_name in SOCIO_LABELS:
            df[f"{col_key}_label"] = df[col_name].map(SOCIO_LABELS[col_name])

    # Map menopausal status
    status_map = {0: "Premenopausal", 1: "Perimenopausal", 2: "Postmenopausal"}
    status_col = "_19_Which_of_the_fol_k_best_describes_you"
    if status_col in df.columns:
        df["menopausal_status_label"] = df[status_col].map(status_map)

    return df


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute knowledge, attitude, and practice scores."""
    df = df.copy()

    # --- Knowledge scoring ---
    item_scores = []
    for col in KNOWLEDGE_COLS:
        if col not in df.columns:
            continue
        correct_code = CORRECT_ANSWER_KEY.get(col)
        if correct_code is None:
            continue

        if correct_code == "1_1":
            scored = df[col].apply(
                lambda x: 1 if x == 11.0 or x == 2.0 else 0 if pd.notna(x) else np.nan
            )
        elif correct_code == "0_1":
            scored = df[col].apply(
                lambda x: 1 if x == 1.0 else 0 if pd.notna(x) else np.nan
            )
        elif correct_code == "2":
            scored = df[col].apply(
                lambda x: 1 if x == 2.0 else 0 if pd.notna(x) else np.nan
            )
        elif correct_code == "1":
            scored = df[col].apply(
                lambda x: 1 if x == 1.0 else 0 if pd.notna(x) else np.nan
            )
        else:
            numeric = float(correct_code)
            scored = df[col].apply(
                lambda x, n=numeric: 1 if x == n else 0 if pd.notna(x) else np.nan
            )
        item_scores.append(scored)

    if item_scores:
        score_df = pd.concat(item_scores, axis=1)
        df["knowledge_score"] = score_df.sum(axis=1)
        df["knowledge_max"] = score_df.notna().sum(axis=1)
        df["knowledge_pct"] = (df["knowledge_score"] / df["knowledge_max"] * 100).round(
            1
        )

    # --- Attitude scoring ---
    att_df = pd.DataFrame(index=df.index)
    for col in ATTITUDE_COLS:
        if col not in df.columns:
            continue
        values = df[col].copy()
        if col in REVERSE_SCORED:
            values = values.apply(
                lambda x: 6 - x if pd.notna(x) and 1 <= x <= 5 else np.nan
            )
        else:
            values = values.apply(
                lambda x: x if pd.notna(x) and 1 <= x <= 5 else np.nan
            )
        att_df[col] = values

    df["attitude_score"] = att_df.sum(axis=1)
    df["attitude_max"] = att_df.notna().sum(axis=1) * 5
    df["attitude_items_answered"] = att_df.notna().sum(axis=1)
    df["attitude_pct"] = (df["attitude_score"] / df["attitude_max"] * 100).round(1)

    # --- Practice variables ---
    hrt_col = PRACTICE_COLS.get("on_hrt", "")
    ever_col = PRACTICE_COLS.get("ever_used_hrt", "")

    if hrt_col in df.columns:
        df["hrt_current"] = df[hrt_col].map({1: "Yes", 0: "No"})
    if ever_col in df.columns:
        df["hrt_ever"] = df[ever_col].map({1: "Yes", 0: "No"})

    def classify_hrt(row):
        if pd.notna(row.get(hrt_col)) and row[hrt_col] == 1:
            return "Currently using HRT"
        elif pd.notna(row.get(ever_col)) and row[ever_col] == 1:
            return "Previously used HRT"
        elif pd.notna(row.get(ever_col)):
            return "Never used HRT"
        return np.nan

    df["hrt_practice"] = df.apply(classify_hrt, axis=1)
    return df


def categorize_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Create Good/Poor knowledge and Positive/Negative attitude categories."""
    df = df.copy()

    df["knowledge_category"] = df["knowledge_pct"].apply(
        lambda x: (
            "Good" if pd.notna(x) and x >= 50 else ("Poor" if pd.notna(x) else np.nan)
        )
    )

    att_mean = df["attitude_score"].mean()
    df["attitude_category"] = df["attitude_score"].apply(
        lambda x: (
            "Positive"
            if pd.notna(x) and x >= att_mean
            else ("Negative" if pd.notna(x) else np.nan)
        )
    )
    return df


def run_chi_square(df: pd.DataFrame) -> list[dict]:
    """Run chi-square tests and return results as a list of dicts."""
    demo_vars = {
        "Age Group": "age_label",
        "Education Level": "education_label",
        "Occupation": "occupation_label",
        "Marital Status": "marital_label",
        "Monthly Income": "income_label",
    }
    outcomes = {
        "Knowledge (Good/Poor)": "knowledge_category",
        "Attitude (Positive/Negative)": "attitude_category",
        "HRT Use (Yes/No)": "hrt_current",
    }

    results = []
    for demo_name, demo_col in demo_vars.items():
        if demo_col not in df.columns:
            continue
        for outcome_name, outcome_col in outcomes.items():
            if outcome_col not in df.columns:
                continue

            subset = df[[demo_col, outcome_col]].dropna()
            if len(subset) == 0:
                continue

            contingency = pd.crosstab(subset[demo_col], subset[outcome_col])
            if contingency.shape[0] < 2 or contingency.shape[1] < 2:
                results.append(
                    {
                        "demographic": demo_name,
                        "outcome": outcome_name,
                        "chi2": None,
                        "df": None,
                        "p_value": None,
                        "significant": False,
                        "note": "Insufficient categories",
                    }
                )
                continue

            try:
                chi2, p, dof, expected = stats.chi2_contingency(contingency)
                note = ""
                if expected.min() < 5:
                    note = f"Min expected = {expected.min():.1f} (<5)"

                results.append(
                    {
                        "demographic": demo_name,
                        "outcome": outcome_name,
                        "chi2": round(chi2, 3),
                        "df": int(dof),
                        "p_value": round(p, 4),
                        "significant": bool(p < 0.05),
                        "note": note,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "demographic": demo_name,
                        "outcome": outcome_name,
                        "chi2": None,
                        "df": None,
                        "p_value": None,
                        "significant": False,
                        "note": f"Error: {str(e)}",
                    }
                )

    return results


def build_summary(
    df: pd.DataFrame, n_total: int, n_excluded: int, chi_results: list[dict]
) -> dict:
    """Build JSON-serializable summary dict for the frontend."""
    n = len(df)

    # Sociodemographics: frequency counts per label
    socio = {}
    for key, display_name in SOCIO_DISPLAY_NAMES.items():
        label_col = f"{key}_label"
        if label_col in df.columns:
            counts = df[label_col].dropna().value_counts()
            socio[display_name] = {str(k): int(v) for k, v in counts.items()}

    # Menopausal status
    if "menopausal_status_label" in df.columns:
        counts = df["menopausal_status_label"].dropna().value_counts()
        socio["Menopausal Status"] = {str(k): int(v) for k, v in counts.items()}

    # Knowledge
    know = df[df["knowledge_score"].notna()]
    knowledge = {
        "mean_score": round(float(know["knowledge_score"].mean()), 1)
        if len(know)
        else 0,
        "mean_max": round(float(know["knowledge_max"].mean()), 1) if len(know) else 0,
        "mean_pct": round(float(know["knowledge_pct"].mean()), 1) if len(know) else 0,
        "sd": round(float(know["knowledge_score"].std()), 1) if len(know) else 0,
        "good_n": int((know["knowledge_category"] == "Good").sum()) if len(know) else 0,
        "good_pct": round(
            float((know["knowledge_category"] == "Good").sum() / len(know) * 100), 1
        )
        if len(know)
        else 0,
        "poor_n": int((know["knowledge_category"] == "Poor").sum()) if len(know) else 0,
        "poor_pct": round(
            float((know["knowledge_category"] == "Poor").sum() / len(know) * 100), 1
        )
        if len(know)
        else 0,
    }

    # Attitude
    att = df[df["attitude_score"].notna()]
    attitude = {
        "mean_score": round(float(att["attitude_score"].mean()), 1) if len(att) else 0,
        "mean_max": round(float(att["attitude_max"].mean()), 1) if len(att) else 0,
        "mean_pct": round(float(att["attitude_pct"].mean()), 1) if len(att) else 0,
        "sd": round(float(att["attitude_score"].std()), 1) if len(att) else 0,
        "positive_n": int((att["attitude_category"] == "Positive").sum())
        if len(att)
        else 0,
        "positive_pct": round(
            float((att["attitude_category"] == "Positive").sum() / len(att) * 100), 1
        )
        if len(att)
        else 0,
        "negative_n": int((att["attitude_category"] == "Negative").sum())
        if len(att)
        else 0,
        "negative_pct": round(
            float((att["attitude_category"] == "Negative").sum() / len(att) * 100), 1
        )
        if len(att)
        else 0,
    }

    # HRT practice
    hrt_counts = (
        df["hrt_practice"].value_counts()
        if "hrt_practice" in df.columns
        else pd.Series()
    )
    hrt_practice = {
        "currently_using": int(hrt_counts.get("Currently using HRT", 0)),
        "previously_used": int(hrt_counts.get("Previously used HRT", 0)),
        "never_used": int(hrt_counts.get("Never used HRT", 0)),
    }

    return {
        "total_respondents": n,
        "total_submissions": n_total,
        "excluded": n_excluded,
        "sociodemographics": socio,
        "knowledge": knowledge,
        "attitude": attitude,
        "hrt_practice": hrt_practice,
        "chi_square": chi_results,
    }


def descriptive_stats(df):
    """
    Generate publication-ready descriptive statistics tables:

    Table 1: Sociodemographic characteristics (frequencies & percentages)
    Table 2: Knowledge score distribution
    Table 3: Attitude score distribution
    Table 4: HRT practice patterns

    Returns: dict of DataFrames (table_name → DataFrame)

    JS analogy: Like building summary objects with .reduce(), then formatting
    them as arrays of {variable, frequency, percentage} objects.
    """
    print("=" * 70)
    print("PHASE 3: Generating descriptive statistics...")
    print("=" * 70)

    tables = {}

    # ── Table 1: Sociodemographic Characteristics ────────────────────────
    rows = []
    socio_display = {
        "age": ("Age Group", "_1_Age_in_years"),
        "education": ("Education Level", "_2_Education_level"),
        "occupation": ("Occupation", "_3_What_is_your_profession"),
        "marital": ("Marital Status", "_4_Marital_status"),
        "income": ("Average Monthly Income", "_5_Average_monthly_income"),
        "insurance": ("Health Insurance", "_6_Enrolled_in_health_insurance"),
        "children": ("Number of Children", "_7_Number_of_children"),
        "sex": (
            "Sexual experience in Last 3 Months",
            "_8_Have_you_had_any_in_the_last_3_months",
        ),
    }

    for key, (display_name, col_name) in socio_display.items():
        label_col = f"{key}_label"
        if label_col in df.columns:
            series = df[label_col].dropna()
        elif col_name in df.columns:
            series = df[col_name].dropna()
        else:
            continue

        total = len(series)
        counts = series.value_counts()

        # Add variable header row
        rows.append(
            {
                "Variable": display_name,
                "Category": "",
                "Frequency (n)": "",
                "Percentage (%)": "",
            }
        )

        # Sort categories in a meaningful order (use the codebook order)
        if col_name in SOCIO_LABELS and label_col in df.columns:
            ordered_labels = list(SOCIO_LABELS[col_name].values())
            for label in ordered_labels:
                n = counts.get(label, 0)
                pct = n / total * 100 if total > 0 else 0
                rows.append(
                    {
                        "Variable": "",
                        "Category": label,
                        "Frequency (n)": n,
                        "Percentage (%)": f"{pct:.1f}",
                    }
                )
        else:
            for cat, n in counts.items():
                pct = n / total * 100 if total > 0 else 0
                rows.append(
                    {
                        "Variable": "",
                        "Category": str(cat),
                        "Frequency (n)": n,
                        "Percentage (%)": f"{pct:.1f}",
                    }
                )

    # Add menopausal status
    if "menopausal_status_label" in df.columns:
        series = df["menopausal_status_label"].dropna()
        total = len(series)
        counts = series.value_counts()
        rows.append(
            {
                "Variable": "Menopausal Status",
                "Category": "",
                "Frequency (n)": "",
                "Percentage (%)": "",
            }
        )
        for cat in ["Premenopausal", "Perimenopausal", "Postmenopausal"]:
            n = counts.get(cat, 0)
            pct = n / total * 100 if total > 0 else 0
            rows.append(
                {
                    "Variable": "",
                    "Category": cat,
                    "Frequency (n)": n,
                    "Percentage (%)": f"{pct:.1f}",
                }
            )

    table1 = pd.DataFrame(rows)
    tables["Table 1 - Sociodemographics"] = table1

    print("\n  TABLE 1: Sociodemographic Characteristics of Respondents")
    print("  " + "─" * 65)
    print(table1.to_string(index=False))

    # ── Table 2: Knowledge Score Distribution ────────────────────────────
    know_data = df[df["knowledge_score"].notna()]

    know_rows = []
    know_rows.append(
        {"Measure": "Total respondents scored", "Value": f"{len(know_data)}"}
    )
    know_rows.append(
        {
            "Measure": "Mean knowledge score ± SD",
            "Value": f"{know_data['knowledge_score'].mean():.1f} ± "
            f"{know_data['knowledge_score'].std():.1f}",
        }
    )
    know_rows.append(
        {
            "Measure": "Mean items attempted",
            "Value": f"{know_data['knowledge_max'].mean():.1f} / {len(KNOWLEDGE_COLS)}",
        }
    )
    know_rows.append(
        {
            "Measure": "Mean percentage correct",
            "Value": f"{know_data['knowledge_pct'].mean():.1f}%",
        }
    )
    know_rows.append({"Measure": "---", "Value": "---"})

    for cat in ["Good", "Poor"]:
        n = (know_data["knowledge_category"] == cat).sum()
        pct = n / len(know_data) * 100
        know_rows.append(
            {"Measure": f"{cat} knowledge (n, %)", "Value": f"{n} ({pct:.1f}%)"}
        )

    table2 = pd.DataFrame(know_rows)
    tables["Table 2 - Knowledge Scores"] = table2

    print(f"\n\n  TABLE 2: Knowledge Score Distribution")  # noqa: F541
    print("  " + "─" * 50)
    print(table2.to_string(index=False))

    # ── Table 3: Attitude Score Distribution ─────────────────────────────
    att_data = df[df["attitude_score"].notna()]
    att_mean = att_data["attitude_score"].mean()

    att_rows = []
    att_rows.append(
        {"Measure": "Total respondents scored", "Value": f"{len(att_data)}"}
    )
    att_rows.append(
        {
            "Measure": "Mean attitude score ± SD",
            "Value": f"{att_data['attitude_score'].mean():.1f} ± "
            f"{att_data['attitude_score'].std():.1f}",
        }
    )
    att_rows.append(
        {
            "Measure": "Score range",
            "Value": f"{att_data['attitude_score'].min():.0f} – "
            f"{att_data['attitude_score'].max():.0f}",
        }
    )
    att_rows.append(
        {
            "Measure": "Mean items answered",
            "Value": f"{att_data['attitude_items_answered'].mean():.1f} / "
            f"{len(ATTITUDE_COLS)}",
        }
    )
    att_rows.append(
        {"Measure": f"Categorization cutoff (mean)", "Value": f"{att_mean:.1f}"}  # noqa: F541
    )
    att_rows.append({"Measure": "---", "Value": "---"})

    for cat in ["Positive", "Negative"]:
        n = (att_data["attitude_category"] == cat).sum()
        pct = n / len(att_data) * 100
        att_rows.append(
            {"Measure": f"{cat} attitude (n, %)", "Value": f"{n} ({pct:.1f}%)"}
        )

    table3 = pd.DataFrame(att_rows)
    tables["Table 3 - Attitude Scores"] = table3

    print(f"\n\n  TABLE 3: Attitude Score Distribution")  # noqa: F541
    print("  " + "─" * 50)
    print(table3.to_string(index=False))

    # ── Table 4: HRT Practice Patterns ───────────────────────────────────
    practice_rows = []

    # HRT awareness and usage
    practice_items = [
        ("Aware of any treatment for menopause", "aware_treatment"),
        ("Aware of HRT", "aware_hrt"),
        ("Ever used any form of HRT", "ever_used_hrt"),
        ("Currently using HRT", "on_hrt"),
        ("Discussed menopause/HRT with healthcare provider", "discussed_hcp"),
        ("Would like to know more about menopause/HRT", "want_to_know"),
    ]

    practice_rows.append(
        {
            "Variable": "HRT Awareness & Usage",
            "Category": "",
            "Frequency (n)": "",
            "Percentage (%)": "",
        }
    )

    for label, key in practice_items:
        col = PRACTICE_COLS.get(key, "")
        if col in df.columns:
            series = df[col].dropna()
            total = len(series)
            yes_n = (series == 1).sum()
            yes_pct = yes_n / total * 100 if total > 0 else 0
            practice_rows.append(
                {
                    "Variable": "",
                    "Category": label,
                    "Frequency (n)": f"{yes_n}/{total}",
                    "Percentage (%)": f"{yes_pct:.1f}",
                }
            )

    # Symptom prevalence
    practice_rows.append(
        {
            "Variable": "Genitourinary Symptoms (Yes)",
            "Category": "",
            "Frequency (n)": "",
            "Percentage (%)": "",
        }
    )

    for symptom_label, symptom_col in SYMPTOM_COLS.items():
        if symptom_col in df.columns:
            series = df[symptom_col].dropna()
            total = len(series)
            yes_n = (series == 1).sum()
            yes_pct = yes_n / total * 100 if total > 0 else 0
            practice_rows.append(
                {
                    "Variable": "",
                    "Category": symptom_label,
                    "Frequency (n)": f"{yes_n}/{total}",
                    "Percentage (%)": f"{yes_pct:.1f}",
                }
            )

    # Symptom management
    practice_rows.append(
        {
            "Variable": "Symptom Management Methods",
            "Category": "",
            "Frequency (n)": "",
            "Percentage (%)": "",
        }
    )

    for mgmt_label, mgmt_col in MANAGEMENT_COLS.items():
        if mgmt_col in df.columns:
            series = df[mgmt_col].dropna()
            total = len(series)
            yes_n = (series == 1).sum()
            yes_pct = yes_n / total * 100 if total > 0 else 0
            practice_rows.append(
                {
                    "Variable": "",
                    "Category": mgmt_label,
                    "Frequency (n)": f"{yes_n}/{total}",
                    "Percentage (%)": f"{yes_pct:.1f}",
                }
            )

    table4 = pd.DataFrame(practice_rows)
    tables["Table 4 - HRT Practices"] = table4

    print(f"\n\n  TABLE 4: HRT Practice Patterns")  # noqa: F541
    print("  " + "─" * 65)
    print(table4.to_string(index=False))

    print()
    return tables


def build_excel_files(
    df: pd.DataFrame, chi_results: list[dict]
) -> tuple[io.BytesIO, io.BytesIO]:
    """Write results and cleaned data to in-memory Excel buffers."""
    # --- results_output.xlsx ---
    results_buf = io.BytesIO()
    chi_df = pd.DataFrame(chi_results)

    if "significant" in chi_df.columns:
        chi_df["significant"] = chi_df["significant"].map({True: "Yes", False: "No"})

    chi_df.rename(
        columns={
            "demographic": "Demographic Variable",
            "outcome": "Outcome Variable",
            "chi2": "Chi-Square (χ²)",
            "df": "df",
            "p_value": "p-value",
            "significant": "Significance",
            "note": "Note",
        },
        inplace=True,
    )

    # Generate the formatted tables for the Excel export
    tables = descriptive_stats(df)

    with pd.ExcelWriter(results_buf, engine="openpyxl") as writer:
        # Table 1-4 from descriptive stats
        for sheet_name, table_df in tables.items():
            safe_name = sheet_name[:31]
            table_df.to_excel(writer, sheet_name=safe_name, index=False)

        # Chi-Square sheet
        chi_df.to_excel(writer, sheet_name="Table 5 - Chi-Square", index=False)

        # Scores & Labels sheet
        score_cols = [
            "knowledge_score",
            "knowledge_max",
            "knowledge_pct",
            "knowledge_category",
            "attitude_score",
            "attitude_max",
            "attitude_pct",
            "attitude_category",
            "hrt_practice",
            "hrt_current",
            "hrt_ever",
        ]
        label_cols = [c for c in df.columns if c.endswith("_label")]
        export_cols = label_cols + [c for c in score_cols if c in df.columns]
        df[export_cols].to_excel(writer, sheet_name="Scores & Labels", index=False)

    results_buf.seek(0)

    # --- raw_data_cleaned.xlsx ---
    cleaned_buf = io.BytesIO()
    df.to_excel(cleaned_buf, index=False, engine="openpyxl")
    cleaned_buf.seek(0)

    return results_buf, cleaned_buf


# =============================================================================
# MAIN ENTRY POINT — called by FastAPI
# =============================================================================


def run_pipeline(df: pd.DataFrame) -> dict:
    """
    Run the full analysis pipeline on an uploaded DataFrame.

    Returns a dict with:
      - "summary": JSON-serializable dashboard data
      - "results_xlsx": BytesIO buffer of results_output.xlsx
      - "cleaned_xlsx": BytesIO buffer of raw_data_cleaned.xlsx
    """
    # Step 1: Validate
    validate_dataframe(df)

    # Step 2: Filter consent
    df, n_total, n_excluded = filter_consent(df)
    if len(df) == 0:
        raise ValueError("No consented participants found in the dataset.")

    # Step 3: Clean
    df = drop_metadata(df)
    df = coalesce_duplicates(df)
    df = clean_data(df)

    # Step 4: Score & categorize
    df = compute_scores(df)
    df = categorize_variables(df)

    # Step 5: Chi-square tests
    chi_results = run_chi_square(df)

    # Step 6: Build outputs
    summary = build_summary(df, n_total, n_excluded, chi_results)
    results_buf, cleaned_buf = build_excel_files(df, chi_results)

    return {
        "summary": summary,
        "results_xlsx": results_buf,
        "cleaned_xlsx": cleaned_buf,
    }
