#!/usr/bin/python
# -*- coding: utf-8 -*-
"""An image contained in a Misura HDF5 output file time/Image array reference."""
import os
import logging

import veusz.utils
import veusz.widgets
import veusz.compat
import veusz.document as document
import veusz.setting as setting

import utils

from PyQt4 import QtCore,QtSvg

class ImageReference(utils.OperationWrapper,veusz.widgets.ImageFile):
	"""Draw an image contained in a Misura HDF5 output file, referring to a nearest time"""
	typename = 'imagereference'
	description = 'Misura Image'
	allowusercreation = True
	_dec=False
	
	def __init__(self,parent,name=None):
		veusz.widgets.ImageFile.__init__(self,parent,name=name)
		
	@property
	def dec(self):
		"""Instantiate decoder on need"""
		if self._dec is False:
			from .. import filedata
			self._dec=filedata.DataDecoder()
		return self._dec
		
	@classmethod	
	def addSettings(klass, s):
		"""Construct list of settings."""
		veusz.widgets.ImageFile.addSettings(s)	
		s.add( setting.Str('dataset', '',
						   descr='Source dataset',
						   usertext= 'Source dataset'),
			0 )
		s.add( setting.Float(
				'target', 0,
				descr='Target time',
				usertext='Target time'),
			1 )		
		s.add( setting.Str('embeddedDataset', '',
				descr='Dataset source for embedded image',
				usertext='Dataset source for embedded image',
				hidden=True) )
		s.add( setting.Float('embeddedTarget', 0,
				descr='Target time for embedded image',
				usertext='Target time for embedded image',
				hidden=True) )
		s.add( setting.Str('codec', 'JPG',
				descr='Image codec',
				usertext='Image codec',
				),
			10 )
		
	def updateCachedImage(self):
		"""Take the image from the Misura file, at the desired dataset and time"""
		s = self.settings
		if not os.path.exists(s.filename):
			self.updateCachedEmbedded()
			return
		from .. import filedata
		fp=filedata.getFileProxy(s.filename)
		t=fp.get_node_attr('/conf','zerotime')
		if s.target<t:
			t+=s.target
		dec=self.dec
		dec.reset(fp,datapath=s.dataset)
		seq=dec.get_time(t)
		logging.debug('%s %s', 'sequence', seq)
		r=dec.get_data(seq)
		fp.close()
		
		logging.debug('%s %s', 'data', r)
		if not r:
			logging.debug('%s %s %s', 'Could not get image data', t, seq)
			return
		t,pix=r
		ba = QtCore.QByteArray()
		buf = QtCore.QBuffer(ba)
		buf.open(QtCore.QIODevice.WriteOnly)
		pix.save(buf, 'PNG')
		encoded = veusz.compat.cbytes(ba.toBase64()).decode('ascii')
		logging.debug('%s', 'encoded')
		self.cacheimage = pix
		self.cacheembeddata=encoded	
		
	def actionEmbed(self):
		"""Override Veusz ImageFile.actionEmbed in order """
		s = self.settings
		self.updateCachedImage()
		# now put embedded data in hidden setting
		ops = [
		    document.OperationSettingSet(s.get('embeddedImageData'),
		                                 self.cacheembeddata),
		    document.OperationSettingSet(s.get('embeddedDataset'),
										s.dataset),
		    document.OperationSettingSet(s.get('embeddedTarget'),
										s.target),
		    document.OperationSettingSet(s.get('codec'),
										self.dec.comp)
		    ]
		self.document.applyOperation(
		    document.OperationMultiple(ops, descr='image reference') )
		
	def drawShape(self, painter, rect):
		"""Draw image."""
		s = self.settings
		logging.debug('%s', 'drawShape')
		# draw border and fill
		painter.drawRect(rect)
		
		# check to see whether image needs reloading
		image = None
		if s.embeddedDataset!=s.dataset or s.embeddedTarget!=s.target:
			self.actionEmbed()
			image = self.cacheimage
		
		# or needs recreating from embedded data
		elif s.embeddedImageData != '':
			if s.embeddedImageData is not self.cacheembeddata:
				self.updateCachedEmbedded()
				self.updateCachedImage()
			image = self.cacheimage
		
		# if no image, then use default image
		if ( not image or image.isNull() or
			 image.width() == 0 or image.height() == 0 ):
			# load replacement image
			fname = os.path.join(veusz.utils.imagedir, 'button_imagefile.svg')
			r = QtSvg.QSvgRenderer(fname)
			
			r.render(painter, rect)
		
		else:
			# image rectangle
			irect = QtCore.QRectF(image.rect())
			
			# preserve aspect ratio
			if s.aspect:
				xr = rect.width() / irect.width()
				yr = rect.height() / irect.height()
			
				if xr > yr:
					rect = QtCore.QRectF(
						rect.left()+(rect.width()-irect.width()*yr)*0.5,
						rect.top(), irect.width()*yr, rect.height())
				else:
					rect = QtCore.QRectF(
						rect.left(),
						rect.top()+(rect.height()-irect.height()*xr)*0.5,
						rect.width(), irect.height()*xr)
		
			# finally draw image
			painter.drawImage(rect, image, irect)		


document.thefactory.register( ImageReference )
