# -*- coding: cp932 -*-
import cv2
import numpy as np

img = cv2.imread("frame0007.jpg");

w = 615
h=308
deep_w=200

par1 = np.float32([[0,h],[w,h],[w-deep_w,0],[deep_w,0]])# ���̍��W�ʒu
par2 = np.float32([[0,h],[w,h],[w,0],[0,0]]) # �ϊ���̍��W�ʒu
psp_matrix = cv2.getPerspectiveTransform(par1, par2)
img_psp = cv2.warpPerspective(img , psp_matrix , (w ,h+100))

cv2.imshow("image org",img)

cv2.imshow("image",img_psp)
key= cv2.waitKey(0)
