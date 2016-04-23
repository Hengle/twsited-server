#-*-coding: utf-8-*-
# Version: 0.1
# Author: Don Li <donne.cn@gmail.com>
# License: Copyright(c) 2012 Don.Li
# Summary: 

MAX_SYNC_CNT_PER_LOOP = 1000
SYNC_DB_INTERVAL      = 2 # 2s
KEEP_LIVE_CONNECT = 300 # 5min

ALLOW_NET_DELAY_SECONDS = 5 # 可接受的网络延迟秒数 5s

CS_USER_TOTSEC   = 600
GS_USER_TOTSEC   = 550
GATE_USER_TOTSEC = 400

MAX_SYNC_CNT_PER_LOOP = 1000
SYNC_CS_INTERVAL      = 5
SYNC_DB_INTERVAL      = 2
SYNC_ALLIANCE_INTERVAL = 20


MAX_SYNC_CS_CNT_PER_LOOP = 100

SESSIONKEY_TIMEOUT = 30
SESSION_LOGOUT_REAL = 300  # client logout timeout 5min


GAME_REGION_SEQ = 0 
GAME_REGION_NAME = ''

FOR_ALL         = 0
FOR_SERVER_ONLY = 1
FOR_CLIENT_ONLY = 2

# 不同类型球的半径大小 放大10倍
FOODBALL_RADIUS = 5
SPINEBALL_RADIUS =  50
USERBALL_RADIUS = 10

COMMON_RADIUS = 10
RADIUS_ENLARGE = 10 # 半径放大的倍数
COORDINATE_ENLARGE = 10000 # 坐标放大的倍数
COMMON_HIGHT = 10 # 默认高度，高度小于COMMON_RADIUS 表示为去掉顶部和底部某些区域的点.

MAX_ROOM_COUNT = 20 # 房间最大玩家人数
