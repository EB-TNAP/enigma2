from enigma import eComponentScan, iDVBFrontend, eTimer
from Components.NimManager import nimmanager as nimmgr
from Components.About import about
from Components.TunerInfo import TunerInfo   # (Extra Import)
from Components.TuneTest import Tuner    # (Extra Import)
from Tools.Transponder import getChannelNumber
from Tools.Directories import fileExists
from time import strftime, time
import os
import pwd
import grp



BOX_MODEL = "none"
BOX_NAME = ""
if fileExists("/proc/stb/info/vumodel") and not fileExists("/proc/stb/info/hwmodel") and not fileExists("/proc/stb/info/boxtype"):
	try:
		l = open("/proc/stb/info/vumodel")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		BOX_MODEL = "vuplus"
	except:
		pass
elif fileExists("/proc/stb/info/boxtype") and not fileExists("/proc/stb/info/hwmodel") and not fileExists("/proc/stb/info/gbmodel"):
	try:
		l = open("/proc/stb/info/boxtype")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		if BOX_NAME.startswith("et"):
			BOX_MODEL = "xtrend"
		elif BOX_NAME.startswith("os"):
			BOX_MODEL = "edision"
	except:
		pass

class ServiceScan:
	Idle = 1
	Running = 2
	Done = 3
	Error = 4
	DonePartially = 5
	Errors = {0: _('error starting scanning'), 
	   1: _('error while scanning'), 
	   2: _('no resource manager'), 
	   3: _('no channel list')}

	def scanStatusChanged(self):
		if self.state == self.Running:
			self.progressbar.setValue(self.scan.getProgress())
			self.lcd_summary and self.lcd_summary.updateProgress(self.scan.getProgress())
			if self.scan.isDone():
				errcode = self.scan.getError()
				if errcode == 0:
					self.state = self.DonePartially
					self.servicelist.listAll()
				else:
					self.state = self.Error
					self.errorcode = errcode
				self.network.setText("")
				self.transponder.setText("")
			else:
				result = self.foundServices + self.scan.getNumServices()
				total = self.tt
				tpnumb = 0 + self.t
				percentage = self.scan.getProgress()
				if percentage > 99:                                                                                                                                                                                                ##
					percentage = 99
				#TRANSLATORS: The stb is performing a channel scan, progress percentage is printed in '%d' (and '%%' will show a single '%' symbol)
				message = ngettext("(%d ", " (%d ", tpnumb) % tpnumb
				message += ngettext(" of %d)" , "of %d)", total) % total
				#TRANSLATORS: Intermediate scanning result, '%d' channel(s) have been found so far
				message += ngettext("  Channels Found = %d", "  Channels Found = %d", result) % result
				self.t = self.t+1
				self.text.setText(message)
				transponder = self.scan.getCurrentTransponder()
				network = ""
				global tp_text
				tp_text = ""
				if transponder:
					tp_type = transponder.getSystem()
					if tp_type == iDVBFrontend.feSatellite:
						network = _('Satellite')
						tp = transponder.getDVBS()
						orb_pos = tp.orbital_position
						try:
							sat_name = str(nimmgr.getSatDescription(orb_pos))
						except KeyError:
							sat_name = ''
						if orb_pos > 1800:
							orb_pos = 3600 - orb_pos
							h = _('W')
						else:
							h = _('E')
						try:
							self.network1 = (" %d.%d%s") % ( orb_pos / 10, orb_pos % 10, h)  ##
						except:
							pass
						if '%d.%d' % (orb_pos / 10, orb_pos % 10) in sat_name:
							network = sat_name
						else:
							network = '%s %d.%d %s' % (sat_name, orb_pos / 10, orb_pos % 10, h)
						if "Ku-band" in sat_name:
							self.network1 += " Ku-band"
						if "Ku-band" not in sat_name:
							self.network1 += " C-band"
						tp_text = {tp.System_DVB_S: 'DVB-S', tp.System_DVB_S2: 'DVB-S2'}.get(tp.system, '')
						if tp_text == 'DVB-S2':
							tp_text = '%s %s' % (tp_text,
							 {tp.Modulation_Auto: 'Auto', tp.Modulation_QPSK: 'QPSK', tp.Modulation_8PSK: '8PSK', 
								tp.Modulation_QAM16: 'QAM16', tp.Modulation_16APSK: '16APSK', 
								tp.Modulation_32APSK: '32APSK'}.get(tp.modulation, ''))
						tp_text = '%s %d%c / %d / %s' % (tp_text, tp.frequency / 1000,
						 {tp.Polarisation_Horizontal: 'H', tp.Polarisation_Vertical: 'V', tp.Polarisation_CircularLeft: 'L', tp.Polarisation_CircularRight: 'R'}.get(tp.polarisation, ' '),
						 tp.symbol_rate / 1000,
						 {tp.FEC_Auto: 'AUTO', tp.FEC_1_2: '1/2', tp.FEC_2_3: '2/3', tp.FEC_3_4: '3/4', 
							tp.FEC_3_5: '3/5', tp.FEC_4_5: '4/5', tp.FEC_5_6: '5/6', 
							tp.FEC_6_7: '6/7', tp.FEC_7_8: '7/8', tp.FEC_8_9: '8/9', 
							tp.FEC_9_10: '9/10', tp.FEC_None: 'NONE'}.get(tp.fec, ''))
						if tp.system == tp.System_DVB_S2:
							if tp.is_id > tp.No_Stream_Id_Filter:
								tp_text = '%s MIS %d' % (tp_text, tp.is_id)
							if tp.pls_code > 0:
								tp_text = '%s Gold %d' % (tp_text, tp.pls_code)
							if tp.t2mi_plp_id > tp.No_T2MI_PLP_Id:
								tp_text = '%s T2MI %d PID %d' % (tp_text, tp.t2mi_plp_id, tp.t2mi_pid)
					elif tp_type == iDVBFrontend.feCable:
						network = _('Cable')
						self.network1 = "Cable"
						tp = transponder.getDVBC()
						tp_text = 'DVB-C %s %d / %d / %s' % (
						 {tp.Modulation_Auto: 'AUTO', tp.Modulation_QAM16: 'QAM16', 
							tp.Modulation_QAM32: 'QAM32', tp.Modulation_QAM64: 'QAM64', 
							tp.Modulation_QAM128: 'QAM128', tp.Modulation_QAM256: 'QAM256'}.get(tp.modulation, ''),
						 tp.frequency,
						 tp.symbol_rate / 1000,
						 {tp.FEC_Auto: 'AUTO', tp.FEC_1_2: '1/2', tp.FEC_2_3: '2/3', tp.FEC_3_4: '3/4', 
							tp.FEC_3_5: '3/5', tp.FEC_4_5: '4/5', tp.FEC_5_6: '5/6', 
							tp.FEC_6_7: '6/7', tp.FEC_7_8: '7/8', tp.FEC_8_9: '8/9', 
							tp.FEC_9_10: '9/10', tp.FEC_None: 'NONE'}.get(tp.fec_inner, ''))
					elif tp_type == iDVBFrontend.feTerrestrial:
						network = _('Terrestrial')
						self.network1 = "Terrestrial"
						tp = transponder.getDVBT()
						channel = getChannelNumber(tp.frequency, self.scanList[self.run]['feid'])
						if channel:
							channel = _('CH') + '%s ' % channel
						freqMHz = '%0.1f MHz' % (tp.frequency / 1000000.0)
						tp_text = '%s %s %s %s' % (
						 {tp.System_DVB_T_T2: 'DVB-T/T2', 
							tp.System_DVB_T: 'DVB-T', 
							tp.System_DVB_T2: 'DVB-T2'}.get(tp.system, ''),
						 {tp.Modulation_QPSK: 'QPSK', 
							tp.Modulation_QAM16: 'QAM16', 
							tp.Modulation_QAM64: 'QAM64', tp.Modulation_Auto: 'AUTO', 
							tp.Modulation_QAM256: 'QAM256'}.get(tp.modulation, ''),
						 '%s%s' % (channel, freqMHz.replace('.0', '')),
						 {tp.Bandwidth_8MHz: 'Bw 8MHz', 
							tp.Bandwidth_7MHz: 'Bw 7MHz', tp.Bandwidth_6MHz: 'Bw 6MHz', tp.Bandwidth_Auto: 'Bw Auto', 
							tp.Bandwidth_5MHz: 'Bw 5MHz', tp.Bandwidth_1_712MHz: 'Bw 1.712MHz', 
							tp.Bandwidth_10MHz: 'Bw 10MHz'}.get(tp.bandwidth, ''))
					elif tp_type == iDVBFrontend.feATSC:
						network = _('ATSC')
						self.network1 ="ATSC"
						tp = transponder.getATSC()
						freqMHz = '%0.1f MHz' % (tp.frequency / 1000000.0)
						tp_text = '%s %s %s %s' % (
						 {tp.System_ATSC: _('ATSC'), 
							tp.System_DVB_C_ANNEX_B: _('DVB-C ANNEX B')}.get(tp.system, ''),
						 {tp.Modulation_Auto: _('Auto'), 
							tp.Modulation_QAM16: 'QAM16', 
							tp.Modulation_QAM32: 'QAM32', 
							tp.Modulation_QAM64: 'QAM64', 
							tp.Modulation_QAM128: 'QAM128', 
							tp.Modulation_QAM256: 'QAM256', 
							tp.Modulation_VSB_8: '8VSB', 
							tp.Modulation_VSB_16: '16VSB'}.get(tp.modulation, ''),
						 freqMHz.replace('.0', ''),
						 {tp.Inversion_Off: _('Off'), 
							tp.Inversion_On: _('On'), 
							tp.Inversion_Unknown: _('Auto')}.get(tp.inversion, ''))
					else:
						print 'unknown transponder type in scanStatusChanged'
				if self.l == 0:
					self.xml_dir = "/tmp"
					try:
					    if os.path.exists("/media/usb/ServiceScan"):
						    self.xml_dir = "/media/usb/ServiceScan"
					    if os.path.exists("/media/FTA/ServiceScan"):
						    self.xml_dir = "/media/FTA/ServiceScan" 
					    if os.path.exists("/hdd/ServiceScan"):
						    self.xml_dir = "/hdd/ServiceScan"
					except:
					    self.xml_dir = "/tmp"                                                                                                                                                                                              ##
					self.location = '%s/%s_Scan Report_%s' %(self.xml_dir, self.network1, strftime("%d-%m-%Y_%H-%M-%S"))
					self.l = 1
					xml = ['                         Scan Report \n\n']
					xml.append ('< File created on %s > \n' %(strftime("%A, %B %d, %Y at %H:%M:%S")))
					xml.append ("< Satellite =  %s >\n" % network) 
					xml.append ("< Receiver = %s %s >\n" %(BOX_MODEL, BOX_NAME))
					try:
					    xml.append ('< Enigma2 Image = %s > \n' % (about.getImageTypeString()))
					except:
					    from boxbranding import getImageVersion
					    xml.append ('< Enigma2 Image = %s > \n' % (getImageVersion()))
					xml.append ('< Kernel Version = %s > \n' % (about.getKernelVersionString()))
					xml.append ('< DVB Driver Date = %s > \n' % (about.getDriverInstalledDate()))
					xml.append ('< Blindscan Frequency Range = %s to %s MHz > \n' % (self.freq1, self.freq2))
					xml.append ('< Blindscan Symbol Rate Range = %s to %s Msps > \n' % (self.symbol1, self.symbol2))
					xml.append ('< Blindscan Only Free Channels or Services? = %s  > \n' % (self.free))
					if self.tuner != "":
					    xml.append ("< Tuner = %s >\n" % self.tuner)
					f = open(self.location, "w")
					f.writelines(xml)

				if tpnumb != 0:                                                                                                                                                                                                ##
					f = open(self.location, "a")
					xml = "\n\n< '%s' > Tp# %s" %(tp_text, tpnumb )
					f.writelines(xml)
				self.network.setText(network)
				self.transponder.setText(tp_text)
		if self.state == self.DonePartially:
			runtime = int(time()) - int(self.start_time)
			runtime = runtime + self.start_time1
			self.foundServices += self.scan.getNumServices()
			T = self.foundServices - self.r
			try:
			    f = open(self.location, "a")
			    if self.start_time1 > 10:
			        self.transponder.setText(_("Blind Scan Time = %d Min.  %02d Sec.")  %( runtime / 60, (runtime % 60)))
			        xml = "< \n\nBlind Scan Time = %d Min. %02d Sec.\n"  %( runtime / 60, (runtime % 60))
			    if self.start_time1 < 10:
			        self.transponder.setText(_("Service Scan Time = %d Min.  %02d Sec.")  %( runtime / 60, (runtime % 60)))
			        xml = "< \n\ Service Scan Completed in %d Minutes  %02d Seconds.\n\n"  %( runtime / 60, (runtime % 60))			
			    self.text.setText(_("%d Channels ( TV = %d  Radio = %d)  %d of %d Transponders Scanned.")  %( self.foundServices, T, self.r, (self.t-1), self.tt)) 
 			    xml += ("%d Channels ( TV = %d  Radio = %d)  %d of %d Transponders Scanned.")  %( self.foundServices, T, self.r, (self.t-1), self.tt) 
			    f.writelines(xml)
			    f.close()
			    self.rename = '%s/%s_%sch_%stp_%s.xml' %(self.xml_dir, self.network1, self.foundServices, self.tt, strftime("%m-%d-%Y_%H-%M-%S"))
			    os.rename(self.location, self.rename)  # ServiceScan_
			except:
			    self.transponder.setText(_("Scan Error!!Press exit to abort"))
		if self.state == self.Error:
			self.text.setText(_('ERROR - failed to scan (%s)!') % self.Errors[self.errorcode])
		if self.state == self.DonePartially or self.state == self.Error:
			self.delaytimer.start(100, True)

			
	def __init__(self, progressbar, text, servicelist, passNumber, scanList, network, transponder, frontendInfo, lcd_summary):
		self.foundServices = 0
		self.progressbar = progressbar
		self.text = text
		self.servicelist = servicelist
		self.passNumber = passNumber
		self.scanList = scanList
		self.frontendInfo = frontendInfo
		self.transponder = transponder
		self.network = network
		self.run = 0
		self.lcd_summary = lcd_summary
		self.scan = None
		self.delaytimer = eTimer()
		self.delaytimer.callback.append(self.execEnd)
		self.t = 0
		self.tt = 0
		self.start_time1 = 0
		self.start_time2 = 0
		self.start_time = time()
		self.name ="" #Name of box or box type
		self.y = 1 #For Channel Numbers
		self.l = 0 #Stops Duplicate Files
		self.location ="" #Creates File Location
		self.rename ="" # Used for renaming created file
		self.xml_dir = "/tmp" # Default location for created file.
		self.r = 0  # Used to count Radio Channels
		self.network1 =""
		self.tuner ="" # Key from blindscan used to identify tuner
		self.freq1 ="" #Blindscan start frequency
		self.freq2 ="" #Blindscan Stop frequency
		self.symbol1 ="" #Blindscan start symbol rate
		self.symbol2 ="" #Blindscan stop symbol rate
		self.free ="" #Blindscan scan only free
		return

	def doRun(self):
		self.scan = eComponentScan()
		self.frontendInfo.frontend_source = lambda : self.scan.getFrontend()
		self.feid = self.scanList[self.run]["feid"]
		self.flags = self.scanList[self.run]["flags"]
		try:
			self.start_time1 = self.scanList[self.run]["start"]
		except:
			pass
		try:
			self.start_time2 = self.scanList[self.run]["start1"]
		except:
			pass	
		try:
			self.name = self.scanList[self.run]["name"]
		except:
			pass	
		try:
			self.tuner = self.scanList[self.run]["tuner"]
		except:
			pass	

		try:  #Add Blindscan frequency 7 symbol rate to scan report
			self.freq1 = self.scanList[self.run]["freq1"]
			self.freq2 = self.scanList[self.run]["freq2"]
			self.symbol1 = self.scanList[self.run]["symbol1"]
			self.symbol2 = self.scanList[self.run]["symbol2"]
			self.free = self.scanList[self.run]["free"]
		except:
			pass

		self.networkid = 0
		if self.scanList[self.run].has_key("networkid"):
			self.networkid = self.scanList[self.run]["networkid"]			
		self.state = self.Idle
		self.scanStatusChanged()
		for x in self.scanList[self.run]["transponders"]:
			self.tt = self.tt+1
			self.scan.addInitial(x)

	def updatePass(self):
		size = len(self.scanList)
		if size > 1:
			txt = '%s %s/%s (%s)' % (_('pass'), self.run + 1, size, nimmgr.getNim(self.scanList[self.run]['feid']).slot_name)
			self.passNumber.setText(txt)

	def execBegin(self):
		self.doRun()
		self.updatePass()
		self.scan.statusChanged.get().append(self.scanStatusChanged)
		self.scan.newService.get().append(self.newService)
		self.servicelist.clear()
		self.state = self.Running
		err = self.scan.start(self.feid, self.flags, self.networkid)
		self.frontendInfo.updateFrontendData()
		if err:
			self.state = self.Error
			self.errorcode = 0
		self.scanStatusChanged()

	def execEnd(self):
		if self.scan is None:
			if not self.isDone():
				print "*** warning *** scan was not finished!"
			return
		self.scan.statusChanged.get().remove(self.scanStatusChanged)
		self.scan.newService.get().remove(self.newService)
		self.scan = None
		if self.run != len(self.scanList) - 1:
			self.run += 1
			self.execBegin()
		else:
			self.state = self.Done
		if self.name is not "":
			self.network.setText(_("%s.  (%s)") % (self.network1, self.name) )
		if self.start_time2 > 0:                                                                           
			runtime = int(time()) - int(self.start_time2)
			self.transponder.setText(_("Scan Completed in %d Minutes  %02d Seconds.")  %( runtime / 60, (runtime % 60)))



	def isDone(self):
		return self.state == self.Done or self.state == self.Error

	def newService(self):
		newServiceName = self.scan.getLastServiceName()
		newServiceRef = self.scan.getLastServiceRef()
		if newServiceRef[4] >= "2.1":                                
			if newServiceName =="":
			    newServiceName ="NoName"
			if newServiceRef[4] !="B":
			    if newServiceRef[4] !="C":
			        newServiceName += " --- UnKnown Service Type %s%s" %(newServiceRef[4],newServiceRef[5] )
		if newServiceRef[4] == "2":
			self.r = self.r + 1                                                                    
			newServiceName += ("   (Radio #%d)" % self.r)
		self.servicelist.addItem((newServiceName, newServiceRef))
		self.lcd_summary and self.lcd_summary.updateService(newServiceName)
		xml = '\n< (%s)%s />  %s' % (self.y, newServiceName, newServiceRef) #(newServiceName,,  %s  newServiceRef tp_text)   < %s >
		self.y = self.y + 1
		f = open(self.location, "a")
		f.writelines(xml)


	def destroy(self):
		self.state = self.Idle
		if self.scan is not None:
			self.scan.statusChanged.get().remove(self.scanStatusChanged)
			self.scan.newService.get().remove(self.newService)
			self.scan = None
		return
