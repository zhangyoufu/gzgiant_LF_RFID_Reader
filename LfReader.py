# coding: utf-8 
import serial
import operator
import struct

'''
Keyword:
 广州小巨人
 USB-203-RW
 读卡
 发卡
 读写
 模块
 EM4100 T5577
 ID card reader & writer6
 AA DD
 0xAA 0xDD
 AADD
 0xAADD

Reference:
 http://www.xdowns.com/soft/4/25/2013/soft_114116.html
 ( or http://www.rsdown.cn/down/32957.html )
 http://www.baidu.com/p/gzgeant?from=wenku
 https://github.com/merbanan/rfid_app/blob/master/rfid_app.c
 http://www.geant.icoc.cc
 http://gzgiant.taobao.com
 ( aka http://shop73078509.taobao.com )
 ( This is the official shop, but you can buy cheaper elsewhere )
'''

class LfReader( serial.Serial ):
	BAUDRATE_LIST = [9600, 14400, 19200, 28800, 38400, 57600, 115200]
	LED_RED   = 1
	LED_GREEN = 2
	MODE_MANCHESTER_64 = 0x25
	MODE_MANCHESTER_32 = 0x2A
	MODE_EM4100        = 0x35
	MODE_FDX_B         = 0x3A

	# Note: the module only accepts a subset of commands
	SET_BAUDRATE = '\x01\x01'
	GET_MODEL    = '\x01\x02'
	BEEP         = '\x01\x03'
	LED          = '\x01\x04'
	SLEEP        = '\x01\x05'

	SET_MODE     = '\x01\x07'

	READ_FDX_A   = '\x01\x0A'
	READ_FDX_B   = '\x01\x0B'
	READ_EM4100  = '\x01\x0C'
	READ_HID     = '\x01\x0D'

	ATA5567_WRITE                = '\x02\x01'
	ATA5567_WRITE_WITH_PWD       = '\x02\x02'
	ATA5567_WAKEUP               = '\x02\x03'
	ATA5567_READ                 = '\x02\x04'
	ATA5567_READ_WITH_PWD        = '\x02\x05'
	ATA5567_READ_PAGE            = '\x02\x06'
	ATA5567_RESET                = '\x02\x07'
	ATA5567_ACCESS_MANCHESTER_32 = '\x02\x08'
	ATA5567_ACCESS_MANCHESTER_64 = '\x02\x09'
	
	WRITE_FDX_A  = '\x02\x0A'
	WRITE_FDX_B  = '\x02\x0B'
	WRITE_EM4100 = '\x02\x0C'
	WRITE_HID    = '\x02\x0D'

	CONFIG    = '\x03\x01'
	READ_WORD = '\x03\x02'
	LOGIN     = '\x03\x03'
	LOCK      = '\x03\x04'
	DISABLE   = '\x03\x05'
	
	WRITE_FDX_B_ALT  = '\x03\x0B'
	WRITE_EM4100_ALT = '\x03\x0C'

	def __init__( self, *args, **kwargs ):
		kwargs.setdefault( 'baudrate', 38400 )
		serial.Serial.__init__( self, *args, **kwargs )
		assert self.get_model() == 'ID card reader & writer'

	def cksum( self, data ):
		return reduce( operator.xor, bytearray( data ))

	def pack( self,data ):
		data += chr( self.cksum( data ))
		size = struct.pack( '>H', len( data ))
		payload = size + data
		return '\xAA\xDD' + payload.replace( '\xAA', '\xAA\x00' )

	def _read( self, n ):
		s = ''
		while n:
			c = self.read(1)
			if c == '\xAA':
				assert self.read(1) == '\x00'
			s += c
			n -= 1
		return s

	def unpack( self ):
		assert self.read(2) == '\xAA\xDD'
		size = struct.unpack( '>H', self._read(2) )[0]
		data = self._read( size )
		assert self.cksum( data ) == 0
		return data[:-1]

	def request( self, req, extra=False, wait_response=True ):
		assert len(req) >= 2
		self.write( self.pack( req ))
		if wait_response:
			resp = self.unpack()
			assert resp[:2] == req[:2]
			retval = ord( resp[2] )
			if extra:
				return retval, resp[3:]
			else:
				assert resp[3:] == ''
				return retval

	def get_model( self ):
		retval, model = self.request( self.GET_MODEL, extra=True )
		assert retval == 0
		return model

	# duration (unit: 5ms)
	def beep( self, duration=10 ):
		assert self.request( self.BEEP+chr(duration) ) == 0

	# bit0: red
	# bit1: green
	def led( self, mask ):
		assert mask in range(4)
		assert self.request( self.LED+chr(mask) ) == 0

	def sleep( self ):
		assert self.request( self.SLEEP ) == 0

	def read_em4100( self ):
		retval, cardid = self.request( self.READ_EM4100, extra=True )
		if retval == 0:
			assert len(cardid) == 5
		else:
			assert 1 <= retval <= 3
			assert cardid == ''
		return cardid

	def write_em4100( self, cardid, lock=False ):
		if isinstance( cardid, (str,bytearray) ):
			assert len( cardid ) == 5
		else:
			assert cardid >= 0 and cardid <= 0xFFFFFFFFFF
			cardid = ('%.10X' % cardid).decode('hex')
		lock = '\x01' if lock else '\x00'

		assert self.request( self.WRITE_EM4100+lock+cardid ) == 0
		if self.read_em4100() == cardid: return True

		assert self.request( self.WRITE_EM4100_ALT+lock+cardid ) == 0
		if self.read_em4100() == cardid: return True

		return False

if __name__ == '__main__':
	import time
	reader = LfReader( 'COM1' )

	# correct card id         incorrect samples
	# '\x00\x00\x00\x00\xcc', '\x00\x00\x00\x00\x33', '\x00\x00\x00\x00\x66'
	# '\x00\x00\x00\x00\xaa', '\x00\x00\x00\x00\x22', '\x00\x00\x00\x00\x55'

	last = None
	while 1:
		result = reader.request( reader.READ_EM4100, extra=True )
		if result != last:
			print time.ctime(), `result`
			if result[0] == 0:
				reader.led(reader.LED_GREEN)
			else:
				reader.led(reader.LED_RED)
			last = result
