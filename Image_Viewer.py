from PyQt5 import QtNetwork, QtCore, QtGui, uic, QtWidgets
from PyQt5 import *
from PyQt5 import uic, QtGui, QtOpenGL
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from cv2 import cvtColor, COLOR_BGR2RGB
from sys import platform as _platform


class Image_Viewer( QtWidgets.QGraphicsView ):

	def __init__( self, parent ):
		super().__init__( parent )

		self._zoom = 0;
		self._scene = QtWidgets.QGraphicsScene( self )
		self._photo = None
		self._photo_handle = None
		#self._scene.addItem( self._photo );
		self.setScene( self._scene )

		self.setTransformationAnchor( QtWidgets.QGraphicsView.AnchorUnderMouse )
		self.setResizeAnchor( QtWidgets.QGraphicsView.AnchorUnderMouse )
		self.setVerticalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )
		self.setHorizontalScrollBarPolicy( QtCore.Qt.ScrollBarAlwaysOff )
		#self.setBackgroundBrush( QBrush( QColor( 30, 30, 30 ) ) );
		self.setFrameShape( QtWidgets.QFrame.NoFrame )

		self.viewport().grabGesture(Qt.PinchGesture)
		self.firstcall = 1

		#right_graphicsView

	def resizeEvent( self, event ):
		if self._photo != None and self._zoom == 0:
			self.fitInView( 0, 0, self._photo.size().width(), self._photo.size().height(), QtCore.Qt.KeepAspectRatio )

		super().resizeEvent( event )

	def setImage( self, opencv_image ):
		if self._photo is not None:
			self._scene.removeItem( self._photo_handle )
			self._photo_handle = None
			self._photo = None

		image = cvtColor( opencv_image, COLOR_BGR2RGB )
		temp_image = QtGui.QImage( image.data, image.shape[1], image.shape[0], image.strides[0], QtGui.QImage.Format_RGB888 )
		self._photo = QtGui.QPixmap.fromImage( temp_image )

		if self._photo is not None:
			self._photo_handle = self._scene.addPixmap( self._photo )
			self.setDragMode( QtWidgets.QGraphicsView.ScrollHandDrag )
		else:
			self.setDragMode( QtWidgets.QGraphicsView.NoDrag )

		if self.firstcall == 1:
			self.fitImageInView()
			self.firstcall = 0

	def fitImageInView( self ):
		if self._photo is None:
			return
		rect = self._photo.rect()
		to_identity = self.transform().mapRect( QtCore.QRectF( 0, 0, 1, 1 ) )
		self.scale( 1 / to_identity.width(), 1 / to_identity.height() )
		view_rect = self.viewport().rect()
		scene_rect = self.transform().mapRect( rect );
		factor = min( view_rect.width() / scene_rect.width(),
							 view_rect.height() / scene_rect.height() );
		self.scale( factor, factor );
		self.centerOn( rect.center() );
		self._zoom = 0

	def mousePressEvent( self, event ):
		if( event.button() == QtCore.Qt.RightButton ):
			self.setCursor( QtCore.Qt.CrossCursor )

			# get scene coords from the view coord
			scenePt = self.mapToScene( event.pos() )

			# get the item that was clicked on
			the_item = self._scene.itemAt( scenePt, self.transform() )

			if the_item is not None:
				# get the scene pos in the item's local coordinate space
				localPt = the_item.mapFromScene( scenePt )
				#emit self.rightClicked( localPt.x(), localPt.y() )

			event.accept();
			return;
		super().mousePressEvent( event )

	if _platform != "darwin":	# Use the mouse scroll wheel to zoom in and out for Windows and other systems.
		def wheelEvent( self, event ):
			if( self._photo is None or self._photo.isNull() ):
				return
			change = 1.0
			if( event.angleDelta().y() > 0 ):
				change = 1.25
				self._zoom += 1
			else:
				change = 0.8
				self._zoom -= 1

			if( self._zoom > 0 ):
				self.scale( change, change )
			elif( self._zoom == 0 ):
				self.fitImageInView()
			else:
				self.fitImageInView()
				self._zoom = 0

			event.accept()

	if _platform == "darwin":  # Use Multi-touch trackpad to zoom in and out for mac.
		def viewportEvent(self, event):
			if event.type() == QEvent.Gesture:
				pinch = event.gesture(Qt.PinchGesture)
				if pinch:
					changeFlags = pinch.changeFlags()
					if changeFlags & QPinchGesture.ScaleFactorChanged:
						factor = pinch.property("scaleFactor")
						self.scale(factor, factor)
					if pinch.state() == Qt.GestureFinished:
						pass
					return True
			return QGraphicsView.viewportEvent(self, event)
