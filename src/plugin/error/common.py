from spaceone.core.error import *


class ERROR_INVALID_TOKEN(ERROR_INVALID_ARGUMENT):
    _message = "Invalid token: {token}"


class ERROR_SYNC_PROCESS(ERROR_INVALID_ARGUMENT):
    _message = "An Error occurred while syncing accounts: {message}"
