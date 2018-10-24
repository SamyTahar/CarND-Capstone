from styx_msgs.msg import TrafficLight
import tensorflow as tf
import numpy as np
import datetime
import rospy


class TLClassifier(object):
    def __init__(self, is_sim):
        #TODO load classifier

        if is_sim is False:
            PATH_TO_GRAPH = r'light_classification/models/sim/frozen_inference_graph.pb'
            rospy.logwarn('PATH_TO_GRAPH: %s', PATH_TO_GRAPH)
            rospy.logwarn('simulator')
        else:
            PATH_TO_GRAPH = r'light_classification/models/site/frozen_inference_graph.pb'
            rospy.logwarn('PATH_TO_GRAPH: %s', PATH_TO_GRAPH)
            rospy.logwarn('on site')

        self.graph = tf.Graph()
        self.threshold = .5

        with self.graph.as_default():
             od_graph_def = tf.GraphDef()
             with tf.gfile.GFile(PATH_TO_GRAPH, 'rb') as fid:
                 od_graph_def.ParseFromString(fid.read())
                 tf.import_graph_def(od_graph_def, name='')

             self.image_tensor = self.graph.get_tensor_by_name('image_tensor:0')
             self.boxes = self.graph.get_tensor_by_name('detection_boxes:0')
             self.scores = self.graph.get_tensor_by_name('detection_scores:0')
             self.classes = self.graph.get_tensor_by_name('detection_classes:0')
             self.num_detections = self.graph.get_tensor_by_name('num_detections:0')

        self.sess = tf.Session(graph=self.graph)

    def get_classification(self, image):
        """Determines the color of the traffic light in the image
        Args:
            image (cv::Mat): image containing the traffic light
        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)
        """
        #TODO implement light color prediction

        with self.graph.as_default():
            img_expand = np.expand_dims(np.asarray(image, dtype=np.uint8), 0)
            (boxes, scores, classes, num_detections) = self.sess.run(
                [self.boxes, self.scores, self.classes, self.num_detections],
                feed_dict={self.image_tensor: img_expand})

        boxes = np.squeeze(boxes)
        scores = np.squeeze(scores)
        classes = np.squeeze(classes).astype(np.int32)

        #confidence_cutoff = .1

        #boxes, scores, classes = self.filter_boxes(confidence_cutoff, boxes, scores, classes)

        #if scores[0] is not None:
        #    print('SCORES: ', scores[0])
        #    print('CLASSES: ', classes[0])

        if scores[0] > self.threshold:
            if classes[0] == 1:
                print('GREEN')
                return TrafficLight.GREEN
            elif classes[0] == 2:
                print('RED')
                return TrafficLight.RED
            elif classes[0] == 3:
                print('YELLOW')
                return TrafficLight.YELLOW
            elif classes[0] == 4:
                print('UNKNOWN')
                return TrafficLight.UNKNOWN

        return TrafficLight.UNKNOWN

    def filter_boxes(self, min_score, boxes, scores, classes):
        """Return boxes with a confidence >= `min_score`"""
        n = len(classes)
        idxs = []
        for i in range(n):
            if scores[i] >= min_score:
                idxs.append(i)

        filtered_boxes = boxes[idxs, ...]
        filtered_scores = scores[idxs, ...]
        filtered_classes = classes[idxs, ...]
        return filtered_boxes, filtered_scores, filtered_classes
