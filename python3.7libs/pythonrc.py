import hou
from UI_WelcomePage import WelcomePage

print('pythonrc')

# 保证仅创建一次
if not hasattr(hou, 'fpp_welcome'):
    hou.fpp_welcome = WelcomePage()

