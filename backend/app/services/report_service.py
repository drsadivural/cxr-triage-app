"""
Report generation service with deterministic templates and optional LLM rewriting.
"""
from typing import List, Optional, Tuple
from app.schemas import FindingResult, ReportResult
from app.config import LLMSettings, AISettings
from app.services.llm_service import LLMService, get_llm_service


# Finding templates based on status and confidence
FINDING_TEMPLATES = {
    "pneumothorax": {
        "POSITIVE_STRONG": "There is evidence of pneumothorax.",
        "POSITIVE": "Findings suggestive of pneumothorax. Clinical correlation recommended.",
        "POSSIBLE": "Cannot exclude small pneumothorax. Recommend clinical correlation and consider follow-up imaging if clinically indicated.",
        "UNCERTAIN": "Equivocal findings in the pleural space. Cannot exclude pneumothorax. Radiologist review recommended.",
        "NEG_STRONG": "No pneumothorax identified.",
        "NEG": "No definite pneumothorax seen on this examination.",
    },
    "pleural_effusion": {
        "POSITIVE_STRONG": "Pleural effusion is present.",
        "POSITIVE": "Findings consistent with pleural effusion.",
        "POSSIBLE": "Possible small pleural effusion. Clinical correlation recommended.",
        "UNCERTAIN": "Equivocal findings at the costophrenic angle. Cannot exclude small effusion.",
        "NEG_STRONG": "No pleural effusion.",
        "NEG": "No significant pleural effusion identified.",
    },
    "consolidation": {
        "POSITIVE_STRONG": "Pulmonary consolidation is present, which may represent pneumonia or other airspace disease.",
        "POSITIVE": "Findings suggestive of consolidation. Clinical correlation for infection or other etiology recommended.",
        "POSSIBLE": "Possible area of consolidation. Recommend clinical correlation.",
        "UNCERTAIN": "Equivocal opacity that may represent consolidation. Further evaluation may be warranted.",
        "NEG_STRONG": "No consolidation identified.",
        "NEG": "No definite consolidation seen.",
    },
    "cardiomegaly": {
        "POSITIVE_STRONG": "The cardiac silhouette is enlarged, consistent with cardiomegaly.",
        "POSITIVE": "The heart appears enlarged. Clinical correlation recommended.",
        "POSSIBLE": "The cardiac silhouette is at the upper limits of normal. Possible mild cardiomegaly.",
        "UNCERTAIN": "Cardiac silhouette size is difficult to assess. Consider dedicated cardiac imaging if clinically indicated.",
        "NEG_STRONG": "Normal cardiac silhouette size.",
        "NEG": "The cardiac silhouette is within normal limits.",
    },
    "edema": {
        "POSITIVE_STRONG": "Findings consistent with pulmonary edema.",
        "POSITIVE": "Interstitial markings suggestive of pulmonary edema. Clinical correlation recommended.",
        "POSSIBLE": "Possible mild pulmonary edema. Recommend clinical correlation.",
        "UNCERTAIN": "Equivocal interstitial markings. Cannot exclude early pulmonary edema.",
        "NEG_STRONG": "No pulmonary edema.",
        "NEG": "No significant pulmonary edema identified.",
    },
    "nodule": {
        "POSITIVE_STRONG": "Pulmonary nodule identified. Further evaluation with CT recommended.",
        "POSITIVE": "Possible pulmonary nodule. Consider CT for further characterization.",
        "POSSIBLE": "Questionable nodular opacity. CT may be considered for further evaluation if clinically indicated.",
        "UNCERTAIN": "Equivocal finding that may represent a nodule. Clinical correlation and possible follow-up recommended.",
        "NEG_STRONG": "No pulmonary nodules identified.",
        "NEG": "No definite pulmonary nodules seen on this examination.",
    },
    "mass": {
        "POSITIVE_STRONG": "Pulmonary mass identified. Urgent CT and clinical correlation recommended.",
        "POSITIVE": "Findings suggestive of pulmonary mass. CT recommended for further evaluation.",
        "POSSIBLE": "Possible pulmonary mass. Further imaging recommended.",
        "UNCERTAIN": "Equivocal opacity that may represent a mass. Further evaluation recommended.",
        "NEG_STRONG": "No pulmonary masses identified.",
        "NEG": "No definite pulmonary masses seen.",
    },
}

IMPRESSION_TEMPLATES = {
    "URGENT": "URGENT: {urgent_findings}. Immediate clinical attention recommended.",
    "ROUTINE": "Abnormal chest radiograph with {routine_findings}. Clinical correlation recommended.",
    "NORMAL": "No acute cardiopulmonary abnormality identified.",
    "UNCERTAIN": "Limited examination with equivocal findings. Radiologist review recommended. {uncertain_findings}",
}

DISCLAIMER = "AI assistance only. Not for standalone diagnosis. All findings require radiologist review."


class ReportGenerator:
    """Generates grounded radiology reports from model findings."""
    
    def __init__(self, ai_settings: AISettings, llm_settings: LLMSettings):
        self.ai_settings = ai_settings
        self.llm_service = get_llm_service(llm_settings)
    
    def _get_finding_status_key(self, finding: FindingResult) -> str:
        """Determine the template key based on finding status and probability."""
        prob = finding.calibrated_probability or finding.probability
        
        if finding.status == "POSITIVE":
            if prob >= finding.strong_threshold:
                return "POSITIVE_STRONG"
            return "POSITIVE"
        elif finding.status == "POSSIBLE":
            return "POSSIBLE"
        elif finding.status == "UNCERTAIN":
            return "UNCERTAIN"
        else:  # NEG
            if prob < 0.1:  # Strong negative
                return "NEG_STRONG"
            return "NEG"
    
    def _generate_finding_text(self, finding: FindingResult) -> str:
        """Generate text for a single finding."""
        finding_name = finding.finding_name.lower().replace(" ", "_")
        templates = FINDING_TEMPLATES.get(finding_name, {})
        
        status_key = self._get_finding_status_key(finding)
        template = templates.get(status_key)
        
        if not template:
            # Fallback generic template
            if finding.status == "POSITIVE":
                return f"Findings suggestive of {finding.finding_name}."
            elif finding.status == "POSSIBLE":
                return f"Possible {finding.finding_name}. Clinical correlation recommended."
            elif finding.status == "UNCERTAIN":
                return f"Cannot exclude {finding.finding_name}. Radiologist review recommended."
            else:
                return f"No significant {finding.finding_name} identified."
        
        return template
    
    def _categorize_findings(self, findings: List[FindingResult]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Categorize findings into urgent, routine, uncertain, and negative."""
        urgent = []
        routine = []
        uncertain = []
        negative = []
        
        for finding in findings:
            threshold = self.ai_settings.get_threshold(finding.finding_name)
            if not threshold.enabled:
                continue
            
            prob = finding.calibrated_probability or finding.probability
            
            if finding.status == "POSITIVE" and prob >= threshold.strong_threshold:
                urgent.append(finding.finding_name)
            elif finding.status in ["POSITIVE", "POSSIBLE"]:
                routine.append(finding.finding_name)
            elif finding.status == "UNCERTAIN":
                uncertain.append(finding.finding_name)
            else:
                negative.append(finding.finding_name)
        
        return urgent, routine, uncertain, negative
    
    def _generate_impression(self, findings: List[FindingResult]) -> Tuple[str, str]:
        """Generate impression text and determine triage level."""
        urgent, routine, uncertain, negative = self._categorize_findings(findings)
        
        if urgent:
            triage_level = "URGENT"
            impression = IMPRESSION_TEMPLATES["URGENT"].format(
                urgent_findings=", ".join(urgent)
            )
        elif routine:
            triage_level = "ROUTINE"
            impression = IMPRESSION_TEMPLATES["ROUTINE"].format(
                routine_findings=", ".join(routine)
            )
        elif uncertain:
            triage_level = "ROUTINE"  # Uncertain findings still need review
            impression = IMPRESSION_TEMPLATES["UNCERTAIN"].format(
                uncertain_findings="Cannot exclude: " + ", ".join(uncertain)
            )
        else:
            triage_level = "NORMAL"
            impression = IMPRESSION_TEMPLATES["NORMAL"]
        
        return impression, triage_level
    
    async def generate_report(self, findings: List[FindingResult]) -> ReportResult:
        """Generate a complete report from findings."""
        # Generate findings section
        findings_texts = []
        finding_names = []
        
        for finding in findings:
            threshold = self.ai_settings.get_threshold(finding.finding_name)
            if not threshold.enabled:
                continue
            
            text = self._generate_finding_text(finding)
            findings_texts.append(text)
            finding_names.append(finding.finding_name)
        
        findings_text = " ".join(findings_texts) if findings_texts else "No significant abnormalities identified."
        
        # Generate impression
        impression_text, _ = self._generate_impression(findings)
        
        # Combine into template
        template_report = f"FINDINGS:\n{findings_text}\n\nIMPRESSION:\n{impression_text}"
        
        # Try LLM rewrite if enabled
        llm_rewritten = False
        if self.llm_service.is_available():
            rewritten = await self.llm_service.rewrite_report(template_report, finding_names)
            if rewritten:
                # Parse rewritten report
                if "FINDINGS:" in rewritten and "IMPRESSION:" in rewritten:
                    parts = rewritten.split("IMPRESSION:")
                    findings_text = parts[0].replace("FINDINGS:", "").strip()
                    impression_text = parts[1].strip() if len(parts) > 1 else impression_text
                    llm_rewritten = True
                else:
                    # Use as-is if format is different
                    findings_text = rewritten
                    llm_rewritten = True
        
        return ReportResult(
            findings_text=findings_text,
            impression_text=impression_text,
            llm_rewritten=llm_rewritten,
            disclaimer=DISCLAIMER
        )
    
    def determine_triage(self, findings: List[FindingResult]) -> Tuple[str, List[str]]:
        """Determine triage level and reasons from findings."""
        urgent, routine, uncertain, _ = self._categorize_findings(findings)
        
        reasons = []
        
        if urgent:
            triage_level = "URGENT"
            for f in urgent:
                reasons.append(f"High confidence {f} detected")
        elif routine:
            triage_level = "ROUTINE"
            for f in routine:
                reasons.append(f"Possible {f} detected")
        elif uncertain:
            triage_level = "ROUTINE"
            for f in uncertain:
                reasons.append(f"Uncertain {f} - needs review")
        else:
            triage_level = "NORMAL"
            reasons.append("No significant abnormalities detected")
        
        return triage_level, reasons


def get_report_generator(ai_settings: AISettings, llm_settings: LLMSettings) -> ReportGenerator:
    """Factory function to create report generator."""
    return ReportGenerator(ai_settings, llm_settings)
