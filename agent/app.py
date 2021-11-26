# encoding: utf-8

import requests
from agent.ckb_indexer import CKBIndexer
from agent.ckb_rpc import CkbRpc
from agent.godwoken_rpc import GodwokenRpc
from agent.gw_config import GwConfig, testnet_config, mainnet_config
import prometheus_client
from prometheus_client.core import CollectorRegistry, Gauge, Info
from flask import Response, Flask
import os


NodeFlask = Flask(__name__)
web3_url = os.environ['WEB3_URL']
gw_rpc_url = os.environ['GW_RPC_URL']
ckb_indexer_url = os.environ['CKB_INDEXER_URL']
ckb_rpc_url = os.environ['CKB_RPC_URL']
net_env = os.environ['NET_ENV']

def convert_int(value):
    try:
        return int(value)
    except ValueError:
        return int(value, base=16)
    except Exception as exp:
        raise exp


class RpcGet(object):
    def __init__(self, web3_url):
        self.web3_url = web3_url

    def get_LastBlockHeight(self):
        headers = {"Content-Type": "application/json"}
        data = '{"id":2, "jsonrpc":"2.0", "method":"eth_blockNumber", "params":[]}'
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "last_blocknumber": convert_int(replay)
            }
        except:
            return {
                "last_blocknumber": "-1"
            }

    def get_LastBlockHash(self):
        headers = {"Content-Type": "application/json"}
        data = '{"id":2, "jsonrpc":"2.0", "method":"gw_get_tip_block_hash", "params":[]}'
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "last_block_hash": str(replay)
            }
        except:
            return {
                "last_block_hash": "-1"
            }

    def get_BlockDetail(self, block_hash):
        headers = {"Content-Type":  "application/json"}
        data = '{"id":2, "jsonrpc":"2.0", "method":"gw_get_block", "params":["%s"]}' % (
            block_hash)
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "blocknumber": convert_int(replay["block"]["raw"]["number"]),
                "parent_block_hash": replay['block']['raw']['parent_block_hash'],
                "commit_transactions": len(replay["block"]["transactions"]),
                "transactions": replay["block"]["transactions"],
                "blocknumber_timestamp": convert_int(replay["block"]["raw"]["timestamp"])
            }
        except:
            return {
                "blocknumber": "-1",
                "parent_block_hash": "-1",
                "commit_transactions": "-1",
                "transactions": [],
                "blocknumber_timestamp": "-1"
            }

    def get_BlockDetailByNumber(self, number):
        headers = {"Content-Type":  "application/json"}
        data = '{"id":2, "jsonrpc":"2.0", "method":"gw_get_block_by_number", "params":["%s"]}' % (
            number)
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "blocknumber": convert_int(replay["block"]["raw"]["number"]),
                "commit_transactions": len(replay["block"]["transactions"]),
                "transactions": replay["block"]["transactions"],
                "blocknumber_timestamp": convert_int(replay["block"]["raw"]["timestamp"])
            }
        except:
            return {
                "blocknumber": "-1",
                "commit_transactions": "-1",
                "transactions": [],
                "blocknumber_timestamp": "-1"
            }

    def get_block_hash(self, blocknumber):
        headers = {"Content-Type":  "application/json"}
        data = '{"id":2, "jsonrpc":"2.0", "method":"gw_get_block_hash", "params":["%s"]}' % (
            blocknumber)
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "blocknumber_hash": str(replay)
            }
        except:
            return {
                "blocknumber_hash": "-1"
            }

    def get_gw_ping(self):
        headers = {"Content-Type": "application/json"}
        data = '{"id":2, "jsonrpc":"2.0", "method":"gw_ping", "params":[]}'
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "gw_ping_status": replay
            }
        except:
            return {
                "gw_ping_status": "-1"
            }

    def web3_clientVersion(self):
        headers = {"Content-Type": "application/json"}
        data = '{"id":1, "jsonrpc":"2.0", "method":"web3_clientVersion", "params":[]}'
        try:
            r = requests.post(
                url="%s" % (self.web3_url),
                data=data,
                headers=headers
            )
            replay = r.json()["result"]
            return {
                "web3_clientVersion": replay
            }
        except:
            return {
                "web3_clientVersion": "-1"
            }


def get_custodian_ckb(ckb_indexer: CKBIndexer, gw_config: GwConfig) -> int:
    custodian_script_type_hash = gw_config.get_lock_type_hash("custodian_lock")
    rollup_type_hash = gw_config.get_rollup_type_hash()
    capacity = 0
    cursor = None
    while True:
        limit = 1000
        res = ckb_indexer.get_cells(custodian_script_type_hash, rollup_type_hash, limit, cursor)
        if res['result'] == -1:
            return -1
        result = res['result']
        for cell in result['objects']:
            c = convert_int(cell['output']['capacity'])
            capacity += c

        cursor = result['last_cursor']
        if cursor == "0x":
            break
        print(cursor, capacity)
    return capacity
    
def get_gw_stat_by_lock(lock_name, gw_rpc: GodwokenRpc, block_hash, ckb_rpc: CkbRpc):
    lock_type_hash = gw_config.get_lock_type_hash(lock_name)
    res = gw_rpc.gw_get_block_committed_info(block_hash)
    tx = res['result']['transaction_hash']
    res = ckb_rpc.get_transaction(tx)
    inputs = res['result']['transaction']['inputs']
    cnt = 0
    amount = 0
    if inputs is None or len(inputs) == 0:
        return (cnt, amount)
    for i in inputs:
        tx_hash = i['previous_output']['tx_hash']
        res = ckb_rpc.get_transaction(tx_hash)
        outputs = res['result']['transaction']['ouputs']
        for o in outputs:
            code_hash = o['lock']['code_hash']
            if code_hash == lock_type_hash:
                cnt += 1
                amount += convert_int(o['capacity'])
    return (cnt, amount)

get_result = RpcGet(web3_url)
gw_rpc = GodwokenRpc(gw_rpc_url)
ckb_indexer = CKBIndexer(ckb_indexer_url)
ckb_rpc = CkbRpc(ckb_rpc_url)
gw_config = mainnet_config() if net_env.lower() == "mainnet" else testnet_config()


@NodeFlask.route("/metrics/godwoken")
def exporter():
    registry = CollectorRegistry(auto_describe=False)

    last_block_number = Gauge("Node_Get_LastBlockNumber",
                              "LAST_BLOCK_NUMBER", ["web3_url"],
                              registry=registry)

    node_gw_ping = Gauge("Node_Get_Gw_Ping",
                         "Node_GW_PING", ["web3_url", "gw_ping"],
                         registry=registry)
    node_web3_clientVersion = Info("Node_Get_Web3_ClientVersion",
                                   "Node_Web3_ClientVersion", ["web3_url"],
                                   registry=registry)

    node_LastBlockInfo = Gauge("Node_Get_LastBlockInfo",
                               "Get LastBlockInfo, label include last_block_hash, last_blocknumber. value is last_block_timestamp;",
                               ["web3_url", "last_block_hash",
                                "last_blocknumber", "last_block_timestamp"],
                               registry=registry)

    node_BlockDetail_transactions = Gauge("Node_Get_BlockDetail_transactions",
                                          "Get LastTxInfo, label include last_block_hash, tx_hash. value is proposal_transactions in block;",
                                          ["web3_url"],
                                          registry=registry)

    node_BlockTimeDifference = Gauge("Node_Get_BlockTimeDifference",
                                     "Get current block time and previous block time,value is Calculate the difference into seconds;",
                                     ["web3_url"],
                                     registry=registry)

    gw_custodian_capacity = Gauge("Node_Get_CustodianCapacity",
                                    "Get custodian ckb capacity from ckb indexer",
                                    ["web3_url"],
                                    registry=registry)

    gw_deposit_cnt = Gauge("Node_Get_DepositCnt", "Get deposit count from current block", ["web3-url"], registry=registry)
    gw_deposit_capacity = Gauge("Node_Get_DepositCnt", "Get deposit capacity from current block", ["web3-url"], registry=registry)
    gw_withdrawal_cnt = Gauge("Node_Get_WithdrawalCnt", "Get withdrawal count from current block", ["web3-url"], registry=registry)
    gw_withdrawal_capacity = Gauge("Node_Get_WithdrawalCnt", "Get withdrawal capacityfrom current block", ["web3-url"], registry=registry)

    LastBlockHeight = get_result.get_LastBlockHeight()
    if "-1" in LastBlockHeight.values():
        print(LastBlockHeight)
    else:
        last_block_number.labels(
            web3_url=web3_url
        ).set(LastBlockHeight["last_blocknumber"])

    gw_ping = get_result.get_gw_ping()
    if "-1" in gw_ping.values():
        print(gw_ping)
    else:
        node_gw_ping.labels(
            web3_url=web3_url,
            gw_ping=gw_ping["gw_ping_status"]
        ).set(1)

    web3_clientVersion = get_result.web3_clientVersion()
    if "-1" in web3_clientVersion.values():
        print(web3_clientVersion)
    else:
        node_web3_clientVersion.labels(
            web3_url=web3_url
        ).info(web3_clientVersion)

    LastBlockHash = get_result.get_LastBlockHash()
    LastBlockDetail = get_result.get_BlockDetail(
        LastBlockHash["last_block_hash"])
    if "-1" in LastBlockDetail.values():
        print(LastBlockDetail)
    else:
        PreviousBlock_hash = get_result.get_block_hash(
            hex((LastBlockDetail["blocknumber"]) - 1))
        PreviousBlockDetail = get_result.get_BlockDetail(
            PreviousBlock_hash["blocknumber_hash"])
        LastBlock_Time = convert_int(LastBlockDetail["blocknumber_timestamp"])
        PreviousBlock_Time = convert_int(
            PreviousBlockDetail["blocknumber_timestamp"])
        TimeDifference = abs(LastBlock_Time - PreviousBlock_Time)
        node_LastBlockInfo.labels(
            web3_url=web3_url,
            last_block_hash=LastBlockHash["last_block_hash"],
            last_blocknumber=LastBlockDetail["blocknumber"],
            last_block_timestamp=LastBlockDetail["blocknumber_timestamp"]
        ).set(TimeDifference)

        node_BlockDetail_transactions.labels(
            web3_url=web3_url
        ).set(LastBlockDetail["commit_transactions"])

        node_BlockTimeDifference.labels(
            web3_url=web3_url
        ).set(TimeDifference)

    capacity = get_custodian_ckb(ckb_indexer, gw_config)
    gw_custodian_capacity.labels(web3_url).set(capacity)

    cnt, amount = get_gw_stat_by_lock('deposit_lock', gw_rpc, LastBlockHash, ckb_rpc)
    gw_deposit_cnt.labels(web3_url=web3_url).set(cnt)
    gw_deposit_capacity.labels(web3_url=web3_url).set(capacity)
    cnt, amount = get_gw_stat_by_lock('withdrawal_lock', gw_rpc, LastBlockHash, ckb_rpc)
    gw_withdrawal_cnt.labels(web3_url=web3_url).set(cnt)
    gw_withdrawal_capacity.labels(web3_url=web3_url).set(capacity)

    return Response(prometheus_client.generate_latest(registry), mimetype="text/plain")
