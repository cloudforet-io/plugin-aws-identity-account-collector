import copy
import logging
from collections import deque
from spaceone.core.manager import BaseManager
from spaceone.identity.plugin.account_collector.model.account_collect_response import (
    AccountResponse,
)
from plugin.conf.account_conf import *
from plugin.connector.connector import AccountsConnector


_LOGGER = logging.getLogger("spaceone")


class AccountsManager(BaseManager):
    def __init__(self, params):
        super().__init__()
        self._account_connector = AccountsConnector(**params)
        self.external_id = params.get("secret_data", {}).get("external_id", "")
        self.spaceone_role_name = params.get("secret_data", {}).get("role_name", "")
        self.synced_accounts = []
        self.account_paths = {}

    def collect_accounts(self) -> list:
        root_info = self._account_connector.get_root_account_info()
        management_account_root_id = root_info["Roots"][0]["Id"]
        # management_account_root_name = root_info["Roots"][0]["Name"]
        # management_account_id = self._account_connector.get_management_account_id()
        # starting_path_dict = {
        #     "name": management_account_root_name,
        #     "resource_id": management_account_root_id,
        # }

        self._map_all_ous(management_account_root_id, [])
        for ou_id in self.account_paths:
            ou_info = self._account_connector.get_ou_info(ou_id)
            ou_name = ou_info["OrganizationalUnit"]["Name"]
            if ou_name == SECURITY_OU_NAME:
                self._sync_security_accounts(ou_id)
            else:
                self._sync_other_member_accounts(ou_id)
        return self.synced_accounts

    def _sync_other_member_accounts(self, ou_id: str) -> None:
        member_accounts = self._get_all_ou_member_accounts(ou_id)
        for member_account_id in member_accounts:
            account_name, role_arn = self._get_spaceone_role_info(member_account_id)
            response_data = {}
            response_secret_data = {
                "external_id": self.external_id,
                "account_id": member_account_id,
                "role_arn": role_arn,
            }
            response_schema_id = "aws-secret-assume-role"

            response_result = {
                "name": account_name,
                "data": response_data,
                "resource_id": member_account_id,
                "secret_schema_id": response_schema_id,
                "secret_data": response_secret_data,
                "location": self.account_paths[ou_id],
            }
            self.synced_accounts.append(AccountResponse(**response_result).dict())

    def _sync_security_accounts(self, ou_id: str) -> None:
        member_accounts = self._get_all_ou_member_accounts(ou_id)

        for member_account_id in member_accounts:
            account_name = self._account_connector.get_account_name(member_account_id)
            response_data = {}
            response_secret_data = {"account_id": member_account_id}
            response_schema_id = "aws-security-ou-secret"

            response_result = {
                "name": account_name,
                "data": response_data,
                "resource_id": member_account_id,
                "secret_schema_id": response_schema_id,
                "secret_data": response_secret_data,
                "location": self.account_paths[ou_id],
            }

            self.synced_accounts.append(AccountResponse(**response_result).dict())

    def _map_all_ous(self, parent_ou_id: str, path: list) -> None:
        dq = deque()
        dq.append([parent_ou_id, path])
        while dq:
            for i in range(len(dq)):
                parent_id, current_path = dq.popleft()
                iterator = self._account_connector.get_ou_ids(parent_id)
                for page in iterator:
                    children = page["Children"]
                    for child in children:
                        ou_info = self._account_connector.get_ou_info(child["Id"])
                        ou_name = ou_info["OrganizationalUnit"]["Name"]
                        ou_id = ou_info["OrganizationalUnit"]["Id"]
                        ou_dict = {"name": ou_name, "resource_id": ou_id}
                        current_path.append(ou_dict)
                        next_path = copy.deepcopy(current_path)
                        self.account_paths[child["Id"]] = next_path
                        dq.append([child["Id"], next_path])
                        current_path.pop()

    def _get_all_ou_member_accounts(self, ou_id: str) -> list:
        accounts = []
        results = self._account_connector.get_accounts_ou(ou_id)
        for result in results:
            accounts.append(result["Id"])
        return accounts

    def _get_spaceone_role_info(self, member_account_id: str) -> list:
        role_info = self._account_connector.get_assumed_role_info(member_account_id)
        account_name = self._account_connector.get_account_name(member_account_id)
        role_arn = role_info["Role"]["Arn"]
        return [account_name, role_arn]
