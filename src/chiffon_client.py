# -*- coding:utf-8 -*-
import logging
import logging.config
import multiprocessing
import os
import sys
import requests
import lib.init
import lib.thread
import lib.myutils
import lib.loop
import lib.table_object_manager
from lib.log_record_socket_receiver import LogRecordSocketReceiver

def process_main(dict_conf):
    logger = logging.getLogger()
    lib.myutils.setup_child_process_logger(logger)

    logger.info("chiffon_client is started.")
    logger.info("session_id: {session_id}".format(session_id=dict_conf["session_id"]))
    logger.info("recipe_id: {recipe_id}".format(recipe_id=dict_conf["recipe_id"]))

    # ディレクトリ作成(TableObjectManager,FeatureExtractorに用いる)
    # 同時に辞書のデータ保存ディレクトリの値を絶対パスに更新
    lib.init.makeImageDir(dict_conf)

    url_recog="http://{domain}:{port}{path}".format(domain=dict_conf["serv4recog"]["host"],port=dict_conf["serv4recog"]["port"],path=dict_conf["serv4recog"]["path"])
    filepath_img = 'dummy.log'
    result_feature = "0, 0, 0"
    dict_query=lib.loop.make_dict_query_s4r(filepath_img,result_feature,dict_conf)
    logger.info("URL(server4recog): "+url_recog)
    logger.debug("Query(server4recog): " + str(dict_query))

    try:
        response = requests.get(url_recog,params=dict_query)
        logger.info("Send dummy data to server4recog")
    except requests.exceptions.RequestException:
        logger.error("Fail to send dummy data to server4recog")

    log_file_path = os.path.join(dict_conf["chiffon_client"]["output_root"],dict_conf["session_id"],dict_conf['table_object_manager']['output_log'])
    output_to = open(log_file_path, 'w')
    # TableObjectManager起動
    p = lib.table_object_manager.startTableObjectManager(dict_conf, output_to)
    logger.info("Table Object Manager is started.")

    # ループ(画像取得->スレッド作成)
    try:
        lib.thread.makeNewThreads(dict_conf)
    except Exception:
        pass
    finally:
        logger.info("chiffon_client is terminated.")
        p.kill()
        output_to.flush()
        output_to.close()

if __name__=="__main__":
    # 設定用の辞書を作成(引数,設定ファイル)
    # このとき拡張子の組の文字列をリストに変換
    dict_conf=lib.init.loadSettings()
    logging_conf_path = os.path.join(os.path.dirname(os.path.abspath(dict_conf["config_file_path"])), "logging.conf")

    # session_idの取得
    dict_conf["session_id"],dict_conf["recipe_id"]=lib.init.getChiffonId(dict_conf)

    if not dict_conf["session_id"]:
        print("Fail to retrieve session_id from chiffon_server")
        exit();

    if not dict_conf["recipe_id"]:
        print("Fail to retrieve recipe_id from chiffon_server")
        exit();

    # output_rootに移動
    work_directory = os.path.join(dict_conf["chiffon_client"]["output_root"], dict_conf["session_id"])
    if not os.path.isdir(work_directory):
        os.makedirs(work_directory)
    os.chdir(work_directory)

    # ロガーのセットアップ
    logging.config.fileConfig(logging_conf_path)
    logserver = LogRecordSocketReceiver()

    # メイン処理は子プロセスに譲り、親プロセスはロガーに徹する
    try:
        proc_main=multiprocessing.Process(target=process_main,args=(dict_conf,))
        proc_main.start()
        logserver.serve_until_stopped()
    except:
        pass
    finally:
        proc_main.join()
        sys.exit()
