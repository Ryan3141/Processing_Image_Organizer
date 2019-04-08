
import os
import sys
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QWidget, QAbstractScrollArea
from PyQt5 import QtCore

try:
	import mysql.connector
except:
	Ask_For_Install( "mysql-connector-python" )
	import mysql.connector

import sqlite3

import datetime
import configparser
from File_Loader import File_Loader


def resource_path( relative_path ):
	return "./" + relative_path

Ui_MainWindow, QtBaseClass = uic.loadUiType( resource_path("Processing_Image_Organizer_GUI.ui") )


from tkinter import messagebox, Tk
def Ask_Yes_Or_No_Popup( title_of_window, message ):
	root = Tk()
	root.withdraw()
	root.lift()
	root.attributes("-topmost", True)
	answer_was_yes = messagebox.askyesno( title_of_window, message )

	return answer_was_yes

def Connect_To_SQL( configuration_file_path ):
	should_open_file = False
	try:
		configuration_file = configparser.ConfigParser()
		configuration_file.read( configuration_file_path )
		db_type = configuration_file['SQL_Server']['database_type']
		db_name = configuration_file['SQL_Server']['database_name']
		if db_type == "QSQLITE":
			sql_conn = sqlite3.connect( db_name )
		elif db_type == "QMYSQL":
			sql_conn = mysql.connector.connect( host=configuration_file['SQL_Server']['host_location'], database=db_name,
								user=configuration_file['SQL_Server']['username'], password=configuration_file['SQL_Server']['password'] )
			sql_conn.ping( True ) # Maintain connection to avoid timing out
		return db_type, sql_conn

	except sqlite3.Error as e:
		should_open_file = Ask_Yes_Or_No_Popup( "SQL Connection Error, Open config.ini?", "There was an issue connecting the SQL server described in the config.ini file" )
		if should_open_file:
			os.startfile( os.path.abspath(configuration_file_path ) )
		return None, None
	except mysql.connector.Error as e:
		should_open_file = Ask_Yes_Or_No_Popup( "SQL Connection Error, Open config.ini?", "There was an issue connecting the SQL server described in the config.ini file" )
		if should_open_file:
			os.startfile( os.path.abspath(configuration_file_path ) )
		return None, None
	except Exception as e:
		should_open_file = Ask_Yes_Or_No_Popup( "Error In config.ini File, Open It?", "Error finding: " + str(e) )
		if should_open_file:
			os.startfile( os.path.abspath(configuration_file_path ) )


def Commit_To_SQL( sql_type, sql_conn, **commit_things ):
	sql_insert_string = '''INSERT INTO processing_images({}) VALUES({})'''.format( ','.join( commit_things.keys() ), ','.join( ['%s'] * len(commit_things.keys()) ) )
	if sql_type == 'QSQLITE':
		sql_insert_string.replace( '%s', '?' )

	cur = sql_conn.cursor()
	cur.execute( sql_insert_string, list(commit_things.values()) )
	#data_as_tuple = tuple(zip([measurement_id] * len(x_data),(float(x) for x in x_data),(float(y) for y in y_data))) # mysql.connector requires a tuple or list (not generator) and native float type as input
	#cur.executemany( sql_insert_string, data_as_tuple )
	sql_conn.commit()


class IV_Measurement_Assistant_App(QWidget, Ui_MainWindow):
	measurementRequested_signal = QtCore.pyqtSignal(float, float, float)
	Async_Grab_File = QtCore.pyqtSignal(str, str)

	def __init__(self, parent=None, root_window=None):
		QWidget.__init__(self, parent)
		Ui_MainWindow.__init__(self)
		self.setupUi(self)

		self.Init_Subsystems()

		self.Connect_Functions()


		self.ftp_server_thread.start()


	def Init_Subsystems(self):
		self.sql_type, self.sql_connection = Connect_To_SQL( resource_path( "configuration.ini" ) )

		self.ftp_server = File_Loader( resource_path( "configuration.ini" ) )
		self.ftp_server_thread = QtCore.QThread()
		self.ftp_server.moveToThread( self.ftp_server_thread )
		self.ftp_server_thread.started.connect( self.ftp_server.Connect )

		self.Initialize_Tree_Table()
		

	def Connect_Functions( self ):
		self.refreshConnection_toolButton.clicked.connect( self.Grab_Image )

		self.treeWidget.itemDoubleClicked.connect( self.Grab_Image )
		self.ftp_server.imageReady_signal.connect( self.graphicsView.setImage )
		self.Async_Grab_File.connect( self.ftp_server.GetImageFile )
		pass

	def Grab_Image( self, tree_item, column ):
		selected = self.Get_Bottom_Children_Elements_Under( tree_item )
		file_location = selected[0].text(selected[0].columnCount() - 1)
		file_name = os.path.basename( file_location )
		folder = os.path.dirname( file_location )
		self.Async_Grab_File.emit( folder, file_name )
		#file_name = "477K Pads (1).jpg"
		#folder = '/Microscope_Computer/Microscope Images/Ryan/Gold Pads'
		#self.ftp_server.GetFile( folder, file_name )
		#QtCore.QMetaObject.invokeMethod( self.ftp_server, "GetImageFile" )
		#self.graphicsView.setImage( imread(file_name) )
		#materialSelection_lineEdit

	def Initialize_Images_Info( self ):
		data_headers = [ "time", "sample_name", "processing_step", "image_location", "microscope_location", "user", "path_to_file", "processing_step_part", "processing_step_attempt" ]


	def Initialize_Tree_Table(self):
		self.Reinitialize_Tree_Table()

		## setup policy and connect slot for context menu popup:
		#self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu);
		#self.treeWidget.customContextMenuRequested.connect(self.treeContextMenuRequest);

	def Reinitialize_Tree_Table(self):
		self.treeWidget.clear()
		self.treeWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

		user = self.user_lineEdit.text()
		header_titles = ["Sample Name", "Process", "Process Sequence", "Attempt", "Location", "Time", "Microscope", "File Location"]
		self.treeWidget.setHeaderLabels(header_titles)
		self.treeWidget.hideColumn(len(header_titles) - 1)
		what_to_collect = ["sample_name", "processing_step", "processing_step_part", "processing_step_attempt", "image_location", "time", "microscope_location", "path_to_file" ]

		query = self.sql_connection.cursor()
		querey_string = 'SELECT {} FROM processing_images WHERE user="{}"'.format( ','.join(what_to_collect), user )
		try:
			test = query.execute(querey_string)
			selected_rows = query.fetchall()
		except mysql.connector.Error as e:
			print("Error pulling data from ftir_measurments:%d:%s" % (e.args[0], e.args[1]))
			return

		self.Recursive_Tree_Table_Build( what_to_collect, self.treeWidget.invisibleRootItem(), 0, selected_rows )
		for i in range(len(header_titles)):
			self.treeWidget.resizeColumnToContents(i)


	def Recursive_Tree_Table_Build(self, what_to_collect, parent_tree, current_collectable_i, selected_rows):
		if (current_collectable_i == len(what_to_collect)):
			return

		unique_elements = sorted( set( x[current_collectable_i] for x in selected_rows ) )

		numberOfRows = len(unique_elements)

		for unique_element in unique_elements:
			current_value = unique_element
			if isinstance(current_value, datetime.timedelta):
				hours, remainder = divmod(current_value.total_seconds(), 3600)
				minutes, seconds = divmod(remainder, 60)
				current_value = '%02d:%02d:%02d' % (hours, minutes, seconds)

			filtered_rows = [ x for x in selected_rows if x[current_collectable_i] == unique_element ]
			new_tree_branch = parent_tree;  # Only add a new breakout for the first one, and if more than 1 child
			if numberOfRows > 1 or current_collectable_i == 0:
				new_tree_branch = QtWidgets.QTreeWidgetItem(parent_tree)

			new_tree_branch.setText(current_collectable_i, str(current_value));
			self.Recursive_Tree_Table_Build(what_to_collect, new_tree_branch, current_collectable_i + 1, filtered_rows)


	def Get_Bottom_Children_Elements_Under(self, tree_item):
		number_of_children = tree_item.childCount()
		if number_of_children == 0:
			return [tree_item]

		lowest_level_children = []
		for i in range(number_of_children):
			i_lowest_level_children = self.Get_Bottom_Children_Elements_Under(tree_item.child(i))
			lowest_level_children += i_lowest_level_children

		return lowest_level_children



if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	window = IV_Measurement_Assistant_App()
	window.show()
	sys.exit(app.exec_())
