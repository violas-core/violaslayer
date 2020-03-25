#!/usr/bin/python3
import operator
import sys, getopt
import json
import os
sys.path.append(os.getcwd())
sys.path.append("..")
import log
import log.logger
import traceback
import datetime
import stmanage
import requests
import comm
import comm.error
import comm.result
from comm.result import result
from comm.error import error
from comm.parseargs import parseargs
from comm.functions import json_print
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from btc.btcclient import btcclient
from enum import Enum

#module name
name="btctools"

#load logging
logger = log.logger.getLogger(name) 

def getbtcclient():
    return btcclient(name, stmanage.get_btc_conn())

def btchelp():
    client = getbtcclient()
    ret = client.help()
    assert ret.state == error.SUCCEED, " btchelp failed"
    print(ret.datas)

def getblockcount():
    client = getbtcclient()
    ret = client.getblockcount()
    assert ret.state == error.SUCCEED, f"getblockcount() failed"
    print(f"wallet balance:{ret.datas}")

def getblockhash(index):
    client = getbtcclient()
    ret = client.getblockhash(index)
    assert ret.state == error.SUCCEED, f"getblockhash({index}) failed"
    print(f"blockhash({index}):{ret.datas}")

def getblockforhash(blockhash):
    client = getbtcclient()
    ret = client.getblockforhash(blockhash)
    assert ret.state == error.SUCCEED, f"getblockforhash({blockhash}) failed"
    json_print(ret.datas)

def getblockforindex(index):
    client = getbtcclient()
    ret = client.getblockforindex(index)
    assert ret.state == error.SUCCEED, f"getblockforindex({index}) failed"
    json_print(ret.datas)

def getblocktxidsforindex(index):
    client = getbtcclient()
    ret = client.getblocktxidsforindex(index)
    assert ret.state == error.SUCCEED, f"getblocktxidsforindex({index}) failed"
    json_print(ret.datas)

def getblocktxidsforhash(blockhash):
    client = getbtcclient()
    ret = client.getblocktxidsforhash(blockhash)
    assert ret.state == error.SUCCEED, f"getblocktxidsforhash({blockhash}) failed"
    json_print(ret.datas)

def getrawtransaction(txid, verbose = True, blockhash = None):
    client = getbtcclient()
    ret = client.getrawtransaction(txid, verbose, blockhash)
    assert ret.state == error.SUCCEED, f"getrawtransaction({txid}, {verbose}, {blockhash}) failed"
    json_print(ret.datas)

def gettxoutin(txid):
    client = getbtcclient()
    ret = client.gettxoutin(txid)
    assert ret.state == error.SUCCEED, f"gettxoutin({txid}) failed"
    json_print(ret.datas)

def gettxoutforn(txid, n):
    client = getbtcclient()
    ret = client.gettxoutforn(txid, n)
    assert ret.state == error.SUCCEED, f"gettxoutforn({txid}, {n}) failed"
    json_print(ret.datas)

def init_args(pargs):
    pargs.append("help", "show arg list")
    pargs.append("getblockcount", "get block count.")
    pargs.append("getblockhash", "get block hash.", True, ["index"])
    pargs.append("getblockforhash", "get block info with blockhash.", True, ["blockhash"])
    pargs.append("getblockforindex", "get block info with index.", True, ["index"])
    pargs.append("getblocktxidsforhash", "get block txid list with blockhash.", True, ["blockhash"])
    pargs.append("getblocktxidsforindex", "get block txid list with index.", True, ["index"])
    pargs.append("getrawtransaction", "get raw transaction", True, ["txid", "verbose", "blockhash"])
    pargs.append("gettxoutin", "get transaction vin and vout", True, ["txid"])
    pargs.append("gettxoutforn", "get transaction vout[n]", True, ["txid", "n"])

def run(argc, argv):
    try:
        logger.debug("start btc.main")
        pargs = parseargs()
        init_args(pargs)
        pargs.show_help(argv)
        opts, err_args = pargs.getopt(argv)
    except getopt.GetoptError as e:
        logger.error(e)
        sys.exit(2)
    except Exception as e:
        logger.error(e)
        sys.exit(2)

    #argument start for --
    if len(err_args) > 0:
        pargs.show_args()

    names = [opt for opt, arg in opts]
    pargs.check_unique(names)

    for opt, arg in opts:
        if len(arg) > 0:
            count, arg_list = pargs.split_arg(arg)

            print("opt = {}, arg = {}".format(opt, arg_list))
        if pargs.is_matched(opt, ["btchelp"]):
            ret = btchelp()
        elif pargs.is_matched(opt, ["getblockcount"]):
            ret = getblockcount()
        elif pargs.is_matched(opt, ["getblockhash"]):
            if len(arg_list) != 1:
                pargs.exit_error_opt(opt)
            ret = getblockhash(int(arg_list[0]))
        elif pargs.is_matched(opt, ["getblockforhash"]):
            if len(arg_list) != 1:
                pargs.exit_error_opt(opt)
            ret = getblockforhash(arg_list[0])
        elif pargs.is_matched(opt, ["getblockforindex"]):
            if len(arg_list) != 1:
                pargs.exit_error_opt(opt)
            ret = getblockforindex(int(arg_list[0]))
        elif pargs.is_matched(opt, ["getblocktxidsforhash"]):
            if len(arg_list) != 1:
                pargs.exit_error_opt(opt)
            ret = getblocktxidsforhash(arg_list[0])
        elif pargs.is_matched(opt, ["getblocktxidsforindex"]):
            if len(arg_list) != 1:
                pargs.exit_error_opt(opt)
            ret = getblocktxidsforindex(int(arg_list[0]))
        elif pargs.is_matched(opt, ["getrawtransaction"]):
            if len(arg_list) not in (1, 2, 3):
                pargs.exit_error_opt(opt)
            txid = None
            verbose = True
            blockhash= None
            if len(arg_list) >= 1:
                txid = arg_list[0]
            if len(arg_list) >= 2:
                verbose = arg_list[1] == "True"
            if len(arg_list) >= 2:
                blockhash = arg_list[2]
            ret = getrawtransaction(txid, verbose, blockhash)
        elif pargs.is_matched(opt, ["gettxoutin"]):
            if len(arg_list) != 1:
                pargs.exit_error_opt(opt)
            ret = gettxoutin(arg_list[0])
        elif pargs.is_matched(opt, ["gettxoutforn"]):
            if len(arg_list) != 2:
                pargs.exit_error_opt(opt)
            ret = gettxoutforn(arg_list[0], int(arg_list[1]))

    logger.debug("end manage.main")

if __name__ == "__main__":
    run(len(sys.argv) - 1, sys.argv[1:])