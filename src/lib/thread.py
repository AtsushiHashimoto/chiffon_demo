# -*- coding:utf-8 -*-
import logging

import loop
import myutils

import sys
import os
import multiprocessing
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DIRNAME_LIST=["output_touch","output_release"]


def process_loop(filepath_img_masked,dict_conf, mode, frcnn):
    logger = logging.getLogger()
    myutils.setup_child_process_logger(logger)

    result_recog=loop.recogByFasterRCNN(filepath_img_masked,dict_conf, mode, frcnn)
    #result_feature=loop.featureExtraction(filepath_img,dict_conf, mode)
    #result_recog=loop.sendToServer4recog(filepath_img,dict_conf,result_feature, mode)
    print(result_recog)
    # sendToChiffonでresult_recogの翻訳が必要．modeは廃止
    loop.sendToChiffon(filepath_img,dict_conf,result_recog, mode)


class ChangeHandler(FileSystemEventHandler):
    def __init__(self,dict_conf,frcnn):
        self.dict_conf=dict_conf
        self.loop_job_list = []
        self.frcnn = frcnn

    def on_created(self, event):
        logger = logging.getLogger()

        if event.is_directory:
            return
        if myutils.get_ext(event.src_path) in self.dict_conf["table_object_manager"]["fileexts"]:
            logger.info("New File '{filepath}' was detected.".format(filepath=event.src_path))

            file_abspath_img = os.path.abspath(event.src_path)
            if(file_abspath_img.find(self.dict_conf["table_object_manager"]["output_touch"]) > -1):
                mode = "output_touch"
            elif(file_abspath_img.find(self.dict_conf["table_object_manager"]["output_release"]) > -1):
                mode = "output_release"
            else :
                raise OnError("Illegal Path:" + file_abspath_img)

            logger.info("mode is " + mode)

            proc_loop=multiprocessing.Process(target=process_loop,args=(event.src_path,self.dict_conf, mode, self.frcnn))
            self.loop_job_list.append(proc_loop)
            proc_loop.start()

class RawfileHandler(FileSystemEventHandler):
    def __init__(self, dict_conf):
        self.dict_conf = dict_conf
        self.i = 0

    def on_created(self, event):
        if event.is_directory:
            return
        if myutils.get_ext(event.src_path) in self.dict_conf["table_object_manager"]["fileexts"]:
            sys.stdout.write("\rBackground No. %i\r" % self.i)
            sys.stdout.flush()
            self.i = self.i + 1

def makeNewThreads(dict_conf,fcnn):
    logger = logging.getLogger()

    event_handler=ChangeHandler(dict_conf)
    observer_release=Observer()
    for dirname in DIRNAME_LIST:
        observer_release.schedule(event_handler,dict_conf["table_object_manager"][dirname],recursive=True)

    # 背景画像は別ハンドラ
    observer_release.schedule(RawfileHandler(dict_conf),dict_conf["table_object_manager"]['output_rawimage'],recursive=True)

    observer_release.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer_release.stop()
        logger.info("observer_release is stopped.")
    observer_release.join()
    [j.join() for j in event_handler.loop_job_list]

    logger.info("End all thread");
