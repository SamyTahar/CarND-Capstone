#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml
from scipy.spatial import KDTree
import numpy as np
import math

STATE_COUNT_THRESHOLD = 0

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector')

        self.pose = None
        self.waypoints = None
        self.camera_image = None
        self.waypoint_tree = None
        self.waypoints_2d = None
        self.lights = []
        self.has_image = None

        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)
        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        '''
        /vehicle/traffic_lights provides you with the location of the traffic light in 3D map space and
        helps you acquire an accurate ground truth data source for the traffic light
        classifier by sending the current color state of all traffic lights in the
        simulator. When testing on the vehicle, the color state will not be available. You'll need to
        rely on the position of the light and the camera image to predict it.
        '''
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)
        sub6 = rospy.Subscriber('/image_color', Image, self.image_cb)

        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)
        self.is_sim = self.config["is_site"]

        self.bridge = CvBridge()
        self.light_classifier = TLClassifier(self.is_sim)
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0
        #line_wp_idx, state = self.process_traffic_lights()

        self.loop()

    def loop(self):
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            if self.pose and self.last_wp is not None and self.camera_image is not None and self.waypoints is not None:
                self.publish_light()

    def publish_light(self):
        #self.upcoming_red_light_pub.publish(Int32(light_seen))
        '''
        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.
        '''
        line_wp_idx, state = self.process_traffic_lights()

        if self.state != state:
            self.state_count = 0
            self.state = state
        elif self.state_count >= STATE_COUNT_THRESHOLD:
            self.last_state = self.state
            rospy.logerr('current_light_state: %s', state)
            if state == 0 :
                rospy.logerr('state red yes: %s', state)
                line_wp_idx = line_wp_idx
            else:
                rospy.logerr('state red no: %s', state)
                line_wp_idx = -1

            self.last_wp = line_wp_idx
            self.upcoming_red_light_pub.publish(Int32(line_wp_idx))
        else:
            self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        self.state_count += 1

    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):

        self.waypoints = waypoints
        if not self.waypoints_2d:
            #rospy.loginfo("inside waypoints_cb waypoints_2d")
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            #rospy.loginfo("waypoints_2d: %s, %s",self.waypoints_2d[0],self.waypoints_2d[1])
            self.waypoint_tree = KDTree(self.waypoints_2d)

    def traffic_cb(self, msg):
        self.lights = msg.lights
        #rospy.loginfo("lights are: %s", self.lights )

    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light's stop line to /traffic_waypoint

        Args:
            msg (Image): image from car-mounted camera

        """
        self.has_image = True
        self.camera_image = msg

    def get_closest_waypoint(self, pose_x, pose_y):
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to

        Returns:
            int: index of the closest waypoint in self.waypoints

        """
        #TODO implement
        x = pose_x
        y = pose_y

        closest_idx = None

        if self.waypoint_tree is not None:
            #rospy.loginfo("type waypoint_tree: %s", self.waypoint_tree.query([x,y],1)[1])
            closest_idx = self.waypoint_tree.query([x,y],1)[1]


        return closest_idx

    def get_light_state(self, light):
        """Determines the current color of the traffic light

        Args:
            light (TrafficLight): light to classify

        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        #rospy.loginfo('light state: %s',light.state )

        #return light.state
        if(not self.has_image):
            self.prev_light_loc = None
            return False

        cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "bgr8")

        #Get classification
        return self.light_classifier.get_classification(cv_image)

    def process_traffic_lights(self):
        """Finds closest visible traffic light, if one exists, and determines its
            location and color

        Returns:
            int: index of waypoint closes to the upcoming stop line for a traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        #light = None
        closest_light = None
        line_wp_idx = None
        #temp_wp_idx = None
        car_wp_idx = None


        rospy.loginfo('process_traffic_lights used')

        # List of positions that correspond to the line to stop in front of for a given intersection
        stop_line_positions = self.config['stop_line_positions']
        if(self.pose):
            car_wp_idx = self.get_closest_waypoint(self.pose.pose.position.x, self.pose.pose.position.y)

        #TODO find the closest visible traffic light (if one exists)
        if self.waypoints and car_wp_idx is not None:
            diff = len(self.waypoints.waypoints)
            for i, light in enumerate(self.lights):
                #get stop line waypoint idx
                line = stop_line_positions[i]
                traffic_light_wp_idx = self.get_closest_waypoint(line[0],line[1])
                #Find closest stop line waypoint index
                d = (traffic_light_wp_idx - car_wp_idx)
                if d  >= 0 and d < diff:
                    diff = d
                    closest_light = light
                    line_wp_idx = traffic_light_wp_idx

        if closest_light:
            state = self.get_light_state(closest_light)
            #distance = self.__calc_distance(car_wp_idx, line_wp_idx)
            #if hasattr(closest_light, 'state') and (closest_light.state != state) and (distance < 75.0):
            #    rospy.logwarn("Incorrect classification at TL %i: state=%s expected=%s at distance %.1f m",
            #                  closest_light_idx, state, closest_light.state, distance)
            return line_wp_idx , state

        #self.waypoints = None
        return -1, TrafficLight.UNKNOWN

    def __calc_distance(self, start_idx, end_idx):
        """Calculates the distance between two base waypoints"""

        def dl(a, b):
            return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

        total_dist = 0
        num_wps = (end_idx - start_idx) % len(self.waypoints.waypoints)
        idx1 = start_idx
        for i in range(num_wps):
            idx0 = idx1
            idx1 = (idx0 + 1) % len(self.waypoints.waypoints)

            total_dist += dl(self.waypoints.waypoints[idx0].pose.pose.position,
                             self.waypoints.waypoints[idx1].pose.pose.position)
        return total_dist

if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')
