import click
import json
import sys
from typing import Optional, Dict, Any
import requests
from pathlib import Path
from datetime import datetime
import time

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """SkySentinel CLI - Cloud Policy Evaluation Tool"""
    pass

@cli.command()
@click.option('--api-url', required=True, help='SkySentinel API URL')
@click.option('--api-key', required=True, help='SkySentinel API Key')
@click.option('--iac-type', required=True, type=click.Choice(['terraform', 'cloudformation', 'arm']))
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to IaC file')
@click.option('--timeout', default=300, help='Evaluation timeout in seconds')
@click.option('--output', type=click.Choice(['json', 'yaml', 'table']), default='table')
@click.option('--fail-on-warn', is_flag=True, help='Fail on warnings')
def evaluate(api_url, api_key, iac_type, file, timeout, output, fail_on_warn):
    """Evaluate IaC against policies"""
    
    try:
        # Read IaC file
        with open(file, 'r') as f:
            if file.endswith('.json'):
                iac_content = json.load(f)
            elif file.endswith('.yaml') or file.endswith('.yml'):
                import yaml
                iac_content = yaml.safe_load(f)
            else:
                # Try to auto-detect
                content = f.read()
                try:
                    iac_content = json.loads(content)
                except json.JSONDecodeError:
                    iac_content = yaml.safe_load(content)
        
        # Prepare request
        context = {
            "cli_version": "1.0.0",
            "file": file,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Submit evaluation
        response = requests.post(
            f"{api_url}/cicd/webhook/evaluate",
            json={
                "iac_type": iac_type,
                "iac_content": iac_content,
                "context": context
            },
            headers={
                "X-Sky-API-Key": api_key,
                "Content-Type": "application/json"
            },
            timeout=timeout
        )
        
        if response.status_code != 200:
            click.echo(f"Error: {response.status_code} - {response.text}", err=True)
            sys.exit(1)
        
        result = response.json()
        evaluation_id = result['evaluation_id']
        
        # Poll for result
        click.echo(f"Evaluation started: {evaluation_id}")
        click.echo("Waiting for result...")
        
        result_data = None
        for i in range(timeout // 5):
            result_response = requests.get(
                f"{api_url}/cicd/results/{evaluation_id}",
                headers={"X-Sky-API-Key": api_key},
                timeout=10
            )
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                if result_data.get('status') == 'completed':
                    break
            
            time.sleep(5)
        
        if not result_data:
            click.echo("Timeout waiting for evaluation result", err=True)
            sys.exit(1)
        
        # Output result
        if output == 'json':
            click.echo(json.dumps(result_data, indent=2))
        elif output == 'yaml':
            import yaml
            click.echo(yaml.dump(result_data, default_flow_style=False))
        else:
            # Table output
            _print_table_result(result_data)
        
        # Exit code based on result
        if result_data.get('result') == 'block':
            click.echo("❌ Evaluation blocked deployment", err=True)
            sys.exit(1)
        elif fail_on_warn and result_data.get('result') == 'warn':
            click.echo("⚠️  Warnings found (fail-on-warn enabled)", err=True)
            sys.exit(1)
        else:
            click.echo("✅ Evaluation passed")
            sys.exit(0)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--api-url', required=True, help='SkySentinel API URL')
@click.option('--api-key', required=True, help='SkySentinel API Key')
@click.option('--policy-file', type=click.Path(exists=True), help='Path to policy file')
@click.option('--policy-dir', type=click.Path(exists=True), help='Directory with policy files')
def policy(api_url, api_key, policy_file, policy_dir):
    """Manage policies"""
    import yaml
    
    if policy_file:
        files = [Path(policy_file)]
    elif policy_dir:
        files = list(Path(policy_dir).glob('*.yaml')) + list(Path(policy_dir).glob('*.yml'))
    else:
        click.echo("Please specify either --policy-file or --policy-dir", err=True)
        sys.exit(1)
    
    for file in files:
        try:
            with open(file, 'r') as f:
                policy_content = yaml.safe_load(f)
            
            # Validate and submit policy
            click.echo(f"Processing policy: {file.name}")
            
            response = requests.post(
                f"{api_url}/policies",
                json=policy_content,
                headers={
                    "X-Sky-API-Key": api_key,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                click.echo(f"✅ Policy loaded: {file.name}")
            else:
                click.echo(f"❌ Failed to load {file.name}: {response.text}", err=True)
                
        except Exception as e:
            click.echo(f"Error processing {file.name}: {e}", err=True)

@cli.command()
@click.option('--api-url', required=True, help='SkySentinel API URL')
@click.option('--api-key', required=True, help='SkySentinel API Key')
@click.option('--evaluation-id', help='Specific evaluation ID')
@click.option('--limit', default=10, help='Number of evaluations to show')
@click.option('--status', type=click.Choice(['pass', 'warn', 'block', 'error']))
def history(api_url, api_key, evaluation_id, limit, status):
    """View evaluation history"""
    
    try:
        if evaluation_id:
            response = requests.get(
                f"{api_url}/cicd/results/{evaluation_id}",
                headers={"X-Sky-API-Key": api_key}
            )
            
            if response.status_code != 200:
                click.echo(f"Error: {response.text}", err=True)
                sys.exit(1)
            
            result = response.json()
            _print_evaluation_detail(result)
            
        else:
            # List evaluations
            params = {'limit': limit}
            if status:
                params['status'] = status
            
            response = requests.get(
                f"{api_url}/cicd/evaluations",
                headers={"X-Sky-API-Key": api_key},
                params=params
            )
            
            if response.status_code != 200:
                click.echo(f"Error: {response.text}", err=True)
                sys.exit(1)
            
            evaluations = response.json()
            _print_evaluations_table(evaluations)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

def _print_table_result(result: Dict):
    """Print evaluation result in table format"""
    from rich.console import Console
    from rich.table import Table
    from rich import box
    
    console = Console()
    
    # Summary table
    summary_table = Table(title="SkySentinel Evaluation Result", box=box.ROUNDED)
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Evaluation ID", result.get('evaluation_id', 'N/A'))
    summary_table.add_row("Status", result.get('result', 'N/A').upper())
    summary_table.add_row("Timestamp", result.get('timestamp', 'N/A'))
    
    plan_summary = result.get('plan_summary', {})
    summary_table.add_row("IaC Type", plan_summary.get('source_type', 'N/A'))
    summary_table.add_row("Total Resources", str(plan_summary.get('total_resources', 0)))
    
    policy_eval = result.get('policy_evaluation', {})
    summary_table.add_row("Total Violations", str(policy_eval.get('total_violations', 0)))
    summary_table.add_row("Violation Rate", f"{policy_eval.get('violation_rate', 0):.1%}")
    
    console.print(summary_table)
    
    # Violations table
    violations_by_severity = policy_eval.get('violations_by_severity', {})
    if any(violations_by_severity.values()):
        violations_table = Table(title="Policy Violations", box=box.SIMPLE)
        violations_table.add_column("Severity", style="bold")
        violations_table.add_column("Count", style="white")
        
        for severity, violations in violations_by_severity.items():
            if violations:
                violations_table.add_row(severity.upper(), str(len(violations)))
        
        console.print("\n")
        console.print(violations_table)
        
        # Show top violations
        console.print("\n[bold]Top Violations:[/bold]")
        for severity in ['critical', 'high', 'medium']:
            violations = violations_by_severity.get(severity, [])
            for i, violation in enumerate(violations[:3]):  # Show top 3 per severity
                console.print(f"  [{severity.upper()}] {violation.get('description', 'Unknown')}")

def _print_evaluation_detail(result: Dict):
    """Print detailed evaluation information"""
    from rich.console import Console
    from rich.table import Table
    from rich import box
    
    console = Console()
    
    # Basic info
    info_table = Table(title="Evaluation Details", box=box.ROUNDED)
    info_table.add_column("Field", style="cyan")
    info_table.add_column("Value", style="white")
    
    info_table.add_row("Evaluation ID", result.get('evaluation_id', 'N/A'))
    info_table.add_row("Status", result.get('result', 'N/A').upper())
    info_table.add_row("Timestamp", result.get('timestamp', 'N/A'))
    
    console.print(info_table)
    
    # Policy evaluation details
    policy_eval = result.get('policy_evaluation', {})
    if policy_eval:
        console.print("\n[bold]Policy Evaluation:[/bold]")
        console.print(f"Total Violations: {policy_eval.get('total_violations', 0)}")
        console.print(f"Violation Rate: {policy_eval.get('violation_rate', 0):.1%}")

def _print_evaluations_table(evaluations: list):
    """Print evaluations in table format"""
    from rich.console import Console
    from rich.table import Table
    from rich import box
    
    console = Console()
    
    table = Table(title="Evaluation History", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Timestamp", style="white")
    table.add_column("Violations", style="white")
    
    for eval_item in evaluations:
        table.add_row(
            eval_item.get('evaluation_id', 'N/A')[:8] + '...',
            eval_item.get('result', 'N/A').upper(),
            eval_item.get('timestamp', 'N/A'),
            str(eval_item.get('policy_evaluation', {}).get('total_violations', 0))
        )
    
    console.print(table)

if __name__ == '__main__':
    cli()
