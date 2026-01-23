from typing import Dict, List

class HIPAA_Controls:
    """HIPAA Security Rule Controls Implementation"""
    
    def __init__(self):
        self.controls = self._load_all_controls()
    
    def _load_all_controls(self) -> Dict[str, Dict]:
        """Load all HIPAA controls"""
        return {
            # Administrative Safeguards
            "HIPAA.164.308.a.1": {
                "id": "HIPAA.164.308.a.1",
                "title": "Security Officer",
                "description": "Designate a security official responsible for developing and implementing security policies.",
                "severity": "HIGH",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Appoint a designated security officer with documented responsibilities.",
                "test_procedure": "Review documented security officer appointment and responsibilities.",
                "policies": ["security-officer-designated"]
            },
            
            "HIPAA.164.308.a.2": {
                "id": "HIPAA.164.308.a.2",
                "title": "Workforce Security",
                "description": "Implement policies and procedures to ensure workforce members comply with security policies.",
                "severity": "HIGH",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Develop and implement workforce security policies and procedures.",
                "test_procedure": "Review workforce security policies and training records.",
                "policies": ["workforce-security-policies", "security-training-program"]
            },
            
            "HIPAA.164.308.a.3": {
                "id": "HIPAA.164.308.a.3",
                "title": "Information Access Management",
                "description": "Implement policies and procedures for authorizing access to ePHI.",
                "severity": "HIGH",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Implement formal access authorization procedures.",
                "test_procedure": "Review access authorization policies and procedures.",
                "policies": ["information-access-management", "phi-access-authorization"]
            },
            
            "HIPAA.164.308.a.4": {
                "id": "HIPAA.164.308.a.4",
                "title": "Workforce Clearance",
                "description": "Implement policies and procedures for workforce clearance procedures.",
                "severity": "MEDIUM",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Implement workforce clearance and authorization procedures.",
                "test_procedure": "Review workforce clearance procedures.",
                "policies": ["workforce-clearance-procedures"]
            },
            
            "HIPAA.164.308.a.5": {
                "id": "HIPAA.164.308.a.5",
                "title": "Workforce Training",
                "description": "Provide security awareness training to workforce members.",
                "severity": "HIGH",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Implement and document security awareness training program.",
                "test_procedure": "Review training program and training records.",
                "policies": ["security-awareness-training", "workforce-training-program"]
            },
            
            "HIPAA.164.308.a.6": {
                "id": "HIPAA.164.308.a.6",
                "title": "Contingency Planning",
                "description": "Implement policies and procedures for responding to emergencies.",
                "severity": "HIGH",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Develop and test contingency plans including data backup and recovery.",
                "test_procedure": "Review contingency plans and test results.",
                "policies": ["contingency-planning", "disaster-recovery-plan"]
            },
            
            "HIPAA.164.308.a.7": {
                "id": "HIPAA.164.308.a.7",
                "title": "Evaluation",
                "description": "Perform periodic evaluations of security policies and procedures.",
                "severity": "MEDIUM",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Implement regular security evaluations and assessments.",
                "test_procedure": "Review evaluation procedures and results.",
                "policies": ["security-evaluation-process", "periodic-security-assessment"]
            },
            
            "HIPAA.164.308.a.8": {
                "id": "HIPAA.164.308.a.8",
                "title": "Business Associate Contracts",
                "description": "Ensure business associate contracts contain required security provisions.",
                "severity": "HIGH",
                "category": "Administrative Safeguards",
                "safeguard": "Administrative",
                "remediation": "Review and update business associate agreements.",
                "test_procedure": "Review business associate contracts.",
                "policies": ["business-associate-contracts", "ba-agreement-compliance"]
            },
            
            # Physical Safeguards
            "HIPAA.164.310.a.1": {
                "id": "HIPAA.164.310.a.1",
                "title": "Facility Access Control",
                "description": "Implement policies and procedures to limit physical access to facilities.",
                "severity": "HIGH",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Implement facility access controls and visitor procedures.",
                "test_procedure": "Review facility access control procedures.",
                "policies": ["facility-access-control", "physical-security-controls"]
            },
            
            "HIPAA.164.310.a.2": {
                "id": "HIPAA.164.310.a.2",
                "title": "Workstation Use",
                "description": "Implement policies and procedures for workstation use.",
                "severity": "MEDIUM",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Develop workstation security policies and procedures.",
                "test_procedure": "Review workstation use policies.",
                "policies": ["workstation-use-policies", "workstation-security"]
            },
            
            "HIPAA.164.310.a.2.ii": {
                "id": "HIPAA.164.310.a.2.ii",
                "title": "Workstation Security",
                "description": "Implement physical safeguards for workstations that access ePHI.",
                "severity": "MEDIUM",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Implement physical security for workstations.",
                "test_procedure": "Verify workstation physical security measures.",
                "policies": ["workstation-physical-security"]
            },
            
            "HIPAA.164.310.a.3": {
                "id": "HIPAA.164.310.a.3",
                "title": "Device and Media Controls",
                "description": "Implement policies and procedures for device and media controls.",
                "severity": "HIGH",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Implement device and media control procedures.",
                "test_procedure": "Review device and media control procedures.",
                "policies": ["device-media-controls", "media-security"]
            },
            
            "HIPAA.164.310.a.3.ii": {
                "id": "HIPAA.164.310.a.3.ii",
                "title": "Media Disposal",
                "description": "Implement procedures for disposal of electronic media containing ePHI.",
                "severity": "HIGH",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Implement secure media disposal procedures.",
                "test_procedure": "Review media disposal procedures and records.",
                "policies": ["media-disposal-procedures", "secure-media-disposal"]
            },
            
            "HIPAA.164.310.a.3.iii": {
                "id": "HIPAA.164.310.a.3.iii",
                "title": "Media Re-use",
                "description": "Implement procedures for re-use of electronic media.",
                "severity": "MEDIUM",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Implement secure media re-use procedures.",
                "test_procedure": "Review media re-use procedures.",
                "policies": ["media-reuse-procedures"]
            },
            
            "HIPAA.164.310.a.3.iv": {
                "id": "HIPAA.164.310.a.3.iv",
                "title": "Accountability",
                "description": "Maintain records of movements of hardware and electronic media.",
                "severity": "MEDIUM",
                "category": "Physical Safeguards",
                "safeguard": "Physical",
                "remediation": "Implement hardware and media tracking procedures.",
                "test_procedure": "Review hardware and media tracking records.",
                "policies": ["hardware-media-tracking", "asset-accountability"]
            },
            
            # Technical Safeguards
            "HIPAA.164.312.a.1": {
                "id": "HIPAA.164.312.a.1",
                "title": "Access Control",
                "description": "Implement technical policies and procedures for electronic information access.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement technical access controls for ePHI.",
                "test_procedure": "Review technical access control implementations.",
                "policies": ["technical-access-controls", "phi-access-controls"]
            },
            
            "HIPAA.164.312.a.1.ii": {
                "id": "HIPAA.164.312.a.1.ii",
                "title": "Unique User Identification",
                "description": "Assign unique user names and/or numbers for identifying and tracking user identity.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement unique user identification for all users.",
                "test_procedure": "Verify unique user identification is implemented.",
                "policies": ["unique-user-identification"]
            },
            
            "HIPAA.164.312.a.1.iii": {
                "id": "HIPAA.164.312.a.1.iii",
                "title": "Emergency Access",
                "description": "Implement procedures for obtaining necessary ePHI during an emergency.",
                "severity": "MEDIUM",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement emergency access procedures.",
                "test_procedure": "Review emergency access procedures.",
                "policies": ["emergency-access-procedures"]
            },
            
            "HIPAA.164.312.a.1.iv": {
                "id": "HIPAA.164.312.a.1.iv",
                "title": "Automatic Logoff",
                "description": "Implement electronic procedures that terminate an electronic session after a period of inactivity.",
                "severity": "MEDIUM",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement automatic logoff for inactive sessions.",
                "test_procedure": "Verify automatic logoff is implemented.",
                "policies": ["automatic-logoff", "session-timeout"]
            },
            
            "HIPAA.164.312.a.1.v": {
                "id": "HIPAA.164.312.a.1.v",
                "title": "Encryption and Decryption",
                "description": "Implement encryption and decryption for ePHI.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement encryption for ePHI at rest and in transit.",
                "test_procedure": "Verify encryption implementation.",
                "policies": ["phi-encryption", "encryption-decryption"]
            },
            
            "HIPAA.164.312.a.2": {
                "id": "HIPAA.164.312.a.2",
                "title": "Audit Controls",
                "description": "Implement hardware, software, and procedural mechanisms that record and examine activity.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement comprehensive audit controls.",
                "test_procedure": "Review audit control implementations.",
                "policies": ["audit-controls", "activity-logging"]
            },
            
            "HIPAA.164.312.a.2.i": {
                "id": "HIPAA.164.312.a.2.i",
                "title": "Audit Log Content",
                "description": "Implement audit logs that record date, time, user, and description of events.",
                "severity": "MEDIUM",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Ensure audit logs capture required information.",
                "test_procedure": "Review audit log content and format.",
                "policies": ["audit-log-content", "comprehensive-logging"]
            },
            
            "HIPAA.164.312.a.3": {
                "id": "HIPAA.164.312.a.3",
                "title": "Integrity",
                "description": "Implement policies and procedures to protect ePHI from improper alteration or destruction.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement data integrity controls.",
                "test_procedure": "Review data integrity controls.",
                "policies": ["data-integrity-controls", "phi-integrity-protection"]
            },
            
            "HIPAA.164.312.a.3.i": {
                "id": "HIPAA.164.312.a.3.i",
                "title": "Mechanism to Authenticate ePHI",
                "description": "Implement electronic mechanisms to corroborate ePHI.",
                "severity": "MEDIUM",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement electronic authentication mechanisms.",
                "test_procedure": "Review electronic authentication mechanisms.",
                "policies": ["electronic-authentication", "phi-authentication"]
            },
            
            "HIPAA.164.312.a.4": {
                "id": "HIPAA.164.312.a.4",
                "title": "Transmission Security",
                "description": "Implement technical security measures to guard against unauthorized access to ePHI transmission.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement transmission security controls.",
                "test_procedure": "Review transmission security implementations.",
                "policies": ["transmission-security", "phi-transmission-protection"]
            },
            
            "HIPAA.164.312.a.4.i": {
                "id": "HIPAA.164.312.a.4.i",
                "title": "Encryption of ePHI",
                "description": "Implement encryption for ePHI when transmitted over networks.",
                "severity": "HIGH",
                "category": "Technical Safeguards",
                "safeguard": "Technical",
                "remediation": "Implement encryption for all ePHI transmissions.",
                "test_procedure": "Verify ePHI transmission encryption.",
                "policies": ["phi-transmission-encryption", "network-encryption"]
            },
            
            # Breach Notification Rule (Omnibus)
            "HIPAA.164.312.a.5": {
                "id": "HIPAA.164.312.a.5",
                "title": "Breach Notification",
                "description": "Implement policies and procedures for breach notification.",
                "severity": "HIGH",
                "category": "Breach Notification",
                "safeguard": "Administrative",
                "remediation": "Develop and implement breach notification procedures.",
                "test_procedure": "Review breach notification procedures.",
                "policies": ["breach-notification-procedures", "phi-breach-notification"]
            }
        }
    
    def get_controls_by_safeguard(self, safeguard: str) -> List[Dict]:
        """Get controls filtered by safeguard type"""
        return [
            control for control in self.controls.values()
            if control.get("safeguard") == safeguard
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
