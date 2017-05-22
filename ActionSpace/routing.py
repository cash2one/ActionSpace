# coding=utf-8
from om.worker import om_routing
from cmdb.worker import cmdb_routing


channel_routing = om_routing + cmdb_routing
