#!/usr/bin/env python
'''
**********************************************************************
* Filename    : line_follower
* Description : An example for sensor car kit to followe line
* Author      : Dream
* Brand       : SunFounder
* E-mail      : service@sunfounder.com
* Website     : www.sunfounder.com
* Update      : Dream    2016-09-21    New release
**********************************************************************
'''

from SunFounder_Line_Follower import Line_Follower
from picar import front_wheels
from picar import back_wheels
import time
import picar
import ctypes
import pathlib
import sys
import os
import numpy 


# This is the beginning of the script
# Initialize the access to the C library
libname = os.path.abspath(".") + "/" + "../../../uobjcoll-SunFounder_Line_Follower/libLine_Follower.so";
print(libname)
c_lib = ctypes.CDLL(libname)

banglibname = os.path.abspath(".") + "/" + "libbangbang.so"
bang_lib = ctypes.CDLL(banglibname)
bang_lib.calculate_angle_speed.argtypes = [ numpy.ctypeslib.ndpointer(dtype=numpy.int32), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]

picar.setup()
rslt = c_lib.lib_init()
if rslt == -1:
	print("lib_init() failed")
	exit()

REFERENCES = [200, 200, 200, 200, 200]
#calibrate = True
calibrate = False
forward_speed = 90
backward_speed = 70
turning_angle = 40
current_angle = 0
off_track_count = 0
step=0
a_step = 2
b_step = 8
c_step = 24
d_step = 40

max_off_track_count = 40

delay = 0.0005

fw = front_wheels.Front_Wheels(db='config')
bw = back_wheels.Back_Wheels(db='config')
lf = Line_Follower.Line_Follower()
lf.references = REFERENCES
fw.ready()
bw.ready()
fw.turning_max = 45


def setup():
	if calibrate:
		cali()


def calculate_speed(lt_st_now,fw_speed,st):
	speed=fw_speed
	a_step = 2
	b_step = 8
	c_step = 24
	d_step = 40
	if	lt_st_now == [0,0,1,0,0]:
		st = 0
	elif lt_st_now == [0,1,1,0,0] or lt_st_now == [0,0,1,1,0]:
		step = a_step
		speed = fw_speed - 10
	elif lt_st_now == [0,1,0,0,0] or lt_st_now == [0,0,0,1,0]:
		st = b_step
		speed = fw_speed - 15
	elif lt_st_now == [1,1,0,0,0] or lt_st_now == [0,0,0,1,1]:
		st = c_step
		speed = forward_speed - 25
	elif lt_st_now == [1,0,0,0,0] or lt_st_now == [0,0,0,0,1]:
		st = d_step
		speed = fw_speed - 35
	else:   # Handle the case when we read all 0s - when we are completely out
		st = d_step
		speed = fw_speed - 40
	return speed,st


def calculate_angle(lt_st_now,turn_angle,st):
	if	lt_st_now == [0,0,1,0,0]:
		turn_angle = 90
	# turn right
	elif lt_st_now in ([0,1,1,0,0],[0,1,0,0,0],[1,1,0,0,0],[1,0,0,0,0]):
		turn_angle = int(90 - st)
	# turn left
	elif lt_st_now in ([0,0,1,1,0],[0,0,0,1,0],[0,0,0,1,1],[0,0,0,0,1]):
		turn_angle = int(90 + st)
	return turn_angle


def calculate_angle_speed(lt_st_now,fw_speed,turn_angle,st):
	speed,step = calculate_speed(lt_st_now,fw_speed,st)
	turn_angle = calculate_angle(lt_st_now,turn_angle,st)
	return speed,step,turn_angle
	


def main():
	global turning_angle

	bw.speed = forward_speed
	bw.forward()
	lt_status_now = []
	step = 0

	start_time_ms = time.time() * 1000
	while True:
                ### clib call
		lt_status_now = []
		dt_list = c_lib.read_digital()
		ptr = ctypes.cast(dt_list,ctypes.POINTER(ctypes.c_int))
		for i in range(0,5):
			lt_status_now.append(ptr[i])

		diff_ms = (time.time() * 1000) - start_time_ms
		print(str(lt_status_now)[1:-1] + ", " + str(diff_ms))

		off_track_count = 0

		if lt_status_now == [0,0,0,0,0]:
			off_track_count += 1
			if off_track_count > max_off_track_count:
				tmp_angle = (turning_angle-90)/abs(90-turning_angle)
				tmp_angle *= fw.turning_max
				bw.speed = backward_speed
				bw.backward()
				fw.wheel.write(tmp_angle)
				current_angle = tmp_angle

				### clib call
				c_lib.wait_tile_center()
				bw.stop()

				fw.wheel.write(turning_angle)
				current_angle = turning_angle
				time.sleep(0.2)
				bw.speed = forward_speed
				bw.forward()
				time.sleep(0.2)
			else:
				off_track_count = 0
		else:
			# Call either Python or C functions for getting speed and angle
			#ret_speed,step,turning_angle = calculate_angle_speed(lt_status_now,forward_speed,turning_angle,step)
			#bw.speed = ret_speed
			bang_list = bang_lib.calculate_angle_speed(numpy.array(lt_status_now),5,forward_speed,turning_angle,step)
			ptr = ctypes.cast(bang_list,ctypes.POINTER(ctypes.c_int))
			bw.speed = ptr[0] 
			step = ptr[1]
			turning_angle = ptr[2]
			
		fw.wheel.write(turning_angle)
		current_angle = turning_angle
		time.sleep(delay)

def cali():
	references = [0, 0, 0, 0, 0]
	print("cali for module:\n  first put all sensors on white, then put all sensors on black")
	mount = 100
	fw.turn(70)
	print("\n cali white")
	time.sleep(4)
	fw.turn(90)
	white_references = lf.get_average(mount)
	fw.turn(95)
	time.sleep(0.5)
	fw.turn(85)
	time.sleep(0.5)
	fw.turn(90)
	time.sleep(1)

	fw.turn(110)
	print("\n cali black")
	time.sleep(4)
	fw.turn(90)
	black_references = lf.get_average(mount)
	fw.turn(95)
	time.sleep(0.5)
	fw.turn(85)
	time.sleep(0.5)
	fw.turn(90)
	current_angle = 90
	time.sleep(1)

	for i in range(0, 5):
		references[i] = (white_references[i] + black_references[i]) / 2
	lf.references = references
	print("Middle references =", references)
	time.sleep(1)

def destroy():
	bw.stop()
	fw.turn(90)
	rslt = c_lib.lib_exit()
	if rslt == -1:
		print("lib_exit() failed")

if __name__ == '__main__':
	try:
		while True:
			setup()
			main()
	except KeyboardInterrupt:
		destroy()
