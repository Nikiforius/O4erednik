# -*- coding: utf-8 -*-
'''
    This file is part of O4erednik.

    O4erednik is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License or
    (at your option) any later version.

    O4erednik is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with O4erednik.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2014 Fomichev Dmitriy
'''


from threading import Thread
from logging import exception, debug, warning
from os.path import isfile
from struct import pack, unpack, calcsize
from time import sleep


class LogableThread(Thread):

    def __init__(self):
        super(LogableThread, self).__init__()
        self.daemon = True
        self._alive = True
        self._real_run = self.run
        self.run = self._wrap_run

    def stop(self):
        self._alive = False

    def exception(self):
        exception('Uncaught exception was occured!')
        self.stop()

    def _wrap_run(self):
        if not self._alive:
            return
        try:
            self._real_run()
        except:
            self.exception()


class FileTransfer():
    
    '''
    Header format: [char](?[integer])
    The [char] can be one of theese values:
    A =  Acknoledge of receiving data or command
    B =  Stop data transfer 
    E =  An error occured
    H =  Handshake synchronization request (if bool([integer]) == True then step-by-step mode enabled)
    P =  Next message will be portion of data with length equals to [integer]
    W =  New portion of data still not avalible. Try again after [integer] seconds
    '''
    
    FT_SIGNATURE = 455 # Just a signature, perhaps can be used in future for version control
    FT_HEADERFORMAT = 'cI'
    FT_HEADERSIZE = calcsize(FT_HEADERFORMAT)
    FT_ACKNOLEDGE = b'A'
    FT_HANDSHAKE = b'H'
    FT_PORTION = b'P'
    FT_STOP = b'B'
    FT_ERROR = b'E'
    FT_SLEEP = b'W'
    FT_NOFILE = b'N'
    

    def __init__(self, socket, blocksize=10240):
        if blocksize > 60000:
            warning("Fixed illegal block size:" + str(blocksize) + " Forsed to 60000 bytes.")
            blocksize = 60000
        self.blocksize = blocksize
        self._tcp = socket
        super(FileTransfer, self).__init__()

    def sendfile(self, path, sbs=False, alive=lambda: True,
        sleeptime=10):
        if sbs and alive() and not isfile(path):
            sleep(sleeptime-2) # Wait for file avalibility for a few seconds, but leave 2 seconds for transfer routine
        if not isfile(path): # if file still does not exists, return with non fatal error
            debug('File: ' + path + ' does not exist')
            self.answer(self.FT_NOFILE)
            return
        debug('Handshaking for ' + path)
        # Request for sending
        self._tcp.send(pack(self.FT_HEADERFORMAT, self.FT_HANDSHAKE, int(sbs)))
        self.check_answer()
        with open(path, 'rb', buffering=0) as f:
            # Sending cycle
            while alive():
                where = f.tell()
                buf = f.read(self.blocksize)
                if buf:
                    debug('Portion with len ' + str(len(buf)) + ' will be sent')
                    self._tcp.send(
                        pack(self.FT_HEADERFORMAT,self.FT_PORTION, len(buf)) + buf)
                    self.check_answer()
                    buf = None
                elif sbs:
                    self._tcp.send(pack(
                        self.FT_HEADERFORMAT,self.FT_SLEEP, sleeptime))
                    sleep(sleeptime)
                    f.seek(where)
                else:
                    break
            self.answer(self.FT_STOP)
            debug('Completed ' + path)
            
    def check_answer(self, correct_answer=FT_ACKNOLEDGE):
        answer = None
        while (not answer): #Avoiding of zero-length answer
            answer = self._tcp.recv(self.FT_HEADERSIZE)
        ack, sign = unpack(self.FT_HEADERFORMAT, answer)
        if  ack != correct_answer or sign != self.FT_SIGNATURE:
            raise Exception('Message was refused by receiver!')
            
    def answer(self, ans=FT_ACKNOLEDGE):
        self._tcp.send(pack(self.FT_HEADERFORMAT, ans, self.FT_SIGNATURE))
        

    def recvfile(self, path, alive=lambda: True):
        # Waiting for handshake
        header = self._tcp.recv(self.FT_HEADERSIZE)
        preheader, sbs = unpack(self.FT_HEADERFORMAT, header)
        if preheader == self.FT_NOFILE:
            debug('Receiving file does not exist')
            return
        if preheader != self.FT_HANDSHAKE:
            Exception('FT_HANDSHAKE expected, ' + str(preheader) + ' received')
        sbs = bool(sbs)
        debug('Got Handshake for ' + path)
        with open(path, 'wb+') as f:
            # Sending acknoledge of handshaking
            self.answer()
            while alive():
                # Wait for data portion
                header = self._tcp.recv(self.FT_HEADERSIZE)
                if not header:
                    continue
                preheader, size = unpack(self.FT_HEADERFORMAT, header)
                if preheader == self.FT_PORTION:
                    debug('Portion with size ' + str(size) + ' will be received')
                    while size > 0:
                        buff =  self._tcp.recv(size)# Perhaps there is a performance issue
                        size -= len(buff)
                        debug('Received ' + str(len(buff)) + ' bytes')
                        f.write(buff)
                        buff = None
                    if size < 0:
                        raise Exception('Size lower than 0! Should never happened!')
                    self.answer()
                elif preheader == self.FT_SLEEP:
                    debug('Sleeping... ' + str(size) + ' seconds')
                    sleep(size)
                elif preheader == self.FT_STOP:
                    debug('Completed receiving ' + path)
                    return
                elif preheader == self.FT_ERROR:
                    return
                else:
                    warning('Unexpected answer!')
                    self.answer(self.FT_ERROR)
            self.answer(self.FT_STOP)
            debug('Done ' + path)
