from PyQt5 import QtCore

import numpy as np
import ftplib
import configparser
import os
from cv2 import imread

from tkinter import messagebox, Tk
def Ask_Yes_Or_No_Popup( title_of_window, message ):
	root = Tk()
	root.withdraw()
	root.lift()
	root.attributes("-topmost", True)
	answer_was_yes = messagebox.askyesno( title_of_window, message )

	return answer_was_yes


class File_Loader( QtCore.QObject ):
	imageReady_signal = QtCore.pyqtSignal(np.ndarray)

	def __init__( self, configuration_file_path, parent=None ):
		super().__init__( parent )

		self.configuration_file_path = configuration_file_path
		self.stored_images = {}

	def run(self):
		self.Connect()
		self.Initialize_Connection()
		while( True ):
			#QtCore.QThread.yieldCurrentThread()
			QtCore.QCoreApplication.processEvents()
			time.sleep( 0.5 )

	def Connect( self ):
		try:
			configuration_file = configparser.ConfigParser()
			configuration_file.read( self.configuration_file_path )
			self.local_picture_storage_location = os.path.abspath( configuration_file['File_Server']['local_picture_storage_location'] )
			host = configuration_file['File_Server']['host_location']
			port = int( configuration_file['File_Server']['port'] )
			username = configuration_file['File_Server']['username']
			password = configuration_file['File_Server']['password']

		except Exception as e:
			should_open_file = Ask_Yes_Or_No_Popup( "Error In config.ini File, Open It?", "Error finding: " + str(e) )
			if should_open_file:
				os.startfile( os.path.abspath(configuration_file_path ) )

		self.ftps = ftplib.FTP_TLS()
		#ftps.set_debuglevel(2)

		self.ftps.connect(host, port)
		self.ftps.login(username, password)
		self.ftps.set_pasv(True)
		self.ftps.prot_p()

	def GetImageFile( self, directory, file_name, should_emit_when_loaded ):
		#test = ftps.pwd()
		#test = ftps.dir()
		#print( str(test) )
		local_file_location = os.path.join( self.local_picture_storage_location, directory[1:], file_name ).replace(os.sep, '/')
		local_directory_location = os.path.join( self.local_picture_storage_location, directory[1:] ).replace(os.sep, '/')
		if not os.path.isfile(local_file_location):
			if not os.path.isdir(local_directory_location):
				os.makedirs( local_directory_location )
			try:
				self.ftps.cwd( str(directory) )
				self.ftps.retrbinary( 'RETR {}'.format( str(file_name) ),
							   open(local_file_location, 'wb').write )
			except Exception as e:
				try: # Connection still working, file must just not exist on server
					self.ftps.pwd()
					print( "Error cannot find file: " + local_file_location)
				except: # Connection likely timed out, try again and repeat previous command
					self.Connect()
					self.ftps.cwd( str(directory) )
					self.ftps.retrbinary( 'RETR {}'.format( str(file_name) ),
							   open(local_file_location, 'wb').write )

		if local_file_location in self.stored_images.keys():
			image_from_file = self.stored_images[ local_file_location ]
		else:
			image_from_file = imread( local_file_location )
			self.stored_images[ local_file_location ] = image_from_file

		if image_from_file is not None:
			self.imageReady_signal.emit( image_from_file )
		else:
			print( "Something is wrong with " + local_file_location )

	def Close( self ):
		self.ftps.quit()
