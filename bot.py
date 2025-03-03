# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount
import pandas as pd
from dotenv import load_dotenv
import requests
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Load environment variables
load_dotenv()

credentials = DefaultAzureCredential()
KVUri = f"https://kv-cortex-agent.vault.azure.net"
sc_client = SecretClient(vault_url=KVUri, credential=credentials)
client_id = sc_client.get_secret("client-id-sflake").value.encode('utf-8')
client_secret = sc_client.get_secret("client-secret-sflake").value.encode('utf-8')



def token_generator():
    try:
        url = "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "scope": "scope/.default",
            "client_id": client_id,
            "client_secret": client_secret
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        
        return response.json()["access_token"]
    except requests.exceptions.RequestException as error:
        print("Error fetching token:", error)
        raise

def analyst_query(token, question):
    try:
        url = "https://<account-identifier>.snowflakecomputing.com/api/v2/cortex/analyst/message"
        data = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
            ],
            "semantic_model_file": "@POWER_AUTOMATE.PUBLIC.SALES/file.yaml"
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        return response.json()["message"]["content"][1]["statement"]
    except requests.exceptions.RequestException as error:
        print("Error in analyst query:", error)
        raise

def analyst_sql(token, sql_statement):
    try:
        url = "https://<account-identifier>.snowflakecomputing.com/api/v2/statements"
        data = {
            "statement": sql_statement,
            "timeout": 60,
            "resultSetMetaData": {"format": "json"},
            "database": "POWER_AUTOMATE",
            "schema": "PUBLIC",
            "warehouse": "SANDBOX_WH",
            "role": "ANALYST"
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as error:
        print("Error in analyst SQL execution:", error)
        raise


class MyBot(ActivityHandler):
    # See https://aka.ms/about-bot-activity-message to learn more about the message and other activity types.

    async def on_message_activity(self, turn_context: TurnContext):
        auth_token = token_generator()
        question_ = turn_context.activity.text
        query_statement = analyst_query(auth_token, question_).replace("__", "")
        sql_result = analyst_sql(auth_token, query_statement)
        
        # Extract column names
        column_names = [col["name"] for col in sql_result["resultSetMetaData"]["rowType"]]
        
        # Prepare the data in DataFrame format
        data = [dict(zip(column_names, row)) for row in sql_result["data"]]
        
        # Create a DataFrame
        df = pd.DataFrame(data)
        markdown_table = df.to_markdown(index=False)
        response_message = (
            f"Here is a sample response:\n\n"
            f"```markdown\n{markdown_table}\n```\n\n"
            f"Here is the Query Statement:\n\n"
            f"```sql\n{query_statement}\n```"
        )
        await turn_context.send_activity(f"{response_message}")


    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")
