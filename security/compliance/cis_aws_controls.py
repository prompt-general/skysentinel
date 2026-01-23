from typing import Dict, List

class CIS_AWS_Controls:
    """CIS AWS Foundations Benchmark Controls Implementation"""
    
    def __init__(self):
        self.controls = self._load_all_controls()
    
    def _load_all_controls(self) -> Dict[str, Dict]:
        """Load all CIS AWS Foundations controls"""
        return {
            # Identity and Access Management
            "CIS.1.1": {
                "id": "CIS.1.1",
                "title": "Avoid the use of the 'root' account",
                "description": "The 'root' account has unrestricted access to all resources in the AWS account.",
                "severity": "HIGH",
                "category": "IAM",
                "remediation": "Create individual IAM users for administrative tasks and avoid using the root account for daily operations.",
                "test_procedure": "Check CloudTrail for root account usage and verify MFA is enabled on root account.",
                "policies": ["no-root-account-usage", "root-account-mfa-required"]
            },
            
            "CIS.1.2": {
                "id": "CIS.1.2",
                "title": "Ensure multi-factor authentication (MFA) is enabled for all IAM users",
                "description": "MFA adds an extra layer of protection on top of user name and password.",
                "severity": "HIGH",
                "category": "IAM",
                "remediation": "Enable MFA for all IAM users with console access.",
                "test_procedure": "List all IAM users and verify MFA devices are attached.",
                "policies": ["require-mfa-for-iam-users"]
            },
            
            "CIS.1.3": {
                "id": "CIS.1.3",
                "title": "Ensure credentials unused for 90 days or greater are disabled",
                "description": "Disable credentials that have been unused for 90 days or more.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Configure IAM password policy to expire credentials after 90 days of inactivity.",
                "test_procedure": "Check IAM credential reports for users with unused credentials.",
                "policies": ["disable-unused-credentials"]
            },
            
            "CIS.1.4": {
                "id": "CIS.1.4",
                "title": "Ensure access keys are rotated every 90 days or less",
                "description": "Access keys should be rotated regularly to reduce the window of opportunity for compromised keys.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Implement automated access key rotation every 90 days.",
                "test_procedure": "Check IAM credential reports for access keys older than 90 days.",
                "policies": ["rotate-access-keys-90-days"]
            },
            
            # Storage
            "CIS.2.1": {
                "id": "CIS.2.1",
                "title": "Ensure S3 bucket policy deny HTTP requests",
                "description": "S3 buckets should deny HTTP requests to enforce encryption in transit.",
                "severity": "MEDIUM",
                "category": "Storage",
                "remediation": "Update bucket policies to deny requests that don't use SSL/TLS.",
                "test_procedure": "Review S3 bucket policies for SSL/TLS requirements.",
                "policies": ["s3-ssl-required"]
            },
            
            "CIS.2.2": {
                "id": "CIS.2.2",
                "title": "Ensure S3 bucket encryption is enabled",
                "description": "S3 bucket should have encryption enabled to protect data at rest.",
                "severity": "MEDIUM",
                "category": "Storage",
                "remediation": "Enable server-side encryption on all S3 buckets.",
                "test_procedure": "Check S3 bucket configurations for encryption settings.",
                "policies": ["s3-encryption-required"]
            },
            
            "CIS.2.3": {
                "id": "CIS.2.3",
                "title": "Ensure S3 bucket public access is blocked",
                "description": "S3 buckets should block public access to prevent unauthorized data exposure.",
                "severity": "HIGH",
                "category": "Storage",
                "remediation": "Configure S3 Block Public Access settings at account and bucket level.",
                "test_procedure": "Verify S3 bucket public access block settings.",
                "policies": ["s3-no-public-access"]
            },
            
            # Logging
            "CIS.3.1": {
                "id": "CIS.3.1",
                "title": "Ensure CloudTrail is enabled in all regions",
                "description": "CloudTrail should be enabled in all regions to log API calls.",
                "severity": "HIGH",
                "category": "Logging",
                "remediation": "Enable CloudTrail in all AWS regions.",
                "test_procedure": "Check CloudTrail status in all regions.",
                "policies": ["cloudtrail-enabled-all-regions"]
            },
            
            "CIS.3.2": {
                "id": "CIS.3.2",
                "title": "Ensure CloudTrail logs are encrypted at rest using KMS",
                "description": "CloudTrail logs should be encrypted using KMS to protect log data.",
                "severity": "MEDIUM",
                "category": "Logging",
                "remediation": "Enable KMS encryption for CloudTrail logs.",
                "test_procedure": "Verify CloudTrail KMS encryption configuration.",
                "policies": ["cloudtrail-kms-encryption"]
            },
            
            "CIS.3.3": {
                "id": "CIS.3.3",
                "title": "Ensure CloudTrail log file validation is enabled",
                "description": "CloudTrail log file validation should be enabled to detect tampering.",
                "severity": "MEDIUM",
                "category": "Logging",
                "remediation": "Enable log file validation for all CloudTrail trails.",
                "test_procedure": "Check CloudTrail log file validation settings.",
                "policies": ["cloudtrail-log-validation"]
            },
            
            # Monitoring
            "CIS.4.1": {
                "id": "CIS.4.1",
                "title": "Ensure a log metric filter and alarm exist for unauthorized API calls",
                "description": "Create CloudWatch alarms for unauthorized API calls.",
                "severity": "MEDIUM",
                "category": "Monitoring",
                "remediation": "Create CloudWatch metric filters and alarms for unauthorized API calls.",
                "test_procedure": "Verify CloudWatch alarms for unauthorized API calls exist.",
                "policies": ["unauthorized-api-calls-alarm"]
            },
            
            "CIS.4.2": {
                "id": "CIS.4.2",
                "title": "Ensure a log metric filter and alarm exist for root account usage",
                "description": "Create CloudWatch alarms for root account usage.",
                "severity": "HIGH",
                "category": "Monitoring",
                "remediation": "Create CloudWatch metric filters and alarms for root account usage.",
                "test_procedure": "Verify CloudWatch alarms for root account usage exist.",
                "policies": ["root-account-usage-alarm"]
            },
            
            # Network Security
            "CIS.5.1": {
                "id": "CIS.5.1",
                "title": "Ensure no security groups allow inbound 0.0.0.0/0 to port 22",
                "description": "Security groups should not allow unrestricted SSH access from anywhere.",
                "severity": "HIGH",
                "category": "Network",
                "remediation": "Restrict SSH access to specific IP ranges only.",
                "test_procedure": "Review security group rules for unrestricted SSH access.",
                "policies": ["no-public-ssh", "restrict-ssh-access"]
            },
            
            "CIS.5.2": {
                "id": "CIS.5.2",
                "title": "Ensure no security groups allow inbound 0.0.0.0/0 to port 3389",
                "description": "Security groups should not allow unrestricted RDP access from anywhere.",
                "severity": "HIGH",
                "category": "Network",
                "remediation": "Restrict RDP access to specific IP ranges only.",
                "test_procedure": "Review security group rules for unrestricted RDP access.",
                "policies": ["no-public-rdp", "restrict-rdp-access"]
            },
            
            "CIS.5.3": {
                "id": "CIS.5.3",
                "title": "Ensure the default security group of every VPC restricts all traffic",
                "description": "Default security groups should restrict all inbound and outbound traffic.",
                "severity": "MEDIUM",
                "category": "Network",
                "remediation": "Remove all rules from default security groups.",
                "test_procedure": "Check default security group rules in all VPCs.",
                "policies": ["default-sg-restricted"]
            },
            
            # Additional Advanced Controls
            "CIS.6.1": {
                "id": "CIS.6.1",
                "title": "Ensure IAM password policy requires at least one uppercase letter",
                "description": "IAM password policy should require uppercase letters for password complexity.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Update IAM password policy to require uppercase letters.",
                "test_procedure": "Review IAM password policy settings.",
                "policies": ["password-complexity-uppercase"]
            },
            
            "CIS.6.2": {
                "id": "CIS.6.2",
                "title": "Ensure IAM password policy requires at least one lowercase letter",
                "description": "IAM password policy should require lowercase letters for password complexity.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Update IAM password policy to require lowercase letters.",
                "test_procedure": "Review IAM password policy settings.",
                "policies": ["password-complexity-lowercase"]
            },
            
            "CIS.6.3": {
                "id": "CIS.6.3",
                "title": "Ensure IAM password policy requires at least one symbol",
                "description": "IAM password policy should require symbols for password complexity.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Update IAM password policy to require symbols.",
                "test_procedure": "Review IAM password policy settings.",
                "policies": ["password-complexity-symbols"]
            },
            
            "CIS.6.4": {
                "id": "CIS.6.4",
                "title": "Ensure IAM password policy requires at least one number",
                "description": "IAM password policy should require numbers for password complexity.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Update IAM password policy to require numbers.",
                "test_procedure": "Review IAM password policy settings.",
                "policies": ["password-complexity-numbers"]
            },
            
            "CIS.6.5": {
                "id": "CIS.6.5",
                "title": "Ensure IAM password policy prevents password reuse",
                "description": "IAM password policy should prevent password reuse.",
                "severity": "MEDIUM",
                "category": "IAM",
                "remediation": "Configure password history to prevent reuse.",
                "test_procedure": "Review IAM password policy settings.",
                "policies": ["password-no-reuse"]
            }
        }
    
    def get_controls_by_category(self, category: str) -> List[Dict]:
        """Get controls filtered by category"""
        return [
            control for control in self.controls.values()
            if control.get("category") == category
        ]
    
    def get_controls_by_severity(self, severity: str) -> List[Dict]:
        """Get controls filtered by severity"""
        return [
            control for control in self.controls.values()
            if control.get("severity") == severity
        ]
    
    def get_control(self, control_id: str) -> Dict:
        """Get a specific control by ID"""
        return self.controls.get(control_id, {})
    
    def get_all_control_ids(self) -> List[str]:
        """Get all control IDs"""
        return list(self.controls.keys())
