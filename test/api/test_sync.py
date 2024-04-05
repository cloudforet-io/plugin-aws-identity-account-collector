import os
import logging

from spaceone.core import utils, config
from spaceone.tester import TestCase, print_json
from google.protobuf.json_format import MessageToDict
import pprint

_LOGGER = logging.getLogger(__name__)

AKI = os.environ.get("AWS_ACCESS_KEY_ID", None)
SAK = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
AST = os.environ.get("AWS_SESSION_TOKEN", None)
ROLE_ARN = os.environ.get("ROLE_ARN", None)
EXTERNAL_ID = os.environ.get("EXTERNAL_ID", None)
REGION_NAME = os.environ.get("REGION_NAME", None)

if AKI == None or SAK == None:
    print(
        """
##################################################
# ERROR 
#
# Configure your AWS credential first for test
##################################################
example)

export AWS_ACCESS_KEY_ID=<YOUR_AWS_ACCESS_KEY_ID>
export AWS_SECRET_ACCESS_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>

"""
    )
    exit


class TestSync(TestCase):
    config = utils.load_yaml_from_file(
        os.environ.get("SPACEONE_TEST_CONFIG_FILE", "./config.yml")
    )
    endpoints = config.get("ENDPOINTS", {})
    secret_data = {
        "aws_access_key_id": AKI,
        "aws_secret_access_key": SAK,
        "aws_session_token": AST,
        "external_id": "9d46484b-039f-4407-8ffb-d5157fa64ecf",
        "role_name": "SpaceoneRole",
    }

    def test_init(self):
        v_info = self.identity.AccountCollector.init(
            {"options": {}, "domain_id": "example"}
        )
        print_json(v_info)

    def test_full_collect(self):
        print(f"Action: Collect Accounts!")
        print(
            f"=================== Start collecting unsynced accounts! =========================="
        )
        options = {}
        params = {
            "options": options,
            "secret_data": self.secret_data,
            "domain_id": "example",
        }
        result = self.identity.AccountCollector.sync(params)
        print(result)
        print(
            f"=================== End collecting unsynced accounts! =========================="
        )
