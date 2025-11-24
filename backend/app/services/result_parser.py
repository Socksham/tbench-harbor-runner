import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

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

def read_episode_files(result_path: Path) -> List[Dict[str, Any]]:
    """
    Read episode files from Harbor output.

    Structure expected:
    result_path/agent/episode-0/prompt.txt (terminal state shown to agent)
    result_path/agent/episode-0/response.txt (agent's JSON response)
    ...

    Returns:
        List of episode dictionaries with episode_number, commands, explanation, state_analysis
    """
    episodes = []
    agent_dir = result_path / "agent"

    if not agent_dir.exists():
        return episodes

    # Find all episode-N directories
    episode_dirs = sorted(agent_dir.glob("episode-*"))

    for idx, episode_dir in enumerate(episode_dirs):
        episode_data = {
            "episode_number": idx,
            "commands": None,
            "explanation": None,
            "state_analysis": None
        }

        # Read prompt.txt (terminal state shown to agent)
        prompt_file = episode_dir / "prompt.txt"
        if prompt_file.exists():
            try:
                with open(prompt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Store terminal state/prompt as explanation
                    episode_data["explanation"] = f.read()
            except Exception as e:
                logger.warning(f"Failed to read {prompt_file}: {e}")

        # Read response.txt (agent's JSON response with analysis, plan, commands)
        response_file = episode_dir / "response.txt"
        if response_file.exists():
            try:
                with open(response_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Try to parse JSON from response (may be wrapped in ```json blocks)
                    try:
                        # Remove markdown code blocks if present
                        json_str = content
                        if "```json" in content:
                            # Extract JSON between ```json and ```
                            start = content.find("```json") + 7
                            end = content.find("```", start)
                            if end != -1:
                                json_str = content[start:end].strip()
                        elif "```" in content:
                            # Extract JSON between ``` and ```
                            start = content.find("```") + 3
                            end = content.find("```", start)
                            if end != -1:
                                json_str = content[start:end].strip()

                        # Parse the JSON
                        response_json = json.loads(json_str)

                        # Extract fields from JSON
                        if "analysis" in response_json:
                            episode_data["state_analysis"] = response_json["analysis"]

                        if "commands" in response_json:
                            # Format commands nicely
                            commands = response_json["commands"]
                            if isinstance(commands, list):
                                # Extract keystrokes from command objects
                                cmd_list = []
                                for cmd in commands:
                                    if isinstance(cmd, dict) and "keystrokes" in cmd:
                                        cmd_list.append(cmd["keystrokes"])
                                    elif isinstance(cmd, str):
                                        cmd_list.append(cmd)
                                episode_data["commands"] = "\n".join(cmd_list) if cmd_list else None
                            elif isinstance(commands, str):
                                episode_data["commands"] = commands

                        # Optionally include plan in state_analysis
                        if "plan" in response_json and episode_data["state_analysis"]:
                            episode_data["state_analysis"] += f"\n\nPlan: {response_json['plan']}"
                        elif "plan" in response_json:
                            episode_data["state_analysis"] = f"Plan: {response_json['plan']}"

                    except json.JSONDecodeError:
                        # If JSON parsing fails, store raw response as state_analysis
                        episode_data["state_analysis"] = content

            except Exception as e:
                logger.warning(f"Failed to read {response_file}: {e}")

        episodes.append(episode_data)

    return episodes


def read_harbor_logs(result_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Read Harbor logs and episode files.

    Returns:
        tuple: (logs_string, episodes_list)
    """
    logs = []

    # Try trial.log first
    trial_log = result_path / "trial.log"
    if trial_log.exists():
        try:
            trial_content = trial_log.read_text(encoding='utf-8', errors='ignore')
            if trial_content.strip():  # Only use if not empty
                logs.append(trial_content)
        except Exception as e:
            logger.warning(f"Failed to read trial.log: {e}")

    # Try to find any agent log file (agent name varies: oracle.txt, TERMINUS_2.txt, etc.)
    agent_dir = result_path / "agent"
    if agent_dir.exists() and agent_dir.is_dir():
        # Find any .txt file in the agent directory (excluding episode directories)
        agent_logs = [f for f in agent_dir.glob("*.txt") if f.is_file()]
        if agent_logs:
            # Use the largest .txt file found (usually the main agent log)
            agent_log = max(agent_logs, key=lambda p: p.stat().st_size if p.exists() else 0)
            try:
                logs.append(agent_log.read_text(encoding='utf-8', errors='ignore'))
            except Exception as e:
                logger.warning(f"Failed to read agent log: {e}")

    # Try exception.txt if exists
    exception_log = result_path / "exception.txt"
    if exception_log.exists() and not logs:
        try:
            logs.append(exception_log.read_text(encoding='utf-8', errors='ignore'))
        except Exception as e:
            logger.warning(f"Failed to read exception.txt: {e}")

    # Read episode files
    episodes = read_episode_files(result_path)

    combined_logs = "\n\n=== COMBINED LOGS ===\n\n".join(logs) if logs else ""

    return combined_logs, episodes

