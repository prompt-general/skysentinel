from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

class ComplianceMonitor:
    """Compliance monitoring and alerting system"""
    
    def __init__(self, neo4j_driver, notification_service):
        self.driver = neo4j_driver
        self.notification_service = notification_service
        self.alert_thresholds = self._load_alert_thresholds()
    
    def _load_alert_thresholds(self) -> Dict[str, Dict]:
        """Load alert thresholds for compliance monitoring"""
        return {
            "compliance_percentage": {
                "warning": 80,
                "critical": 70
            },
            "critical_violations": {
                "warning": 5,
                "critical": 10
            },
            "days_since_last_scan": {
                "warning": 30,
                "critical": 60
            },
            "unremediated_findings": {
                "warning": 10,
                "critical": 20
            }
        }
    
    def monitor_compliance_status(self, tenant_id: str) -> Dict[str, Any]:
        """Monitor overall compliance status for a tenant"""
        # Get latest compliance results for all standards
        query = """
        MATCH (c:ComplianceResult)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WITH c.standard as standard, c.compliance_percentage as compliance
        RETURN standard, max(compliance) as latest_compliance
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            compliance_data = [dict(record) for record in result]
        
        # Check for compliance alerts
        alerts = []
        overall_compliance = 0
        
        if compliance_data:
            total_compliance = sum(data["latest_compliance"] for data in compliance_data)
            overall_compliance = total_compliance / len(compliance_data)
            
            # Check compliance percentage thresholds
            if overall_compliance < self.alert_thresholds["compliance_percentage"]["critical"]:
                alerts.append({
                    "type": "critical",
                    "message": f"Overall compliance ({overall_compliance:.1f}%) is below critical threshold",
                    "recommendation": "Immediate action required to address compliance gaps"
                })
            elif overall_compliance < self.alert_thresholds["compliance_percentage"]["warning"]:
                alerts.append({
                    "type": "warning",
                    "message": f"Overall compliance ({overall_compliance:.1f}%) is below warning threshold",
                    "recommendation": "Review and address compliance issues"
                })
        
        # Check for critical violations
        critical_violations = self._get_critical_violations(tenant_id)
        if len(critical_violations) > self.alert_thresholds["critical_violations"]["critical"]:
            alerts.append({
                "type": "critical",
                "message": f"Critical violations count ({len(critical_violations)}) exceeds threshold",
                "recommendation": "Immediate remediation required for critical violations"
            })
        elif len(critical_violations) > self.alert_thresholds["critical_violations"]["warning"]:
            alerts.append({
                "type": "warning",
                "message": f"Critical violations count ({len(critical_violations)}) exceeds warning threshold",
                "recommendation": "Address critical violations promptly"
            })
        
        # Check for stale compliance data
        last_scan_date = self._get_last_compliance_scan_date(tenant_id)
        if last_scan_date:
            days_since_scan = (datetime.utcnow() - last_scan_date).days
            if days_since_scan > self.alert_thresholds["days_since_last_scan"]["critical"]:
                alerts.append({
                    "type": "critical",
                    "message": f"Compliance scan is {days_since_scan} days old",
                    "recommendation": "Run compliance assessment immediately"
                })
            elif days_since_scan > self.alert_thresholds["days_since_last_scan"]["warning"]:
                alerts.append({
                    "type": "warning",
                    "message": f"Compliance scan is {days_since_scan} days old",
                    "recommendation": "Schedule compliance assessment"
                })
        
        # Send notifications for alerts
        for alert in alerts:
            self._send_compliance_alert(tenant_id, alert)
        
        return {
            "tenant_id": tenant_id,
            "overall_compliance": overall_compliance,
            "alerts": alerts,
            "critical_violations": len(critical_violations),
            "last_scan_date": last_scan_date.isoformat() if last_scan_date else None,
            "monitoring_timestamp": datetime.utcnow().isoformat()
        }
    
    def monitor_penetration_test_status(self, tenant_id: str) -> Dict[str, Any]:
        """Monitor penetration test status and findings"""
        # Get latest penetration test results
        query = """
        MATCH (t:PenetrationTest)-[:BELONGS_TO]->(tenant:Tenant {id: $tenant_id})
        WITH t.status as status, t.end_time as end_time
        RETURN status, max(end_time) as latest_end_time
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            test_data = [dict(record) for record in result]
        
        alerts = []
        
        # Check for overdue tests
        latest_test_date = None
        if test_data:
            latest_test_date = test_data[0].get("latest_end_time")
            if latest_test_date:
                days_since_test = (datetime.utcnow() - latest_test_date).days
                if days_since_test > 90:  # Quarterly testing recommended
                    alerts.append({
                        "type": "warning",
                        "message": f"Penetration test is {days_since_test} days old",
                        "recommendation": "Schedule quarterly penetration test"
                    })
        
        # Check for unremediated critical findings
        unremediated_critical = self._get_unremediated_findings(tenant_id, "critical")
        if len(unremediated_critical) > self.alert_thresholds["unremediated_findings"]["critical"]:
            alerts.append({
                "type": "critical",
                "message": f"Unremediated critical findings ({len(unremediated_critical)}) exceed threshold",
                "recommendation": "Immediate remediation required for critical findings"
            })
        elif len(unremediated_critical) > self.alert_thresholds["unremediated_findings"]["warning"]:
            alerts.append({
                "type": "warning",
                "message": f"Unremediated critical findings ({len(unremediated_critical)}) exceed warning threshold",
                "recommendation": "Address critical findings promptly"
            })
        
        # Send notifications for alerts
        for alert in alerts:
            self._send_security_alert(tenant_id, alert)
        
        return {
            "tenant_id": tenant_id,
            "latest_test_date": latest_test_date.isoformat() if latest_test_date else None,
            "unremediated_critical_findings": len(unremediated_critical),
            "alerts": alerts,
            "monitoring_timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_compliance_dashboard_data(self, tenant_id: str) -> Dict[str, Any]:
        """Generate data for compliance dashboard"""
        # Get compliance trends
        compliance_trends = self._get_compliance_trends(tenant_id, days=30)
        
        # Get violation trends
        violation_trends = self._get_violation_trends(tenant_id, days=30)
        
        # Get remediation metrics
        remediation_metrics = self._get_remediation_metrics(tenant_id)
        
        # Get risk assessment
        risk_assessment = self._calculate_risk_score(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "generated_at": datetime.utcnow().isoformat(),
            "compliance_trends": compliance_trends,
            "violation_trends": violation_trends,
            "remediation_metrics": remediation_metrics,
            "risk_assessment": risk_assessment,
            "summary": {
                "overall_compliance": self._get_current_compliance_percentage(tenant_id),
                "total_violations": self._get_total_violations(tenant_id),
                "critical_violations": len(self._get_critical_violations(tenant_id)),
                "remediation_rate": remediation_metrics.get("remediation_rate", 0),
                "risk_score": risk_assessment.get("overall_score", 0)
            }
        }
    
    def schedule_compliance_checks(self, tenant_id: str, schedule: str = "daily") -> str:
        """Schedule automated compliance checks"""
        # This would integrate with a job scheduler
        job_id = f"compliance_check_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        job_config = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "schedule": schedule,
            "check_types": ["compliance_assessment", "violation_monitoring", "remediation_tracking"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store job configuration
        query = """
        CREATE (j:ComplianceJob {
            id: $job_id,
            tenant_id: $tenant_id,
            schedule: $schedule,
            check_types: $check_types,
            config: $config,
            created_at: datetime()
        })
        """
        
        with self.driver.session() as session:
            session.run(query,
                job_id=job_id,
                tenant_id=tenant_id,
                schedule=schedule,
                check_types=json.dumps(job_config["check_types"]),
                config=json.dumps(job_config)
            )
        
        return job_id
    
    def _get_critical_violations(self, tenant_id: str) -> List[Dict]:
        """Get critical violations for a tenant"""
        query = """
        MATCH (v:Violation)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WHERE v.severity = 'CRITICAL' AND v.status = 'OPEN'
        RETURN v
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            return [dict(record["v"]) for record in result]
    
    def _get_last_compliance_scan_date(self, tenant_id: str) -> Optional[datetime]:
        """Get the date of the last compliance scan"""
        query = """
        MATCH (c:ComplianceResult)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        RETURN max(c.evaluation_date) as last_scan
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            record = result.single()
            if record and record["last_scan"]:
                return datetime.fromisoformat(record["last_scan"].replace('Z', '+00:00'))
        return None
    
    def _get_unremediated_findings(self, tenant_id: str, severity: str) -> List[Dict]:
        """Get unremediated findings by severity"""
        query = """
        MATCH (f:Finding)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WHERE f.severity = $severity AND f.status = 'OPEN'
        RETURN f
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id, severity=severity.upper())
            return [dict(record["f"]) for record in result]
    
    def _send_compliance_alert(self, tenant_id: str, alert: Dict):
        """Send compliance alert notification"""
        message = f"🔒 Compliance Alert for {tenant_id}: {alert['message']}"
        
        if self.notification_service:
            self.notification_service.send_alert({
                "type": "compliance",
                "severity": alert["type"],
                "tenant_id": tenant_id,
                "message": message,
                "recommendation": alert["recommendation"],
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def _send_security_alert(self, tenant_id: str, alert: Dict):
        """Send security alert notification"""
        message = f"🛡️ Security Alert for {tenant_id}: {alert['message']}"
        
        if self.notification_service:
            self.notification_service.send_alert({
                "type": "security",
                "severity": alert["type"],
                "tenant_id": tenant_id,
                "message": message,
                "recommendation": alert["recommendation"],
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def _get_compliance_trends(self, tenant_id: str, days: int) -> List[Dict]:
        """Get compliance trends over time"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
        MATCH (c:ComplianceResult)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WHERE c.evaluation_date >= datetime($start_date)
        RETURN c.evaluation_date as date, c.standard as standard, c.compliance_percentage as compliance
        ORDER BY date
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id, start_date=start_date.isoformat())
            return [dict(record) for record in result]
    
    def _get_violation_trends(self, tenant_id: str, days: int) -> List[Dict]:
        """Get violation trends over time"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
        MATCH (v:Violation)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WHERE v.created_at >= datetime($start_date)
        RETURN date(v.created_at) as date, v.severity as severity, count(*) as count
        ORDER BY date
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id, start_date=start_date.isoformat())
            return [dict(record) for record in result]
    
    def _get_remediation_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """Get remediation metrics"""
        query = """
        MATCH (f:Finding)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        RETURN f.status as status, count(*) as count
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            status_counts = {record["status"]: record["count"] for record in result}
        
        total_findings = sum(status_counts.values())
        remediated_findings = status_counts.get("REMEDIATED", 0)
        remediation_rate = (remediated_findings / total_findings * 100) if total_findings > 0 else 0
        
        return {
            "total_findings": total_findings,
            "remediated_findings": remediated_findings,
            "open_findings": status_counts.get("OPEN", 0),
            "remediation_rate": remediation_rate
        }
    
    def _calculate_risk_score(self, tenant_id: str) -> Dict[str, Any]:
        """Calculate overall risk score"""
        # Get violations by severity
        query = """
        MATCH (v:Violation)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WHERE v.status = 'OPEN'
        RETURN v.severity as severity, count(*) as count
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            severity_counts = {record["severity"]: record["count"] for record in result}
        
        # Calculate risk score (weighted by severity)
        weights = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1}
        total_score = 0
        
        for severity, count in severity_counts.items():
            weight = weights.get(severity, 1)
            total_score += count * weight
        
        # Normalize to 0-100 scale
        max_possible_score = 100  # Adjust based on your risk model
        normalized_score = min(total_score, max_possible_score)
        
        # Determine risk level
        if normalized_score >= 80:
            risk_level = "CRITICAL"
        elif normalized_score >= 60:
            risk_level = "HIGH"
        elif normalized_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "overall_score": normalized_score,
            "risk_level": risk_level,
            "severity_breakdown": severity_counts,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _get_current_compliance_percentage(self, tenant_id: str) -> float:
        """Get current overall compliance percentage"""
        query = """
        MATCH (c:ComplianceResult)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        WITH c.standard as standard, c.compliance_percentage as compliance
        RETURN avg(compliance) as overall_compliance
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            record = result.single()
            return record["overall_compliance"] if record else 0.0
    
    def _get_total_violations(self, tenant_id: str) -> int:
        """Get total violations for a tenant"""
        query = """
        MATCH (v:Violation)-[:BELONGS_TO]->(t:Tenant {id: $tenant_id})
        RETURN count(*) as total
        """
        
        with self.driver.session() as session:
            result = session.run(query, tenant_id=tenant_id)
            record = result.single()
            return record["total"] if record else 0
