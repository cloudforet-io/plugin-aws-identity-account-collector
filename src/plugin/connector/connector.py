import logging
from functools import partial
from typing import Union

from boto3.session import Session
from ..conf.account_conf import *
from plugin.error.common import *
from spaceone.core.connector import BaseConnector
from spaceone.core.error import *

__all__ = ["AccountsConnector"]

_LOGGER = logging.getLogger("spaceone")


def get_session(secret_data, region_name):
    try:
        params = {
            "aws_access_key_id": secret_data.get("aws_access_key_id", None),
            "aws_secret_access_key": secret_data.get("aws_secret_access_key", None),
            "region_name": region_name,
        }
        session = Session(**params)
    except Exception as e:
        _LOGGER.error(f"[ERROR] get_session :{e}")
        raise ERROR_INVALID_TOKEN(token=e)
    return session


class AccountsConnector(BaseConnector):
    def __init__(self, **kwargs):
        super().__init__()

        self.secret_data = kwargs.get("secret_data")
        self.region_name = kwargs.get("region_name", DEFAULT_REGION)
        self._session = None
        self._management_account_org_client = None
        self._management_account_sts_client = None
        self.external_id = self.secret_data.get("external_id", "")
        self.spaceone_role_name = self.secret_data.get("role_name", "")

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
        try:
            results = self._management_account_org_client.list_accounts_for_parent(
                ParentId=ou_id
            )["Accounts"]
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return results

    def get_ou_ids(self, parent_id: str) -> list:
        try:
            paginator = self._management_account_org_client.get_paginator(
                "list_children"
            )
            iterator = paginator.paginate(
                ParentId=parent_id, ChildType="ORGANIZATIONAL_UNIT"
            )
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return iterator

    def try_assume_role(self, account_number: str) -> dict:
        try:
            partition = self.management_account_sts_client.get_caller_identity()[
                "Arn"
            ].split(":")[1]
            role_arn = "arn:{}:iam::{}:role/{}".format(
                partition, account_number, self.spaceone_role_name
            )
            result = self.management_account_sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=str(account_number + "-" + self.spaceone_role_name),
                ExternalId=self.external_id,
            )
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return result

    def get_assumed_session(self, account_number: str):
        response = self.try_assume_role(account_number)
        if "Credentials" in response:
            try:
                assumed_sts_session = Session(
                    aws_access_key_id=response["Credentials"]["AccessKeyId"],
                    aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
                    aws_session_token=response["Credentials"]["SessionToken"],
                )
            except Exception as e:
                _LOGGER.error(f"[ERROR] get_assumed_session :{e}")
                raise ERROR_INVALID_TOKEN(token=e)
            return assumed_sts_session

    def get_root_account_info(self) -> dict:
        try:
            root_info = self.management_account_org_client.list_roots()
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return root_info

    def get_management_account_id(self) -> str:
        try:
            management_account_id = (
                self.management_account_sts_client.get_caller_identity()["Account"]
            )
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return management_account_id

    def get_account_name(self, child_account_id: str) -> Union[str, None]:
        try:
            account_info = self.management_account_org_client.describe_account(
                AccountId=child_account_id
            )
            if account_info["Account"]["Status"] == "ACTIVE":
                return account_info["Account"]["Name"]
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)

    def get_assumed_role_info(self, member_account_id: str) -> dict:
        account_session = self.get_assumed_session(member_account_id)
        try:
            iam = account_session.client("iam")
            role_info = iam.get_role(RoleName=self.spaceone_role_name)
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return role_info

    def get_ou_info(self, ou_id: str) -> dict:
        try:
            org_client = self.management_account_org_client
            ou_info = org_client.describe_organizational_unit(
                OrganizationalUnitId=ou_id
            )
        except Exception as e:
            raise ERROR_SYNC_PROCESS(message=e)
        return ou_info
