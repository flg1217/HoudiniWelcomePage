# coding=utf8
###################################################################
# Author: 冯爬爬
# Date  : 2022/03/28
# 声明：本项目仅用于学习和测试！请勿滥用！
###################################################################

import hou
import os
import time
import re
import json
import webbrowser
from collections import OrderedDict
from functools import partial
from lxml import etree
import requests
from PySide2.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QGridLayout, QScrollArea, \
    QTabWidget
from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtGui import QMovie

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'}


class WelcomePage(QWidget):
    def __init__(self):
        super(WelcomePage, self).__init__()
        self.setFixedSize(700, 400)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_lay = QVBoxLayout()
        main_lay.setMargin(0)
        bg_widget = QWidget()
        bg_widget.setObjectName('BG')
        bg_widget.setStyleSheet('''
        .QWidget#BG{
          background-color:#303030;
          border: 2px groove gray;
          border-style: solid;
          border-radius: 10px;
        }
        ''')
        main_lay.addWidget(bg_widget)
        
        # 上部分， 左边文字，右边表情
        top_lay = QHBoxLayout()
        
        self.lb_msg = QLabel()
        self.lb_msg.setWordWrap(True)
        self.lb_msg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lb_msg.mousePressEvent = self.on_refresh_joke
        self.lb_msg.setStyleSheet('font:15px; color:white')
        
        self.lb_gif = QLabel()
        self.lb_gif.setScaledContents(True)
        self.lb_gif.setFixedSize(150, 150)
        self.set_gif('working.gif')
        
        top_lay.addWidget(self.lb_msg)
        top_lay.addWidget(self.lb_gif)
        top_lay.setStretch(0, 3)
        top_lay.setStretch(1, 1)
        
        # 中间节目部分
        self.bili_tab = QTabWidget()
        self.bili_tab.setStyleSheet('''
            QTabWidget::pane { /* The tab widget frame */
                border: 1px solid groove gray;
                border-radius: 3px;
                top: -1px;
                background-color: groove gray;
            }
            QTabWidget::tab-bar {
                padding: 5px;
            }
        ''')
        self.bili_tab.enterEvent = self.on_enter_bili_list
        self.bili_tab.leaveEvent = self.on_leave_bili_list
        
        # 底部按钮
        bot_lay = QHBoxLayout()
        bot_lay.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        
        self.bt_close = QPushButton('确定')
        self.bt_close.setFixedWidth(200)
        self.bt_close.setStyleSheet('''
         QPushButton{
             padding:5px;
             border-radius: 10px;
             border: 2px groove gray;
             border-style: solid;
         }
         QPushButton:hover{background-color:gray}
         ''')
        
        bot_lay.addWidget(self.bt_close)
        
        content_lay = QVBoxLayout(bg_widget)
        content_lay.addLayout(top_lay)
        content_lay.addWidget(self.bili_tab)
        content_lay.addLayout(bot_lay)
        
        self.setLayout(main_lay)
        
        self.bt_close.clicked.connect(self.close)

        self.show()
        
        self.th_get_joke = None
        self.bili_threads = {}
        self.start_joke_thread()
        self.start_bili_thread()
    
    def start_joke_thread(self):
        # 创建请求并解析笑话的线程
        if not self.th_get_joke:
            self.th_get_joke = ThreadGetJoke()
            self.th_get_joke.on_finished.connect(self.on_finished_joke)
            self.th_get_joke.start()
    
    def start_bili_thread(self):
        # 注册需要订阅的节目
        info = {}
        info['凡人修仙传'] = 'https://www.bilibili.com/bangumi/play/ss28747'
        info['永生'] = 'https://www.bilibili.com/bangumi/play/ep458588'
        info['兵主奇魂'] = 'https://www.bilibili.com/bangumi/play/ss39702'
        
        # 创建请求并解析B站页面内容的线程
        self.bili_threads = {}  # 持久化保持线程，否则houdini闪退
        for name, url in info.items():
            thread = ThreadGetBili(name, url)
            self.bili_threads[name] = thread
            thread.on_finished.connect(self.on_finished_bili)
            thread.start()
    
    def on_refresh_joke(self, event):
        '''覆盖标签的mousePressEvent事件'''
        self.start_joke_thread()
    
    def set_gif(self, gif_name):
        '''设置gif动画'''
        gif = QMovie('%s/textures/%s' % (os.getenv('FPP_LABS'), gif_name))
        gif.start()
        self.lb_gif.setMovie(gif)
    
    def on_finished_joke(self, msg):
        '''线程任务完成之后的回调'''
        self.lb_msg.setText(msg)
        self.th_get_joke = None  # 释放线程
    
    def on_finished_bili(self, data_dict):
        '''线程任务完成之后的回调'''
        tab_name = data_dict['name']
        self.bili_threads.pop(tab_name)  # 释放线程
        
        # 每个节目创建一个tab分页
        scroll_bili = QScrollArea()
        scroll_widget = QWidget()
        tv_lay = QGridLayout()
        scroll_widget.setLayout(tv_lay)
        scroll_bili.setWidget(scroll_widget)
        scroll_bili.setWidgetResizable(True)
        
        self.bili_tab.addTab(scroll_bili, tab_name)
        
        # 创建tab分页里面的节目内容
        for index, item in enumerate(data_dict['items']):
            long_title = item['long_title']
            title_format = item['titleFormat']  # 第n话
            badge = item['badge']  # 预告或者会员
            label = '%s-%s' % (title_format, long_title)
            if badge:   label += '(%s)' % badge
            link = item['link']
            bt = QPushButton(label)
            bt.clicked.connect(partial(self.on_open_bili_item, link))  # 点击对应节目的时候传入其链接
            bt.setStyleSheet('''
             QPushButton{
                 padding:2px;
                 border-radius: 5px;
                 border: 2px groove gray;
                 border-style: solid;
                 border-width:1px;
                 padding:5px
                 }
             QPushButton:hover{background-color:gray}
             ''')
            column = 3
            tv_lay.addWidget(bt, index / column, index % column)
            
        
    
    def on_open_bili_item(self, link):
        '''打开页面'''
        webbrowser.open(link)
        self.close()
    
    def on_enter_bili_list(self, event):
        self.set_gif('watching.gif')
    
    def on_leave_bili_list(self, event):
        self.set_gif('working.gif')
    
    def closeEvent(self, event):
        super(WelcomePage, self).closeEvent(event)
        self.setParent(None)
        hou.fpp_welcome = None


class ThreadGetBili(QThread):
    on_finished = Signal(dict)
    
    def __init__(self, name, url):
        self.name = name
        self.url = url
        super(ThreadGetBili, self).__init__()
    
    def get_data(self, page_text):
        tree = etree.HTML(page_text)
        res = tree.xpath('/html/body//script')
        
        for i in res:
            if i.attrib:    continue
            if 'window.__INITIAL_STATE__' not in i.text:    continue
            
            finds = re.findall('window.__INITIAL_STATE__=(.*).*?\;\(function', i.text, re.S | re.M)
            if not finds:   return []
            
            js = json.loads(finds[0])
            
            return {'name': self.name, 'items': js['initEpList']}
    
    def run(self):
        try:
            r = requests.get(self.url, headers = headers)
            data_dict = self.get_data(r.text)
        except Exception as ex:
            print(ex)
            self.on_finished.emit({})
        else:
            self.on_finished.emit(data_dict)


class ThreadGetJoke(QThread):
    on_finished = Signal(str)
    
    def __init__(self):
        super(ThreadGetJoke, self).__init__()
    
    def get_data(self, page_text):
        tree = etree.HTML(page_text)
        res = tree.xpath('/html/body/div[1]/section/div[1]//text()')
        
        for i in res:
            if not i or len(i) < 2:   continue
            return i
        return ''
    
    def get_time_text(self):
        return time.strftime("%Y-%m-%d", time.localtime())
    
    def run(self):
        try:
            url = 'https://www.nihaowua.com/home.html'
            r = requests.get(url, headers = headers)
            msg = self.get_data(r.text)
        except Exception as ex:
            print(ex)
            msg = '获取数据失败！'
        
        self.on_finished.emit(self.get_time_text() + '\t又是好好学习的一天\n\n' + msg)
