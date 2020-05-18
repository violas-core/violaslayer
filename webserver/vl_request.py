#!/usr/bin/python3
from flask import Flask , url_for, request
from markupsafe import escape
app = Flask(__name__)

import operator
import sys, os
import json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import log
import log.logger
import traceback
import datetime
import stmanage
import requests
import comm
import comm.error
import comm.result
import comm.values
from comm.result import result, parse_except
from comm.error import error
from enum import Enum
from vrequest.request_proof import requestproof
from vrequest.request_filter import requestfilter
from btc.btcclient import btcclient
from btc.payload import payload


#module self.name
name="webserver"
logger = log.logger.getLogger(name)
COINS = comm.values.COINS
@app.route('/')
def main():
    args    = request.args
    print(f"args: {args}")
    opt     = args.get("opt")
    opttype = args.get("type")
    datatype = args.get("datatype", "record")

    if opt is None:
        raise Exception("opt not found.")
    elif opt == "get":
        if datatype == "record":
            return get_record(args)
        elif datatype == "version":
            return get_version(args)
    elif opt == "check":
        return check_record(args)
    elif opt == "set":
        #btc transaction
        fromaddress     = args.get("fromaddress")
        toaddress       = args.get("toaddress")
        toamount        = float(args.get("toamount"))
        fromprivkeys    = args.get("fromprivkeys")
        print(f"fromprivkeys:{fromprivkeys}")
        combine         = args.get("combine")

        #payload 
        vreceiver       = args.get("vreceiver")
        sequence        = int(args.get("sequence"))
        if fromprivkeys is not None:
            fromprivkeys = json.loads(fromprivkeys)

        if opttype == "start":
            module          = args.get("module")
            return btc_send_exproof_start(fromaddress, toaddress, toamount, fromprivkeys, combine, \
                    vreceiver, sequence, module)
        elif opttype in ("end", "mark"):
            version  = int(args.get("version"))
            if opttype == "end":
                amount   = float(args.get("amount"))
                return btc_send_exproof_end(fromaddress, toaddress, toamount, fromprivkeys, combine, \
                        vreceiver, sequence, amount, version)
            else:
                return btc_send_exproof_mark(fromaddress, toaddress, toamount, fromprivkeys, combine, \
                        vreceiver, sequence, toamount, version)
        else:
            raise Exception(f"type:{type} not found.")
    else:
        raise Exception(f"opt:{opt} not found.")

def opttype_to_dbname(opttype):
    dbname = ""
    if opttype == "b2v":
        return "b2vproof"
    elif opttype == "filter":
        return "base"
    elif opttype in ("mark", "btcmark"):
        return "markproof"
    else:
        return ""

def list_dbname_for_get_latest_ver():
    return ("b2v", "b2vproof", "filter", "mark", "btcmark")

def get_version(args):
    opttype = args.get("type")

    if opttype not in list_dbname_for_get_latest_ver():
        raise Exception(f"opttype:{opttype} not found.")

    return get_proof_latest_saved_ver(opttype_to_dbname(opttype))

def get_record(args):
    cursor  = int(args.get("cursor", 0))
    limit   = int(args.get("limit", 10))
    receiver = args.get("address")
    opttype = args.get("type")
    client = get_request_client(opttype_to_dbname(opttype))

    if opttype == "b2v":
        state = args.get("state")
        return list_exproof_state(client, receiver, state, cursor, limit)
    elif opttype == "filter":
        return list_opreturn_txids(client, cursor, limit)
    elif opttype == "mark":
        return list_proof_mark(client, receiver, cursor, limit)
    elif opttype == "btcmark":
        return list_proof_btcmark(client, receiver, cursor, limit)
    elif opttype in ("balance", "listunspent"):
        minconf = int(args.get("minconf", 1))
        maxconf = int(args.get("maxconf", 99999999))
        if opttype == "listunspent":
            return btc_list_address_unspent(json.loads(receiver), minconf, maxconf)
        else:
            return btc_get_address_balance(receiver, minconf, maxconf)
    else:
        raise Exception(f"type:{type} not found.")

def check_record(args):
    opttype = args.get("type")
    client = get_request_client(opttype_to_dbname(opttype))

    if opttype == "b2v":
        address = args.get("address")
        sequence = int(args.get("sequence"))
        return check_proof_is_complete(client, address, sequence)
    else:
        raise Exception(f"type:{type} not found.")

def get_btcclient():
    return btcclient(name, stmanage.get_btc_conn())

def btc_get_address_balance(address, minconf = 0, maxconf = 99999999):
    try:
        bclient = get_btcclient()
        ret = bclient.getaddressbalance(address, minconf, maxconf)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def btc_list_address_unspent(address, minconf = 0, maxconf = 99999999):
    try:
        bclient = get_btcclient()
        ret = bclient.listaddressunspent(address, minconf, maxconf)
        if ret.state == error.SUCCEED:
            ret = result(error.SUCCEED, "", ret.datas)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def btc_send_exproof_start(fromaddress, toaddress, toamount, fromprivkeys, combine, \
        vreceiver, sequence, module):
    try:
        bclient = get_btcclient()
        pl = payload(name)
        ret = pl.create_ex_start(vreceiver, sequence, module)
        assert ret.state == error.SUCCEED, f"payload create_ex_start.{ret.message}"
        data = ret.datas

        ret = bclient.sendtoaddress(fromaddress, toaddress, toamount, fromprivkeys, \
                data = data, combine = combine)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()
    
def btc_send_exproof_end(fromaddress, toaddress, toamount, fromprivkeys, combine, \
        vreceiver, sequence, amount, version):
    try:
        bclient = get_btcclient()
        pl = payload(name)
        ret = pl.create_ex_end(vreceiver, sequence, int(amount * COINS), version)
        assert ret.state == error.SUCCEED, f"payload create_ex_end.{ret.message}"
        data = ret.datas

        ret = bclient.sendtoaddress(fromaddress, toaddress, toamount, fromprivkeys, \
                data = data, combine = combine)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def btc_send_exproof_mark(fromaddress, toaddress, toamount, fromprivkeys, combine, \
        vreceiver, sequence, amount, version):
    try:
        bclient = get_btcclient()
        pl = payload(name)
        ret = pl.create_ex_mark(vreceiver, sequence, version, int(COINS * amount))
        assert ret.state == error.SUCCEED, f"payload create_ex_mark.{ret.message}"
        data = ret.datas

        ret = bclient.sendtoaddress(fromaddress, toaddress, toamount, fromprivkeys, \
                data = data, combine = combine)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def get_request_client(db):
    if db in ("base"):
        return requestfilter(name, stmanage.get_db(db))
    else:
        return requestproof(name, stmanage.get_db(db))

def get_proof_latest_saved_ver(db):
    try:
        client = get_request_client(db)
        ret = client.get_proof_latest_saved_ver()
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def list_exproof_state(client, receiver, state_name, cursor = 0, limit = 10):
    try:
        if state_name is None and receiver is None:
            return client.list_exproof(cursor, limit).to_json()

        state = client.proofstate[state_name.upper()]

        if state == client.proofstate.START:
            ret = client.list_exproof_start(receiver, cursor, limit)
        elif state == client.proofstate.END:
            ret = client.list_exproof_end(receiver, cursor, limit)
        else:
            raise Exception(f"state{state} is invalid.")

    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def list_proof_mark(client, receiver, cursor = 0, limit = 10):
    try:
        ret = client.list_proof_mark(receiver, cursor, limit)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def list_proof_btcmark(client, receiver, cursor = 0, limit = 10):
    try:
        ret = client.list_proof_btcmark(receiver, cursor, limit)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

def list_opreturn_txids(client, cursor = 0, limit = 10):
    try:
        ret = client.list_opreturn_txids(cursor, limit)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

'''
***check record 
'''
def check_proof_is_complete(client, address, sequence):
    try:
        ret = client.check_proof_is_complete(address, sequence)
    except Exception as e:
        ret = parse_except(e)
    return ret.to_json()

'''
with app.test_request_context():
    logger.debug(url_for('tranaddress', chain = "violas", cursor = 0, limit = 10))
    logger.debug(url_for('tranrecord', chain = "violas", sender="af5bd475aafb3e4fe82cf0d6fcb0239b3fe11cef5f9a650e830c2a2b89c8798f", cursor=0, limit=10))
    logger.debug(url_for('trandetail', dtype="v2b", version="5075154"))
'''

if __name__ == "__main__":
    from werkzeug.contrib.fixers import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run()
