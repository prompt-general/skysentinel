from typing import Dict, List

class PCI_DSS_Controls:
    """PCI DSS 4.0 Controls Implementation"""
    
    def __init__(self):
        self.controls = self._load_all_controls()
    
    def _load_all_controls(self) -> Dict[str, Dict]:
        """Load all PCI DSS controls"""
        return {
            # Requirement 1: Install and maintain network security controls
            "PCI.1.1": {
                "id": "PCI.1.1",
                "title": "Firewall configuration standards",
                "description": "Establish and implement firewall configuration standards.",
                "severity": "HIGH",
                "category": "Network Security",
                "requirement": "1",
                "remediation": "Document and implement firewall configuration standards, review every six months.",
                "test_procedure": "Review firewall configuration documentation and actual settings.",
                "policies": ["firewall-configuration-standards", "firewall-review-policy"]
            },
            
            "PCI.1.2": {
                "id": "PCI.1.2",
                "title": "Firewall rules for all traffic",
                "description": "Develop firewall configuration standards that include all traffic.",
                "severity": "HIGH",
                "category": "Network Security",
                "requirement": "1",
                "remediation": "Configure firewall rules to explicitly allow/deny all traffic types.",
                "test_procedure": "Verify firewall rules cover all traffic types and are documented.",
                "policies": ["comprehensive-firewall-rules"]
            },
            
            "PCI.1.3": {
                "id": "PCI.1.3",
                "title": "Deny all traffic by default",
                "description": "Configure firewall rules to deny all traffic by default.",
                "severity": "HIGH",
                "category": "Network Security",
                "requirement": "1",
                "remediation": "Implement deny-by-default firewall policy with explicit allow rules.",
                "test_procedure": "Verify default deny policy is in place.",
                "policies": ["deny-by-default-firewall"]
            },
            
            # Requirement 2: Apply Secure Configuration to All System Components
            "PCI.2.1": {
                "id": "PCI.2.1",
                "title": "Secure configuration standards",
                "description": "Establish and implement secure configuration standards for all system components.",
                "severity": "HIGH",
                "category": "Secure Configuration",
                "requirement": "2",
                "remediation": "Develop and implement secure configuration standards.",
                "test_procedure": "Review secure configuration documentation and implementation.",
                "policies": ["secure-configuration-standards"]
            },
            
            "PCI.2.2": {
                "id": "PCI.2.2",
                "title": "System component hardening",
                "description": "Develop configuration standards for hardening system components.",
                "severity": "HIGH",
                "category": "Secure Configuration",
                "requirement": "2",
                "remediation": "Implement system hardening standards and procedures.",
                "test_procedure": "Verify system hardening procedures are implemented.",
                "policies": ["system-hardening-standards"]
            },
            
            "PCI.2.3": {
                "id": "PCI.2.3",
                "title": "Encrypt all non-console administrative access",
                "description": "Encrypt all non-console administrative access using strong cryptography.",
                "severity": "HIGH",
                "category": "Secure Configuration",
                "requirement": "2",
                "remediation": "Implement encrypted administrative access protocols.",
                "test_procedure": "Verify administrative access uses encryption.",
                "policies": ["encrypted-admin-access"]
            },
            
            # Requirement 3: Protect Cardholder Data
            "PCI.3.1": {
                "id": "PCI.3.1",
                "title": "Keep cardholder data to a minimum",
                "description": "Keep cardholder data to a minimum by implementing data retention policies.",
                "severity": "HIGH",
                "category": "Data Protection",
                "requirement": "3",
                "remediation": "Implement data retention and disposal policies.",
                "test_procedure": "Review data retention policies and verify implementation.",
                "policies": ["data-retention-policy", "data-minimization"]
            },
            
            "PCI.3.2": {
                "id": "PCI.3.2",
                "title": "Sensitive authentication data retention limit",
                "description": "Do not store sensitive authentication data after authorization.",
                "severity": "HIGH",
                "category": "Data Protection",
                "requirement": "3",
                "remediation": "Implement procedures to not store sensitive authentication data.",
                "test_procedure": "Verify sensitive authentication data is not stored.",
                "policies": ["no-sensitive-auth-storage"]
            },
            
            "PCI.3.3": {
                "id": "PCI.3.3",
                "title": "Mask PAN when displayed",
                "description": "Mask PAN when displayed on screens, paper receipts, etc.",
                "severity": "HIGH",
                "category": "Data Protection",
                "requirement": "3",
                "remediation": "Implement PAN masking in all displays and outputs.",
                "test_procedure": "Verify PAN masking is implemented correctly.",
                "policies": ["pan-masking-policy"]
            },
            
            "PCI.3.4": {
                "id": "PCI.3.4",
                "title": "Render cardholder data unreadable",
                "description": "Render cardholder data unreadable when stored.",
                "severity": "HIGH",
                "category": "Data Protection",
                "requirement": "3",
                "remediation": "Implement strong cryptography for stored cardholder data.",
                "test_procedure": "Verify stored cardholder data is encrypted.",
                "policies": ["cardholder-data-encryption"]
            },
            
            # Requirement 4: Protect Cardholder Data in Transit
            "PCI.4.1": {
                "id": "PCI.4.1",
                "title": "Strong cryptography and security protocols",
                "description": "Use strong cryptography and security protocols to protect cardholder data in transit.",
                "severity": "HIGH",
                "category": "Data Protection",
                "requirement": "4",
                "remediation": "Implement TLS 1.2+ for all data in transit.",
                "test_procedure": "Verify TLS 1.2+ is used for all data transmission.",
                "policies": ["tls-12-plus-required", "strong-cryptography"]
            },
            
            "PCI.4.2": {
                "id": "PCI.4.2",
                "title": "Secure cryptographic protocols",
                "description": "Never send unprotected PANs by end-user messaging technologies.",
                "severity": "HIGH",
                "category": "Data Protection",
                "requirement": "4",
                "remediation": "Implement secure channels for all PAN transmission.",
                "test_procedure": "Verify PAN is never sent unprotected.",
                "policies": ["secure-pan-transmission"]
            },
            
            # Requirement 5: Protect All Systems Against Malware
            "PCI.5.1": {
                "id": "PCI.5.1",
                "title": "Anti-virus software",
                "description": "Deploy anti-virus software on all systems commonly affected by malware.",
                "severity": "HIGH",
                "category": "Malware Protection",
                "requirement": "5",
                "remediation": "Install and maintain anti-virus software on all relevant systems.",
                "test_procedure": "Verify anti-virus software is installed and running.",
                "policies": ["anti-virus-required", "malware-protection"]
            },
            
            "PCI.5.2": {
                "id": "PCI.5.2",
                "title": "Anti-virus mechanisms update",
                "description": "Update anti-virus mechanisms regularly.",
                "severity": "HIGH",
                "category": "Malware Protection",
                "requirement": "5",
                "remediation": "Implement automated anti-virus updates.",
                "test_procedure": "Verify anti-virus definitions are current.",
                "policies": ["anti-virus-updates"]
            },
            
            # Requirement 6: Develop and Maintain Secure Systems and Software
            "PCI.6.1": {
                "id": "PCI.6.1",
                "title": "Security vulnerability management process",
                "description": "Develop a process for identifying and managing security vulnerabilities.",
                "severity": "HIGH",
                "category": "Secure Development",
                "requirement": "6",
                "remediation": "Implement vulnerability management process.",
                "test_procedure": "Review vulnerability management procedures.",
                "policies": ["vulnerability-management-process"]
            },
            
            "PCI.6.2": {
                "id": "PCI.6.2",
                "title": "Protect all system components and software",
                "description": "Protect all system components and software from vulnerabilities.",
                "severity": "HIGH",
                "category": "Secure Development",
                "requirement": "6",
                "remediation": "Implement patch management process.",
                "test_procedure": "Verify patch management procedures are in place.",
                "policies": ["patch-management-process"]
            },
            
            # Requirement 7: Restrict Access to Cardholder Data
            "PCI.7.1": {
                "id": "PCI.7.1",
                "title": "Access control system",
                "description": "Limit access to cardholder data based on need to know.",
                "severity": "HIGH",
                "category": "Access Control",
                "requirement": "7",
                "remediation": "Implement role-based access control.",
                "test_procedure": "Verify access controls are based on job function.",
                "policies": ["role-based-access-control", "need-to-know-access"]
            },
            
            "PCI.7.2": {
                "id": "PCI.7.2",
                "title": "Unique identification for each person",
                "description": "Assign a unique identification to each person with computer access.",
                "severity": "HIGH",
                "category": "Access Control",
                "requirement": "7",
                "remediation": "Implement unique user accounts for all individuals.",
                "test_procedure": "Verify each user has a unique account.",
                "policies": ["unique-user-accounts"]
            },
            
            # Requirement 8: Identify and Authenticate Access to System Components
            "PCI.8.1": {
                "id": "PCI.8.1",
                "title": "Authentication policies and procedures",
                "description": "Implement authentication policies and procedures for all users.",
                "severity": "HIGH",
                "category": "Authentication",
                "requirement": "8",
                "remediation": "Develop and implement authentication policies.",
                "test_procedure": "Review authentication policies and procedures.",
                "policies": ["authentication-policies"]
            },
            
            "PCI.8.2": {
                "id": "PCI.8.2",
                "title": "Multi-factor authentication",
                "description": "Use multi-factor authentication for all remote network access.",
                "severity": "HIGH",
                "category": "Authentication",
                "requirement": "8",
                "remediation": "Implement MFA for all remote access.",
                "test_procedure": "Verify MFA is required for remote access.",
                "policies": ["mfa-remote-access", "multi-factor-authentication"]
            },
            
            # Requirement 9: Restrict Physical Access to Cardholder Data
            "PCI.9.1": {
                "id": "PCI.9.1",
                "title": "Physical access controls",
                "description": "Develop and implement procedures to limit physical access.",
                "severity": "MEDIUM",
                "category": "Physical Security",
                "requirement": "9",
                "remediation": "Implement physical access controls.",
                "test_procedure": "Review physical access control procedures.",
                "policies": ["physical-access-controls"]
            },
            
            # Requirement 10: Track and Monitor All Access to Network Resources
            "PCI.10.1": {
                "id": "PCI.10.1",
                "title": "Audit logging",
                "description": "Implement audit trails to link all access to system components.",
                "severity": "HIGH",
                "category": "Logging and Monitoring",
                "requirement": "10",
                "remediation": "Implement comprehensive audit logging.",
                "test_procedure": "Verify audit logs capture all access.",
                "policies": ["comprehensive-audit-logging"]
            },
            
            "PCI.10.2": {
                "id": "PCI.10.2",
                "title": "Automated audit trails",
                "description": "Implement automated audit trails for all system components.",
                "severity": "HIGH",
                "category": "Logging and Monitoring",
                "requirement": "10",
                "remediation": "Configure automated audit logging.",
                "test_procedure": "Verify automated audit trails are implemented.",
                "policies": ["automated-audit-trails"]
            },
            
            # Requirement 11: Regularly Test Security Systems and Processes
            "PCI.11.1": {
                "id": "PCI.11.1",
                "title": "Security testing methodology",
                "description": "Implement security testing methodologies.",
                "severity": "HIGH",
                "category": "Security Testing",
                "requirement": "11",
                "remediation": "Develop and implement security testing procedures.",
                "test_procedure": "Review security testing methodologies.",
                "policies": ["security-testing-methodology"]
            },
            
            "PCI.11.2": {
                "id": "PCI.11.2",
                "title": "Run internal and external vulnerability scans",
                "description": "Run internal and external vulnerability scans at least quarterly.",
                "severity": "HIGH",
                "category": "Security Testing",
                "requirement": "11",
                "remediation": "Implement quarterly vulnerability scanning.",
                "test_procedure": "Verify vulnerability scanning schedule.",
                "policies": ["quarterly-vulnerability-scanning"]
            },
            
            # Requirement 12: Maintain an Information Security Policy
            "PCI.12.1": {
                "id": "PCI.12.1",
                "title": "Information security policy",
                "description": "Establish, publish, and maintain an information security policy.",
                "severity": "MEDIUM",
                "category": "Policy Management",
                "requirement": "12",
                "remediation": "Develop and maintain information security policy.",
                "test_procedure": "Review information security policy.",
                "policies": ["information-security-policy"]
            }
        }
    
    def get_controls_by_requirement(self, requirement: str) -> List[Dict]:
        """Get controls filtered by requirement number"""
        return [
            control for control in self.controls.values()
            if control.get("requirement") == requirement
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
