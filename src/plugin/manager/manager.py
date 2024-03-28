import json
import uuid
import copy
from collections import deque
from spaceone.core.manager import BaseManager
from spaceone.core.error import *
from spaceone.identity.plugin.account_collector.model.account_collect_response import (
    AccountResponse,
)
from plugin.conf.account_conf import *
from plugin.connector.connector import AccountsConnector


class AccountsManager(BaseManager):
    def __init__(self, params):
        super().__init__()
        self._account_connector = AccountsConnector(**params)
        self.synced_accounts = []
        self.account_paths = {}

    def collect_accounts(self) -> list:
        root_info = self._account_connector.get_root_account_info()
        management_account_root_id = root_info["Roots"][0]["Id"]
        management_account_root_name = root_info["Roots"][0]["Name"]
        management_account_id = self._account_connector.get_management_account_id()
        self._map_all_ous(management_account_root_id, [management_account_root_name])
        print(self.account_paths)
        # for ou_id in self.account_paths:
        #     ou_info = self._account_connector.get_ou_name(ou_id)
        #     ou_name = ou_info["OrganizationalUnit"]["Name"]
        #     if ou_name == SECURITY_OU_NAME:
        #         self._sync_security_accounts(ou_id)
        #     else:
        #         self._sync_other_member_accounts(management_account_id, ou_id)
        return self.synced_accounts

    def _create_iam_role(
        self, parent_account_id: str, child_account_id: str, external_id: str
    ) -> list:
        assume_role_policy_document = json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{parent_account_id}:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"sts:ExternalId": external_id}},
                    }
                ],
            }
        )
        member_account_name = self._account_connector.get_account_name(child_account_id)
        if not member_account_name:
            member_account_name = f"Member Account {child_account_id}"
        new_role = self._account_connector.generate_new_role(
            child_account_id, CONTROL_TOWER_ROLE_NAME, assume_role_policy_document
        )
        return [member_account_name, new_role["Role"]["Arn"]]

    def _sync_other_member_accounts(
        self, management_account_id: str, ou_id: str
    ) -> None:
        member_accounts = self._get_all_ou_member_accounts(ou_id)
        for member_account_id in member_accounts:
            spaceone_role_exists = self._account_connector.role_exists(
                member_account_id, DEFAULT_ROLE_NAME
            )
            account_name, external_id, role_arn = None, None, None
            if not spaceone_role_exists:
                external_id = str(uuid.uuid4())
                account_name, role_arn = self._create_iam_role(
                    management_account_id, member_account_id, external_id
                )
            else:
                account_name, external_id, role_arn = self._get_spaceone_role_info(
                    member_account_id
                )
            response_data = {}
            response_secret_data = {
                "external_id": external_id,
                "account_id": member_account_id,
                "role_arn": role_arn,
            }
            response_schema_id = "aws_assume_role_with_external_id"

            response_result = {
                "name": account_name,
                "data": response_data,
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
            response_schema_id = "aws_access_key"

            response_result = {
                "name": account_name,
                "data": response_data,
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
                        ou_info = self._account_connector.get_ou_name(child["Id"])
                        ou_name = ou_info["OrganizationalUnit"]["Name"]
                        current_path.append(ou_name)
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
        policy_document = role_info["Role"]["AssumeRolePolicyDocument"]
        policy_condition = policy_document["Statement"][0]["Condition"]
        external_id = policy_condition["StringEquals"]["sts:ExternalId"]
        role_arn = role_info["Role"]["Arn"]
        return [account_name, external_id, role_arn]
