#!/usr/bin/env python3
"""
SkySentinel GitHub Action Evaluator

This script handles the evaluation logic for the SkySentinel GitHub Action.
"""

import json
import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SkySentinelEvaluator:
    """SkySentinel evaluation client for GitHub Actions"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'skysentinel-github-action/1.0.0'
        })
        
        return session
    
    def evaluate_files(
        self,
        iac_type: str,
        files: List[str],
        context: Dict[str, Any],
        timeout: int = 300,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Evaluate IaC files against SkySentinel policies"""
        
        logger.info(f"Starting evaluation of {len(files)} files")
        logger.info(f"IaC type: {iac_type}")
        logger.info(f"API URL: {self.api_url}")
        
        # Prepare evaluation request
        evaluation_data = self._prepare_evaluation_data(
            iac_type, files, context, priority
        )
        
        # Submit evaluation
        evaluation_id = self._submit_evaluation(evaluation_data)
        if not evaluation_id:
            raise Exception("Failed to submit evaluation")
        
        # Wait for results
        result = self._wait_for_results(evaluation_id, timeout)
        
        return {
            'evaluation_id': evaluation_id,
            'result': result,
            'files_evaluated': files
        }
    
    def _prepare_evaluation_data(
        self,
        iac_type: str,
        files: List[str],
        context: Dict[str, Any],
        priority: str
    ) -> Dict[str, Any]:
        """Prepare evaluation request data"""
        
        # Load file contents
        if len(files) == 1:
            # Single file evaluation
            content = self._load_file(files[0])
            evaluation_data = {
                'iac_type': iac_type,
                'iac_content': content,
                'context': context,
                'priority': priority
            }
        else:
            # Multiple files evaluation
            combined_content = {'files': {}}
            for file_path in files:
                try:
                    content = self._load_file(file_path)
                    combined_content['files'][file_path] = content
                except Exception as e:
                    logger.warning(f"Failed to load file {file_path}: {e}")
                    continue
            
            evaluation_data = {
                'iac_type': iac_type,
                'iac_content': combined_content,
                'context': context,
                'priority': priority
            }
        
        return evaluation_data
    
    def _load_file(self, file_path: str) -> Dict[str, Any]:
        """Load and parse file content"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse based on file extension
        if file_path.suffix.lower() == '.json':
            return json.loads(content)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            try:
                import yaml
                return yaml.safe_load(content)
            except ImportError:
                raise Exception("PyYAML is required for YAML file support")
        else:
            # Return raw content for other file types
            return {'raw_content': content}
    
    def _submit_evaluation(self, evaluation_data: Dict[str, Any]) -> Optional[str]:
        """Submit evaluation to SkySentinel API"""
        
        logger.info("Submitting evaluation to SkySentinel API")
        
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/cicd/evaluate",
                json=evaluation_data,
                timeout=30
            )
            
            if response.status_code == 202:
                result = response.json()
                evaluation_id = result.get('evaluation_id')
                logger.info(f"Evaluation submitted with ID: {evaluation_id}")
                return evaluation_id
            else:
                logger.error(f"Failed to submit evaluation: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error submitting evaluation: {e}")
            return None
    
    def _wait_for_results(self, evaluation_id: str, timeout: int) -> Dict[str, Any]:
        """Wait for evaluation results"""
        
        logger.info(f"Waiting for evaluation {evaluation_id} results")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(
                    f"{self.api_url}/api/v1/cicd/evaluate/{evaluation_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status')
                    progress = result.get('progress', 0)
                    
                    logger.info(f"Evaluation status: {status} (progress: {progress}%)")
                    
                    if status in ['completed', 'failed', 'cancelled']:
                        logger.info(f"Evaluation finished with status: {status}")
                        return result
                    else:
                        time.sleep(5)
                else:
                    logger.warning(f"Error checking status: {response.status_code}")
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error checking evaluation status: {e}")
                time.sleep(5)
        
        raise Exception(f"Evaluation timed out after {timeout} seconds")
    
    def get_evaluation_details(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed evaluation results"""
        
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/cicd/evaluate/{evaluation_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get evaluation details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting evaluation details: {e}")
            return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='SkySentinel GitHub Action Evaluator')
    parser.add_argument('--api-url', required=True, help='SkySentinel API URL')
    parser.add_argument('--api-key', required=True, help='SkySentinel API key')
    parser.add_argument('--iac-type', required=True, help='IaC type')
    parser.add_argument('--files', required=True, nargs='+', help='Files to evaluate')
    parser.add_argument('--context', help='Evaluation context (JSON string)')
    parser.add_argument('--timeout', type=int, default=300, help='Evaluation timeout')
    parser.add_argument('--priority', default='normal', help='Evaluation priority')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    # Parse context
    context = {}
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid context JSON: {e}")
            sys.exit(1)
    
    # Create evaluator
    evaluator = SkySentinelEvaluator(args.api_url, args.api_key)
    
    try:
        # Run evaluation
        result = evaluator.evaluate_files(
            iac_type=args.iac_type,
            files=args.files,
            context=context,
            timeout=args.timeout,
            priority=args.priority
        )
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        else:
            print(json.dumps(result, indent=2))
        
        # Determine exit code
        evaluation_result = result.get('result', {})
        status = evaluation_result.get('status', 'unknown')
        
        if status == 'completed':
            # Check for blocking violations
            violations = evaluation_result.get('violations', [])
            critical_violations = [v for v in violations if v.get('severity') == 'critical']
            high_violations = [v for v in violations if v.get('severity') == 'high']
            
            if critical_violations:
                logger.error("Critical violations found")
                sys.exit(1)
            elif high_violations:
                logger.warning("High severity violations found")
                sys.exit(0)  # Don't fail for high violations by default
            else:
                logger.info("No blocking violations found")
                sys.exit(0)
        elif status in ['failed', 'cancelled']:
            logger.error(f"Evaluation {status}")
            sys.exit(1)
        else:
            logger.warning(f"Unknown evaluation status: {status}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
