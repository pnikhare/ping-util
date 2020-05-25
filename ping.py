#!/usr/bin/env python

import os, sys, socket
import struct, select, time
import re
 
class PingPacket():
    def __init__(self):
        pass
    
    def checksum(self, source_string):
        sum = 0
        countTo = (len(source_string)/2)*2
        count = 0
        while count<countTo:
            #print(source_string[(count + 1):(count+2)],"+",source_string[count:(count+1)])
            #thisVal = ord(str(source_string[count + 1]).strip())*256 + ord(str(source_string[count]).strip())
            thisVal = source_string[count + 1]*256 + source_string[count]
            sum = sum + thisVal
            sum = sum & 0xffffffff # Necessary?
            count = count + 2
 
        if countTo<len(source_string):
            sum = sum + ord(source_string[len(source_string) - 1])
            sum = sum & 0xffffffff # Necessary?
 
        sum = (sum >> 16)  +  (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff
 
        # Swap bytes. Bugger me if I know why.
        answer = answer >> 8 | (answer << 8 & 0xff00)
 
        return answer
    
    def createPacket(self):
        # Header is type (8), code (8), checksum (16), id (16), sequence (16)
        ICMP_ECHO_REQUEST = 8
        code = 0
        pktChecksum = 0
        processId = os.getpid()
        sequenceNum = 1
 
        # header with a 0 checksum.
        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, code, pktChecksum, processId, sequenceNum)
        data = struct.pack("d", time.time())
    
        # Calculate the checksum on the data and the header.
        pktChecksum = self.checksum(header + data)
 
        # Place the correct checksum in header
        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, code, socket.htons(pktChecksum), processId, sequenceNum)
        packet = header + data
        return packet
    
class Ping:
    def __init__(self):
        pass
    
    def createSocket(self):
        icmp = socket.getprotobyname("icmp")
        try:
            pingSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        except(socket.error, (errno, msg)):
            if errno == 1:
            # Operation not permitted
                msg = msg + (" - Note that ICMP messages can only be sent from processes"
                " running as root.")
                raise socket.error(msg)
            raise # raise the original error
        return pingSocket

    def receivePing(self, pingSocket):
        opt = PingOptions()
        timeLeft = opt.timeout
        while True:
            startTime = time.time()
            waitEvent = select.select([pingSocket], [], [], timeLeft)
            execTime = (time.time() - startTime)
            # Timeout
            if waitEvent[0] == []: 
                return
 
            timeReceived = time.time()
            packet, addr = pingSocket.recvfrom(1024)
            icmpHeader = packet[20:28]
            #un pack received packet
            type, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)
            if packetID == os.getpid():
                bytesInDouble = struct.calcsize("d")
                timeSent = struct.unpack("d", packet[28:28 + bytesInDouble])[0]
                return timeReceived - timeSent
 
            timeLeft = timeLeft - execTime
            if timeLeft <= 0:
                return

    def ping(self, opt):
        # get ping options
        #opt = PingOptions()
        destAddr = opt.hostAddress
        print("timeout is", opt.timeout, " count is",opt.count)
        print("Pinging ",destAddr, ": ")
        pktSent, pktReceived = 0, 0 
    
        # Send ICMP Pkts of count set
        for pktCount in range(opt.count):        
            try:
                pingSocket = self.createSocket()
                pingPacket = PingPacket()
                packet = pingPacket.createPacket() 
                pingSocket.sendto(packet, (destAddr, 1))
                pktSent += 1
                txTime = self.receivePing(pingSocket)
                pingSocket.close()
            except(socket.gaierror):
                print("failed to create socket ")
                break
 
            if txTime  ==  None:
                print("failed. Timeout in ",opt.timeout, " sec")
            else:
                txTime  =  txTime * 1000
                pktReceived += 1
                print("Reply recevied from ", destAddr,": time=", txTime," ms")
        print(" ")
        print("Packet Statistics")
        print("  Packet sent=", pktSent, "received=", pktReceived, "Loss=",pktSent-pktReceived)

    
 
 
 
class PingOptions :
    def __init__(self):
        self._timeout = 2
        self._count = 4
        self.hostAddress = None

    @property
    def timeout(self):
        return self._timeout
    
    @timeout.setter
    def timeout(self, value):
        if(value > 5) :
            print("cannot set to more than 5. Setting it to 5")
            value = 5
        self._timeout = value
        
    @property
    def count(self):
        return self._count
    
    @count.setter
    def count(self, value):
        if(int(value) > 100) :
            print("cannot set to more than 100. Setting count to 100")
            value = 100
        self._count = value


def validateArg(args, pingOpt):
    if len(args) < 2 :
        printHelp()
        return 4
       
    index = 1
    while index <  len(args):
        if args[index] == '-n' and args[index+1].isnumeric() :
            pingOpt.count = int(args[index+1])
            index += 2
        elif args[index] == '-w' and args[index+1].isnumeric() :
            pingOpt.timeout = int(args[index+1])
            index += 2
        elif validateIp(args[index]) :
            pingOpt.hostAddress = args[index]
            index += 1
        
        else:
            return 2

    if pingOpt.hostAddress == None :
        return 3

    return 1

def validateIp(hostAddress) :
    try :
        regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''
    
        # validate by host name
        hostAddress  =  socket.gethostbyname(hostAddress)  
        if(re.search(regex, hostAddress)):  
            return True  

    
        return False
    except:
        return False

def printHelp(valid):
    if valid == 4 :
        print("Usage :")
        print("ping [-n count] [-w timeout] target_ip_address\n")
        print("-n count       Number of echo requests to send.")
        print("-w timeout     Timeout in milliseconds to wait for each reply.")
    elif valid == 2 :
        print("Bad Parameter for Host Address")
    elif valid == 3 :
        print("Host Address must be specified.")
     
if __name__ == '__main__':
    pingOpt = PingOptions()
    
    valid = validateArg(sys.argv, pingOpt)      
    if valid == 1:
        host = sys.argv[len(sys.argv) - 1]
        pingUtil = Ping()
        pingUtil.ping(pingOpt)
    else :
        printHelp(valid)
