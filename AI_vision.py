import os
import tensorflow as tf
from PIL import Image
import numpy as np
import cv2

#画像を加工する関数たち-----------------------------------------------
def convert_to_opencv(image):
    # RGB -> BGR conversion is performed as well.
    image = image.convert('RGB')
    r,g,b = np.array(image).T
    opencv_image = np.array([b,g,r]).transpose()
    return opencv_image

def crop_center(img,cropx,cropy):
    h, w = img.shape[:2]
    startx = w//2-(cropx//2)
    starty = h//2-(cropy//2)
    return img[starty:starty+cropy, startx:startx+cropx]

def resize_down_to_1600_max_dim(image):
    h, w = image.shape[:2]
    if (h < 1600 and w < 1600):
        return image

    new_size = (1600 * w // h, 1600) if (h > w) else (1600, 1600 * h // w)
    return cv2.resize(image, new_size, interpolation = cv2.INTER_LINEAR)

def resize_to_256_square(image):
    h, w = image.shape[:2]
    return cv2.resize(image, (256, 256), interpolation = cv2.INTER_LINEAR)

def update_orientation(image):
    exif_orientation_tag = 0x0112
    if hasattr(image, '_getexif'):
        exif = image._getexif()
        if (exif != None and exif_orientation_tag in exif):
            orientation = exif.get(exif_orientation_tag, 1)
            # orientation is 1 based, shift to zero based and flip/transpose based on 0-based values
            orientation -= 1
            if orientation >= 4:
                image = image.transpose(Image.TRANSPOSE)
            if orientation == 2 or orientation == 3 or orientation == 6 or orientation == 7:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
            if orientation == 1 or orientation == 2 or orientation == 5 or orientation == 6:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
    return image

#----------------------------------------------------------------------------------------

graph_def = tf.compat.v1.GraphDef()
labels = []

AI = "AI_Model/model.pb"
labels_name = "AI_Model/labels.txt"
#AIモデルの読み込み
with tf.io.gfile.GFile(AI, 'rb') as f:
    graph_def.ParseFromString(f.read())
    tf.import_graph_def(graph_def, name='')
#ラベル情報のよみこみ
with open(labels_name, 'rt') as lf:
    for l in lf:
        labels.append(l.strip())

imageFile = "image_temp/test.jpg"
image = Image.open(imageFile)

image = update_orientation(image)
image = convert_to_opencv(image)
image = resize_down_to_1600_max_dim(image)

h, w = image.shape[:2]
min_dim = min(w,h)
max_square_image = crop_center(image, min_dim, min_dim)

augmented_image = resize_to_256_square(max_square_image)



with tf.compat.v1.Session() as sess:
    input_tensor_shape = sess.graph.get_tensor_by_name('Placeholder:0').shape.as_list()
network_input_size = input_tensor_shape[1]

# Crop the center for the specified network_input_Size
augmented_image = crop_center(augmented_image, network_input_size, network_input_size)

#おそらくメインの処理部
output_layer = 'loss:0'
input_node = 'Placeholder:0'

with tf.compat.v1.Session() as sess:
    try:
        prob_tensor = sess.graph.get_tensor_by_name(output_layer)
        predictions = sess.run(prob_tensor, {input_node: [augmented_image] })
    except KeyError:
        print ("分類出力レイヤーが見つかりませんでした: " + output_layer + ".")
        print ("オブジェクト検出プロジェクトからエクスポートされたモデルであることを確認します.")
        exit(-1)

#表示部分
#最も高い確率であるラベルを表示する
highest_probability_index = np.argmax(predictions)
print('Classified as: ' + labels[highest_probability_index])
print()

# 各ラベルの確立の羅列
label_index = 0
for p in predictions:
    truncated_probablity = np.float64(np.round(p,8))
    print (labels[label_index], truncated_probablity)
    label_index += 1
