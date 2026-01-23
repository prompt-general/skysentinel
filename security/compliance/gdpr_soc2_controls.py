from typing import Dict, List

class GDPR_Controls:
    """GDPR Compliance Controls Implementation"""
    
    def __init__(self):
        self.controls = self._load_all_controls()
    
    def _load_all_controls(self) -> Dict[str, Dict]:
        """Load all GDPR controls"""
        return {
            # Data Protection Principles
            "GDPR.ART.5.1.a": {
                "id": "GDPR.ART.5.1.a",
                "title": "Lawfulness, fairness and transparency",
                "description": "Personal data shall be processed lawfully, fairly and in a transparent manner.",
                "severity": "HIGH",
                "category": "Data Protection Principles",
                "article": "5",
                "remediation": "Implement transparent data processing policies and procedures.",
                "test_procedure": "Review data processing policies and transparency notices.",
                "policies": ["lawful-processing", "fair-processing", "transparency"]
            },
            
            "GDPR.ART.5.1.b": {
                "id": "GDPR.ART.5.1.b",
                "title": "Purpose limitation",
                "description": "Personal data shall be collected for specified, explicit and legitimate purposes.",
                "severity": "HIGH",
                "category": "Data Protection Principles",
                "article": "5",
                "remediation": "Implement purpose limitation controls and documentation.",
                "test_procedure": "Review purpose documentation and implementation.",
                "policies": ["purpose-limitation", "data-purpose-specification"]
            },
            
            "GDPR.ART.5.1.c": {
                "id": "GDPR.ART.5.1.c",
                "title": "Data minimization",
                "description": "Personal data shall be adequate, relevant and limited to what is necessary.",
                "severity": "HIGH",
                "category": "Data Protection Principles",
                "article": "5",
                "remediation": "Implement data minimization procedures.",
                "test_procedure": "Review data minimization implementation.",
                "policies": ["data-minimization", "data-adequacy"]
            },
            
            "GDPR.ART.5.1.d": {
                "id": "GDPR.ART.5.1.d",
                "title": "Accuracy",
                "description": "Personal data shall be accurate and kept up to date.",
                "severity": "MEDIUM",
                "category": "Data Protection Principles",
                "article": "5",
                "remediation": "Implement data accuracy and update procedures.",
                "test_procedure": "Review data accuracy procedures.",
                "policies": ["data-accuracy", "data-updates"]
            },
            
            "GDPR.ART.5.1.e": {
                "id": "GDPR.ART.5.1.e",
                "title": "Storage limitation",
                "description": "Personal data shall be kept in a form which permits identification for no longer than necessary.",
                "severity": "HIGH",
                "category": "Data Protection Principles",
                "article": "5",
                "remediation": "Implement data retention and deletion procedures.",
                "test_procedure": "Review data retention policies and implementation.",
                "policies": ["storage-limitation", "data-retention-policy"]
            },
            
            "GDPR.ART.5.1.f": {
                "id": "GDPR.ART.5.1.f",
                "title": "Integrity and confidentiality",
                "description": "Personal data shall be processed in a manner that ensures security.",
                "severity": "HIGH",
                "category": "Data Protection Principles",
                "article": "5",
                "remediation": "Implement appropriate security measures.",
                "test_procedure": "Review security measures implementation.",
                "policies": ["data-security", "integrity-confidentiality"]
            },
            
            "GDPR.ART.5.2": {
                "id": "GDPR.ART.5.2",
                "title": "Accountability",
                "description": "The controller shall be responsible for and be able to demonstrate compliance.",
                "severity": "HIGH",
                "category": "Accountability",
                "article": "5",
                "remediation": "Implement accountability and documentation procedures.",
                "test_procedure": "Review accountability documentation.",
                "policies": ["accountability", "compliance-documentation"]
            },
            
            # Rights of Data Subjects
            "GDPR.ART.15": {
                "id": "GDPR.ART.15",
                "title": "Right of access",
                "description": "Data subjects have the right to obtain confirmation of processing and access to personal data.",
                "severity": "HIGH",
                "category": "Data Subject Rights",
                "article": "15",
                "remediation": "Implement procedures for handling data subject access requests.",
                "test_procedure": "Test data subject access request procedures.",
                "policies": ["right-of-access", "dsar-procedures"]
            },
            
            "GDPR.ART.16": {
                "id": "GDPR.ART.16",
                "title": "Right to rectification",
                "description": "Data subjects have the right to obtain rectification of inaccurate personal data.",
                "severity": "HIGH",
                "category": "Data Subject Rights",
                "article": "16",
                "remediation": "Implement procedures for handling rectification requests.",
                "test_procedure": "Test rectification request procedures.",
                "policies": ["right-to-rectification", "data-correction"]
            },
            
            "GDPR.ART.17": {
                "id": "GDPR.ART.17",
                "title": "Right to erasure",
                "description": "Data subjects have the right to obtain erasure of personal data.",
                "severity": "HIGH",
                "category": "Data Subject Rights",
                "article": "17",
                "remediation": "Implement procedures for handling erasure requests.",
                "test_procedure": "Test erasure request procedures.",
                "policies": ["right-to-erasure", "right-to-be-forgotten"]
            },
            
            "GDPR.ART.18": {
                "id": "GDPR.ART.18",
                "title": "Right to restriction of processing",
                "description": "Data subjects have the right to obtain restriction of processing.",
                "severity": "MEDIUM",
                "category": "Data Subject Rights",
                "article": "18",
                "remediation": "Implement procedures for handling restriction requests.",
                "test_procedure": "Test restriction request procedures.",
                "policies": ["right-to-restriction", "processing-limitation"]
            },
            
            "GDPR.ART.20": {
                "id": "GDPR.ART.20",
                "title": "Right to data portability",
                "description": "Data subjects have the right to receive personal data in a structured, machine-readable format.",
                "severity": "MEDIUM",
                "category": "Data Subject Rights",
                "article": "20",
                "remediation": "Implement data portability procedures.",
                "test_procedure": "Test data portability procedures.",
                "policies": ["right-to-data-portability", "data-export"]
            },
            
            # Security Measures
            "GDPR.ART.32": {
                "id": "GDPR.ART.32",
                "title": "Security of processing",
                "description": "Implement appropriate technical and organizational measures for security.",
                "severity": "HIGH",
                "category": "Security Measures",
                "article": "32",
                "remediation": "Implement comprehensive security measures.",
                "test_procedure": "Review security measures implementation.",
                "policies": ["security-of-processing", "technical-organizational-measures"]
            },
            
            "GDPR.ART.33": {
                "id": "GDPR.ART.33",
                "title": "Notification of personal data breach",
                "description": "Notify personal data breaches to supervisory authority without undue delay.",
                "severity": "HIGH",
                "category": "Breach Notification",
                "article": "33",
                "remediation": "Implement breach notification procedures.",
                "test_procedure": "Test breach notification procedures.",
                "policies": ["breach-notification", "data-breach-procedures"]
            },
            
            "GDPR.ART.34": {
                "id": "GDPR.ART.34",
                "title": "Communication of personal data breach",
                "description": "Communicate personal data breaches to data subjects without undue delay.",
                "severity": "HIGH",
                "category": "Breach Notification",
                "article": "34",
                "remediation": "Implement data subject breach communication procedures.",
                "test_procedure": "Test breach communication procedures.",
                "policies": ["breach-communication", "data-subject-notification"]
            }
        }
    
    def get_controls_by_article(self, article: str) -> List[Dict]:
        """Get controls filtered by GDPR article"""
        return [
            control for control in self.controls.values()
            if control.get("article") == article
        ]
    
    def get_controls_by_category(self, category: str) -> List[Dict]:
        """Get controls filtered by category"""
        return [
            control for control in self.controls.values()
            if control.get("category") == category
        ]
    
    def get_control(self, control_id: str) -> Dict:
        """Get a specific control by ID"""
        return self.controls.get(control_id, {})
    
    def get_all_control_ids(self) -> List[str]:
        """Get all control IDs"""
        return list(self.controls.keys())


class SOC2_Controls:
    """SOC2 Type II Controls Implementation"""
    
    def __init__(self):
        self.controls = self._load_all_controls()
    
    def _load_all_controls(self) -> Dict[str, Dict]:
        """Load all SOC2 controls"""
        return {
            # Security Principle
            "SOC2.CC.1.1": {
                "id": "SOC2.CC.1.1",
                "title": "Control Environment",
                "description": "Management establishes and maintains control environment.",
                "severity": "HIGH",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Establish and maintain documented control environment.",
                "test_procedure": "Review control environment documentation.",
                "policies": ["control-environment", "governance-controls"]
            },
            
            "SOC2.CC.2.1": {
                "id": "SOC2.CC.2.1",
                "title": "Communication and Responsibility",
                "description": "Management communicates control responsibilities.",
                "severity": "MEDIUM",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Implement communication procedures for control responsibilities.",
                "test_procedure": "Review communication procedures.",
                "policies": ["control-communication", "responsibility-documentation"]
            },
            
            "SOC2.CC.3.1": {
                "id": "SOC2.CC.3.1",
                "title": "Risk Assessment",
                "description": "Management identifies risks that may affect achievement of objectives.",
                "severity": "HIGH",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Implement risk assessment procedures.",
                "test_procedure": "Review risk assessment procedures and results.",
                "policies": ["risk-assessment", "risk-management"]
            },
            
            "SOC2.CC.4.1": {
                "id": "SOC2.CC.4.1",
                "title": "Design and Implementation",
                "description": "Management designs and implements controls to respond to risks.",
                "severity": "HIGH",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Design and implement appropriate controls.",
                "test_procedure": "Review control design and implementation.",
                "policies": ["control-design", "control-implementation"]
            },
            
            "SOC2.CC.5.1": {
                "id": "SOC2.CC.5.1",
                "title": "Control Activities",
                "description": "Management implements control activities through policies.",
                "severity": "HIGH",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Implement control activities through documented policies.",
                "test_procedure": "Review control activities and policies.",
                "policies": ["control-activities", "policy-implementation"]
            },
            
            "SOC2.CC.6.1": {
                "id": "SOC2.CC.6.1",
                "title": "Information and Communication",
                "description": "Management obtains, generates, and uses relevant information.",
                "severity": "MEDIUM",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Implement information and communication systems.",
                "test_procedure": "Review information and communication systems.",
                "policies": ["information-communication", "relevant-information"]
            },
            
            "SOC2.CC.7.1": {
                "id": "SOC2.CC.7.1",
                "title": "Monitoring",
                "description": "Management monitors controls and performance.",
                "severity": "HIGH",
                "category": "Security",
                "trust_service": "Security",
                "remediation": "Implement monitoring procedures for controls.",
                "test_procedure": "Review monitoring procedures and results.",
                "policies": ["control-monitoring", "performance-monitoring"]
            },
            
            # Availability Principle
            "SOC2.A1.1": {
                "id": "SOC2.A1.1",
                "title": "Availability of Information",
                "description": "System is available for operation and use as committed.",
                "severity": "HIGH",
                "category": "Availability",
                "trust_service": "Availability",
                "remediation": "Implement availability controls and monitoring.",
                "test_procedure": "Review availability controls and metrics.",
                "policies": ["availability-controls", "system-availability"]
            },
            
            "SOC2.A1.2": {
                "id": "SOC2.A1.2",
                "title": "Processing Capacity",
                "description": "System meets processing capacity commitments.",
                "severity": "MEDIUM",
                "category": "Availability",
                "trust_service": "Availability",
                "remediation": "Monitor and maintain processing capacity.",
                "test_procedure": "Review processing capacity monitoring.",
                "policies": ["processing-capacity", "capacity-planning"]
            },
            
            # Confidentiality Principle
            "SOC2.C1.1": {
                "id": "SOC2.C1.1",
                "title": "Confidential Information",
                "description": "Information designated as confidential is protected.",
                "severity": "HIGH",
                "category": "Confidentiality",
                "trust_service": "Confidentiality",
                "remediation": "Implement confidentiality controls.",
                "test_procedure": "Review confidentiality controls.",
                "policies": ["confidentiality-controls", "information-classification"]
            },
            
            "SOC2.C1.2": {
                "id": "SOC2.C1.2",
                "title": "Confidential Information Use",
                "description": "Confidential information is used only for specified purposes.",
                "severity": "HIGH",
                "category": "Confidentiality",
                "trust_service": "Confidentiality",
                "remediation": "Implement confidentiality use controls.",
                "test_procedure": "Review confidentiality use procedures.",
                "policies": ["confidentiality-use", "purpose-limitation"]
            },
            
            # Privacy Principle
            "SOC2.P1.1": {
                "id": "SOC2.P1.1",
                "title": "Personal Information",
                "description": "Personal information is collected, used, retained, disclosed, and disposed.",
                "severity": "HIGH",
                "category": "Privacy",
                "trust_service": "Privacy",
                "remediation": "Implement privacy controls for personal information.",
                "test_procedure": "Review privacy controls.",
                "policies": ["personal-information-controls", "privacy-protection"]
            },
            
            "SOC2.P1.2": {
                "id": "SOC2.P1.2",
                "title": "Privacy Notice",
                "description": "Privacy notice is provided to individuals.",
                "severity": "MEDIUM",
                "category": "Privacy",
                "trust_service": "Privacy",
                "remediation": "Implement privacy notice procedures.",
                "test_procedure": "Review privacy notice implementation.",
                "policies": ["privacy-notice", "privacy-transparency"]
            }
        }
    
    def get_controls_by_trust_service(self, trust_service: str) -> List[Dict]:
        """Get controls filtered by trust service"""
        return [
            control for control in self.controls.values()
            if control.get("trust_service") == trust_service
        ]
    
    def get_controls_by_category(self, category: str) -> List[Dict]:
        """Get controls filtered by category"""
        return [
            control for control in self.controls.values()
            if control.get("category") == category
        ]
    
    def get_control(self, control_id: str) -> Dict:
        """Get a specific control by ID"""
        return self.controls.get(control_id, {})
    
    def get_all_control_ids(self) -> List[str]:
        """Get all control IDs"""
        return list(self.controls.keys())
