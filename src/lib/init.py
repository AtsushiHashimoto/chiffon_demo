# -*- coding:utf-8 -*-
import myutils

import argparse
import os
import csv
import subprocess

# このモジュールでは logger のセットアップはしないこと。chifon_client.py を参照。

LIST_NAME_DIR_EXEC={
    "table_object_manager":["output_touch","output_release","output_rawimage"],
    "fasterrcnn":["output_touch","output_release"],
    "chiffon_server":["output_touch","output_release"],
    }

# 引数,設定ファイルから設定に関する辞書を作成
# 拡張子の組の文字列をリストに変換

def parse_args():
    parser_args=argparse.ArgumentParser("CHIFFONに用いられる各モジュールの連携用スクリプト")
    parser_args.add_argument("config_file_path",help="chiffon_client.conf")
    parser_args.add_argument("user_id",help="CHIFFONのユーザー名")
    parser_args.add_argument("grouptag",nargs="+",help="サンプルに付加するグループタグ")
    args_client=parser_args.parse_args()
    return vars(parser_args.parse_args())


def loadSettings():
    dict_conf=parse_args()
    dict_conf_file=myutils.make_dict_conf(dict_conf["config_file_path"])
    dict_conf.update(dict_conf_file)

    dict_conf["table_object_manager"]["fileexts"]=dict_conf["table_object_manager"]["fileexts"].split(",")

    dict_conf["fasterrcnn"]["convtable"]={}
    filepath_table_csv=dict_conf["fasterrcnn"]["path_convtable"]
    with open(filepath_table_csv,"r") as f:
        reader_table=csv.reader(f,delimiter=",")
        for row in reader_table:
            dict_conf["fasterrcnn"]["convtable"][row[0]]=row[1]

    return dict_conf



# CHIFFONからsession_id,recipe_idを取得

def get_sessionid(dict_conf):
    url_session=myutils.get_url_request(dict_conf["chiffon_server"]["host"],dict_conf["chiffon_server"]["port"],[dict_conf["chiffon_server"]["path_sessionid"],dict_conf["user_id"]])
    session_id=myutils.get_session_id(url_session)
    return session_id


def get_recipeid(dict_conf,session_id):
    url_recipe=myutils.get_url_request(dict_conf["chiffon_server"]["host"],dict_conf["chiffon_server"]["port"],[dict_conf["chiffon_server"]["path_recipe"],session_id])
    recipe_id=myutils.get_recipe_id(url_recipe)
    return recipe_id


def getChiffonId(dict_conf):
    session_id=get_sessionid(dict_conf)
    recipe_id=get_recipeid(dict_conf,session_id)

    return (session_id,recipe_id)



# データ保存用ディレクトリの作成
# 辞書内のディレクトリ名も絶対パスに更新

def makeImageDir(dict_conf):
    for name_dir_exec in LIST_NAME_DIR_EXEC.keys():
        for name_dir_out in LIST_NAME_DIR_EXEC[name_dir_exec]:
            abspath_dir=os.path.join(dict_conf["chiffon_client"]["output_root"],dict_conf["session_id"],dict_conf[name_dir_exec][name_dir_out])
            myutils.makedirs_ex(abspath_dir)
            dict_conf[name_dir_exec][name_dir_out]=abspath_dir
