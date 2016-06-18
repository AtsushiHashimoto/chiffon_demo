# -*- coding: utf-8 -*-

import sys
import os
import cv2
import numpy as np

caffe_root = '/Users/ahashimoto/tmp/fasterrcnn_tmp/py-faster-rcnn'
#caffe_root = '/Users/fujino/caffe/py-faster-rcnn/caffe-fast-rcnn/'
frcnn_root = '/Users/ahashimoto/tmp/fasterrcnn_tmp/py-faster-rcnn/tools/'
#frcnn_root = '/Users/fujino/caffe/py-faster-rcnn/tools/'
sys.path.insert(0, caffe_root + 'python')
sys.path.insert(0, frcnn_root)

import caffe
import _init_paths
from fast_rcnn.config import cfg
from fast_rcnn.test import im_detect
from fast_rcnn.nms_wrapper import nms


class Frcnn:
    """
    private:
        caffemodel_path
        prototxt_path
    public:
        classes: a tuple of classes (class1, class2, ... )
        net: caffe.Net 
    """
    def __init__(self,
                 caffemodel_path,
                 prototxt_path,
                 classes, 
                 gpu = False, gpu_id = 0) :
        self._caffemodel_path = caffemodel_path
        self._prototxt_path = prototxt_path
        self.classes = classes
        cfg.TEST.HAS_RPN = True  # Use RPN for proposals
        if gpu:
            caffe.set_mode_gpu()
            caffe.set_device(gpu_id)
            cfg.GPU_ID = gpu_id
        else:
            caffe.set_mode_cpu()
        self.net = caffe.Net(self._prototxt_path, self._caffemodel_path, caffe.TEST)

    def detect(self, img):
        scores, boxes = im_detect(self.net, img) # scores 300*1, boxes 300*4 
        return scores, boxes


#def visualize(detection, img):
#    print 'visualize...'
#    color = [(255,0,0), (0,255,0), (0,0,255), (0,255,255), (255,0,255), (255,255,0)]
#    color_idx = 0
#    for cls, dets in detection.items():
#        for det in sorted(dets, key = lambda x: x[4]):
#            xmin, ymin, xmax, ymax, score = det
#            img = cv2.rectangle(img, (xmin, ymin), (xmax, ymax), color[color_idx], 1)
#            print (u'\t%s:%.2f'%(cls, score)).encode('utf-8')
#            try:
#                cv2.putText(img, '%s:%.2f'%(cls, score), \
#                                (xmin, ymin), cv2.FONT_HERSHEY_SIMPLEX, \
#                                0.6, color[color_idx], 2)
#            except:
#                cv2.putText(img, '%.2f'%score, \
#                                (xmin, ymin), cv2.FONT_HERSHEY_SIMPLEX, \
#                                0.6, color[color_idx], 2)
#            color_idx = (color_idx + 1) % len(color)
#    cv2.imshow('visualize', img)
#    cv2.waitKey(0)
#    cv2.destroyAllWindows() 


def frcnn_detection(background_img, observed_img, mask_img, frcnn):
    XMIN_IDX = 0
    YMIN_IDX = 1
    XMAX_IDX = 2
    YMAX_IDX = 3
    SCORE_IDX = 4

    NMS_THRESH =0.3
    SCORE_THRESH =0.01
    OVERLAP_THRESH =0.5


    def _non_maximum_suppression(scores, boxes, classes):
        """
        output: dictionay key: classs; value: a list of [xmin, ymin, xmax, ymax, score] 
        """
        detection = {}
        for cls_idx, cls in enumerate(classes[1:]):
            cls_idx += 1 # because we skipped background
            cls_boxes = boxes[:, 4*cls_idx:4*(cls_idx + 1)]
            cls_scores = scores[:, cls_idx]
            dets = np.hstack((cls_boxes, cls_scores[:, np.newaxis])).astype(np.float32)
            keep = nms(dets, NMS_THRESH) # non maximum suppression
            dets = dets[keep, :] # remove overlapped non maximum boxes
            dets = dets[dets[:, SCORE_IDX] > SCORE_THRESH, :] # remove boxes with low scores
            if dets.size > 0:
                detection[cls] = dets
        return detection 


    def _overlap_area(box1, box2):
        """
        return the area of overlapped region
        """
        xmin1, ymin1, xmax1, ymax1 = box1
        xmin2, ymin2, xmax2, ymax2 = box2
        if xmin1 <= xmax2 and xmin2 <= xmax1 and ymin1 <= ymax2 and ymin2 <= ymax1: # two boxes intersects?
            overlap_xmin = np.max([xmin1, xmin2]) 
            overlap_ymin = np.max([ymin1, ymin2]) 
            overlap_xmax = np.min([xmax1, xmax2]) 
            overlap_ymax = np.min([ymax1, ymax2]) 
            overlap_area = float((overlap_xmax - overlap_xmin) * (overlap_ymax - overlap_ymin))
            return overlap_area 
        else:
            return 0.0


    def _subtraction(bg_detection, ob_detection): 
        """
        return probabilities of put-taken
        taken : -1.0 ~ 1.0 : put

        output: a list of tuples (class, probability)

        subtracion of background box and observed box:
        1. overlap rate = intersection area of two boxes / union area of two boxes
        2. make pair of background box and observed box in decreasing order in overlap rate (no duplication)
        3. estimate the probaility of the pair by subtracting background probability from observed probability 
        """
        put_probabilities = {} 
        taken_probabilities = {} 
        bg_classes = set(list(bg_detection.keys()))
        ob_classes = set(list(ob_detection.keys()))

        for cls in bg_classes - ob_classes: # appear in only background image
            for det in bg_detection[cls]:
                if cls not in taken_probabilities:
                    taken_probabilities[cls] = []
                taken_probabilities[cls].append(det[SCORE_IDX]) # taken

        for cls in ob_classes - bg_classes: # appear in only observed image 
            for det in ob_detection[cls]:
                if cls not in put_probabilities:
                    put_probabilities[cls] = []
                put_probabilities[cls].append(det[SCORE_IDX]) # put

        for cls in  bg_classes & ob_classes: # appear in both background image and observed image 
            overlap_boxes = {}
            bg_dets = bg_detection[cls] 
            ob_dets = ob_detection[cls] 
            bg_areas = (bg_dets[:,XMAX_IDX] - bg_dets[:,XMIN_IDX]) * (bg_dets[:,YMAX_IDX] - bg_dets[:,YMIN_IDX])
            ob_areas = (ob_dets[:,XMAX_IDX] - ob_dets[:,XMIN_IDX]) * (ob_dets[:,YMAX_IDX] - ob_dets[:,YMIN_IDX])
            for bg_idx, bg_det in enumerate(bg_dets):
                for ob_idx, ob_det in enumerate(ob_dets):
                    overlap_area = _overlap_area(bg_det[:-1], ob_det[:-1])
                    if overlap_area != 0.0:
                        # overlap rate = intersection area of two boxes / union area of two boxes
                        overlap_rate = overlap_area / (bg_areas[bg_idx] + ob_areas[ob_idx] - overlap_area)
                        if overlap_rate >= OVERLAP_THRESH:
                            overlap_boxes[(bg_idx, ob_idx)] = overlap_rate

            bg_finished = np.array([False] * bg_dets.shape[0]) 
            ob_finished = np.array([False] * ob_dets.shape[0]) 
            # make pair of background box and observed box in decreasing order in overlap rate (no duplication)
            for indices, overlap_rate in sorted(overlap_boxes.items(), key = lambda x : x[1], reverse = True):
                bg_idx, ob_idx = indices
                if not bg_finished[bg_idx] and not ob_finished[ob_idx]:
                    bg_finished[bg_idx] = True
                    ob_finished[ob_idx] = True
                    if cls not in put_probabilities:
                        put_probabilities[cls] = []
                    put_probabilities[cls].append(ob_dets[ob_idx, SCORE_IDX] * (1 - bg_dets[bg_idx, SCORE_IDX]))
                    if cls not in taken_probabilities:
                        taken_probabilities[cls] = []
                    taken_probabilities[cls].append((1 - ob_dets[ob_idx, SCORE_IDX]) * bg_dets[bg_idx, SCORE_IDX])

            # the rest of boxes 
            for det in bg_dets[~bg_finished, :]:
                if cls not in taken_probabilities:
                    taken_probabilities[cls] = []
                taken_probabilities[cls].append(det[SCORE_IDX]) # taken
            for det in ob_dets[~ob_finished, :]:
                if cls not in put_probabilities:
                    put_probabilities[cls] = []
                put_probabilities[cls].append(det[SCORE_IDX]) # put 

        probabilities = [(cls, np.max(put_probabilities[cls])) for cls in put_probabilities.keys()]
        probabilities.extend([(cls, -np.max(taken_probabilities[cls])) for cls in taken_probabilities.keys()])

        return probabilities


    gray_mask_img = cv2.cvtColor(mask_img, cv2.COLOR_RGB2GRAY)
    # dilation 
    neiborhood8 = np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]], np.uint8)
    gray_mask_img = cv2.dilate(gray_mask_img, neiborhood8, iterations=50)

    masked_background_img = background_img
    masked_background_img[gray_mask_img == 0] = [0,0,0] 

    masked_observed_img = observed_img
    masked_observed_img[gray_mask_img == 0] = [0,0,0] 

    bg_scores, bg_boxes = frcnn.detect(masked_background_img)
    bg_detection = _non_maximum_suppression(bg_scores, bg_boxes, frcnn.classes) 
    #visualize(bg_detection, masked_background_img)

    ob_scores, ob_boxes = frcnn.detect(masked_observed_img)
    ob_detection = _non_maximum_suppression(ob_scores, ob_boxes, frcnn.classes) 
    #visualize(ob_detection, masked_observed_img)

    probabilities = _subtraction(bg_detection, ob_detection) 

    return sorted(probabilities, key = lambda x : x[1])

