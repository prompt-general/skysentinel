#!/usr/bin/env python3
"""
SkySentinel CI Action - Simplified GitHub Action for IaC Security Evaluation

This action evaluates Infrastructure as Code files against SkySentinel security policies.
"""

import requests
import json
import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SkySentinelCIAction:
    """SkySentinel CI Action for GitHub"""
    
    def __init__(self):
        self.api_url = os.getenv('INPUT_API_URL')
        self.api_key = os.getenv('INPUT_API_KEY')
        self.iac_type = os.getenv('INPUT_IAC_TYPE')
        self.iac_file = os.getenv('INPUT_IAC_FILE')
        self.context_json = os.getenv('INPUT_CONTEXT', '{}')
        self.fail_on_critical = os.getenv('INPUT_FAIL_ON_CRITICAL', 'true').lower() == 'true'
        self.fail_on_high = os.getenv('INPUT_FAIL_ON_HIGH', 'false').lower() == 'true'
        self.timeout = int(os.getenv('INPUT_TIMEOUT', '300'))
        
        # GitHub environment variables
        self.github_context = {
            'repository': os.getenv('GITHUB_REPOSITORY', ''),
            'ref': os.getenv('GITHUB_REF', ''),
            'sha': os.getenv('GITHUB_SHA', ''),
            'run_id': os.getenv('GITHUB_RUN_ID', ''),
            'run_number': os.getenv('GITHUB_RUN_NUMBER', ''),
            'actor': os.getenv('GITHUB_ACTOR', ''),
            'event_name': os.getenv('GITHUB_EVENT_NAME', ''),
            'workspace': os.getenv('GITHUB_WORKSPACE', ''),
        }
        
        # PR specific context
        if os.getenv('GITHUB_EVENT_NAME') == 'pull_request':
            self.github_context.update({
                'pr_number': os.getenv('GITHUB_REF_NAME', '').replace('refs/pull/', '').replace('/merge', ''),
                'base_ref': os.getenv('GITHUB_BASE_REF', ''),
                'head_ref': os.getenv('GITHUB_HEAD_REF', ''),
            })
    
    def validate_inputs(self) -> bool:
        """Validate required inputs"""
        if not self.api_url:
            logger.error("INPUT_API_URL is required")
            return False
        
        if not self.api_key:
            logger.error("INPUT_API_KEY is required")
            return False
        
        if not self.iac_type:
            logger.error("INPUT_IAC_TYPE is required")
            return False
        
        if not self.iac_file:
            logger.error("INPUT_IAC_FILE is required")
            return False
        
        if not Path(self.iac_file).exists():
            logger.error(f"IaC file not found: {self.iac_file}")
            return False
        
        return True
    
    def load_iac_content(self) -> Dict[str, Any]:
        """Load IaC file content"""
        try:
            with open(self.iac_file, 'r') as f:
                if self.iac_file.endswith('.json'):
                    return json.load(f)
                elif self.iac_file.endswith(('.yaml', '.yml')):
                    import yaml
                    return yaml.safe_load(f)
                else:
                    # Try to parse as JSON first, then as raw content
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        return {'raw_content': f.read()}
        except Exception as e:
            logger.error(f"Failed to load IaC file: {e}")
            raise
    
    def prepare_context(self) -> Dict[str, Any]:
        """Prepare evaluation context"""
        try:
            user_context = json.loads(self.context_json) if self.context_json else {}
        except json.JSONDecodeError:
            logger.warning("Invalid context JSON, using empty context")
            user_context = {}
        
        # Merge with GitHub context
        context = {
            'github': self.github_context,
            'action': {
                'name': 'skysentinel-ci-action',
                'version': '1.0.0',
                'fail_on_critical': self.fail_on_critical,
                'fail_on_high': self.fail_on_high
            },
            **user_context
        }
        
        return context
    
    def submit_evaluation(self, iac_content: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
        """Submit evaluation to SkySentinel API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'skysentinel-ci-action/1.0.0'
        }
        
        data = {
            'iac_type': self.iac_type,
            'iac_content': iac_content,
            'context': context,
            'priority': 'high'
        }
        
        try:
            logger.info(f"Submitting evaluation to {self.api_url}")
            response = requests.post(f'{self.api_url}/api/v1/cicd/evaluate', json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            evaluation = response.json()
            evaluation_id = evaluation.get('evaluation_id')
            logger.info(f"Evaluation submitted with ID: {evaluation_id}")
            return evaluation_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit evaluation: {e}")
            return None
    
    def wait_for_result(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Wait for evaluation result"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'skysentinel-ci-action/1.0.0'
        }
        
        start_time = time.time()
        logger.info(f"Waiting for evaluation {evaluation_id} result (timeout: {self.timeout}s)")
        
        while time.time() - start_time < self.timeout:
            try:
                response = requests.get(f'{self.api_url}/api/v1/cicd/evaluate/{evaluation_id}', headers=headers, timeout=10)
                response.raise_for_status()
                
                result = response.json()
                status = result.get('status')
                progress = result.get('progress', 0)
                
                logger.info(f"Evaluation status: {status} (progress: {progress}%)")
                
                if status == 'completed':
                    logger.info("Evaluation completed successfully")
                    return result
                elif status == 'failed':
                    logger.error(f"Evaluation failed: {result.get('error', 'Unknown error')}")
                    return result
                elif status == 'cancelled':
                    logger.warning("Evaluation was cancelled")
                    return result
                
                time.sleep(5)
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error checking evaluation status: {e}")
                time.sleep(5)
        
        logger.error("Timeout waiting for evaluation result")
        return None
    
    def process_result(self, result: Dict[str, Any]) -> int:
        """Process evaluation result and determine exit code"""
        if result.get('status') != 'completed':
            logger.error(f"Evaluation did not complete: {result.get('status')}")
            return 1
        
        evaluation_result = result.get('result', {})
        status = evaluation_result.get('status', 'unknown')
        violations = evaluation_result.get('violations', [])
        
        logger.info(f"Evaluation status: {status}")
        logger.info(f"Violations found: {len(violations)}")
        
        # Count violations by severity
        critical_count = sum(1 for v in violations if v.get('severity') == 'critical')
        high_count = sum(1 for v in violations if v.get('severity') == 'high')
        medium_count = sum(1 for v in violations if v.get('severity') == 'medium')
        low_count = sum(1 for v in violations if v.get('severity') == 'low')
        
        logger.info(f"Critical violations: {critical_count}")
        logger.info(f"High violations: {high_count}")
        logger.info(f"Medium violations: {medium_count}")
        logger.info(f"Low violations: {low_count}")
        
        # Set GitHub outputs
        self.set_github_outputs({
            'status': status,
            'violations': str(len(violations)),
            'critical_violations': str(critical_count),
            'high_violations': str(high_count),
            'medium_violations': str(medium_count),
            'low_violations': str(low_count),
            'evaluation_id': result.get('evaluation_id', ''),
        })
        
        # Print detailed results
        if violations:
            logger.info("Violations details:")
            for i, violation in enumerate(violations[:10]):  # Limit to 10 violations
                severity = violation.get('severity', 'unknown')
                message = violation.get('message', 'No message')
                policy = violation.get('policy_name', 'Unknown policy')
                logger.info(f"  {i+1}. [{severity.upper()}] {policy}: {message}")
            
            if len(violations) > 10:
                logger.info(f"  ... and {len(violations) - 10} more violations")
        
        # Determine exit code
        if status == 'block':
            logger.error("Evaluation blocked due to critical violations")
            return 1
        elif status == 'failure':
            logger.error("Evaluation failed")
            return 1
        elif self.fail_on_critical and critical_count > 0:
            logger.error("Failing due to critical violations")
            return 1
        elif self.fail_on_high and high_count > 0:
            logger.error("Failing due to high severity violations")
            return 1
        elif status == 'warn':
            logger.warning("Evaluation completed with warnings")
            return 0
        else:
            logger.info("Evaluation completed successfully")
            return 0
    
    def set_github_outputs(self, outputs: Dict[str, str]):
        """Set GitHub Action outputs"""
        output_file = os.environ.get('GITHUB_OUTPUT')
        if output_file:
            try:
                with open(output_file, 'a') as f:
                    for key, value in outputs.items():
                        f.write(f"{key}={value}\n")
                logger.info(f"Set GitHub outputs: {list(outputs.keys())}")
            except Exception as e:
                logger.warning(f"Failed to set GitHub outputs: {e}")
    
    def create_pr_comment(self, result: Dict[str, Any]):
        """Create PR comment with results (if in PR context)"""
        if os.getenv('GITHUB_EVENT_NAME') != 'pull_request':
            return
        
        try:
            evaluation_result = result.get('result', {})
            status = evaluation_result.get('status', 'unknown')
            violations = evaluation_result.get('violations', [])
            
            comment = f"""## 🛡️ SkySentinel Security Evaluation

**Status**: {status.upper()}
**IaC Type**: {self.iac_type}
**Violations Found**: {len(violations)}

"""
            
            if violations:
                comment += "### Violations\n\n"
                for violation in violations[:5]:  # Limit to 5 violations in comment
                    severity = violation.get('severity', 'unknown')
                    message = violation.get('message', 'No message')
                    policy = violation.get('policy_name', 'Unknown policy')
                    comment += f"- **{severity.upper()}**: {policy}\n  {message}\n\n"
                
                if len(violations) > 5:
                    comment += f"... and {len(violations) - 5} more violations\n\n"
            else:
                comment += "✅ No violations found!\n\n"
            
            comment += f"**Evaluation ID**: {result.get('evaluation_id', 'unknown')}\n"
            comment += f"**Action**: ${GITHUB_SERVER_URL}/${{ github.repository }}/actions/runs/${{ github.run_id }}\n"
            
            # Write comment to file for GitHub script action
            with open('pr-comment.txt', 'w') as f:
                f.write(comment)
            
            logger.info("PR comment generated")
            
        except Exception as e:
            logger.warning(f"Failed to create PR comment: {e}")
    
    def run(self) -> int:
        """Run the CI action"""
        logger.info("Starting SkySentinel CI Action")
        logger.info(f"IaC Type: {self.iac_type}")
        logger.info(f"IaC File: {self.iac_file}")
        logger.info(f"Repository: {self.github_context['repository']}")
        
        # Validate inputs
        if not self.validate_inputs():
            return 1
        
        try:
            # Load IaC content
            logger.info("Loading IaC content...")
            iac_content = self.load_iac_content()
            
            # Prepare context
            context = self.prepare_context()
            
            # Submit evaluation
            evaluation_id = self.submit_evaluation(iac_content, context)
            if not evaluation_id:
                return 1
            
            # Wait for result
            result = self.wait_for_result(evaluation_id)
            if not result:
                return 1
            
            # Process result
            exit_code = self.process_result(result)
            
            # Create PR comment if applicable
            self.create_pr_comment(result)
            
            return exit_code
            
        except Exception as e:
            logger.error(f"CI Action failed: {e}")
            return 1


def main():
    """Main entry point"""
    action = SkySentinelCIAction()
    exit_code = action.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
