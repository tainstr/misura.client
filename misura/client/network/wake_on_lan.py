import socket
import struct
#http://code.activestate.com/recipes/358449-wake-on-lan/
def wake_on_lan(macaddress):
    """ Switches on remote computers using WOL. """

    # Check macaddress format and try to compensate.
    if len(macaddress) == 12:
        pass
    elif len(macaddress) == 12 + 5:
        sep = macaddress[2]
        macaddress = macaddress.replace(sep, '')
    else:
        raise ValueError('Incorrect MAC address format')
    macaddress = macaddress.upper()
    # Pad the synchronization stream.
    data = ''.join(['FFFFFFFFFFFF', macaddress * 18])
    send_data = '' 
    
    # Split up the hex values and pack.
    for i in range(0, len(data), 2):
        send_data = ''.join([send_data,
                             struct.pack('B', int(data[i: i + 2], 16))])

    # Broadcast it to the LAN.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, ('<broadcast>', 7))
    print 'Wake on LAN packet:', data
    

if __name__ == '__main__':
    # Use macaddresses with any seperators.
    #import sys
    #wake_on_lan(sys.argv[1])
    wake_on_lan('d0:50:99:51:9e:88')
    #wake_on_lan('0F-0F-DF-0F-BF-EF')
    # or without any seperators.
    #wake_on_lan('0F0FDF0FBFEF')