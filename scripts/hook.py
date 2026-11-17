"""Translate local Codex hook events into the Orchestra workflow."""
import json
import os
from pathlib import Path
import re
import shlex
import sys

import common as c
import guard_main


SKILLS = ("conductor", "interview", "delegation", "documentation")
MODE = re.compile(r"^\s*\$orchestra-codex:(enable|disable|conductor)(?=\s|$)")
MENTION = re.compile(r"^\s*\[\$(?:orchestra-codex:)?(enable|disable|conductor)\]\((.*?)\)(?=\s|$)")
# Code mode and tool discovery must remain able to reach the nested Bash tool.
BOOTSTRAP_TOOLS = {"exec", "wait", "functions.exec", "functions.wait", "functionsexec",
                   "functionswait", "tool_search", "tool_search_tool"}


def skill_file(name):
    return c.ROOT / "skills" / name / "SKILL.md"


def read_instruction(name):
    return "Run this standalone shell command, allowing at least 8000 output tokens: " + shlex.join(
        ["cat", str(skill_file(name))])


def mode_command(prompt):
    match = MODE.match(prompt)
    if match:
        return match[1]
    match = MENTION.match(prompt)
    if match and Path(match[2]).resolve() == skill_file(match[1]):
        return match[1]
    return None


def skill_read(data, tool, args):
    if tool != "Bash" or not isinstance(args.get("command"), str):
        return None
    target = guard_main.literal_cat(args["command"])
    if target:
        path = Path(c.resolve(target, data))
        return next((name for name in SKILLS if path == skill_file(name)), None)
    return None


def reset_skills(folder):
    for name in SKILLS:
        (folder / ("skill-" + name)).unlink(missing_ok=True)


def verified_read(name, response):
    if isinstance(response, dict):
        response = response.get("output", response.get("stdout"))
    text = c.read_text(skill_file(name)).strip()
    return bool(text and isinstance(response, str) and text in response)


def agent_tool(tool):
    # 0.169 flattens a V2 namespace and tool name without a separator.
    for prefix in ("collaboration", "multi_agent_v1"):
        if tool.startswith(prefix):
            return tool[len(prefix):].lstrip(".")
    return tool


def worker_event(data, event, tool, args):
    import check_report
    import guard_agent

    task = guard_agent.assignment_for(data)
    if not task:
        if guard_agent.pending_worker(data):
            kickoff = ("Start the assigned task by running cat on the exact installed role file and task spec "
                       "in the dispatch message, together in one command.")
            if event == "SubagentStart":
                c.context(event, kickoff)
            if event == "SubagentStop":
                check_report.retry(data, "this worker", kickoff)
            if event == "PreToolUse" and tool not in BOOTSTRAP_TOOLS:
                c.deny(kickoff)
        return
    data["_assignment"] = task
    data["_project_dir"] = task["project"]
    role = task["role"]
    if event == "SubagentStart":
        c.context(event, f"Your Orchestra role is {role}. Read the role and task spec together: "
                  + shlex.join(["cat", str(c.ROOT / "roles" / (role + ".md")), task["spec"]]))
    if event == "SubagentStop":
        check_report.finish(data, task)
    if event != "PreToolUse":
        return
    if data.get("model") != c.SOL:
        c.deny(f"This Orchestra worker requires {c.SOL}. Ask the conductor to dispatch it again.")
    if agent_tool(tool) in ("spawn_agent", "followup_task", "send_message", "send_input",
                            "spawn_agents_on_csv", "resume_agent", "Workflow", "Agent"):
        c.deny("Workers report to the conductor through their final status and report file. "
               "Return BLOCKED if the assignment needs another worker or a decision.")
    guard_main.check(data, "readonly" if role == "analyst" else "impl")


def dispatch(data):
    event = data["hook_event_name"]
    folder = c.session_dir(data)
    model = data.get("model")
    tool = data.get("tool_name", "")
    args = data.get("tool_input") or {}
    if data.get("agent_id"):
        data["_project_dir"] = c.read_text(folder / "project") or data["cwd"]
        if event in ("PreToolUse", "SubagentStart", "SubagentStop"):
            worker_event(data, event, tool, args)
        return

    prompt = data.get("prompt", "") if event == "UserPromptSubmit" else ""
    command = mode_command(prompt) if prompt else None
    disabled = folder / "disabled"
    if command == "disable":
        c.write_state(disabled, "")
        reset_skills(folder)
        c.context(event, "Orchestra conductor mode is off for this chat.")
    if command in ("enable", "conductor"):
        disabled.unlink(missing_ok=True)
    if disabled.exists():
        return

    root_file = folder / "project"
    model_file = folder / "model"
    if model != c.ASTRA:
        if c.read_text(model_file) == c.ASTRA:
            c.write_state(model_file, str(model or ""))
            reset_skills(folder)
            if event == "UserPromptSubmit":
                c.context(event, "This model uses the ordinary Codex workflow.")
        return

    first = c.read_text(model_file) != model
    if first:
        c.write_state(model_file, model)
    if event in ("SessionStart", "UserPromptSubmit") or not root_file.exists():
        project = os.path.realpath(data["cwd"])
        if c.read_text(root_file) != project:
            c.write_state(root_file, project)
    data["_project_dir"] = c.read_text(root_file)
    if first or event in ("SessionStart", "PostCompact"):
        reset_skills(folder)
    if event == "PostCompact":
        return
    if event == "UserPromptSubmit":
        reply = re.fullmatch(r"orchestra approve ([0-9a-f]{12})", prompt.strip())
        if reply:
            matched = c.approve_reply(data, reply[1])
            c.context(event, "The user authorized one exact retry." if matched
                      else "There is no pending Orchestra approval with that code in this chat.")
        if not command:
            c.mark_user_turn(data)
    loaded = folder / "skill-conductor"
    if event in ("SessionStart", "UserPromptSubmit"):
        if not loaded.exists() or command:
            c.context(event, "You are the GPT-6.2 Astra conductor. Design, delegate implementation, "
                      "and review the result independently. " + read_instruction("conductor"))
        return

    name = skill_read(data, tool, args)
    if event == "PostToolUse":
        if name and (name == "conductor" or loaded.exists()) and verified_read(name, data.get("tool_response")):
            c.write_state(folder / ("skill-" + name), "")
        return
    if event != "PreToolUse":
        return
    if not loaded.exists() and name != "conductor" and tool not in BOOTSTRAP_TOOLS:
        c.deny(read_instruction("conductor"))
    action = agent_tool(tool)
    if action in ("spawn_agent", "Agent", "followup_task", "send_message", "send_input", "resume_agent"):
        import guard_agent
        if not (folder / "skill-delegation").exists():
            c.deny(read_instruction("delegation"))
        if action in ("spawn_agent", "Agent"):
            guard_agent.check_spawn(data, args)
        else:
            guard_agent.check_followup(data, args)
    elif action in ("spawn_agents_on_csv", "Workflow"):
        c.deny("Use a named Orchestra assignment and an explicit Sol model and effort for each task.")
    else:
        guard_main.check(data, "conductor")


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    try:
        dispatch(payload)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        message = f"Orchestra could not process {payload.get('hook_event_name')}: {exc}"
        if payload.get("hook_event_name") == "PreToolUse":
            c.deny(message)
        if payload.get("hook_event_name") == "SubagentStop":
            c.emit({"decision": "block", "reason": message})
        c.emit({"systemMessage": message})
