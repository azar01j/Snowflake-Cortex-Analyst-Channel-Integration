#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


credentials = DefaultAzureCredential()
KVUri = f"https://kv-cortex-agent.vault.azure.net"
sc_client = SecretClient(vault_url=KVUri, credential=credentials)
app_id=sc_client.get_secret("app-id").value
app_pwd=sc_client.get_secret("app-pwd").value

class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = app_id
    APP_PASSWORD = app_pwd
