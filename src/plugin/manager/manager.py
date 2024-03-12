import json
import uuid
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

    def collect_accounts(self):
        unsynced_accounts = []
        try:
            root_info = self._account_connector.get_root_account_info()
            management_account_root_id = root_info["Roots"][0]["Id"]
            management_account_id = self._account_connector.get_management_account_id()
            ou_ids = self._get_all_ou_ids(management_account_root_id)
            for ou_id in ou_ids:
                member_accounts = self._get_all_ou_member_accounts(ou_id)
                for member_account_id in member_accounts:
                    spaceone_role_exists = self._account_connector.role_exists(
                        member_account_id, DEFAULT_ROLE_NAME
                    )
                    if not spaceone_role_exists:
                        if member_account_id == "260966982575":
                            """
                            new role을 만들더라도, control tower상의 config - guardrail, scp로 인해서 새로 만든 role이 없어질 수 있다.
                            --> 만들 고객사의 scp 를 확인하고 진행해보는 방법이 필요할 것으로 보인다.
                            """
                            external_id = str(uuid.uuid4())
                            account_name, role_arn = self._create_iam_role(
                                management_account_id, member_account_id, external_id
                            )
                            # SpaceONE Console 상에서 General Account 추가 시 필요한 데이터 중, "프로젝트"는?
                            # role_arn, external_id 는 response_secret_data 에 넣는 것이 맞을까?
                            response_data = {
                                "role_arn": role_arn,
                                "external_id": external_id,
                                "account_id": member_account_id,
                            }
                            response_secret_data = {"external_id": external_id}

                            # multiple schema ids? -> aws_assume_role_with_external_id, aws_assume_role, aws_access_key?
                            response_schema_ids = "aws_assume_role_with_external_id"

                            response_result = {
                                "name": account_name,
                                "data": response_data,
                                "secret_schema_id": response_schema_ids,
                                "secret_data": response_secret_data,
                            }
                            unsynced_accounts.append(AccountResponse(**response_result))
                            print("DONE?")
                            print(unsynced_accounts)
                            break
                        # external_id = str(uuid.uuid4())
                        # account_name, role_arn = self._create_iam_role(
                        #     management_account_id, member_account_id, external_id
                        # )

                        # SpaceONE Console 상에서 General Account 추가 시 필요한 데이터 중, "프로젝트"는?
                        # role_arn, external_id 는 response_secret_data 에 넣는 것이 맞을까?
                        # response_data = {
                        #     "role_arn": role_arn,
                        #     "external_id": external_id,
                        #     "account_id": member_account_id,
                        # }
                        # response_secret_data = {}
                        #
                        # # multiple schema ids? -> aws_assume_role_with_external_id, aws_assume_role, aws_access_key?
                        # response_schema_ids = "aws_assume_role_with_external_id"
                        #
                        # response_result = {
                        #     "name": account_name,
                        #     "data": response_data,
                        #     "secret_schema_id": response_schema_ids,
                        #     "secret_data": response_secret_data,
                        # }
                        # unsynced_accounts.append(AccountsResponse(**response_result))

        except Exception as e:
            print(e)

        return unsynced_accounts

    def _create_iam_role(self, parent_account_id, child_account_id, external_id):
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

    def _get_all_ou_ids(self, parent_ou_id):
        full_result = []
        iterator = self._account_connector.get_ou_ids(parent_ou_id)

        for page in iterator:
            for ou in page["Children"]:
                full_result.append(ou["Id"])
                full_result.extend(self._get_all_ou_ids(ou["Id"]))
        return full_result

    def _get_all_ou_member_accounts(self, ou_id):
        accounts = []
        results = self._account_connector.get_accounts_ou(ou_id)
        for result in results:
            accounts.append(result["Id"])
        return accounts
