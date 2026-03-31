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
import statsmodels.api as sm

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
    "_26_The_main_symptoms_of_menopause",
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
    "_65_HRT_may_potentia_side_effects_such_as",
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
    "_26_The_main_symptoms_of_menopause": "MULTI",
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
    """Fix malformed values, coerce types, map labels, impute NaNs, recode Menopausal status."""
    import numpy as np

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

    # Proportional Imputation for SOCIO_COLS (Requirement 1)
    imputation_cols = [
        "_3_What_is_your_profession",
        "_4_Marital_status",
        "_5_Average_monthly_income",
        "_6_Enrolled_in_health_insurance",
        "_7_Number_of_children",
        "_8_Have_you_had_any_in_the_last_3_months",
    ]
    for col in imputation_cols:
        if col in df.columns:
            non_nulls = df[col].dropna()
            if len(non_nulls) > 0 and df[col].isnull().sum() > 0:
                probs = non_nulls.value_counts(normalize=True)
                missing_mask = df[col].isnull()
                fill_values = np.random.choice(
                    probs.index, size=missing_mask.sum(), p=probs.values
                )
                df.loc[missing_mask, col] = fill_values

    # Map sociodemographic codes to labels
    for col_key, col_name in SOCIO_COLS.items():
        if col_name in df.columns and col_name in SOCIO_LABELS:
            df[f"{col_key}_label"] = df[col_name].map(SOCIO_LABELS[col_name])

    # Recode Menopausal Status (Requirement 2)
    status_col = "_19_Which_of_the_fol_k_best_describes_you"
    age_col = "_1_Age_in_years"

    def infer_status(row):
        val = row.get(status_col)
        age = row.get(age_col)

        # Rule 1: Explicit 1 or 2
        if pd.notna(val) and val in [1, 2, "1", "2", 1.0, 2.0]:
            return float(val)

        # Rule 2 & 3: Infer based on age (1=Peri, 2=Post)
        # SOCIO_LABELS age: 5:"40-44", 4:"45-49" are Peri. 3,2,1 are Post.
        if pd.notna(age):
            if float(age) in [4.0, 5.0]:
                return 1.0  # Peri
            else:
                return 2.0  # Post
        return np.nan

    if status_col in df.columns and age_col in df.columns:
        df[status_col] = df.apply(infer_status, axis=1)

    status_map = {1.0: "Perimenopausal", 2.0: "Postmenopausal"}
    if status_col in df.columns:
        df["menopausal_status_label"] = df[status_col].map(status_map)

    return df


def calculate_cronbach_alpha(df_items: pd.DataFrame) -> float:
    """Calculate Cronbach's Alpha for internal consistency."""
    k = df_items.shape[1]
    if k < 2 or len(df_items.dropna()) == 0:
        return 0.0
    item_vars = df_items.var(axis=0, ddof=1)
    total_var = df_items.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return 0.0
    alpha = (k / (k - 1)) * (1 - (item_vars.sum() / total_var))
    return alpha


def compute_split_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute split knowledge/attitude constructs (Meno & HRT) and practice scores."""
    df = df.copy()

    # Split construct columns
    idx_know_split = KNOWLEDGE_COLS.index("_59_HRT_can_be_taken_r_used_in_the_vagina")
    KNOW_MENO_COLS = KNOWLEDGE_COLS[:idx_know_split]
    KNOW_HRT_COLS = KNOWLEDGE_COLS[idx_know_split:]

    idx_att_split = ATTITUDE_COLS.index("_87_I_have_a_full_un_imenopausal_syndrome")
    ATT_MENO_COLS = ATTITUDE_COLS[:idx_att_split]
    ATT_HRT_COLS = ATTITUDE_COLS[idx_att_split:]

    def score_knowledge_block(cols):
        scores = []
        for col in cols:
            if col in [
                "_26_The_main_symptoms_of_menopause",
                "_65_HRT_may_potentia_side_effects_such_as",
            ]:
                if col in df.columns:

                    def score_multi(x):
                        if pd.isna(x):
                            return np.nan
                        return len(str(x).split())

                    scored = df[col].apply(score_multi)
                else:
                    q26_cols = [c for c in df.columns if str(c).startswith(col + "/")]
                    if q26_cols:
                        scored = df[q26_cols].sum(axis=1)
                        all_na = df[q26_cols].isna().all(axis=1)
                        scored.loc[all_na] = np.nan
                    else:
                        scored = pd.Series(np.nan, index=df.index)
                scores.append(pd.Series(scored, name=col))
                continue

            if col not in df.columns:
                continue
            ans = CORRECT_ANSWER_KEY.get(col)
            if not ans:
                continue
            if ans == "1_1":
                scored = df[col].apply(
                    lambda x: 1 if x in [11.0, 2.0] else 0 if pd.notna(x) else np.nan
                )
            elif ans == "0_1":
                scored = df[col].apply(
                    lambda x: 1 if x == 1.0 else 0 if pd.notna(x) else np.nan
                )
            else:
                n = float(ans)
                scored = df[col].apply(
                    lambda x, n=n: 1 if x == n else 0 if pd.notna(x) else np.nan
                )
            scores.append(scored)
        if scores:
            return pd.concat(scores, axis=1)
        return pd.DataFrame(index=df.index)

    def score_attitude_block(cols):
        att_df = pd.DataFrame(index=df.index)
        for col in cols:
            if col not in df.columns:
                continue
            vals = df[col].copy()
            if col in REVERSE_SCORED:
                vals = vals.apply(
                    lambda x: 6 - x if pd.notna(x) and 1 <= x <= 5 else np.nan
                )
            else:
                vals = vals.apply(
                    lambda x: x if pd.notna(x) and 1 <= x <= 5 else np.nan
                )
            att_df[col] = vals
        return att_df

    # Calculate DataFrames
    df_know_meno = score_knowledge_block(KNOW_MENO_COLS)
    df_know_hrt = score_knowledge_block(KNOW_HRT_COLS)
    df_att_meno = score_attitude_block(ATT_MENO_COLS)
    df_att_hrt = score_attitude_block(ATT_HRT_COLS)

    # Missing respondents fix for Knowledge of HRT (User requested imputation of minimum score)
    # If a respondent has completely blank responses (NaN in all columns), impute 0 across all variables.
    all_na_know_hrt = df_know_hrt.isna().all(axis=1)
    if all_na_know_hrt.any():
        df_know_hrt.loc[all_na_know_hrt, :] = 0.0

    # Missing respondents fix for Attitude towards HRT (User requested imputation of minimum score)
    # If a respondent has completely blank responses (NaN in all columns), impute 1 across all 12 variables.
    all_na_att_hrt = df_att_hrt.isna().all(axis=1)
    if all_na_att_hrt.any():
        df_att_hrt.loc[all_na_att_hrt, :] = 1.0

    # Ensure respondents who skipped HRT knowledge due to selecting No (0) for "Do you know about hormone replacement therapy?"
    # receive a legitimate 0 score instead of NaN, anchoring the pool to the full dataset (n=239)
    filter_col = next(
        (c for c in df.columns if "Do_you_know_about_hormone_repl" in str(c)), None
    )
    if filter_col:
        # Check against string '0', float 0.0, int 0, 'No', etc.
        no_mask = df[filter_col].apply(
            lambda x: str(x).strip().lower() in ["0", "0.0", "no", "false"]
        )

        # Force physical 0.0 so they contribute precisely 0 marks to their total denominator
        df_know_hrt.loc[no_mask, :] = 0.0

    # Print Cronbach's Alpha (Requirement 3)
    c_m = calculate_cronbach_alpha(df_know_meno)
    c_h = calculate_cronbach_alpha(df_know_hrt)
    a_m = calculate_cronbach_alpha(df_att_meno)
    a_h = calculate_cronbach_alpha(df_att_hrt)

    print("=" * 70)
    print("RELIABILITY CHECKS (Cronbach's Alpha)")
    print("=" * 70)
    print(f"Knowledge of Menopause: {c_m:.3f}")
    print(f"Knowledge of HRT:       {c_h:.3f}")
    print(f"Attitude regarding Menopause: {a_m:.3f}")
    print(f"Attitude regarding HRT:       {a_h:.3f}")

    df.attrs["cronbach"] = {
        "Knowledge of Menopause": c_m,
        "Knowledge of HRT": c_h,
        "Attitude towards Menopause": a_m,
        "Attitude towards HRT": a_h,
    }

    # Compute Sums (using min_count=1 to preserve NaN for completely skipped sections)
    df["know_meno_score"] = df_know_meno.sum(axis=1, min_count=1)
    df["know_hrt_score"] = df_know_hrt.sum(axis=1, min_count=1)
    df["att_meno_score"] = df_att_meno.sum(axis=1, min_count=1)
    df["att_hrt_score"] = df_att_hrt.sum(axis=1, min_count=1)

    # Note: Retain overall knowledge/attitude fields to avoid breaking dashboard compatibility,
    # but base them on sum of sub-scales.
    df["knowledge_score"] = df["know_meno_score"] + df["know_hrt_score"]

    def get_max_score(df_scored):
        max_scores = pd.Series(0.0, index=df_scored.index)
        for col in df_scored.columns:
            if col == "_26_The_main_symptoms_of_menopause":
                max_scores += df_scored[col].notna() * 12
            elif col == "_65_HRT_may_potentia_side_effects_such_as":
                max_scores += df_scored[col].notna() * 3
            else:
                max_scores += df_scored[col].notna() * 1
        return max_scores

    df["knowledge_max"] = get_max_score(df_know_meno) + get_max_score(df_know_hrt)
    df["knowledge_pct"] = (df["knowledge_score"] / df["knowledge_max"] * 100).round(1)

    df["attitude_score"] = df["att_meno_score"] + df["att_hrt_score"]
    df["attitude_max"] = (
        df_att_meno.notna().sum(axis=1) + df_att_hrt.notna().sum(axis=1)
    ) * 5
    df["attitude_items_answered"] = df_att_meno.notna().sum(
        axis=1
    ) + df_att_hrt.notna().sum(axis=1)
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
    """Create Good/Poor and Positive/Negative based strictly on cohort means (Requirement 3)."""
    df = df.copy()

    # Knowledge Menopause Cutoff
    km_mean = df["know_meno_score"].mean()
    df["know_meno_category"] = df["know_meno_score"].apply(
        lambda x: (
            "Good"
            if pd.notna(x) and x >= km_mean
            else "Poor"
            if pd.notna(x)
            else np.nan
        )
    )

    # Knowledge HRT Cutoff
    kh_mean = df["know_hrt_score"].mean()
    df["know_hrt_category"] = df["know_hrt_score"].apply(
        lambda x: (
            "Good"
            if pd.notna(x) and x >= kh_mean
            else "Poor"
            if pd.notna(x)
            else np.nan
        )
    )

    # Attitude Menopause Cutoff
    am_mean = df["att_meno_score"].mean()
    df["att_meno_category"] = df["att_meno_score"].apply(
        lambda x: (
            "Positive"
            if pd.notna(x) and x >= am_mean
            else "Negative"
            if pd.notna(x)
            else np.nan
        )
    )

    # Attitude HRT Cutoff
    ah_mean = df["att_hrt_score"].mean()
    df["att_hrt_category"] = df["att_hrt_score"].apply(
        lambda x: (
            "Positive"
            if pd.notna(x) and x >= ah_mean
            else "Negative"
            if pd.notna(x)
            else np.nan
        )
    )

    # Overall categories (for dashboard compatibility using combined mean)
    k_mean = df["knowledge_score"].mean()
    df["knowledge_category"] = df["knowledge_score"].apply(
        lambda x: (
            "Good" if pd.notna(x) and x >= k_mean else "Poor" if pd.notna(x) else np.nan
        )
    )

    a_mean = df["attitude_score"].mean()
    df["attitude_category"] = df["attitude_score"].apply(
        lambda x: (
            "Positive"
            if pd.notna(x) and x >= a_mean
            else "Negative"
            if pd.notna(x)
            else np.nan
        )
    )

    return df


def run_chi_square(df: pd.DataFrame) -> list[dict]:
    """Run detailed chi-square tests with Fisher Exact fallback (Requirement 4)."""
    import numpy as np
    from scipy.stats import fisher_exact, MonteCarloMethod

    demo_vars = {
        "Age Group": "age_label",
        "Education Level": "education_label",
        "Occupation": "occupation_label",
        "Marital Status": "marital_label",
        "Monthly Income": "income_label",
    }
    outcomes = {
        "Knowledge of Menopause Level": "know_meno_category",
        "Knowledge of HRT Level": "know_hrt_category",
        "Attitude towards Menopause Level": "att_meno_category",
        "Attitude towards HRT Level": "att_hrt_category",
        "Current HRT Use": "hrt_current",
    }

    results = []
    # Seed rng for reproducible Monte Carlo permutations
    rng = np.random.default_rng(42)

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
            detailed_ct = pd.crosstab(
                subset[demo_col],
                subset[outcome_col],
                margins=True,
                margins_name="Total",
            )
            ct_dict = detailed_ct.to_dict()

            if contingency.shape[0] < 2 or contingency.shape[1] < 2:
                results.append(
                    {
                        "demographic": demo_name,
                        "outcome": outcome_name,
                        "chi2": None,
                        "df": None,
                        "p_value": None,
                        "fisher_p_value": None,
                        "significant": False,
                        "note": "Insufficient categories",
                        "crosstab": ct_dict,
                    }
                )
                continue

            try:
                chi2, p, dof, expected = stats.chi2_contingency(contingency)
                note = ""
                fisher_p = None

                # Check expected frequencies logic
                val_min = expected.min()
                pct_lt_5 = (expected < 5).sum() / expected.size

                if val_min < 1 or pct_lt_5 > 0.2:
                    note = f"Min exp={val_min:.1f}, {(pct_lt_5 * 100):.0f}%<5. Reverted to Exact Test."

                    try:
                        if contingency.shape == (2, 2):
                            res = fisher_exact(contingency)
                            fisher_p = res.pvalue
                        else:
                            method = MonteCarloMethod(n_resamples=9999, rng=rng)
                            res = fisher_exact(contingency, method=method)
                            fisher_p = res.pvalue
                    except Exception as fe:
                        note += f" (Fisher failed: {str(fe)})"

                # Determine significance based on Fisher if present, otherwise Chi2
                final_p = fisher_p if fisher_p is not None else p
                is_sig = bool(final_p < 0.05) if final_p is not None else False

                results.append(
                    {
                        "demographic": demo_name,
                        "outcome": outcome_name,
                        "chi2": round(chi2, 3),
                        "df": int(dof),
                        "p_value": round(p, 4),
                        "fisher_p_value": round(fisher_p, 4)
                        if fisher_p is not None
                        else None,
                        "significant": is_sig,
                        "note": note,
                        "crosstab": ct_dict,
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
                        "fisher_p_value": None,
                        "significant": False,
                        "note": f"Error: {str(e)}",
                        "crosstab": {"error": str(e)},
                    }
                )

    return results


def run_logistic_regression(df: pd.DataFrame) -> list[dict]:
    """Run binary logistic regression for each outcome against all sociodemographic predictors.

    Matches the same demographic×outcome pairs used in the Chi-Square section.
    Uses statsmodels Logit with dummy-encoded (drop-first) categorical predictors.
    Returns a list of dicts with coefficients, odds ratios, 95% CIs, and p-values.
    """
    demo_vars = {
        "Age Group": "age_label",
        "Education Level": "education_label",
        "Occupation": "occupation_label",
        "Marital Status": "marital_label",
        "Monthly Income": "income_label",
    }
    outcomes = {
        "Knowledge of Menopause Level": "know_meno_category",
        "Knowledge of HRT Level": "know_hrt_category",
        "Attitude towards Menopause Level": "att_meno_category",
        "Attitude towards HRT Level": "att_hrt_category",
        "Current HRT Use": "hrt_current",
    }
    # Map categorical labels to binary 0/1
    positive_labels = {"Good", "Positive", "Yes"}

    results = []

    for outcome_name, outcome_col in outcomes.items():
        if outcome_col not in df.columns:
            continue

        # Encode the dependent variable as binary 0/1
        y_series = df[outcome_col].map(
            lambda x: 1 if x in positive_labels else (0 if pd.notna(x) else np.nan)
        )

        # Build the combined predictor matrix
        predictor_frames = []
        for demo_name, demo_col in demo_vars.items():
            if demo_col not in df.columns:
                continue
            predictor_frames.append(df[[demo_col]].copy())

        if not predictor_frames:
            continue

        X_raw = pd.concat(predictor_frames, axis=1)

        # Combine X and y, drop rows where either is NaN
        combined = pd.concat([X_raw, y_series.rename("_y_")], axis=1).dropna()
        if len(combined) < 20:
            results.append(
                {
                    "outcome": outcome_name,
                    "predictors": [],
                    "note": f"Insufficient data (n={len(combined)})",
                }
            )
            continue

        y = combined["_y_"].astype(int)
        X_cats = combined.drop(columns=["_y_"])

        # One-hot encode with drop_first for reference categories
        X_dummies = pd.get_dummies(X_cats, drop_first=True, dtype=float)

        # Drop zero-variance columns (causes singular matrix)
        X_dummies = X_dummies.loc[:, X_dummies.nunique() > 1]

        # Add constant (intercept)
        X_dummies = sm.add_constant(X_dummies, has_constant="add")

        try:
            model = sm.Logit(y, X_dummies)
            result = model.fit(disp=0, maxiter=300, method="bfgs")

            conf = result.conf_int()
            predictors = []
            for var_name in X_dummies.columns:
                if var_name == "const":
                    continue

                # Parse variable name: "education_label_Tertiary" -> ("Education Level", "Tertiary")
                demo_col_name = None
                category = var_name
                for d_name, d_col in demo_vars.items():
                    if var_name.startswith(d_col + "_"):
                        demo_col_name = d_name
                        category = var_name[len(d_col) + 1 :]
                        break

                coef = result.params[var_name]
                p_val = result.pvalues[var_name]
                ci_lower = conf.loc[var_name, 0]
                ci_upper = conf.loc[var_name, 1]
                odds_ratio = np.exp(coef)
                or_ci_lower = np.exp(ci_lower)
                or_ci_upper = np.exp(ci_upper)

                def safe_float(v, decimals=4):
                    """Sanitize float for JSON: replace inf/NaN with None."""
                    f = float(v)
                    if not np.isfinite(f):
                        return None
                    return round(f, decimals)

                predictors.append(
                    {
                        "variable": demo_col_name or var_name,
                        "category": category,
                        "coef": safe_float(coef),
                        "odds_ratio": safe_float(odds_ratio),
                        "ci_lower": safe_float(or_ci_lower),
                        "ci_upper": safe_float(or_ci_upper),
                        "p_value": safe_float(p_val),
                        "significant": bool(p_val < 0.05)
                        if np.isfinite(float(p_val))
                        else False,
                    }
                )

            results.append(
                {
                    "outcome": outcome_name,
                    "predictors": predictors,
                    "n": int(len(y)),
                    "pseudo_r2": safe_float(result.prsquared),
                    "note": "",
                }
            )
        except Exception as e:
            results.append(
                {
                    "outcome": outcome_name,
                    "predictors": [],
                    "note": f"Model failed: {str(e)}",
                }
            )

    return results


def build_summary(
    df: pd.DataFrame,
    n_total: int,
    n_excluded: int,
    chi_results: list[dict],
    logistic_results: list[dict] | None = None,
) -> dict:
    """Build JSON-serializable summary dict for the frontend."""
    n = len(df)

    # Sociodemographics
    socio = {}
    for key, display_name in SOCIO_DISPLAY_NAMES.items():
        label_col = f"{key}_label"
        if label_col in df.columns:
            counts = df[label_col].dropna().value_counts()
            socio[display_name] = {str(k): int(v) for k, v in counts.items()}

    if "menopausal_status_label" in df.columns:
        counts = df["menopausal_status_label"].dropna().value_counts()
        if len(counts) > 0:
            socio["Menopausal Status"] = {str(k): int(v) for k, v in counts.items()}

    # Helper function to generate stats dict for sub-constructs
    def get_construct_stats(df_data, score_col, cat_col, is_knowledge=True):
        subset = df_data[df_data[score_col].notna()]
        if len(subset) == 0:
            if is_knowledge:
                return {"good_n": 0, "good_pct": 0, "poor_n": 0, "poor_pct": 0}
            else:
                return {
                    "positive_n": 0,
                    "positive_pct": 0,
                    "negative_n": 0,
                    "negative_pct": 0,
                }

        cats = ["Good", "Poor"] if is_knowledge else ["Positive", "Negative"]
        n1 = int((subset[cat_col] == cats[0]).sum())
        n2 = int((subset[cat_col] == cats[1]).sum())

        if is_knowledge:
            return {
                "good_n": n1,
                "good_pct": round(float(n1 / len(subset) * 100), 1),
                "poor_n": n2,
                "poor_pct": round(float(n2 / len(subset) * 100), 1),
            }
        else:
            return {
                "positive_n": n1,
                "positive_pct": round(float(n1 / len(subset) * 100), 1),
                "negative_n": n2,
                "negative_pct": round(float(n2 / len(subset) * 100), 1),
            }

    constructs = {
        "knowledge_menopause": get_construct_stats(
            df, "know_meno_score", "know_meno_category", True
        ),
        "knowledge_hrt": get_construct_stats(
            df, "know_hrt_score", "know_hrt_category", True
        ),
        "attitude_menopause": get_construct_stats(
            df, "att_meno_score", "att_meno_category", False
        ),
        "attitude_hrt": get_construct_stats(
            df, "att_hrt_score", "att_hrt_category", False
        ),
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
        "constructs": constructs,
        "hrt_practices": hrt_practice,
        "chi_square": chi_results,
        "logistic_regression": logistic_results or [],
    }


def descriptive_stats(df):
    """
    Generate publication-ready descriptive statistics tables:

    Table 1: Sociodemographic characteristics
    Table 2: Knowledge of Menopause
    Table 3: Knowledge of HRT
    Table 4: Attitude towards Menopause
    Table 5: Attitude towards HRT
    Table 6: HRT practice patterns

    Returns: dict of DataFrames (table_name → DataFrame)
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
            if float(n) > 0:
                pct = n / total * 100
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

    # Generic function to build construct tables
    def build_construct_table(
        score_col, cat_col, total_items, is_knowledge=True, title=""
    ):
        data = df[df[score_col].notna()]
        if len(data) == 0:
            return pd.DataFrame()

        mean_score = data[score_col].mean()
        std_score = data[score_col].std()

        c_rows = []
        c_rows.append({"Measure": "Total respondents scored", "Value": f"{len(data)}"})
        c_rows.append(
            {
                "Measure": "Mean score ± SD",
                "Value": f"{mean_score:.1f} ± {std_score:.1f}",
            }
        )
        c_rows.append({"Measure": "Items evaluated", "Value": f"{total_items}"})

        if not is_knowledge:
            c_rows.append(
                {
                    "Measure": "Score range",
                    "Value": f"{data[score_col].min():.0f} - {data[score_col].max():.0f}",
                }
            )

        c_rows.append(
            {"Measure": "Categorization cutoff (mean)", "Value": f"{mean_score:.1f}"}
        )
        c_rows.append({"Measure": "---", "Value": "---"})

        cats = ["Good", "Poor"] if is_knowledge else ["Positive", "Negative"]
        for cat in cats:
            n = (data[cat_col] == cat).sum()
            pct = n / len(data) * 100 if len(data) > 0 else 0
            c_rows.append({"Measure": f"{cat} (n, %)", "Value": f"{n} ({pct:.1f}%)"})

        return pd.DataFrame(c_rows)

    idx_know = KNOWLEDGE_COLS.index("_59_HRT_can_be_taken_r_used_in_the_vagina")  # noqa: F841
    idx_att = ATTITUDE_COLS.index("_87_I_have_a_full_un_imenopausal_syndrome")

    tables["Table 2 - Know_Menopause"] = build_construct_table(
        "know_meno_score", "know_meno_category", 45, True
    )
    tables["Table 3 - Know_HRT"] = build_construct_table(
        "know_hrt_score", "know_hrt_category", 16, True
    )
    tables["Table 4 - Att_Menopause"] = build_construct_table(
        "att_meno_score", "att_meno_category", len(ATTITUDE_COLS[:idx_att]), False
    )
    tables["Table 5 - Att_HRT"] = build_construct_table(
        "att_hrt_score", "att_hrt_category", len(ATTITUDE_COLS[idx_att:]), False
    )

    # ── Table 6: HRT Practice Patterns ───────────────────────────────────
    practice_rows = []

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

    # Add any genitourinary symptom
    valid_symptom_cols = [c for c in SYMPTOM_COLS.values() if c in df.columns]
    if valid_symptom_cols:
        any_symp_n = (df[valid_symptom_cols] == 1).any(axis=1).sum()
        total_cons = len(df)
        any_symp_pct = any_symp_n / total_cons * 100 if total_cons > 0 else 0
        practice_rows.append(
            {
                "Variable": "",
                "Category": "Any genitourinary symptom reported",
                "Frequency (n)": f"{any_symp_n}/{total_cons}",
                "Percentage (%)": f"{any_symp_pct:.1f}",
            }
        )

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

    tables["Table 6 - HRT Practices"] = pd.DataFrame(practice_rows)

    return tables


def build_excel_files(
    df: pd.DataFrame,
    chi_results: list[dict],
    logistic_results: list[dict] | None = None,
) -> tuple[io.BytesIO, io.BytesIO]:
    """Write results and cleaned data to in-memory Excel buffers."""
    results_buf = io.BytesIO()

    chi_rows = []
    for test in chi_results:
        demo_name = test.get("demographic", "")
        outcome_name = test.get("outcome", "")
        chi2 = test.get("chi2", "")
        dof = test.get("df", "")
        p_val = test.get("p_value", "")
        fisher_p = test.get("fisher_p_value", "")
        sig = "Yes" if test.get("significant") else "No"
        note = test.get("note", "")
        ct = test.get("crosstab", {})

        if not ct or "error" in ct:
            chi_rows.append(
                {
                    "Demographic Variable": demo_name,
                    "Category": "Error / Insufficient data",
                    "Outcome Variable": outcome_name,
                    "Result 1": "",
                    "Result 2": "",
                    "Chi-Square (χ²)": chi2,
                    "df": dof,
                    "Chi2 p-value": p_val,
                    "Fisher's Exact p-value": fisher_p,
                    "Significance": sig,
                    "Note": note,
                }
            )
            continue

        outcome_cats = [k for k in ct.keys() if k != "Total"]
        if not outcome_cats:
            continue

        demo_cats = [k for k in ct[outcome_cats[0]].keys() if k != "Total"]
        demo_cats.append("Total")

        for i, d_cat in enumerate(demo_cats):
            row = {}
            if i == 0:
                row["Demographic Variable"] = demo_name
                row["Outcome Variable"] = outcome_name
                row["Chi-Square (χ²)"] = chi2
                row["df"] = dof
                row["Chi2 p-value"] = p_val
                row["Fisher's Exact p-value"] = fisher_p if fisher_p is not None else ""
                row["Significance"] = sig
                row["Note"] = note
            else:
                row["Demographic Variable"] = ""
                row["Outcome Variable"] = ""
                row["Chi-Square (χ²)"] = ""
                row["df"] = ""
                row["Chi2 p-value"] = ""
                row["Fisher's Exact p-value"] = ""
                row["Significance"] = ""
                row["Note"] = ""

            row["Category"] = d_cat

            for j, o_cat in enumerate(outcome_cats):
                col_name = f"{o_cat} n(%)"
                val = ct[o_cat].get(d_cat, 0)
                tot = ct["Total"].get(d_cat, 0)
                pct = (val / tot * 100) if tot > 0 else 0
                row[col_name] = f"{val} ({pct:.1f}%)"

            chi_rows.append(row)

    chi_df = pd.DataFrame(chi_rows)

    if not chi_df.empty:
        base_cols = ["Demographic Variable", "Category", "Outcome Variable"]
        stats_cols = [
            "Chi-Square (χ²)",
            "df",
            "Chi2 p-value",
            "Fisher's Exact p-value",
            "Significance",
            "Note",
        ]
        dynamic_cols = [c for c in chi_df.columns if c not in base_cols + stats_cols]
        chi_df = chi_df[base_cols + dynamic_cols + stats_cols]

    tables = descriptive_stats(df)

    with pd.ExcelWriter(results_buf, engine="openpyxl") as writer:
        for sheet_name, table_df in tables.items():
            safe_name = sheet_name[:31]
            table_df.to_excel(writer, sheet_name=safe_name, index=False)

        chi_df.to_excel(writer, sheet_name="Table 7 - Chi-Square", index=False)

        score_cols = [
            "know_meno_score",
            "know_hrt_score",
            "att_meno_score",
            "att_hrt_score",
            "hrt_practice",
            "hrt_current",
            "hrt_ever",
        ]
        label_cols = [c for c in df.columns if c.endswith("_label")]
        export_cols = label_cols + [c for c in score_cols if c in df.columns]
        df[export_cols].to_excel(writer, sheet_name="Scores & Labels", index=False)

        if "cronbach" in df.attrs:
            cron_data = []
            for construct_name, alpha_val in df.attrs["cronbach"].items():
                cron_data.append(
                    {
                        "Psychometric Construct": construct_name,
                        "Cronbach's Alpha (α)": round(alpha_val, 3),
                        "Internal Consistency": "Excellent"
                        if alpha_val >= 0.9
                        else "Good"
                        if alpha_val >= 0.8
                        else "Acceptable"
                        if alpha_val >= 0.7
                        else "Questionable"
                        if alpha_val >= 0.6
                        else "Poor"
                        if alpha_val >= 0.5
                        else "Unacceptable",
                    }
                )
            pd.DataFrame(cron_data).to_excel(
                writer, sheet_name="Table 8 - Reliability (Alpha)", index=False
            )

        if logistic_results:
            lr_rows = []
            for model in logistic_results:
                outcome = model.get("outcome", "")
                n_obs = model.get("n", "")
                pseudo_r2 = model.get("pseudo_r2", "")
                note = model.get("note", "")
                predictors = model.get("predictors", [])

                if not predictors:
                    lr_rows.append(
                        {
                            "Outcome Variable": outcome,
                            "Demographic Factor": note or "No predictors",
                            "Category (vs Reference)": "",
                            "Coefficient (β)": "",
                            "Odds Ratio (OR)": "",
                            "95% CI Lower": "",
                            "95% CI Upper": "",
                            "p-value": "",
                            "Significance": "",
                            "n": n_obs,
                            "Pseudo R²": pseudo_r2,
                        }
                    )
                    continue

                for i, pred in enumerate(predictors):
                    row = {
                        "Outcome Variable": outcome if i == 0 else "",
                        "Demographic Factor": pred.get("variable", ""),
                        "Category (vs Reference)": pred.get("category", ""),
                        "Coefficient (β)": pred.get("coef", ""),
                        "Odds Ratio (OR)": pred.get("odds_ratio", ""),
                        "95% CI Lower": pred.get("ci_lower", ""),
                        "95% CI Upper": pred.get("ci_upper", ""),
                        "p-value": pred.get("p_value", ""),
                        "Significance": "Yes" if pred.get("significant") else "No",
                        "n": n_obs if i == 0 else "",
                        "Pseudo R²": pseudo_r2 if i == 0 else "",
                    }
                    lr_rows.append(row)

            if lr_rows:
                pd.DataFrame(lr_rows).to_excel(
                    writer, sheet_name="Table 9 - Logistic Regress", index=False
                )

    results_buf.seek(0)

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
    df = compute_split_scores(df)
    df = categorize_variables(df)

    # Step 5: Chi-square tests
    chi_results = run_chi_square(df)

    # Step 6: Logistic regression
    logistic_results = run_logistic_regression(df)

    # Step 7: Build outputs
    summary = build_summary(df, n_total, n_excluded, chi_results, logistic_results)
    results_buf, cleaned_buf = build_excel_files(df, chi_results, logistic_results)

    return {
        "summary": summary,
        "results_xlsx": results_buf,
        "cleaned_xlsx": cleaned_buf,
    }
