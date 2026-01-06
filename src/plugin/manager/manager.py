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
        self.sync_options = params.get("options", {})
        self.external_id = params.get("secret_data", {}).get("external_id", "")
        self.spaceone_role_name = params.get("secret_data", {}).get("role_name", "")
        self.synced_accounts = []
        self.account_paths = {}
        self.account_to_ou_path = {}

    def collect_accounts(self) -> list:
        root_info = self._account_connector.get_root_account_info()
        management_account_root_id = root_info["Roots"][0]["Id"]

        self._map_all_ous(management_account_root_id, [])

        workspace_mapping_type = self.sync_options.get("workspace_mapping_type")
        if workspace_mapping_type == "custom_depth_groups":
            for account_id, ou_path in self.account_to_ou_path.items():
                if account_name := self._account_connector.get_account_name(account_id):
                    is_security = (
                        ou_path and ou_path[-1].get("name") == SECURITY_OU_NAME
                    )
                    if is_security:
                        self._sync_security_account(account_id, account_name, ou_path)
                    else:
                        self._sync_regular_account(account_id, account_name, ou_path)
        else:
            for ou_id in self.account_paths:
                ou_info = self._account_connector.get_ou_info(ou_id)
                ou_name = ou_info["OrganizationalUnit"]["Name"]

                if ou_name == SECURITY_OU_NAME:
                    self._sync_security_accounts(ou_id)
                else:
                    self._sync_regular_accounts(ou_id)

        return self.synced_accounts

    def _sync_regular_accounts(self, ou_id: str) -> None:
        member_accounts = self._get_all_ou_member_accounts(ou_id)
        for member_account_id in member_accounts:
            if account_name := self._account_connector.get_account_name(
                member_account_id
            ):
                role_arn_info = self._account_connector.get_assumed_role_info(
                    member_account_id
                )
                role_arn = role_arn_info["Role"]["Arn"]

                response_data = {
                    "account_id": member_account_id,
                }
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
            if account_name := self._account_connector.get_account_name(
                member_account_id
            ):
                response_result = {
                    "name": account_name,
                    "data": {"account_id": member_account_id},
                    "resource_id": member_account_id,
                    "secret_schema_id": "aws-security-ou-secret",
                    "secret_data": {"account_id": member_account_id},
                    "location": self.account_paths[ou_id],
                }
                self.synced_accounts.append(AccountResponse(**response_result).dict())

    def _map_all_ous(self, parent_ou_id: str, path: list) -> None:
        mapping_type = self.sync_options.get("workspace_mapping_type")
        custom_depth = int(self.sync_options.get("custom_depth", 1))
        dq = deque([(parent_ou_id, path, 0)])

        while dq:
            ou_id, current_path, depth = dq.popleft()
            children = self._get_children_ous(ou_id)

            if mapping_type == "custom_depth_groups" and depth == custom_depth:
                self._process_custom_depth_ou(
                    ou_id, current_path, children, custom_depth
                )
                continue

            if not children:
                if mapping_type == "leaf_level_groups":
                    self.account_paths[ou_id] = (
                        [current_path[-1]]
                        if current_path
                        else [self._get_ou_dict(ou_id)]
                    )
                elif mapping_type != "custom_depth_groups" and current_path:
                    self.account_paths[ou_id] = current_path
                continue

            for child_id, child_dict in children:
                next_path = current_path + [child_dict]
                next_depth = depth + 1

                if mapping_type == "custom_depth_groups":
                    if next_depth > custom_depth:
                        continue
                    if next_depth == custom_depth:
                        self._process_custom_depth_ou(
                            child_id,
                            next_path,
                            self._get_children_ous(child_id),
                            custom_depth,
                        )
                        continue
                elif mapping_type != "leaf_level_groups":
                    self.account_paths[child_id] = next_path

                dq.append((child_id, next_path, next_depth))

    def _process_custom_depth_ou(
        self, ou_id: str, path: list, children: list, custom_depth: int
    ) -> None:
        base_path = path[custom_depth - 1 :]
        self.account_paths[ou_id] = base_path
        for account_id in self._get_all_ou_member_accounts(ou_id):
            self.account_to_ou_path[account_id] = base_path
        for child_id, child_dict in children:
            self._collect_accounts_recursive(child_id, base_path + [child_dict])

    def _get_ou_dict(self, ou_id: str) -> dict:
        ou_info = self._account_connector.get_ou_info(ou_id)
        return {"name": ou_info["OrganizationalUnit"]["Name"], "resource_id": ou_id}

    def _get_children_ous(self, parent_id: str) -> list:
        children = []
        iterator = self._account_connector.get_ou_ids(parent_id)
        for page in iterator:
            for child in page["Children"]:
                child_id = child["Id"]
                ou_info = self._account_connector.get_ou_info(child_id)
                ou_dict = {
                    "name": ou_info["OrganizationalUnit"]["Name"],
                    "resource_id": child_id,
                }
                children.append((child_id, ou_dict))
        return children

    def _get_all_ou_member_accounts(self, ou_id: str) -> list:
        return [
            result["Id"] for result in self._account_connector.get_accounts_ou(ou_id)
        ]

    def _collect_accounts_recursive(self, ou_id: str, path: list) -> None:
        for account_id in self._get_all_ou_member_accounts(ou_id):
            self.account_to_ou_path[account_id] = path
        for child_id, child_dict in self._get_children_ous(ou_id):
            self._collect_accounts_recursive(child_id, path + [child_dict])

    def _sync_security_account(
        self, account_id: str, account_name: str, ou_path: list
    ) -> None:
        response_result = {
            "name": account_name,
            "data": {"account_id": account_id},
            "resource_id": account_id,
            "secret_schema_id": "aws-security-ou-secret",
            "secret_data": {"account_id": account_id},
            "location": ou_path,
        }
        self.synced_accounts.append(AccountResponse(**response_result).dict())

    def _sync_regular_account(
        self, account_id: str, account_name: str, ou_path: list
    ) -> None:
        role_arn = self._account_connector.get_assumed_role_info(account_id)["Role"][
            "Arn"
        ]

        response_result = {
            "name": account_name,
            "data": {"account_id": account_id},
            "resource_id": account_id,
            "secret_schema_id": "aws-secret-assume-role",
            "secret_data": {
                "external_id": self.external_id,
                "account_id": account_id,
                "role_arn": role_arn,
            },
            "location": ou_path,
        }
        self.synced_accounts.append(AccountResponse(**response_result).dict())
