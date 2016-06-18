# -*- coding:utf-8 -*-
import myutils

import glob
import os
import json
import re
import requests
#import subprocess
import datetime
#import locale
import time
import cv2
import chiffon_faster_rcnn as cfr

import logging

# 縮小済みの画像(256*256)を取得
# Put + 1 => bg の番号

# コマンドのヘルプ
# ExtractObjectBoxRegion.exe whole_input_image object_image output_image
# コマンド実行のサンプル
# ExtractObjectBoxRegion.exe ..\bg_0002837.png ..\putobject_0002836_027.png ..\output.png
def recogByFasterRCNN(filepath_img_masked,dict_conf, frcnn):
    logger = logging.getLogger()

    logger.info("Start getUnMaskedImage")

    logger.debug("target file name : " + filepath_img_masked);

    # マスク済みファイル名からフレーム数を抜き出し、背景差分の元情報となるファイル名を取得する。
    maskedimage_filename = os.path.basename(filepath_img_masked)
    pattern=re.compile("(_[0-9]+_)")
    frame_number_astext = pattern.search(maskedimage_filename).group(1)[1:-1]
    logger.info("frame No." + frame_number_astext)
    number_length = len(frame_number_astext)

    '''
    if mode == "output_touch":
        # 背景画像は次の番号になる。
        frame_gap = 1
    elif mode == "output_release":
        # 背景画像は前の番号になる。
        frame_gap = -1
    frame_number = str(int(frame_number_astext) + frame_gap)
    '''
    frame_number = str(int(frame_number_astext))

    image_filename_base = frame_number.zfill(number_length) + "*" + myutils.get_ext(maskedimage_filename)
        
    
    search_path=os.path.join(dict_conf["table_object_manager"]["output_bgimage"],"bg_" + image_filename_base)
    search_path=search_path.replace("\\", "/");
    logger.debug("search query: " + search_path)

    bgimage_path = waitFileCreation(search_path,logger)
    
    search_path=os.path.join(dict_conf["table_object_manager"]["output_rawimage"],image_filename_base)
    search_path=search_path.replace("\\", "/");
    rawimage_path = waitFileCreation(search_path,logger)
    

    # 画像読み込み
    bg_img = cv2.imread(bgimage_path)
    ob_img = cv2.imread(rawimage_path)
    mask_img = cv2.imread(maskedimage_filename)

    # 実行
    return cfr.frcnn_detection(bg_img, ob_img, mask_img, frcnn = frcnn)

        


def waitFileCreation(search_path,logger):
    # ファイルが出力されるのを待つ
    timeout = 0
    filepath=""
    while not os.path.exists(search_path):
        time.sleep(1)
        filepath = glob.glob(search_path)[0]
        if logger:
            logger.info("find : " + filepath) 
        if timeout > 10:
            break
        timeout = timeout + 1
    return filepath

# 特徴量の抽出
# 特徴量を抽出する別実行ファイルの制約で、一時別のカレントディレクトリに移動する処理がある。
def featureExtraction(filepath_img,dict_conf, mode):
    logger = logging.getLogger()

    logger.info("Start featureExtraction")
    cwd = os.getcwd()

    path_exec = dict_conf["image_feature_extractor"]["working_dir"]
    logger.debug("Change directory: " + path_exec)
    os.chdir(os.path.dirname(path_exec))

    result_feature=make_results_FE(filepath_img,dict_conf, mode)

    os.chdir(cwd)
    logger.debug("Change directory: " + cwd)
    logger.info("End featureExtraction")
    return result_feature



# 得た特徴をserver4recogにHTTPで渡す
def make_dict_query_s4r(filepath_img,feature_extracted,dict_conf):
    query_id=dict_conf["session_id"] + "-" + os.path.basename(filepath_img)
    list_group=[dict_conf["user_id"],dict_conf["recipe_id"],dict_conf["session_id"],dict_conf["image_feature_extractor"]["default_group"]]+dict_conf["grouptag"]

    feature_list_as_string = feature_extracted.strip().rstrip(",").replace(" ", "").split(",") # リスト形式
    formatted_feature_extracted = [float(x) for x in feature_list_as_string] # 各値を float に変換

    dict_json_data={"feature":formatted_feature_extracted,"id":query_id,"group":list_group,"name":dict_conf["recipe_id"]}
    dict_query={"json_data":json.dumps(dict_json_data)}
    return dict_query


def make_url_server4recog(filepath_img,feature_extracted,dict_conf):
    dict_query=make_dict_query_s4r(filepath_img,feature_extracted,dict_conf)
    url_recog=myutils.get_url_request(dict_conf["serv4recog"]["host"],dict_conf["serv4recog"]["port"],[dict_conf["serv4recog"]["path"]],dict_query)
    return url_recog


def sendToServer4recog(filepath_img,dict_conf,result_feature, mode):
    logger = logging.getLogger()

    #if(dict_conf["product_env"]["is_product"]=="1"):
    #    with open(filepath_output) as f:
    #        feature_extracted=f.open()
    #else:
    #    feature_extracted="".join(result_feature)

    # ディレクトリパスを置換
    file_abspath_img = os.path.abspath(filepath_img)
    output_path = file_abspath_img.replace(dict_conf["object_region_box_extractor"][mode], dict_conf["serv4recog"][mode])

    # ファイルの拡張子を特徴量用のものに変換
    for ext in dict_conf["table_object_manager"]["fileexts"]:
        if(output_path.rfind(ext) > -1):
            log_output_path = output_path.replace(ext, dict_conf["serv4recog"]["logfileext"])
            output_path = output_path.replace(ext, dict_conf["serv4recog"]["fileext"])
            break


    url_recog="http://{domain}:{port}{path}".format(domain=dict_conf["serv4recog"]["host"],port=dict_conf["serv4recog"]["port"],path=dict_conf["serv4recog"]["path"])
    dict_query=make_dict_query_s4r(filepath_img,result_feature,dict_conf)

    logtime = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("URL(server4recog): "+url_recog)
    logger.debug("Query(server4recog): " + str(dict_query))
    # myutils.output_to_file(log_output_path, "[%s] %s %s" % (logtime, url_recog, dict_query))

    if(dict_conf["product_env"]["enable_server4recog"]=="1"):
        try:
            response = requests.get(url_recog,params=dict_query)
        except requests.exceptions.RequestException:
            logger.error("Fail to send data to server4recog")

        myutils.output_to_file(log_output_path, "%s" % response.url)

        logger.debug(response.text)
        # ファイルへ書き出し。
        myutils.output_to_file(output_path, response.text)

        result_recog=json.loads(response.text)
        # result_recog=myutils.get_http_result(url_recog)
    else:
        result_recog={"tomato":"1"}
    logger.info("Recognition by server4recog has been completed.")

    return result_recog



# 認識結果をCHIFFONにHTTPで渡す
def convert_recjson_to_idjson(recog_name,dict_conf):
    if recog_name in dict_conf["serv4recog"]["convtable"]:
        return dict_conf["serv4recog"]["convtable"][recog_name]
    else :
        return recog_name

def make_dict_query_ch(filepath_img,result_recog,dict_conf):
    dir_img=os.path.dirname(filepath_img)
    timestamp=myutils.get_time_stamp(dict_conf["chiffon_server"]["timestamp"])
    dict_string={"navigator":dict_conf["chiffon_server"]["navigator"],"action":{"target":result_recog,"name":dir_img,"timestamp":timestamp}}
    dict_query={"session_id":dict_conf["session_id"],"string":json.dumps(dict_string)}
    return dict_query

def make_url_chiffon(filepath_img,result_recog,dict_conf):
    dict_query=make_dict_query_ch(filepath_img,result_recog,dict_conf)
    url_chiffon=myutils.get_url_request(dict_conf["chiffon_server"]["host"],dict_conf["chiffon_server"]["port"],[dict_conf["chiffon_server"]["path_receiver"]],dict_query)
    return url_chiffon

def sendToChiffon(filepath_img,dict_conf,result_recog, mode):
    logger = logging.getLogger()

    # dict_recog=convert_recjson_to_idjson(result_recog,dict_conf)
    # url_chiffon=make_url_chiffon(filepath_img,dict_recog,dict_conf)

    recog = result_recog["result"]["likelihood"]
    target = max(recog.items(), key=lambda x:x[1])[0]
    target = convert_recjson_to_idjson(target,dict_conf)

    logger.info("Recog: " + target)

    dir_img=mode.replace("output_", "")
    timestamp=myutils.get_time_stamp(dict_conf["chiffon_server"]["timestamp"])
    dict_string={"navigator":dict_conf["chiffon_server"]["navigator"],"action":{"target":target,"name":dir_img,"timestamp":timestamp}}
    dict_query={"sessionid":dict_conf["session_id"],"string":json.dumps(dict_string)}

    # ディレクトリパスを置換
    file_abspath_img = os.path.abspath(filepath_img)
    output_path = file_abspath_img.replace(dict_conf["object_region_box_extractor"][mode], dict_conf["chiffon_server"][mode])
    # ファイルの拡張子を特徴量用のものに変換
    for ext in dict_conf["table_object_manager"]["fileexts"]:
        if(output_path.rfind(ext) > -1):
            log_output_path = output_path.replace(ext, dict_conf["chiffon_server"]["logfileext"])
            output_path = output_path.replace(ext, dict_conf["chiffon_server"]["fileext"])
            break

    # if(dict_conf["product_env"]["is_product"]=="1"):

    url = "http://{domain}:{port}{path}".format(domain=dict_conf["chiffon_server"]["host"],port=dict_conf["chiffon_server"]["port"],path=dict_conf["chiffon_server"]["path_receiver"])
    logger.info("URL(chiffon): "+url)
    logger.debug("Query(chiffon): "+str(dict_query))
    try:
        response = requests.get(url,params=dict_query)
    except requests.exceptions.RequestException:
        logger.error("Fail to send data to server4recog")

    myutils.output_to_file(log_output_path, "%s" % response.url)

    logger.debug(response.text)
    myutils.output_to_file(output_path, response.text)

    try:
        result=json.loads(response.text)
        if ("status" in result) and (result["status"] == "success"):
            logger.info("Result from server4recog has been successfully sent to CHIFFON server.")
        else :
            # TODO error handling
            pass
    except ValueError:
        logger.error("Fail to send to  CHIFFON server.")
