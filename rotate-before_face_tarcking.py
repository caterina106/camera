#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import time
from threading import Thread
from PIL import Image
from Command import COMMAND as cmd
from Thread import *
from Video import *
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QLineEdit
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
 
 
class mywindow(QMainWindow):
    def __init__(self):
        super(mywindow, self).__init__()
        self.endChar = '\n'
        self.intervalChar = '#'
 
        # read last saved IP data
        try:
            file = open('IP.txt', 'r')
            self.h = file.readline().strip()
            file.close()
        except:
            self.h = '172.20.10.6'
 
        # TCP === instance 
        self.TCP = VideoStreaming()
 
        # servo default degree
        self.servo1 = 90  # horizontal
        self.servo2 = 90  # vertical

        self.scanning = False       # scanning work or no
        self.scan_direction = 1     # scanning direction
        self.face_locked = False    # got face??
 
        # --- UI ---
        self.setWindowTitle("Face Tracking")
        self.setFixedSize(500, 400)
 
        # show video
        self.label_Video = QLabel(self)
        self.label_Video.setGeometry(0, 0, 500, 320)
        self.label_Video.setAlignment(Qt.AlignCenter)
        self.label_Video.setText("No Video")
 
        # IP enter
        self.IP = QLineEdit(self)
        self.IP.setGeometry(10, 330, 150, 30)
        self.IP.setText(self.h)
 
        # connect --  button 
        self.Btn_Connect = QPushButton("Connect", self)
        self.Btn_Connect.setGeometry(170, 330, 100, 30)
        self.Btn_Connect.clicked.connect(self.on_btn_Connect)
 
        # find face -- button
        self.Btn_Tracking = QPushButton("Finding-On", self)
        self.Btn_Tracking.setGeometry(280, 330, 110, 30)
        self.Btn_Tracking.clicked.connect(self.toggle_tracking)
 
        # exit button
        self.Btn_Close = QPushButton("Exit", self)
        self.Btn_Close.setGeometry(400, 330, 80, 30)
        self.Btn_Close.clicked.connect(self.close)
 
        # timer：~30fps refresh video / update datas
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(34)
 
    # -------------connect / disconnect------------------------------ #
    
 
    def on_btn_Connect(self):
        if self.Btn_Connect.text() == "Connect":
            self.h = self.IP.text()
            self.TCP.StartTcpClient(self.h)
            # save IP
            with open('IP.txt', 'w') as f:
                f.write(self.h)
            # start video stream
            try:
                self.streaming = Thread(target=self.TCP.streaming, args=(self.h,))
                self.streaming.start()
            except Exception as e:
                print('video error:', e)
            # receive data（need socket1 if send data to servo）
            try:
                self.recv = Thread(target=self.recvmassage)
                self.recv.start()
            except Exception as e:
                print('recv error:', e)
            self.Btn_Connect.setText("Disconnect")
            print('Connected to:', self.h)
        else:
            self.Btn_Connect.setText("Connect")
            try:
                stop_thread(self.recv)
                stop_thread(self.streaming)
            except:
                pass
            self.TCP.StopTcpcClient()
 
    def recvmassage(self):
        """Only used to establish socket1 connection 
        so that sendData can send servo commands."""
        self.TCP.socket1_connect(self.h)
 
    # --------tracking------------------------------------------------ #

    def toggle_tracking(self):
        if self.Btn_Tracking.text() == "Finding-On":
            self.Btn_Tracking.setText("Finding-Off")
        else:
            self.Btn_Tracking.setText("Finding-On")
 
    # ------timer---------------------------------------------------- #
   
 
    def on_timer(self):
        self.TCP.video_Flag = False
        try:
            if self.is_valid_jpg('video.jpg'):
                self.label_Video.setPixmap(
                    QPixmap('video.jpg').scaled(500, 320, Qt.KeepAspectRatio)
                )
                if self.Btn_Tracking.text() == "Finding-Off":
                    face_x = self.TCP.face_x
                    face_y = self.TCP.face_y
                    if face_x == 0 and face_y == 0:
                        self.face_locked = False
                        self.scan_Face()
                    else:
                        self.find_Face(face_x,face_y)
        except Exception as e:
            print(e)
        self.TCP.video_Flag = True
    


    def scan_Face(self):
        """if no face , just horizontal scan"""
        step = 3
        self.servo1 += step * self.scan_direction

        # protect
        if self.servo1 >= 180:
           self.servo1 = 180
           self.scan_direction = -1
        elif self.servo1 <= 0:
           self.servo1 = 0
           self.scan_direction = 1

        self.TCP.sendData(
        cmd.CMD_SERVO + self.intervalChar + '0'
        + self.intervalChar + str(self.servo1) + self.endChar
    )




    # ------face tracking logic--------------------------------------------- #
   
 
    def find_Face(self, face_x, face_y):
        if face_x != 0 and face_y != 0:
            offset_x = float(face_x / 400 - 0.5) * 2  # normalize to [-1, 1]
            offset_y = float(face_y / 300 - 0.5) * 2  # normalize to [-1, 1]
            delta_degree_x = int(4 * offset_x)         # how much to move horizontally
            delta_degree_y = int(-4 * offset_y)        # how much to move vertically
            
 
            self.servo1 = max(0,  min(180, self.servo1 + delta_degree_x))
            self.servo2 = max(80, min(180, self.servo2 + delta_degree_y))
 
            if offset_x > -0.15 and offset_y > -0.15 and offset_x < 0.15 and offset_y < 0.15:
                if not self.face_locked:
                  self.face_locked = True
                  print(f"servo degree(horizon) : {self.servo1},servo degree(vertical):{self.servo2}")

            else:
                self.face_locked = False
                self.TCP.sendData(
                    cmd.CMD_SERVO + self.intervalChar + '0' + self.intervalChar + str(self.servo1)+self.endChar
                )
                self.TCP.sendData(
                cmd.CMD_SERVO + self.intervalChar + '1'
                + self.intervalChar + str(self.servo2) + self.endChar
            )
              
    # -----tools----------------------------------------------- #
  
 
    def is_valid_jpg(self, jpg_file):
        try:
            if jpg_file.split('.')[-1].lower() == 'jpg':
                with open(jpg_file, 'rb') as f:
                    buf = f.read()
                    if not buf.startswith(b'\xff\xd8'):
                        return False
                    elif buf[6:10] in (b'JFIF', b'Exif'):
                        if not buf.rstrip(b'\0\r\n').endswith(b'\xff\xd9'):
                            return False
                    else:
                        Image.open(f).verify()
        except:
            return False
        return True
 
    def close(self):
        self.timer.stop()
        try:
            stop_thread(self.recv)
            stop_thread(self.streaming)
        except:
            pass
        self.TCP.StopTcpcClient()
        try:
            os.remove("video.jpg")
        except:
            pass
        QtCore.QCoreApplication.instance().quit()
        sys.exit(0)
 
 
if __name__ == '__main__':
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    myshow = mywindow()
    myshow.show()
    sys.exit(app.exec_())
 
