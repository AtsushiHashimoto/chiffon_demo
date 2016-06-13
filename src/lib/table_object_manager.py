# -*- coding:utf-8 -*-
import logging

import myutils

import argparse
import os
import csv
import subprocess

def make_list_args_TOM(dict_conf):
    if(dict_conf["product_env"]["use_cygpath"]=="1"):
        list_args_dir=[ "--output_dir_for_put",myutils.convert_to_cygpath(dict_conf["table_object_manager"]["output_touch"]),
                        "--output_dir_for_taken",myutils.convert_to_cygpath(dict_conf["table_object_manager"]["output_release"]),
                        "--output_dir_for_background",myutils.convert_to_cygpath(dict_conf["table_object_manager"]["output_rawimage"]),
                        ]
    else:
        list_args_dir=[ "--output_dir_for_put",dict_conf["table_object_manager"]["output_touch"],
                        "--output_dir_for_taken",dict_conf["table_object_manager"]["output_release"],
                        "--output_dir_for_background",dict_conf["table_object_manager"]["output_rawimage"],
                        ]

    if dict_conf["table_object_manager"]["workspace_end_filename"] != "":
        if(dict_conf["product_env"]["use_cygpath"]=="1"):
            list_args_dir = list_args_dir + ["--workspace_end_filename",myutils.convert_to_cygpath(dict_conf["table_object_manager"]["workspace_end_filename"]),]
        else:
            list_args_dir = list_args_dir + ["--workspace_end_filename",dict_conf["table_object_manager"]["workspace_end_filename"],]

    list_args_opt=dict_conf["table_object_manager"]["default_options"].split()
    list_args_TOM=list_args_dir+list_args_opt
    return list_args_TOM


def startTableObjectManager(dict_conf, output_to):
    logger = logging.getLogger()

    list_args_TOM=make_list_args_TOM(dict_conf)
    list_cmd = [dict_conf["table_object_manager"]["path_exec"]] + list_args_TOM

    logger.debug("Exec table_object_manager: " + str(list_cmd))

    if(dict_conf["product_env"]["enable_table_object_manager"]=="1"):
        # myutils.callproc_cyg(dict_conf["table_object_manager"]["path_exec"],list_args_TOM)
        try:
            p = subprocess.Popen(
                list_cmd,
                stdout=output_to,
                stderr=subprocess.STDOUT
                )
        except subprocess.CalledProcessError as e:
            logger.critical("({0}): {1}".format(e.returncode, e.output))
        except OSError as e:
            logger.critical("({0}): {1}".format(e.errno, e.strerror))

    return p
