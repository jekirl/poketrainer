from __future__ import absolute_import

import pkg_resources
import logging

from pgoapi.exceptions import PleaseInstallProtobufVersion3

protobuf_exist = False
protobuf_version = 0
try:
    protobuf_version = pkg_resources.get_distribution("protobuf").version
    protobuf_exist = True
except:
    pass

if (not protobuf_exist) or (int(protobuf_version[:1]) < 3):
    raise PleaseInstallProtobufVersion3()

from pgoapi.pgoapi import PGoApi  # noqa
from pgoapi.rpc_api import RpcApi  # noqa
from pgoapi.auth import Auth  # noqa

logging.getLogger("pgoapi").addHandler(logging.NullHandler())
logging.getLogger("rpc_api").addHandler(logging.NullHandler())
logging.getLogger("utilities").addHandler(logging.NullHandler())
logging.getLogger("auth").addHandler(logging.NullHandler())
logging.getLogger("auth_ptc").addHandler(logging.NullHandler())
logging.getLogger("auth_google").addHandler(logging.NullHandler())

try:
    import requests.packages.urllib3

    requests.packages.urllib3.disable_warnings()
except:
    pass
