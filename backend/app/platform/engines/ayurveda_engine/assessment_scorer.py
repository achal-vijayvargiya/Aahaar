"""
Ayurvedic Assessment Scorer.

Deterministic scoring system for Prakriti, Vikriti, Agni, and Ama assessment.
Based on structured questionnaire responses.

Uses knowledge base (KB) files for:
- Prakriti scoring rules (physical constitution indicators)
- Vikriti scoring rules (current imbalance indicators)
- Agni classification rules
- Ama indicator scoring
- Dosha determination thresholds
- Vikriti severity thresholds
- Ama level thresholds
"""
from typing import Dict, List, Any, Optional
from enum import Enum
from .kb_ayurveda import (
    get_prakriti_scoring_rule,
    get_all_prakriti_scoring_rules,
    get_vikriti_scoring_rule,
    get_all_vikriti_scoring_rules,
    get_agni_classification_rule,
    get_all_agni_classification_rules,
    get_ama_indicator,
    get_all_ama_indicators,
    get_dosha_determination_rule,
    get_vikriti_severity_rule,
    get_ama_level_rule,
)


class Dosha(str, Enum):
    """Dosha types."""
    VATA = "Vata"
    PITTA = "Pitta"
    KAPHA = "Kapha"


class AgniType(str, Enum):
    """Agni (digestive fire) types."""
    SAMA = "Sama"  # Balanced
    VISHAMA = "Vishama"  # Irregular
    TIKSHNA = "Tikshna"  # Sharp/Overactive
    MANDA = "Manda"  # Slow/Weak


class AmaLevel(str, Enum):
    """Ama (toxin) levels."""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"


# ============================================================================
# SCORING TABLES (now loaded from KB)
# ============================================================================
# All scoring tables have been moved to KB JSON files.
# Use kb_ayurveda module functions to access them.

# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def calculate_prakriti_scores(responses: Dict[str, Any]) -> Dict[str, int]:
    """
    Calculate Prakriti (constitution) scores from questionnaire responses (from KB).
    
    Prakriti is determined by physical constitution indicators:
    - Body structure, weight pattern, skin, hair, sweating
    - Mental traits (thinking style, memory)
    - Sleep patterns (long-term)
    
    Args:
        responses: Questionnaire responses dictionary
        
    Returns:
        Dictionary with dosha scores: {"Vata": score, "Pitta": score, "Kapha": score}
    """
    scores = {Dosha.VATA: 0, Dosha.PITTA: 0, Dosha.KAPHA: 0}
    
    # Load all Prakriti scoring rules from KB
    prakriti_rules = get_all_prakriti_scoring_rules()
    
    for rule in prakriti_rules:
        question_id = rule.get("question_id")
        if not question_id:
            continue
        
        answer = responses.get(question_id)
        if answer is None or answer == "":
            continue
        
        # Handle both string answers (A/B/C) and array answers (for checkboxes)
        answer_value = None
        if isinstance(answer, list):
            # For checkbox questions, check if "Yes" is in the list
            if "Yes" in answer:
                answer_value = "Yes"
            else:
                continue
        else:
            answer_value = str(answer).strip()
        
        # Get answer options from KB
        answer_options = rule.get("answer_options", {})
        if answer_value and answer_value in answer_options:
            dosha_weights = answer_options[answer_value].get("dosha_weights", {})
            for dosha_name, weight in dosha_weights.items():
                # Map dosha name to enum
                if dosha_name == "Vata":
                    scores[Dosha.VATA] += weight
                elif dosha_name == "Pitta":
                    scores[Dosha.PITTA] += weight
                elif dosha_name == "Kapha":
                    scores[Dosha.KAPHA] += weight
    
    return {dosha.value: score for dosha, score in scores.items()}


def calculate_vikriti_scores(responses: Dict[str, Any], prakriti_scores: Dict[str, int]) -> Dict[str, Any]:
    """
    Calculate Vikriti (current imbalance) scores and determine imbalanced doshas (from KB).
    
    Vikriti is determined by:
    - Digestive discomfort, bowel issues
    - Current complaints
    - Energy patterns, stress response
    - Seasonal aggravation
    
    Args:
        responses: Questionnaire responses dictionary
        prakriti_scores: Baseline Prakriti scores for comparison
        
    Returns:
        Dictionary with:
        - scores: Vikriti scores for each dosha
        - imbalanced_doshas: List of imbalanced dosha names
        - severity: "mild", "moderate", or "severe"
    """
    vikriti_scores_dict = {Dosha.VATA: 0, Dosha.PITTA: 0, Dosha.KAPHA: 0}
    
    # Load all Vikriti scoring rules from KB
    vikriti_rules = get_all_vikriti_scoring_rules()
    
    for rule in vikriti_rules:
        question_id = rule.get("question_id")
        if not question_id:
            continue
        
        answer = responses.get(question_id)
        if answer is None or answer == "":
            continue
        
        # Handle both string answers (A/B/C) and array answers
        answer_value = None
        if isinstance(answer, list):
            if "Yes" in answer:
                answer_value = "Yes"
            else:
                continue
        else:
            answer_value = str(answer).strip()
        
        # Get answer options from KB
        answer_options = rule.get("answer_options", {})
        if answer_value and answer_value in answer_options:
            dosha_weights = answer_options[answer_value].get("dosha_weights", {})
            for dosha_name, weight in dosha_weights.items():
                # Map dosha name to enum
                if dosha_name == "Vata":
                    vikriti_scores_dict[Dosha.VATA] += weight
                elif dosha_name == "Pitta":
                    vikriti_scores_dict[Dosha.PITTA] += weight
                elif dosha_name == "Kapha":
                    vikriti_scores_dict[Dosha.KAPHA] += weight
    
    vikriti_scores = {dosha.value: score for dosha, score in vikriti_scores_dict.items()}
    
    # Calculate total scores for comparison
    total_prakriti = sum(prakriti_scores.values()) or 1
    total_vikriti = sum(vikriti_scores.values()) or 1
    
    # Normalize to percentages for comparison
    prakriti_percentages = {
        dosha: (score / total_prakriti) * 100 
        for dosha, score in prakriti_scores.items()
    }
    vikriti_percentages = {
        dosha: (score / total_vikriti) * 100 
        for dosha, score in vikriti_scores.items()
    }
    
    # Load Vikriti severity thresholds from KB
    severity_rule = get_vikriti_severity_rule()
    thresholds = severity_rule.get("thresholds", {}) if severity_rule else {}
    
    # Find imbalanced doshas (using KB thresholds)
    imbalanced_doshas = []
    max_excess = 0
    
    mild_threshold = thresholds.get("mild", {}).get("min_excess", 15)
    
    for dosha in [Dosha.VATA, Dosha.PITTA, Dosha.KAPHA]:
        dosha_str = dosha.value
        prakriti_pct = prakriti_percentages.get(dosha_str, 0)
        vikriti_pct = vikriti_percentages.get(dosha_str, 0)
        
        excess = vikriti_pct - prakriti_pct
        if excess >= mild_threshold:
            imbalanced_doshas.append(dosha_str)
            max_excess = max(max_excess, excess)
    
    # Determine severity using KB thresholds
    severe_threshold = thresholds.get("severe", {}).get("min_excess", 30)
    moderate_threshold = thresholds.get("moderate", {}).get("min_excess", 20)
    
    if max_excess >= severe_threshold:
        severity = "severe"
    elif max_excess >= moderate_threshold:
        severity = "moderate"
    elif max_excess >= mild_threshold:
        severity = "mild"
    else:
        severity = "none"
    
    return {
        "scores": vikriti_scores,
        "imbalanced_doshas": imbalanced_doshas,
        "severity": severity,
    }


def determine_agni_type(responses: Dict[str, Any]) -> str:
    """
    Determine Agni (digestive fire) type from questionnaire responses (from KB).
    
    Agni types:
    - Sama: Balanced digestion
    - Vishama: Irregular appetite (Vata)
    - Tikshna: Strong/sharp hunger (Pitta)
    - Manda: Slow/weak digestion (Kapha)
    
    Args:
        responses: Questionnaire responses dictionary
        
    Returns:
        Agni type string
    """
    # Load all Agni classification rules from KB
    agni_rules = get_all_agni_classification_rules()
    
    agni_votes = {
        AgniType.VISHAMA: 0,
        AgniType.TIKSHNA: 0,
        AgniType.MANDA: 0,
        AgniType.SAMA: 0,
    }
    
    fallback_agni = AgniType.SAMA.value
    
    for rule in agni_rules:
        question_id = rule.get("question_id")
        if not question_id:
            continue
        
        answer = responses.get(question_id)
        if answer is None or answer == "":
            continue
        
        # Get fallback Agni from rule
        fallback_agni = rule.get("fallback_agni", AgniType.SAMA.value)
        
        # Get agni mapping from KB
        agni_mapping = rule.get("agni_mapping", {})
        answer_value = str(answer).strip()
        
        if answer_value in agni_mapping:
            agni_info = agni_mapping[answer_value]
            agni_type_str = agni_info.get("agni_type")
            weight = agni_info.get("weight", 1)
            
            # Map agni type string to enum
            if agni_type_str == "Vishama":
                agni_votes[AgniType.VISHAMA] += weight
            elif agni_type_str == "Tikshna":
                agni_votes[AgniType.TIKSHNA] += weight
            elif agni_type_str == "Manda":
                agni_votes[AgniType.MANDA] += weight
    
    # If no strong indicators, default to Sama (or fallback from KB)
    max_votes = max(agni_votes.values())
    if max_votes == 0:
        return fallback_agni
    
    # Return the Agni type with most votes
    for agni_type, votes in agni_votes.items():
        if votes == max_votes:
            return agni_type.value
    
    return fallback_agni


def determine_ama_level(responses: Dict[str, Any]) -> str:
    """
    Determine Ama (toxin) level from questionnaire responses (from KB).
    
    Ama levels:
    - None: No indicators
    - Mild: 1-2 indicators
    - Moderate: 3-4 indicators
    - High: 5+ indicators
    
    Args:
        responses: Questionnaire responses dictionary
        
    Returns:
        Ama level string
    """
    ama_score = 0
    
    # Load all Ama indicators from KB
    ama_indicators = get_all_ama_indicators()
    
    for indicator in ama_indicators:
        indicator_id = indicator.get("indicator_id")
        if not indicator_id:
            continue
        
        answer = responses.get(indicator_id)
        if answer is None or answer == "":
            continue
        
        # Get scoring from KB
        scoring = indicator.get("scoring", {})
        
        # Handle both string answers and array answers
        answer_value = None
        if isinstance(answer, list):
            if "Yes" in answer:
                answer_value = "Yes"
            else:
                continue
        else:
            answer_value = str(answer).strip()
        
        if answer_value and answer_value in scoring:
            ama_score += scoring[answer_value].get("ama_score", 0)
    
    # Load Ama level thresholds from KB
    ama_rule = get_ama_level_rule()
    thresholds = ama_rule.get("thresholds", {}) if ama_rule else {}
    
    # Determine level using KB thresholds
    high_threshold = thresholds.get("high", {}).get("min_score", 5)
    moderate_threshold = thresholds.get("moderate", {}).get("min_score", 3)
    mild_threshold = thresholds.get("mild", {}).get("min_score", 1)
    
    if ama_score >= high_threshold:
        return AmaLevel.HIGH.value
    elif ama_score >= moderate_threshold:
        return AmaLevel.MODERATE.value
    elif ama_score >= mild_threshold:
        return AmaLevel.MILD.value
    else:
        return AmaLevel.NONE.value


def determine_dosha_primary_secondary(prakriti_scores: Dict[str, int]) -> Dict[str, Optional[str]]:
    """
    Determine primary and secondary dosha from Prakriti scores (from KB).
    
    Rules (from KB):
    - ≥40% → Dominant dosha
    - 25–39% → Secondary dosha
    
    Args:
        prakriti_scores: Prakriti scores dictionary
        
    Returns:
        Dictionary with "primary" and "secondary" dosha names
    """
    total = sum(prakriti_scores.values())
    if total == 0:
        return {"primary": None, "secondary": None}
    
    # Load dosha determination thresholds from KB
    determination_rule = get_dosha_determination_rule()
    thresholds = determination_rule.get("thresholds", {}) if determination_rule else {}
    
    primary_threshold = thresholds.get("primary_dosha", {}).get("min_percentage", 40)
    secondary_min = thresholds.get("secondary_dosha", {}).get("min_percentage", 25)
    secondary_max = thresholds.get("secondary_dosha", {}).get("max_percentage", 39)
    
    # Calculate percentages
    percentages = {dosha: (score / total) * 100 for dosha, score in prakriti_scores.items()}
    
    # Sort by percentage
    sorted_doshas = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    
    primary = None
    secondary = None
    
    if sorted_doshas[0][1] >= primary_threshold:
        primary = sorted_doshas[0][0]
    
    if len(sorted_doshas) > 1 and secondary_min <= sorted_doshas[1][1] <= secondary_max:
        secondary = sorted_doshas[1][0]
    
    return {"primary": primary, "secondary": secondary}

