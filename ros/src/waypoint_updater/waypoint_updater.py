#!/usr/bin/env python

import rospy
from std_msgs.msg import Int32
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
from scipy.spatial import KDTree
import numpy as np

import math

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.
As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.
Once you have created dbw_node, you will update this node to use the status of traffic lights too.
Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.
TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 55 # Number of waypoints we will publish. You can change this number


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        #  Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)
        rospy.Subscriber('/vehicle/obstacle_points', PointCloud2, self.obstacle_cb)

        self.final_waypoints_pub = rospy.Publisher('/final_waypoints', Lane, queue_size=10)

        # Add other member variables you need below
        self.pose = None
        self.waypoints_2d = None
        self.base_waypoints = None
        self.waypoint_tree = None

        self.loop()

    def loop(self):
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():

            if self.pose and self.base_waypoints:
                closest_waypoint_idx = self.get_closest_waypoint_idx()
                #rospy.loginfo("type waypoint_tree: %s", closest_waypoint_idx)
                self.publish_waypoints(closest_waypoint_idx)

                #for debug purpose display value X and Y from pose publisher by using the pose_cb Callback function
                #rospy.loginfo("pose_cb message: x=%.2f,y=%.2f ", self.pose.pose.position.x,self.pose.pose.position.y)

                #for waypoint in self.base_waypoints.waypoints:
                #    rospy.loginfo("base_waypoints message: x=%.2f ", waypoint.pose.pose.position.x)
            rate.sleep()

    def get_closest_waypoint_idx(self):
        x = self.pose.pose.position.x
        y = self.pose.pose.position.y

        closest_idx = None

        if self.waypoint_tree is not None:
            #rospy.loginfo("type waypoint_tree: %s", self.waypoint_tree.query([x,y],1)[1])
            closest_idx = self.waypoint_tree.query([x,y],1)[1]


            #Check if closest is ahead or behind vehicle
            closest_coord = self.waypoints_2d[closest_idx]
            prev_coord = self.waypoints_2d[closest_idx -1]

            #Equation for hyperplane through closest_coords
            cl_vect = np.array(closest_coord)
            prev_vect = np.array(prev_coord)
            pos_vect = np.array([x,y])

            val = np.dot(cl_vect - prev_vect, pos_vect - cl_vect)

            if val > 0:
                closest_idx = (closest_idx + 1) % len(self.waypoints_2d)

        return closest_idx

    def publish_waypoints(self, closest_idx):
        if closest_idx is not None:
            lane = Lane()
            lane.header = self.base_waypoints.header
            lane.waypoints = self.base_waypoints.waypoints[closest_idx:closest_idx + LOOKAHEAD_WPS]
            rospy.loginfo("lane %s", lane )
            self.final_waypoints_pub.publish(lane)

    def pose_cb(self, msg):
        # use the msg from the /current_pose subscriber
        self.pose = msg


    def waypoints_cb(self, waypoints):
        # TODO: add comment on how it is working
        self.base_waypoints = waypoints
        if not self.waypoints_2d:
            rospy.loginfo("inside waypoints_cb waypoints_2d")
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            rospy.loginfo("waypoints_2d: %s, %s",self.waypoints_2d[0],self.waypoints_2d[1])
            self.waypoint_tree = KDTree(self.waypoints_2d)

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        pass

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
