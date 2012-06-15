#!/home/dotcloud/env/bin/python
#coding:utf-8

import sys,os,threading,time,urllib2,json
from datetime import datetime,timedelta

#only use in dotcloud 
package_dir = '/home/dotcloud/env/lib/python2.6/site-packages'
if os.path.exists(package_dir):
    sys.path.append(package_dir)

current_dir = os.path.dirname(__file__)
settings_dir = os.path.abspath(os.path.join(current_dir,os.path.pardir))
if settings_dir not in sys.path :
    sys.path.append(settings_dir)
import settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['TZ'] = settings.TIME_ZONE
from weather.models import MyFetion, Log, User,City,Weather 

PHONE = settings.FETION[0][0]
PSW = settings.FETION[0][1]

class InfoThread(threading.Thread):
    
    def __init__(self,func,args,name=''):
        threading.Thread.__init__(self)
        self.func = func
        self.args = args
        self.name = name
        
    def run(self):
        apply(self.func,self.args)

def into_db(weather):
    limit = 5
    base_url = 'http://m.weather.com.cn/data/%s.html'
    url = base_url % weather.cid.cid
    
    for i in range(limit):
        try:
            info = urllib2.urlopen(url).read()
            if bool(json.loads(info)): 
                break 
        except:
            info = '获取失败'
        finally:
            i+=1
            
    weather.info = info
    
    weather.save()
    #print u'%s : %s\n' % (weather.cid.city,url)
    
    sendGroupSms(weather)
    
    return True

#发飞信
def sendGroupSms(weather):
    users = weather.user_set.filter(active=True)
    
    if len(users)>0 :
        try:
            ft = MyFetion(PHONE,PSW)            
                                
            for u in users :
                message = parse_json(weather.info,u)
                
                if message == False:
                    Log(level=0,event='json数据解析出错:订阅天气信息%s:s%' %(weather.cid,weather.hour)).save()
                    return False    
                
                if message == None :
                    continue
                               
                ft.sendBYid(u.fid, message.encode('utf-8'))
                print u'SMS sent to %s : %s' % (u.phone_num,message)
                Log(level=2,event = 'Send to %s[%sh]:%s:(%s)' % (u.phone_num,weather.hour,weather.cid.city,message)).save()
        except Exception,e :            
            print "except Happen: ",e
            if 'ft' in locals():
                ft.logout()

def parse_json(jdata,user):
    try:
        info = json.loads(jdata)
    except:
        return False    
    winfo = info['weatherinfo']
    tail = u' (本消息由短信天气网 http://tq.sms128.net 免费提供)'
    weekday_cn = (u'星期一',u'星期二',u'星期三',u'星期四',u'星期五',u'星期六',u'星期日')
    ch_weekday = lambda day: weekday_cn[day.weekday()]
    ch_date = lambda day: u'%s年%s月%s日' % (day.year,day.month,day.day)
    today = datetime.today()
    tomorrow = today +timedelta(days=1)
    is_today = (ch_date(today) == winfo['date_y'])
    today_weather = winfo['weather1'] if is_today else winfo['weather2']
    today_temp = winfo['temp1'] if is_today else winfo['temp2']
    today_wind = winfo['wind1'] if is_today else winfo['wind2']
        
    if user.sub_type == 'B':
        if 0 <= int(user.wid.hour) <=12:            
            if u'雨' not in today_weather:
                return None
            else:                
                template = u'今天是%s(%s) ,%s天气 :%s,%s,%s; 出门请带好雨具。%s' % \
                (ch_date(today),ch_weekday(today),winfo['city'],today_weather,today_temp,today_wind,tail)
        else :
            #13点到23点不必判断是否为昨天数据，取得的数据必为今日
            if u'雨' not in winfo['weather2']:
                return None
            else:                                                
                dt = u'%s年%s月%s日 %s' % (tomorrow.year,tomorrow.month,tomorrow.day,ch_weekday(tomorrow))                                                
                template = u'%s明日(%s)天气 :%s,%s,%s; 出门请带好雨具。%s' % \
                (winfo['city'],dt,winfo['weather2'],winfo['temp2'],winfo['wind2'],tail)
    else:
        tomorrow_weather = winfo['weather2'] if is_today else winfo['weather3']
        tomorrow_temp = winfo['temp2'] if is_today else winfo['temp3']
        #tomorrow_wind = winfo['wind2'] if is_today else winfo['wind3']
        after_tomorrow_weather = winfo['weather3'] if is_today else winfo['weather4']
        after_tomorrow_temp = winfo['temp3'] if is_today else winfo['temp4']
        #after_tomorrow_wind = winfo['wind3'] if is_today else winfo['wind4']                                
        template = u'今天是%s(%s) ,%s天气 :%s,%s,%s;明天:%s,%s;后天:%s,%s。%s' % \
        (ch_date(today),ch_weekday(today),winfo['city'],today_weather,today_temp,today_wind,
         tomorrow_weather,tomorrow_temp,after_tomorrow_weather,after_tomorrow_temp,tail)
    
    
    return template
    
    


def main():
    info_threads = []
    now = datetime.now()
    hour = now.hour
    hour = 5
    weathers = Weather.objects.filter(cid='101280601',hour=hour)
    #weathers = Weather.objects.filter(hour=hour)
    for w in weathers:
        t = InfoThread(into_db,(w,))
        info_threads.append(t)
    
    for i in range(len(weathers)):
        info_threads[i].start()
    
    for i in range(len(weathers)):
        info_threads[i].join()
        
    print "Finish fetching data into db" #实际上不插入数据库也是没事的
        
if __name__ == '__main__':
    start = time.time()
    main()    
    stop = time.time()
    print "Threads time Elapsed :%s \n" % (stop-start)