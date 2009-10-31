# ScriptName    : settingsmgr.py
# Version         = '0.3'
# Author        : Van der Phunck aka Aslak Grinsted. as@phunck.cmo <- not cmo but com
# Desc          : settingsmanager for python
#
# 
# 
#


import xbmc, xbmcgui
import sys, traceback
import os.path
from xml.dom.minidom import parse, parseString

guiTitlePos=[172,140,60,15]
guiMenuPos=[172,170,500,270]
#-------------xml------------------
NODE_ELEMENT=1
NODE_ATTRIBUTE=2
NODE_TEXT=3
NODE_CDATA_SECTION=4


ACTION_MOVE_LEFT        =  1    
ACTION_MOVE_RIGHT       =  2
ACTION_MOVE_UP          =  3
ACTION_MOVE_DOWN        =  4
ACTION_PAGE_UP          =  5 #left trigger
ACTION_PAGE_DOWN        =  6 #right trigger
ACTION_SELECT_ITEM      =  7 #A button
ACTION_HIGHLIGHT_ITEM   =  8 
ACTION_PARENT_DIR       =  9 #B button
ACTION_PREVIOUS_MENU    = 10 #back button
ACTION_SHOW_INFO        = 11
ACTION_PAUSE            = 12
ACTION_STOP             = 13
ACTION_NEXT_ITEM        = 14
ACTION_PREV_ITEM        = 15
ACTION_XBUTTON		= 18 #Y Button
ACTION_WHITEBUTTON	= 117 

ScriptPath              = os.getcwd()
if ScriptPath[-1]==';': ScriptPath=ScriptPath[0:-1]
if ScriptPath[-1]!='\\': ScriptPath=ScriptPath+'\\'

try: Emulating = xbmcgui.Emulating #Thanks alot to alexpoet for the xbmc.py,xmbcgui.py emulator. Very useful!
except: Emulating = False


def message(line1,line2='',line3=''):
	dialog = xbmcgui.Dialog()
	dialog.ok("Info", line1,line2,line3)

def printLastError():
	e=sys.exc_info()
	traceback.print_exception(e[0],e[1],e[2])

def lastErrorString():
	return sys.exc_info()[1]

####################################################################################

def GetNodeText(node):
	dout=''
	for tnode in node.childNodes:
		if (tnode.nodeType==NODE_TEXT)|(tnode.nodeType==NODE_CDATA_SECTION):
			dout=dout+tnode.nodeValue
	return dout.encode("iso-8859-1")

def GetNodeValue(node,tag=None): #helper function for xml reading
	if tag is None: return GetNodeText(node)
	nattr=node.attributes.getNamedItem(tag)
	if not (nattr is None): return nattr.value.encode("iso-8859-1")
	for child in node.childNodes:
		if child.nodeName==tag:
			return GetNodeText(child)
	return None
    
def GetChildNode(node,tag):
	for child in node.childNodes:
		if child.nodeName==tag: return child
	return None

def GetParamValue(pnode):
	type=GetNodeValue(pnode,"type")
	if type=='string': return str(GetNodeValue(pnode,'value'))
	if type=='float': return float(GetNodeValue(pnode,'value'))
	if type=='int': return int(GetNodeValue(pnode,'value'))
	if type=='boolean': return bool(GetNodeValue(pnode,'value'))
	if type=='select': return int(GetNodeValue(pnode,'value'))
	return "unknown type:"+str(GetNodeValue(pnode,'value'))

def SetParamValue(pnode,value):
	type=GetNodeValue(pnode,'type')
	valuenode=GetChildNode(pnode,'value')
	children=valuenode.childNodes
	for child in children:
		valuenode.removeChild(child)
	doc=pnode.ownerDocument
	if type=='string':
		newnode=doc.createCDATASection(str(value))
	else:
		newnode=doc.createTextNode(str(value))
	valuenode.appendChild(newnode)

def GetSelectOptions(pnode):
	options=[]
	for child in pnode.childNodes:
		if child.nodeName=='option': options.append(str(GetNodeText(child)))
	return options

####################################################################################

def OpenControlPanel(settingsfile):
	cp=ControlPanel()
	cp.setSettingsfile(settingsfile)
	cp.doModal()
	del cp

def ReadSettings(settingsfile):
	dom = parse(settingsfile)
	params=dom.getElementsByTagName("param")
	settings={}
	for param in params:
		id=GetNodeValue(param,'id')
		settings[id]=GetParamValue(param)
	return settings

class ControlPanel(xbmcgui.Window):
	def __init__(self):
		if Emulating: xbmcgui.Window.__init__(self)  #for emulator to work

		w=self.getWidth()
		h=self.getHeight()
		self.xratio=float(w/720.0)
		self.yratio=float(h/480.0)

		try:
			self.bg = xbmcgui.ControlImage(0,0,w,h, ScriptPath+'images\\background.png')
			self.addControl(self.bg)
		except:
			pass
		

		self.title = xbmcgui.ControlFadeLabel(int(self.xratio*guiTitlePos[0]),int(self.yratio*guiTitlePos[1]),int(self.xratio*guiTitlePos[2]),int(self.yratio*guiTitlePos[3]), 'font16','0xFFFFFFFF')
		self.addControl(self.title)

		self.list=xbmcgui.ControlList(int(self.xratio*guiMenuPos[0]),int(self.yratio*guiMenuPos[1]),int(self.xratio*guiMenuPos[2]),int(self.yratio*guiMenuPos[3]), 'font14','0xFFFFFFFF')
		self.addControl(self.list)
		self.listnodes=[]
		
	def fillList(self,node):
		self.listnodes=[]
		self.title.reset()
		self.title.addLabel(str(GetNodeValue(node,"name")))
		self.list.reset()
		for child in node.childNodes:
			name=None
			if child.nodeName=='param':
				name=GetNodeValue(child,"name")
				type=GetNodeValue(child,"type")
				value=GetParamValue(child)
				if type=="select":
					options=GetSelectOptions(child)
					value=options[value]
				name=name+': '+str(value)
			if child.nodeName=='settings':
				name='* '+GetNodeValue(child,"name")
			if name:
				self.list.addItem(name)
				self.listnodes.append(child)
		self.setFocus(self.list)
	
	def saveSettings(self):
		self.settingsfile
		xmlstring=self.dom.toxml()
		f=file(self.settingsfile,'wb')
		try:
			f.write(xmlstring)
		finally:
			f.close()
		
	def setSettingsfile(self,settingsfile):
		try:
			self.settingsfile=settingsfile
			self.dom = parse(self.settingsfile)
			self.node=self.dom.getElementsByTagName('settings').item(0)
			self.fillList(self.node)
			
		except:
			self.close()
			raise


		
	def onAction(self, action):
		if action == ACTION_PREVIOUS_MENU:
			dialog = xbmcgui.Dialog()
			if dialog.yesno("Settings","Do you want to save your settings?"):
				self.saveSettings()
			self.close()
			return
		try:
			newvalue=None
			selectedNode=self.listnodes[self.list.getSelectedPosition()]
			listitem=self.list.getSelectedItem()
			if action == ACTION_PARENT_DIR:
				parentNode=selectedNode.parentNode
				if parentNode.nodeName=='settings':
					self.fillList(parentNode)
					return
			if (selectedNode.nodeName=='settings') and (action == ACTION_SELECT_ITEM):
				self.fillList(selectedNode)
				return
				
			if selectedNode.nodeName=='param':
				type=GetNodeValue(selectedNode,'type')
				name=GetNodeValue(selectedNode,'name')
				value=GetParamValue(selectedNode)
				if (type=='string') or (type=='float') or (type=='int'):
					if action == ACTION_SELECT_ITEM:
						keyboard=xbmc.Keyboard(str(value))
						keyboard.doModal()
						newvalue=keyboard.getText()
						try:
							if type=='float': newvalue=float(newvalue)
							if type=='int': newvalue=int(newvalue)
						except:
							newvalue=None
				if (type=='boolean'):
					if (action==ACTION_SELECT_ITEM):
						newvalue=(not value)
				newvaluestring=str(newvalue)
				if (type=='select'):
					options=GetSelectOptions(selectedNode)
					if (action == ACTION_MOVE_LEFT) or (action == ACTION_SELECT_ITEM): newvalue=value+1
					if (action == ACTION_MOVE_RIGHT): newvalue=value-1
					if newvalue:
						newvalue=newvalue % len(options)
						newvaluestring=str(options[newvalue])
				if not (newvalue is None):
					SetParamValue(selectedNode,newvalue)
					listitem.setLabel(name+': '+newvaluestring)
		except: 
			try:
				self.close()
				print('Error!') 
				printLastError()
			except: 
				pass

	def onControl(self,control):
		pass
