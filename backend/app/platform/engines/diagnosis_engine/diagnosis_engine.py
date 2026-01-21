"""
Diagnosis Engine.
Converts raw data into medical conditions and nutrition diagnoses.
Uses knowledge base JSON file for dynamic diagnosis evaluation.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import UUID

from app.platform.core.context import AssessmentContext, DiagnosisContext


class DiagnosisEngine:
    """
    Diagnosis Engine.
    
    Responsibility:
    - Convert raw assessment data into structured medical conditions
    - Rule-based processing (no AI generation)
    - Explainable decisions with evidence tracking
    - Dynamic evaluation using knowledge base
    
    Inputs:
    - Labs data
    - Anthropometry (height, weight, BMI, etc.)
    - Medical history
    
    Outputs:
    - Medical conditions list (from KB JSON file)
    - Nutrition diagnoses list (currently empty - disabled)
    - Evidence for each diagnosis
    
    Rules:
    - Rule-based only, no probabilistic logic
    - All decisions must reference knowledge base IDs
    - No AI-generated medical rules
    - All thresholds and conditions loaded from KB JSON file
    - Nutrition diagnoses disabled (requires diet history data not available from users)
    
    Note:
        MNT rules are applied based on medical conditions only. The system works
        end-to-end without nutrition diagnoses, as MNT rules can be triggered by
        medical conditions directly (e.g., type_2_diabetes → carb restriction).
    """
    
    def __init__(self):
        """Initialize diagnosis engine and load knowledge base."""
        self.medical_kb = self._load_medical_kb()
    
    def _load_medical_kb(self) -> List[Dict[str, Any]]:
        """
        Load medical conditions knowledge base from JSON file.
        
        Returns:
            List of medical condition definitions from KB
        """
        # Path to KB JSON file
        kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "medical" / "medical_conditions_kb_complete.json"
        
        try:
            with open(kb_path, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
            
            # Filter only active conditions
            active_conditions = [
                condition for condition in kb_data 
                if condition.get("status") == "active"
            ]
            
            return active_conditions
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Medical conditions KB file not found at: {kb_path}\n"
                "Please ensure the knowledge base file exists."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in medical conditions KB: {e}")
    
    def process_assessment(self, assessment_context: AssessmentContext) -> DiagnosisContext:
        """
        Process assessment and generate diagnoses.
        
        Args:
            assessment_context: Assessment context with assessment snapshot
            
        Returns:
            DiagnosisContext with medical conditions and nutrition diagnoses.
            Note: nutrition_diagnoses will be an empty list (disabled).
            
        Note:
            This method applies rule-based logic to identify:
            - Medical conditions from labs and clinical data (from KB JSON file)
            - Nutrition diagnoses: Currently disabled, returns empty list
            
            All diagnoses must reference knowledge base IDs.
            MNT rules are applied based on medical conditions only.
        """
        if not assessment_context.assessment_id:
            raise ValueError("assessment_id is required in AssessmentContext")
        
        # Extract data from assessment_snapshot
        snapshot = assessment_context.assessment_snapshot or {}
        
        # Extract structured data sections
        clinical_data = snapshot.get("clinical_data", {})
        labs = clinical_data.get("labs", {}) if isinstance(clinical_data, dict) else {}
        vitals = clinical_data.get("vitals", {}) if isinstance(clinical_data, dict) else {}
        
        client_context = snapshot.get("client_context", {})
        anthropometry = {
            "bmi": client_context.get("bmi"),
            "weight_kg": client_context.get("weight_kg"),
            "height_cm": client_context.get("height_cm"),
            "bp_systolic": vitals.get("bp_systolic") if isinstance(vitals, dict) else None,
            "bp_diastolic": vitals.get("bp_diastolic") if isinstance(vitals, dict) else None,
        }
        
        medical_history = clinical_data.get("medical_history", {}) if isinstance(clinical_data, dict) else {}
        
        diet_data = snapshot.get("diet_data", {})
        diet_history = diet_data.get("diet_history", {}) if isinstance(diet_data, dict) else {}
        
        # Merge labs from different sources
        if isinstance(labs, dict):
            # Labs might be nested or flat
            merged_labs = labs.copy()
        else:
            merged_labs = {}
        
        # Also check if labs are directly in snapshot
        if "labs" in snapshot and isinstance(snapshot["labs"], dict):
            merged_labs.update(snapshot["labs"])
        
        # Identify medical conditions (pass client_context for eligibility validation)
        medical_conditions = self.identify_medical_conditions(
            labs=merged_labs if merged_labs else None,
            anthropometry=anthropometry if any(anthropometry.values()) else None,
            medical_history=medical_history if medical_history else None,
            client_context=client_context  # Pass for eligibility checks
        )
        
        # Identify nutrition diagnoses
        nutrition_diagnoses = self.identify_nutrition_diagnoses(
            labs=merged_labs if merged_labs else None,
            anthropometry=anthropometry if any(anthropometry.values()) else None,
            diet_history=diet_history if diet_history else None
        )
        
        # Create and return diagnosis context
        return DiagnosisContext(
            assessment_id=assessment_context.assessment_id,
            medical_conditions=medical_conditions,
            nutrition_diagnoses=nutrition_diagnoses
        )
    
    def identify_medical_conditions(
        self,
        labs: Optional[Dict[str, Any]] = None,
        anthropometry: Optional[Dict[str, Any]] = None,
        medical_history: Optional[Dict[str, Any]] = None,
        client_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify medical conditions from input data using knowledge base.
        
        Args:
            labs: Laboratory test results
            anthropometry: Height, weight, BMI, body composition data
            medical_history: Historical medical information
            client_context: Client context (age, gender, reproductive_context) for eligibility validation
            
        Returns:
            List of medical conditions, each containing:
            - diagnosis_id: KB reference ID
            - severity_score: Numeric severity indicator (0-10)
            - evidence: Supporting evidence data
            
        Note:
            Rule-based identification only. No AI generation.
            All conditions evaluated dynamically from knowledge base.
            Eligibility constraints are checked before lab threshold matching.
        """
        conditions = []
        
        if not labs:
            labs = {}
        if not anthropometry:
            anthropometry = {}
        if not medical_history:
            medical_history = {}
        if not client_context:
            client_context = {}
        
        # Prepare unified data dictionary for easier lookup
        data_dict = self._prepare_data_dict(labs, anthropometry, medical_history)
        
        # Add age from client_context to data_dict for hierarchical rules
        if client_context.get("age") is not None:
            data_dict["age"] = client_context.get("age")
        
        # Evaluate each condition in the knowledge base
        for condition_kb in self.medical_kb:
            condition_id = condition_kb.get("condition_id")
            if not condition_id:
                continue
            
            # Check if condition matches based on KB thresholds (with eligibility validation)
            match_result = self._evaluate_condition(condition_kb, data_dict, client_context)
            
            if match_result:
                conditions.append({
                    "diagnosis_id": condition_id,
                    "severity_score": match_result["severity_score"],
                    "evidence": match_result["evidence"]
                })
        
        # Sort by severity (highest first) and remove duplicates
        # (in case multiple thresholds match the same condition)
        conditions = self._deduplicate_conditions(conditions)
        
        # Apply hierarchical rules (e.g., don't diagnose prediabetes if diabetes is present)
        conditions = self._apply_hierarchical_rules(conditions, data_dict)
        
        return conditions
    
    def _apply_hierarchical_rules(
        self, 
        conditions: List[Dict[str, Any]], 
        data_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply hierarchical rules to prevent conflicting diagnoses.
        For example, don't diagnose prediabetes if diabetes is already diagnosed.
        
        Args:
            conditions: List of matched conditions
            data_dict: Unified data dictionary for additional validation (e.g., Type 1 evidence)
            
        Returns:
            Filtered list with hierarchical rules applied
        """
        condition_ids = {c["diagnosis_id"] for c in conditions}
        
        # Rule: Remove prediabetes if type_2_diabetes is present
        if "type_2_diabetes" in condition_ids and "prediabetes" in condition_ids:
            conditions = [c for c in conditions if c["diagnosis_id"] != "prediabetes"]
        
        # Rule: Type 1 and Type 2 are mutually exclusive - prefer Type 2 if both match
        if "type_1_diabetes" in condition_ids and "type_2_diabetes" in condition_ids:
            # Type 1 requires specific evidence (autoimmune markers, insulin dependence, age of onset)
            # If not present, prefer Type 2
            type_1_condition = next((c for c in conditions if c["diagnosis_id"] == "type_1_diabetes"), None)
            type_2_condition = next((c for c in conditions if c["diagnosis_id"] == "type_2_diabetes"), None)
            
            if type_1_condition and type_2_condition:
                # Check for Type 1-specific evidence
                type_1_evidence = type_1_condition.get("evidence", {})
                data_dict = data_dict or {}
                
                # Check for autoimmune evidence markers
                has_autoimmune_evidence = (
                    "c_peptide" in type_1_evidence or 
                    "c_peptide" in data_dict or
                    "autoantibodies" in data_dict or
                    "autoimmune_markers" in data_dict
                )
                
                # Check for insulin dependence in evidence
                has_insulin_dependence = type_1_evidence.get("insulin_dependence", False)
                
                # Check age (Type 1 typically diagnosed before 30, though can occur at any age)
                # Age alone is not sufficient, but if age > 30 AND no autoimmune evidence, prefer Type 2
                client_age = data_dict.get("age")
                age_supports_type2 = client_age is not None and client_age > 30
                
                # Only keep Type 1 if specific evidence exists, otherwise prefer Type 2
                if not (has_autoimmune_evidence or has_insulin_dependence):
                    # No Type 1-specific evidence - remove Type 1, keep Type 2
                    conditions = [c for c in conditions if c["diagnosis_id"] != "type_1_diabetes"]
                elif age_supports_type2 and not has_autoimmune_evidence:
                    # Age > 30 and no autoimmune evidence - prefer Type 2
                    conditions = [c for c in conditions if c["diagnosis_id"] != "type_1_diabetes"]
        
        # Rule: Remove overweight if obesity is present
        if "obesity" in condition_ids and "overweight" in condition_ids:
            conditions = [c for c in conditions if c["diagnosis_id"] != "overweight"]
        
        return conditions
    
    def _prepare_data_dict(
        self, 
        labs: Dict[str, Any], 
        anthropometry: Dict[str, Any], 
        medical_history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare unified data dictionary from labs, anthropometry, and medical history.
        Handles various key name variations.
        
        Returns:
            Unified dictionary with normalized keys
        """
        data = {}
        
        # Labs - normalize key names
        lab_mappings = {
            "HbA1c": ["HbA1c", "hba1c", "hba1c_percent"],
            "FBS": ["FBS", "fbs", "fasting_blood_sugar", "fasting_glucose"],
            "PPBS": ["PPBS", "ppbs", "postprandial_blood_sugar", "postprandial_glucose"],
            "OGTT_1h": ["OGTT_1h", "ogtt_1h", "ogtt_1hour"],
            "OGTT_2h": ["OGTT_2h", "ogtt_2h", "ogtt_2hour"],
            "cholesterol": ["cholesterol", "total_cholesterol"],
            "triglycerides": ["triglycerides", "triglyceride"],
            "hdl": ["hdl", "HDL", "hdl_cholesterol"],
            "c_peptide": ["c_peptide", "cpeptide", "c_pep"]
        }
        
        for standard_key, variations in lab_mappings.items():
            for var_key in variations:
                value = labs.get(var_key)
                if value is not None:
                    data[standard_key] = self._safe_float(value)
                    break
        
        # Anthropometry
        bmi = self._safe_float(anthropometry.get("bmi"))
        if bmi is not None:
            data["bmi"] = bmi
        
        # Blood pressure
        bp_systolic_value = anthropometry.get("bp_systolic")
        if bp_systolic_value is None and isinstance(anthropometry.get("blood_pressure"), dict):
            bp_systolic_value = anthropometry.get("blood_pressure", {}).get("systolic")
        bp_systolic = self._safe_float(bp_systolic_value)
        if bp_systolic is not None:
            data["bp_systolic"] = bp_systolic
        
        bp_diastolic_value = anthropometry.get("bp_diastolic")
        if bp_diastolic_value is None and isinstance(anthropometry.get("blood_pressure"), dict):
            bp_diastolic_value = anthropometry.get("blood_pressure", {}).get("diastolic")
        bp_diastolic = self._safe_float(bp_diastolic_value)
        if bp_diastolic is not None:
            data["bp_diastolic"] = bp_diastolic
        
        # Waist circumference
        waist = self._safe_float(
            anthropometry.get("waist_circumference") or 
            anthropometry.get("waist_cm") or
            anthropometry.get("waist")
        )
        if waist is not None:
            data["waist_circumference"] = waist
        
        return data
    
    def _evaluate_condition(
        self, 
        condition_kb: Dict[str, Any], 
        data_dict: Dict[str, Any],
        client_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate if a condition matches based on KB thresholds.
        
        Args:
            condition_kb: Condition definition from knowledge base
            data_dict: Unified data dictionary with patient values
            client_context: Client context for eligibility validation
            
        Returns:
            Match result with severity_score and evidence, or None if no match or not eligible
        """
        # STEP 1: Check eligibility constraints FIRST (before lab matching)
        eligibility = condition_kb.get("eligibility_constraints", {})
        if eligibility:
            if not self._check_eligibility_constraints(eligibility, client_context or {}, data_dict):
                return None  # Not eligible for this diagnosis
        
        severity_thresholds = condition_kb.get("severity_thresholds", {})
        if not severity_thresholds:
            return None
        
        best_match = None
        best_severity_score = 0.0
        
        # STEP 2: Check each threshold parameter in the condition
        for param_name, severity_levels in severity_thresholds.items():
            patient_value = data_dict.get(param_name)
            if patient_value is None:
                continue
            
            # Check each severity level (mild, moderate, severe)
            for severity_level, threshold_range in severity_levels.items():
                if self._value_matches_threshold(patient_value, threshold_range):
                    # Calculate severity score based on level
                    severity_score = self._severity_level_to_score(severity_level, patient_value, threshold_range)
                    
                    # Keep the highest severity match
                    if severity_score > best_severity_score:
                        best_severity_score = severity_score
                        best_match = {
                            "severity_score": severity_score,
                            "evidence": {
                                param_name: patient_value,
                                "threshold_min": threshold_range.get("min"),
                                "threshold_max": threshold_range.get("max"),
                                "severity_level": severity_level,
                                "unit": threshold_range.get("unit"),
                                "source": self._get_evidence_source(param_name)
                            }
                        }
        
        return best_match
    
    def _check_eligibility_constraints(
        self,
        eligibility: Dict[str, Any],
        client_context: Dict[str, Any],
        data_dict: Dict[str, Any]
    ) -> bool:
        """
        Check if client meets eligibility constraints for a condition.
        
        Args:
            eligibility: Eligibility constraints from KB (gender, pregnancy, age, etc.)
            client_context: Client context with age, gender, reproductive_context
            data_dict: Unified data dictionary (may contain additional evidence)
            
        Returns:
            True if eligible, False otherwise
        """
        # Check gender requirement
        required_gender = eligibility.get("gender")
        if required_gender:
            client_gender = client_context.get("gender", "").lower()
            # Normalize gender values
            if client_gender in ["m", "male"]:
                client_gender = "male"
            elif client_gender in ["f", "female"]:
                client_gender = "female"
            
            if required_gender.lower() not in [client_gender, "all"]:
                return False  # Not eligible - gender mismatch
        
        # Check pregnancy requirement (for gestational diabetes)
        requires_pregnancy = eligibility.get("requires_pregnancy", False)
        if requires_pregnancy:
            # Check reproductive_context from snapshot
            reproductive_context = client_context.get("reproductive_context", {})
            pregnancy_status = reproductive_context.get("pregnancy_status")
            
            if pregnancy_status != "pregnant":
                return False  # Cannot diagnose gestational diabetes without pregnancy
            
            # Check gestational weeks range if specified
            gestational_weeks_min = eligibility.get("gestational_weeks_min")
            gestational_weeks_max = eligibility.get("gestational_weeks_max")
            if gestational_weeks_min is not None or gestational_weeks_max is not None:
                gestational_weeks = reproductive_context.get("gestational_weeks")
                if gestational_weeks is not None:
                    if gestational_weeks_min is not None and gestational_weeks < gestational_weeks_min:
                        return False
                    if gestational_weeks_max is not None and gestational_weeks > gestational_weeks_max:
                        return False
        
        # Check age range
        age_min = eligibility.get("age_min")
        age_max = eligibility.get("age_max")
        if age_min is not None or age_max is not None:
            client_age = client_context.get("age")
            if client_age is not None:
                if age_min is not None and client_age < age_min:
                    return False
                if age_max is not None and client_age > age_max:
                    return False
        
        # Check age of onset (for Type 1 diabetes)
        age_of_onset_max = eligibility.get("age_of_onset_max")
        if age_of_onset_max is not None:
            # Age of onset would typically come from medical_history or data_dict
            age_of_onset = (
                data_dict.get("age_of_onset") or 
                data_dict.get("diagnosis_age") or
                client_context.get("age")  # Use current age as proxy if not specified
            )
            if age_of_onset is not None and age_of_onset > age_of_onset_max:
                # Age of onset > max suggests Type 2 rather than Type 1
                # But we still need to check for autoimmune evidence (handled in hierarchical rules)
                pass  # Let it pass, hierarchical rules will handle it
        
        # Check for required autoimmune evidence (for Type 1 diabetes)
        requires_autoimmune_evidence = eligibility.get("requires_autoimmune_evidence", False)
        if requires_autoimmune_evidence:
            # Check for alternative evidence markers
            alternative_evidence = eligibility.get("alternative_evidence", [])
            has_evidence = False
            
            for evidence_marker in alternative_evidence:
                if evidence_marker in data_dict:
                    marker_value = data_dict.get(evidence_marker)
                    # For c_peptide, low values (<0.6) indicate Type 1
                    if evidence_marker == "c_peptide":
                        if marker_value is not None and marker_value < 0.6:
                            has_evidence = True
                            break
                    else:
                        # For other markers (autoantibodies, insulin_dependence), presence indicates Type 1
                        if marker_value is not None:
                            has_evidence = True
                            break
            
            # If requires_autoimmune_evidence but no evidence found, still allow it
            # to pass - hierarchical rules will handle Type 1 vs Type 2 conflict
            # This is because Type 1 can sometimes be diagnosed without these markers
            # if other strong indicators exist
        
        return True  # All eligibility checks passed
    
    def _value_matches_threshold(self, value: float, threshold_range: Dict[str, Any]) -> bool:
        """
        Check if a value matches a threshold range.
        
        Args:
            value: Patient's value
            threshold_range: Threshold definition with min/max
            
        Returns:
            True if value matches threshold
        """
        min_val = threshold_range.get("min")
        max_val = threshold_range.get("max")
        
        # Check minimum threshold
        if min_val is not None and value < min_val:
            return False
        
        # Check maximum threshold
        if max_val is not None and value > max_val:
            return False
        
        return True
    
    def _severity_level_to_score(
        self, 
        severity_level: str, 
        value: float, 
        threshold_range: Dict[str, Any]
    ) -> float:
        """
        Convert severity level to numeric score (0-10).
        
        Args:
            severity_level: "mild", "moderate", or "severe"
            value: Patient's value
            threshold_range: Threshold definition
            
        Returns:
            Severity score from 0-10
        """
        base_scores = {
            "mild": 5.0,
            "moderate": 7.0,
            "severe": 9.0
        }
        
        base_score = base_scores.get(severity_level, 5.0)
        
        # Adjust score based on how far value is from threshold
        min_val = threshold_range.get("min")
        max_val = threshold_range.get("max")
        
        if min_val is not None:
            # For conditions where higher is worse (e.g., HbA1c, BMI)
            if max_val is None:
                # No upper bound - scale based on distance from min
                excess = value - min_val
                adjustment = min(2.0, excess * 0.1)  # Cap at +2.0
                return min(10.0, base_score + adjustment)
            else:
                # Has range - use midpoint for scaling
                midpoint = (min_val + max_val) / 2
                if value > midpoint:
                    # Closer to severe
                    return min(10.0, base_score + 1.0)
                else:
                    # Closer to mild
                    return base_score
        elif max_val is not None:
            # For conditions where lower is worse (e.g., underweight BMI)
            deficit = max_val - value
            adjustment = min(2.0, deficit * 0.1)  # Cap at +2.0
            return min(10.0, base_score + adjustment)
        
        return base_score
    
    def _get_evidence_source(self, param_name: str) -> str:
        """Determine evidence source type based on parameter name."""
        lab_params = ["HbA1c", "FBS", "PPBS", "OGTT_1h", "OGTT_2h", "cholesterol", "triglycerides", "hdl", "c_peptide"]
        vital_params = ["bp_systolic", "bp_diastolic"]
        anthropometry_params = ["bmi", "waist_circumference"]
        
        if param_name in lab_params:
            return "lab_result"
        elif param_name in vital_params:
            return "vital_sign"
        elif param_name in anthropometry_params:
            return "anthropometry"
        else:
            return "clinical_data"
    
    def _deduplicate_conditions(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate conditions, keeping the one with highest severity.
        
        Args:
            conditions: List of condition dictionaries
            
        Returns:
            Deduplicated list sorted by severity (highest first)
        """
        # Group by diagnosis_id
        condition_map = {}
        for condition in conditions:
            diagnosis_id = condition["diagnosis_id"]
            if diagnosis_id not in condition_map:
                condition_map[diagnosis_id] = condition
            else:
                # Keep the one with higher severity
                if condition["severity_score"] > condition_map[diagnosis_id]["severity_score"]:
                    condition_map[diagnosis_id] = condition
        
        # Convert back to list and sort by severity
        result = list(condition_map.values())
        result.sort(key=lambda x: x["severity_score"], reverse=True)
        
        return result
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float, return None if not possible."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def identify_nutrition_diagnoses(
        self,
        labs: Optional[Dict[str, Any]] = None,
        anthropometry: Optional[Dict[str, Any]] = None,
        diet_history: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify nutrition diagnoses from input data.
        
        NOTE: Currently disabled - returns empty list.
        
        Nutrition diagnoses require detailed diet history data (carb_intake_percent,
        fiber_grams, protein_grams, etc.) which is not available from users during intake.
        The system works with medical condition-based MNT rules only.
        
        Args:
            labs: Laboratory test results (not used currently)
            anthropometry: Height, weight, BMI, body composition data (not used currently)
            diet_history: Dietary intake history and patterns (not used currently)
            
        Returns:
            Empty list - nutrition diagnoses are not generated.
            
        Note:
            MNT rules are applied based on medical conditions only:
            - type_2_diabetes → carb restriction
            - hypertension → sodium restriction
            - dyslipidemia → fat modification
            - obesity → calorie restriction
            
            This can be re-enabled in the future when diet history data collection
            is implemented in the intake process.
        """
        # Return empty list - system works with medical conditions only
        return []

