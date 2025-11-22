import json
from pathlib import Path
from typing import Dict, Any, Optional

def parse_harbor_results(result_path: Path) -> Dict[str, Any]:
    """Parse Harbor test results from CTRF format"""
    
    # Try CTRF format first (Terminal-Bench 2 standard)
    ctrf_path = result_path / "verifier" / "ctrf.json"
    if ctrf_path.exists():
        try:
            with open(ctrf_path) as f:
                ctrf = json.load(f)
                
            # Navigate CTRF structure
            results = ctrf.get("results", {})
            summary = results.get("summary", {})
            
            tests = results.get("tests", [])
            passed = summary.get("passed", 0)
            total = summary.get("tests", 0)
            failed = summary.get("failed", 0)
            
            return {
                "passed": passed,
                "total": total,
                "failed": failed,
                "details": tests,
                "format": "ctrf"
            }
        except Exception as e:
            print(f"Error parsing CTRF: {e}")
    
    # Fallback: check reward.txt (simple pass/fail)
    reward_path = result_path / "verifier" / "reward.txt"
    if reward_path.exists():
        try:
            reward = float(reward_path.read_text().strip())
            return {
                "passed": int(reward),
                "total": 1,
                "failed": 1 - int(reward),
                "details": [],
                "format": "reward"
            }
        except Exception as e:
            print(f"Error parsing reward.txt: {e}")
    
    # No results found
    return {
        "passed": 0,
        "total": 0,
        "failed": 0,
        "details": [],
        "format": "none"
    }

def read_harbor_logs(result_path: Path) -> str:
    """Read agent logs from Harbor output directory"""
    
    # Try trial.log first
    trial_log = result_path / "trial.log"
    if trial_log.exists():
        trial_content = trial_log.read_text()
        if trial_content.strip():  # Only use if not empty
            return trial_content
    
    # Try to find any agent log file (agent name varies: oracle.txt, TERMINUS_2.txt, etc.)
    agent_dir = result_path / "agent"
    if agent_dir.exists() and agent_dir.is_dir():
        # Find any .txt file in the agent directory
        agent_logs = list(agent_dir.glob("*.txt"))
        if agent_logs:
            # Use the largest .txt file found (usually the main agent log)
            agent_log = max(agent_logs, key=lambda p: p.stat().st_size if p.exists() else 0)
            return agent_log.read_text()
    
    # Try exception.txt if exists
    exception_log = result_path / "exception.txt"
    if exception_log.exists():
        return exception_log.read_text()
    
    return ""

