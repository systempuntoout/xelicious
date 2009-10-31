import sys, traceback, os.path, re
scriptPath = re.sub('^(.*?)[\\\\;]*$','\\1\\\\',os.getcwd()) #works in both emu and xbox
sys.path.insert(0, scriptPath+'library')
    
import xml.dom.minidom,os
import urllib,urllib2 
import xbmc, xbmcgui
import cachedhttp
import delicious
import time
import settingsmgr

from string import split, replace, find

try: Emulating = xbmcgui.Emulating
except: Emulating = False
###################################################################
#HttpClient
httpFetcher=cachedhttp.CachedHTTPWithProgress() 
httpFetcher.setSocketTimeout(20)
httpFetcher.setUserAgent('Xel.icio.us')

###################################################################
#Settings
SETTINGS_FILE = scriptPath + "library\\settings.xml"
settings=settingsmgr.ReadSettings(SETTINGS_FILE) 

###################################################################
#Variable
#Delicious account
DEL_user=settings['username']
DEL_password=settings['password']
DEL_VIDEO_defaultTags='video'
DEL_AUDIO_defaultTags='audio'
DEL_CUSTOM_defaultTags='custom'

ACTION_PREVIOUS_MENU = 10
ACTION_PLAY = 79
ACTION_PLAY_PAD = 18
ACTION_POST_TO_DELICIOUS = 11 #Info
ACTION_POST_TO_DELICIOUS_PAD = 9

curPage = 1
selectedContent ='VIDEO'
deliciousVideoUrl = "http://del.icio.us/tag/system:media:video?setcount=100&page=";
deliciousAudioUrl = "http://del.icio.us/tag/system:media:audio?setcount=100&page=";
deliciousCustomUrl = "http://del.icio.us/tag/system:media:";

videoExt ='(\\.mov)|(\\.wmv)|(\\.mpg)|(\\.avi)|(\\.mpeg)'
audioExt ='(\\.mp3)|(\\.wav)'
customExt ='(\\.mov)|(\\.wmv)|(\\.mpg)|(\\.avi)|(\\.mpeg)|(\\.mp3)|(\\.wav)' 
contentUrl=[]
contentDescription=[]

customChoices = ["video+screencast","video+gaming", "video+porn", "video+music", "audio+podcast","audio+jazz","audio+rap","KEYBOARD_VIDEO","KEYBOARD_AUDIO","CANCEL"]
keyboardInputKeyword=''
customFormatSelected=''

RESOURCES = scriptPath + '\\images\\'
BACKGROUND =	RESOURCES + 'background.png'
LATER_OFF =    RESOURCES + 'later_off.png'
LATER_ON =    RESOURCES + 'later_on.png'
EARLIER_OFF =    RESOURCES + 'earlier_off.png'
EARLIER_ON =    RESOURCES + 'earlier_on.png'
EXIT_OFF =    RESOURCES + 'exit_off.png'
EXIT_ON =    RESOURCES + 'exit_on.png'
AUDIO_OFF =    RESOURCES + 'audio_off.png'
AUDIO_ON =    RESOURCES + 'audio_on.png'
VIDEO_OFF =    RESOURCES + 'video_off.png'
VIDEO_ON =    RESOURCES + 'video_on.png'
CUSTOM_ON =   RESOURCES + 'custom_on.png'
CUSTOM_OFF =   RESOURCES + 'custom_off.png'
SETTINGS_ON =   RESOURCES + 'settings_on.png'
SETTINGS_OFF =   RESOURCES + 'settings_off.png'

###################################################################
#Def utils
def message(line1,line2='',line3=''):
    dialog = xbmcgui.Dialog()
    dialog.ok("Info", line1,line2,line3)

class ActionBase:
    def open(self,url):
        pass
        return None 

class PlayAction(ActionBase):
    global extensionFilter,selectedContent
    def open(self,url):
        if selectedContent=='VIDEO':ext=videoExt
        elif selectedContent=='AUDIO':ext=audioExt
        else:ext=customExt
        extensionFilter = re.compile(ext+'|(\\.ksh)')
        url=httpFetcher.getFullUrl(url)
        if not contentValid(url): return   
     
        data=OpenUrl(url)
        if data is None:return
        localfile=httpFetcher.cacheFilename(url)
         
        if len(localfile)>0: 
            if(extensionFilter.search(localfile)):
                print ("play from cache")
                xbmc.Player().play(localfile)
            else: message("Content not valid");
            return
               
        if(extensionFilter.search(localfile)):xbmc.Player().play(url)
        else: message("Content not valid"); 
        return  

def OpenUrl(url): 
    url = httpFetcher.getFullUrl(url)
    print("Opening URL:'"+url+"'")
    try:    
        data=httpFetcher.urlopen(url)
        return data
    except:
        httpFetcher.flushCache(url)
        return None 

def filterDuplicate(alist):
    set = {}
    return [set.setdefault(e[3],e) for e in alist if e[3] not in set]
    
def contentValid(url):
    response=urllib2.urlopen(url)
    ct = response.info().getheaders("content-type")
    if ct and ct[0].startswith("text/html"):
        message("This is not a valid video|audio feed")
        return False
    else:return True
    
###################################################################
#main
class XELICIOUS_Main(xbmcgui.Window):
    
    def __init__(self):
          
      if Emulating: xbmcgui.Window.__init__(self)
       
      self.scaleX = ( float(self.getWidth())  / float(720) )
      self.scaleY = ( float(self.getHeight()) / float(480) )
                    
      self.addControl(xbmcgui.ControlImage(0,0,int(720 * self.scaleX), int(480 * self.scaleY), BACKGROUND))
      self.nextbtn = xbmcgui.ControlButton(int(56 * self.scaleX),int(175 * self.scaleY), int(90 * self.scaleX), int(38 * self.scaleY),'',LATER_ON, LATER_OFF)
      self.prevbtn = xbmcgui.ControlButton(int(56 * self.scaleX),int(115 * self.scaleY), int(90 * self.scaleX), int(38 * self.scaleY),'',EARLIER_ON, EARLIER_OFF)
      self.videobtn = xbmcgui.ControlButton(int(66 * self.scaleX),int(240 * self.scaleY), int(70 * self.scaleX), int(30 * self.scaleY),'',VIDEO_ON, VIDEO_OFF)
      self.audiobtn = xbmcgui.ControlButton(int(66 * self.scaleX),int(280 * self.scaleY), int(70 * self.scaleX), int(30 * self.scaleY),'',AUDIO_ON, AUDIO_OFF)
      self.custombtn = xbmcgui.ControlButton(int(66 * self.scaleX),int(320 * self.scaleY), int(70 * self.scaleX), int(30 * self.scaleY),'',CUSTOM_ON, CUSTOM_OFF)
      self.settingsbtn = xbmcgui.ControlButton(int(83 * self.scaleX),int(360 * self.scaleY), int(40 * self.scaleX), int(40 * self.scaleY),'',SETTINGS_ON, SETTINGS_OFF)
      self.exitbtn = xbmcgui.ControlButton(int(83 * self.scaleX),int(400 * self.scaleY), int(40 * self.scaleX), int(40 * self.scaleY),'',EXIT_ON, EXIT_OFF)
      self.contentList =xbmcgui.ControlList(int(172 * self.scaleX),int(140 * self.scaleY), int(500 * self.scaleX), int(300 * self.scaleY))

            
      self.addControl(self.contentList)        
      self.addControl(self.nextbtn)
      self.addControl(self.exitbtn)
      self.addControl(self.prevbtn)
      self.addControl(self.videobtn)
      self.addControl(self.audiobtn)
      self.addControl(self.custombtn)
      self.addControl(self.settingsbtn)
        
      self.prevbtn.controlRight(self.contentList)
      self.prevbtn.controlDown(self.nextbtn)
      self.prevbtn.controlUp(self.exitbtn)
      self.nextbtn.controlDown(self.videobtn)
      self.nextbtn.controlRight(self.contentList)
      self.nextbtn.controlUp(self.prevbtn)
      
      self.videobtn.controlUp(self.nextbtn)
      self.videobtn.controlDown(self.audiobtn)
      self.videobtn.controlRight(self.contentList)
        
      self.audiobtn.controlUp(self.videobtn)
      self.audiobtn.controlDown(self.custombtn)
      self.audiobtn.controlRight(self.contentList)
      self.custombtn.controlUp(self.audiobtn)
      self.custombtn.controlDown(self.settingsbtn)
      self.custombtn.controlRight(self.contentList)
      
      self.settingsbtn.controlRight(self.contentList)
      self.settingsbtn.controlDown(self.exitbtn)
      self.settingsbtn.controlUp(self.custombtn)
      
      self.exitbtn.controlRight(self.contentList)
      self.exitbtn.controlDown(self.prevbtn)
      self.exitbtn.controlUp(self.settingsbtn)
      self.contentList.controlLeft(self.prevbtn)
        
      self.setFocus(self.contentList)
                
      self.getVideoList()

    def onAction(self, action):
        
        if action == ACTION_PREVIOUS_MENU :
		    self.close()
        if  action == ACTION_PLAY_PAD or action == ACTION_PLAY :
            tmpStreamItem = self.contentList.getSelectedPosition()
            if contentValid(str(contentUrl[(tmpStreamItem)])):xbmc.Player().play(str(contentUrl[(tmpStreamItem)]))
        if action == ACTION_POST_TO_DELICIOUS or action == ACTION_POST_TO_DELICIOUS_PAD:
            tmpStreamItem = self.contentList.getSelectedPosition()
            dialog = xbmcgui.Dialog()
            defaultTags=""
            if selectedContent=='VIDEO':
              defaultTags=DEL_VIDEO_defaultTags
            elif selectedContent=='AUDIO':
              defaultTags=DEL_AUDIO_defaultTags
            else: 
              defaultTags=DEL_CUSTOM_defaultTags  
            
            if dialog.yesno("message", "Do you want to post to del.icio.us?"):
               keyboard = xbmc.Keyboard(defaultTags)
               keyboard.doModal()
               if (keyboard.isConfirmed()):
                    if delicious.add(DEL_user, DEL_password,str(contentUrl[(tmpStreamItem)]),str(contentDescription[(tmpStreamItem)]), keyboard.getText(),'',str(time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()))+'Z'):
                        dialog.ok("message","Operation successful")
                    else: dialog.ok("warning","Operation not completed")
               else:return
    def onControl(self, control):
        
        global curPage,selectedContent,customFormatSelected        
        
        if control == self.videobtn:
            curPage = 1
            selectedContent ='VIDEO'
            self.getVideoList()

        if control == self.audiobtn:
            curPage = 1
            selectedContent ='AUDIO'
            self.getAudioList()    
                
        if control == self.custombtn:
            dialog = xbmcgui.Dialog()
            choice = dialog.select("Which format?", customChoices)
            if customChoices[choice]=='CANCEL': return
            elif customChoices[choice]=='KEYBOARD_VIDEO':
                keyboard = xbmc.Keyboard("video+")
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    curPage = 1
                    selectedContent ='CUSTOM'
                    customFormatSelected=keyboard.getText()
                    self.getCustomList(customFormatSelected)
                else:return
            elif customChoices[choice]=='KEYBOARD_AUDIO':
                keyboard = xbmc.Keyboard("audio+")
                keyboard.doModal()
                if (keyboard.isConfirmed()):
                    curPage = 1
                    selectedContent ='CUSTOM'
                    customFormatSelected=keyboard.getText()
                    self.getCustomList(customFormatSelected)
                else:return
            else:
                curPage = 1
                selectedContent ='CUSTOM'
                customFormatSelected=customChoices[choice]
                self.getCustomList(customFormatSelected)
        
        if control == self.exitbtn:
            self.close()
	    
        if control == self.nextbtn:
            if int(curPage) == 1: return
            curPage = int(curPage) - 1
            if selectedContent=='VIDEO':self.getVideoList()
            elif selectedContent=='AUDIO':self.getAudioList()
            else: self.getCustomList(customFormatSelected)
        if control == self.prevbtn:
            curPage = int(curPage) + 1
            if selectedContent=='VIDEO':self.getVideoList()
            elif selectedContent=='AUDIO':self.getAudioList()
            else: self.getCustomList(customFormatSelected)
            
        if control == self.contentList:
            tmpStreamItem = self.contentList.getSelectedPosition()
            action=PlayAction()
            action.open(str(contentUrl[(tmpStreamItem)]))
        
        if control == self.settingsbtn:
            settingsmgr.OpenControlPanel(SETTINGS_FILE)
    
    #############################################################################
    #Data retriever
    
    def getVideoList(self):
          self.getContentList(deliciousVideoUrl,videoExt)

    def getAudioList(self):
          self.getContentList(deliciousAudioUrl,audioExt)
    
    def getCustomList(self,input):
          self.getContentList(deliciousCustomUrl+input+"?setcount=100&page=",customExt)
       
    def getContentList(self,url,ext):
        global curPage
        try:
          XELICIOUS_HTML = httpFetcher.urlopen(url + str(curPage))
          XELICIOUS_re = re.compile('<div class="data">(.*?)<h4>(.*?)<a(.*?)href=\"(.*?)\"(.*?)>(.*?)</a>(.*?)<div class="meta">(.*?)</div>',re.DOTALL|re.IGNORECASE)
          extensionFilter = re.compile(ext)
          numberFilter=re.compile(';">saved by(.*?)other')
            
          XELICIOUS_Cont = XELICIOUS_re.findall(XELICIOUS_HTML)

          self.contentList.reset()
          contentUrl[0:100]=""
          contentDescription[0:100]=""
          contentLinksNumber="";
                              
          XELICIOUS_Cont=filterDuplicate(XELICIOUS_Cont)
 
          for items in XELICIOUS_Cont:
              if(extensionFilter.search(items[3])):
                   contentUrl.append(items[3])
                   nfCont=numberFilter.findall(items[7])
                   if len(nfCont)>0:
                       contentLinksNumber= '('+str(eval(nfCont[0])+1)+' Links) '
                   else: contentLinksNumber=''
                   contentDescription.append(items[5])
                   self.contentList.addItem(contentLinksNumber+(items[5].decode('ascii','replace')))
          self.setFocus(self.contentList)     
        except:
             message("Problems getting "+selectedContent+" feeds")

    		
##########################################################
#Launch
httpFetcher.cleanCache()
try:
    win = XELICIOUS_Main() 
    win.doModal()
    del win 
finally:
    httpFetcher.cleanCache()
