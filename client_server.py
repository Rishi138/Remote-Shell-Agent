"""
Usage:

pip install -r requirements.txt
python -m uvicorn external_server:app --host 0.0.0.0 --port 8000
ipconfig
192.168.100.173
"""

import requests
from agents import Agent, Runner, FunctionTool, RunContextWrapper
from pydantic import BaseModel
from typing import Any
import asyncio

ip = input("IPV4 *Needs to be on same WiFi as server* >")
port = input("Port >")
print("Connecting")
url = 'http://{}:{}/command'.format(ip, port)

commands = ["cd", "cd/"]
all_messages = []


async def check_commands(ctx: RunContextWrapper[Any], args: str) -> list:
    print("Checking Commands")
    return commands

check_commands_tool = FunctionTool(
    name="CheckCommandSequence",
    description="Check current PowerShell command sequence. Takes no parameters.",
    params_json_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False
    },
    on_invoke_tool=check_commands
)


async def reset_commands(ctx: RunContextWrapper[Any], args: str) -> str:
    global commands
    print("Resetting Commands")
    commands = ["cd", "cd/"]
    return "Commands Reset"


reset_command_tool = FunctionTool(
    name="ResetCommandSequence",
    description="Resets the PowerShell command sequence to its initial state. Takes no parameters.",
    params_json_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False
    },
    on_invoke_tool=reset_commands,
)


class AddCommandArgs(BaseModel):
    new_command: str


async def add_command(ctx: RunContextWrapper[Any], args: str) -> str:
    global commands
    parsed = AddCommandArgs.model_validate_json(args)
    print("Adding Command {}".format(parsed.new_command))
    commands.append(parsed.new_command)
    final_comm = " && ".join(commands)
    final_comm = "powershell.exe -Command " + final_comm
    payload = {'data': final_comm}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return_val = data["data"]
    except requests.exceptions.RequestException as e:
        return_val = f"Request failed: {e}"
        print("Resetting Commands")
        commands = ["cd", "cd/"]
    except ValueError:
        return_val = "Failed to decode JSON response."
        print("Resetting Commands")
        commands = ["cd", "cd/"]
    return return_val

schema = AddCommandArgs.model_json_schema()
schema["additionalProperties"] = False

add_new_command = FunctionTool(
    name="AddNewCommand",
    description="Appends a command to the existing terminal sequence and transmits it to the remote execution "
                "endpoint. Terminal sequence is cumulative and will reset on errors. This tool will run the command "
                "sequence automatically. If full command sequence isn't needed, reset command list after usage.",
    params_json_schema=schema,
    on_invoke_tool=add_command,
)

agent = Agent(
    name="Sage",
    instructions="You are Sage, an autonomous ethical hacking assistant with direct access to a remote Windows terminal"
                 " environment through agent tools. Your role is to assist in system exploration, information "
                 "gathering, and command execution. Validation and authentication have already been handled. Use "
                 "available tools iteratively to build context, gather details about the remote system, and summarize "
                 "findings. Always explain what you're doing before executing, and be transparent about errors or "
                 "results. Due to Windows terminal limitations, ensure valid syntax when adding commands. Reset"
                 "command list as often as possible.",
    model="gpt-4o-mini-2024-07-18",
    tools=[
        add_new_command,
        reset_command_tool,
        check_commands_tool
    ]
)


async def get_new_model_response(messages):
    response = await Runner.run(agent, input=messages)
    return response.final_output


async def main():
    while True:
        prompt = input(">")
        if prompt == "break":
            break
        else:
            all_messages.append({
                "role": "user",
                "content": prompt
            })
            model_response = await get_new_model_response(all_messages)
            all_messages.append({
                "role": "assistant",
                "content": model_response
            })
            print("-------------------------------------------------------------\nModel Response")
            print(model_response)

asyncio.run(main())
