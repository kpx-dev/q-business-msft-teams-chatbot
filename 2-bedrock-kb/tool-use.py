from dotenv import load_dotenv
load_dotenv()
import boto3
import os
import json
from datetime import datetime
from botocore.exceptions import ClientError
from datetime import date

session = boto3.Session()
region = session.region_name

# modelId = 'anthropic.claude-3-sonnet-20240229-v1:0'
modelId = 'anthropic.claude-3-haiku-20240307-v1:0'

print(f'Using modelId: {modelId}')
print(f'Using region: ', {region})

bedrock_client = boto3.client(service_name = 'bedrock-runtime', region_name = region)

def provider_member_upgrade(query):
    print(f"Member Upgrade provider: {query}")

def provider_trigger_teamcity(query):
    print(f"Trigger Team City: {query}")
    
    return "Triggered the Team City pipeline!"
    # res = # invoke_team_city_api(query....)

def provider_catch_all(query):
    print(f"Catch-all / fallback provider: {query}")

provider_member_upgrade_schema = {
    "toolSpec": {
        "name": "provider_member_upgrade",
        "description": "A tool to Upgrade a user membership",
        "inputSchema": {
            "json": {
            "type": "object",
            "properties": {
                "user_email": {"type": "string", "description": "The email of the user to upgrade"},
                "plan_name": {"type": "string", "description": "The name of the new plan to upgrade to. Capture raw name if needed."}
            },
            "required": ["user_email", "plan_name"]
            }
        }
    }
}

provider_trigger_teamcity_schema = {
    "toolSpec": {
        "name": "provider_trigger_teamcity",
        "description": "A tool to trigger a Team City build based on a Github Pull request URL.",
        "inputSchema": {
            "json": {
            "type": "object",
            "properties": {
                "pull_request_url": {"type": "string", "description": "The URL of a Github Pull Request"}
            },
            "required": ["pull_request_url"]
            }
        }
    }
}

provider_catch_all_schema = {
    "toolSpec": {
        "name": "provider_catch_all",
        "description": "A tool to handle any generic query that other previous tools can't answer.",
        "inputSchema": {
            "json": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The user query that other previous tool doesn't understand."}
            },
            "required": ["query"]
            }
        }
    }
}

toolConfig = {
    "tools": [provider_member_upgrade_schema, provider_trigger_teamcity_schema, provider_catch_all_schema],
    "toolChoice": {
        "any":{},    # must trigger one of the available tools
        # "auto":{}, # default
        # "tool":{   # always trigger this tool
        #     "name": "provider_scam_detection"
        # },
    }
}

def guardrails(prompt): 
    response = bedrock_client.apply_guardrail(
        guardrailIdentifier=os.environ.get('GUARDRAILS_ID'), # ex: '453cg26ykbxy'
        guardrailVersion='1',
        source='INPUT', #|'OUTPUT',
        content=[
            {
                'text': {
                    'text': prompt,
                    # 'qualifiers': [
                    #     'grounding_source'|'query'|'guard_content',
                    # ]
                }
            },
        ]
    )
    # print(response)
    return response 
    
def router(user_query, enable_guardrails=False):
    # apply guardrails 
    if enable_guardrails:
        guard = guardrails(user_query)
        if guard['action'] == 'GUARDRAIL_INTERVENED':
            print("Guardrails blocked this action", guard["assessments"])
            return

    messages = [{"role": "user", "content": [{"text": user_query}]}]

    system_prompt=f"""
        Break down the user questions and match each question to a tool.
        Don't use a tool if you don't need to. 
    """

    converse_api_params = {
        "modelId": modelId,
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {"temperature": 0.0, "maxTokens": 4096},
        "toolConfig": toolConfig,
    }

    response = bedrock_client.converse(**converse_api_params)

    stop_reason = response['stopReason']

    if stop_reason == "end_turn":
        print("Claude did NOT call a tool")
        print(f"Assistant: {stop_reason}")
    elif stop_reason == "tool_use":
        print("Claude wants to use a tool")
        print(stop_reason)
        print(response['output'])
        # print(response['usage'])
        # print(response['metrics'])
        tool = response['output']['message']['content'][0]['toolUse']
        print(tool['name'])
        print(tool['input'])

        # triggering teamcity build 
        if tool['name'] == "provider_trigger_teamcity": 
            res = provider_trigger_teamcity(tool['input']['pull_request_url'])
            print(res)


if __name__ == "__main__":
    router("trigger build for this pr: https://github.com/aws-samples/prompt-engineering-with-anthropic-claude-v-3/pull/9")
    # router("why is sky blue?")
    # router("I want to upgrade a member to package id 10")
    # router("I want to upgrade a member kien@amazon.com to a higher package")
