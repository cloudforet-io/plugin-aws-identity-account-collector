from functools import partial
from boto3.session import Session
from ..conf.account_conf import *
from spaceone.core.connector import BaseConnector


def get_session(secret_data, region_name):
    params = {
        "aws_access_key_id": secret_data["aws_access_key_id"],
        "aws_secret_access_key": secret_data["aws_secret_access_key"],
        "aws_session_token": secret_data["aws_session_token"],
        "region_name": region_name,
    }
    session = Session(**params)
    return session


class AccountsConnector(BaseConnector):
    def __init__(self, **kwargs):
        super().__init__()

        self.secret_data = kwargs.get("secret_data")
        self.region_name = kwargs.get("region_name", DEFAULT_REGION)
        self._session = None
        self._management_account_org_client = None
        self._management_account_sts_client = None

    @property
    def session(self):
        return self.init_property(
            "_session", partial(get_session, self.secret_data, self.region_name)
        )

    @property
    def management_account_org_client(self):
        if self._management_account_org_client is None:
            self._management_account_org_client = self.session.client("organizations")
        return self._management_account_org_client

    @property
    def management_account_sts_client(self):
        if self._management_account_sts_client is None:
            self._management_account_sts_client = self.session.client("sts")
        return self._management_account_sts_client

    def init_property(self, name: str, init_data: callable):
        if self.__getattribute__(name) is None:
            self.__setattr__(name, init_data())
        return self.__getattribute__(name)

    def get_accounts_ou(self, ou_id: str) -> list:
        results = self._management_account_org_client.list_accounts_for_parent(
            ParentId=ou_id
        )["Accounts"]
        return results

    def get_ou_ids(self, parent_id: str) -> list:
        paginator = self._management_account_org_client.get_paginator("list_children")
        iterator = paginator.paginate(
            ParentId=parent_id, ChildType="ORGANIZATIONAL_UNIT"
        )
        return iterator

    def try_assume_role(self, account_number: str, role_name: str) -> dict:
        partition = self.management_account_sts_client.get_caller_identity()[
            "Arn"
        ].split(":")[1]
        role_arn = "arn:{}:iam::{}:role/{}".format(partition, account_number, role_name)
        result = self.management_account_sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=str(account_number + "-" + role_name)
        )
        return result

    def get_assumed_session(self, account_number: str, role_name: str):
        response = self.try_assume_role(account_number, role_name)
        if "Credentials" in response:
            assumed_sts_session = Session(
                aws_access_key_id=response["Credentials"]["AccessKeyId"],
                aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
                aws_session_token=response["Credentials"]["SessionToken"],
            )
            return assumed_sts_session

    def get_root_account_info(self) -> dict:
        return self.management_account_org_client.list_roots()

    def get_management_account_id(self) -> str:
        return self.management_account_sts_client.get_caller_identity()["Account"]

    def generate_new_role(
        self, child_account_id: str, role_name: str, assume_role_policy_document: dict
    ) -> dict:
        member_account_session = self.get_assumed_session(child_account_id, role_name)

        iam = member_account_session.client("iam")
        response = iam.create_role(
            RoleName=DEFAULT_ROLE_NAME,
            AssumeRolePolicyDocument=assume_role_policy_document,
        )

        iam.attach_role_policy(
            RoleName=DEFAULT_ROLE_NAME,
            PolicyArn=ADMIN_POLICY_ARN,
        )

        print("Role Created with Policy attached!")

        return response

    def get_account_name(self, child_account_id: str) -> str:
        account_info = self.management_account_org_client.describe_account(
            AccountId=child_account_id
        )
        return account_info["Account"]["Name"]

    def role_exists(self, member_account_id: str, role_name: str) -> bool:
        account_session = self.get_assumed_session(
            member_account_id, CONTROL_TOWER_ROLE_NAME
        )
        iam = account_session.client("iam")
        try:
            iam.get_role(RoleName=role_name)
            return True
        except iam.exceptions.NoSuchEntityException:
            return False

    def get_assumed_role_info(self, member_account_id: str) -> dict:
        account_session = self.get_assumed_session(
            member_account_id, CONTROL_TOWER_ROLE_NAME
        )
        iam = account_session.client("iam")
        role_info = iam.get_role(RoleName=DEFAULT_ROLE_NAME)
        return role_info

    def get_ou_name(self, ou_id: str) -> dict:
        org_client = self.management_account_org_client
        ou_info = org_client.describe_organizational_unit(OrganizationalUnitId=ou_id)
        return ou_info

    def list_parents(self, account: str) -> list:
        return self.management_account_org_client.list_parents(ChildId=account)[
            "Parents"
        ]
