#!/usr/bin/env python
import rospy
import rospkg
import numpy as np
from heapq import *
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from geometry_msgs.msg import Vector3
from geometry_msgs.msg import Point
from tf.transformations import euler_from_quaternion
import math
rotate_flag=0
translate_flag=0
new_path=[]
next=[]
global robot_x
robot_x=-8
global robot_y
robot_y=-2
global goalx
global goaly

def getArrayLoc(x,y):
	x=int(x+9)
	if x>=18:
		x=17
	if x<0:
		x=0
	y=int(10-y)
	if y>=20:
		y=19
	if y<0:
		y=0
	return (y,x)

def getActualLoc(y,x):
	x=x-9+0.5
	if x>9:
		x=9
	y=10-y-0.5
	if y>10:
		y=10
	return (x,y)

def heuristic(current,goal):
	manhattan_dist = abs(current[0]-goal[0])+abs(current[1]-goal[1])
	return manhattan_dist

def getNeighbors(current,mapArray):
	x=current[0]
	y=current[1]
	neighbors=set()
	if(x+1<20 and x+1>=0):
		if(not(mapArray[x+1][y])):
			neighbors.add((x+1,y))
	if(x-1>=0 and x-1<20):	
		if(not(mapArray[x-1][y])):
			neighbors.add((x-1,y))
	if(y+1<18 and y+1>=0):	
		if(not(mapArray[x][y+1])):
			neighbors.add((x,y+1))
	if(y-1>=0 and y-1<18):
		if(not(mapArray[x][y-1])):
			neighbors.add((x,y-1))
	return neighbors

def astar(start,goal,mapArray):
	openlist = []
	closedlist = []
	parent = {}
	gvalue = {start:0}
	fvalue = {start:heuristic(start, goal)}
	openlist.append(start)
	while openlist:
		min_f=1000
		for element in openlist:
			if fvalue[element]< min_f:
				min_f=fvalue[element]
				min_element=element
		current=min_element
		index=openlist.index(min_element)
		del openlist[index]
			
		if current == goal:
			path = []
			while current in parent:
				path.append(current)
				current = parent[current]
			path.append(current)
			return path[::-1]

		closedlist.append(current)
		neighbors=getNeighbors(current, mapArray)
		for x in neighbors:
			if x in closedlist:
				continue
			if x in openlist:
				temp = gvalue[current] + 1
				if temp < gvalue[x]:
			    		gvalue[x] = temp
			    		parent[x] = current
		    	else:
				gvalue[x] = gvalue[current] + 1
				fvalue[x] = gvalue[x]+heuristic(x, goal)
				parent[x] = current
				openlist.append(x)
				
def change_next():
	global new_path
	if new_path:
		return new_path.pop(0)
	else:
		return None

def baseCallback(odom):
	global rotate_flag
	global translate_flag
	global next
	global robot_x
	global robot_y
	global goalx
	global goaly

	#Condition when the intermediate point in the path is met
	if translate_flag and rotate_flag:
		#Interrupt when ros parameter is changed
		if goalx!= rospy.get_param('goalx') or goaly!= rospy.get_param('goaly'):
			goalx=rospy.get_param('goalx')
			goaly= rospy.get_param('goaly')
			pathplan((robot_x,robot_y),(goalx,goaly))
		next=change_next()
		#Final goal is met
		if next== None:
			return
		rotate_flag=0
		translate_flag=0
		
	#Motion		
	pub = rospy.Publisher('/cmd_vel',Twist,queue_size=10)
	robot_x=odom.pose.pose.position.x
	robot_y=odom.pose.pose.position.y
	quaternion=(odom.pose.pose.orientation.x,odom.pose.pose.orientation.y,odom.pose.pose.orientation.z,odom.pose.pose.orientation.w)
	euler = euler_from_quaternion(quaternion)
	robot_angle= euler[2]
	
	goal_x=next[0]
	goal_y=next[1]
	if goal_x==robot_x:
		if goal_y>robot_y:
			goal_angle=math.pi/2
		elif goal_y<robot_y:
			goal_angle=-(math.pi/2)
		else:
			goal_angle=robot_angle
	elif goal_y==robot_y:
		if goal_x>robot_x:
			goal_angle=0
		elif goal_x<robot_x:
			goal_angle=math.pi
		else:
			goal_angle=robot_angle
	else:
		goal_angle=math.atan2((goal_y-robot_y),(goal_x-robot_x))
	
	#Rotation
	if abs(goal_angle-robot_angle)>0.1 and rotate_flag==0:
		msg=Twist()
		msg.linear.x=0
		msg.angular.z=-0.8
		pub.publish(msg)
		return
	else:
		rotate_flag=1

	#Translation
	if abs(goal_x-robot_x)>0.15 or abs(goal_y-robot_y)>0.15 and translate_flag==0:
		msg1=Twist()
		msg1.linear.x=2.0
		pub.publish(msg1)
		return
	else:
		translate_flag=1

def pathplan(start,goal):
	global new_path
	global next

	#Reading map.txt
	rospack = rospkg.RosPack()
	f = open(rospack.get_path('lab5')+'/map/map.txt', 'r')
	mapArray=np.zeros((20,18))
	r=0
	for line in f:
		line=line[7:42]
		line=line.replace(',','')
		for c in range(18):
			mapArray[r][c]=line[c]
		r=r+1
	start=getArrayLoc(start[0],start[1])
	goal=getArrayLoc(goal[0],goal[1])

	#Call A*
	path=astar(start,goal,mapArray)

	#Motion
	new_path=[]
	for x in path:
		x=getActualLoc(x[0],x[1])
		new_path.append(x)

	if len(new_path)>1:
		next=new_path[1]
		new_path.pop(0)
	new_path.pop(0)
	rospy.Subscriber("base_pose_ground_truth", Odometry, baseCallback)

if __name__ =="__main__":
	try:
		rospy.init_node('lab5',anonymous=True)
		rate = rospy.Rate(10)

		#Default parameter
		rospy.set_param('goalx', 4.5)
		rospy.set_param('goaly', 9)
		goalx= rospy.get_param('goalx')
		goaly=rospy.get_param('goaly')

		start=(robot_x,robot_y)
		goal=(goalx,goaly)
		pathplan(start,goal)	
					
	except rospy.ROSInterruptException:
        	pass
	rospy.spin()
