#!/usr/bin/env python
#-*-coding: utf-8-*-

# Version: 0.1
# Author: Don Li <donne.cn@gmail.com>
# License: Copyright(c) 2013 Don.Li
# Summary: 

from twisted.internet import reactor, protocol, defer
from twisted.protocols import basic
from twisted.protocols.policies import TimeoutMixin
from twisted.python import failure
from log import log
from os import listdir
import struct
import traceback
from gemsgpack import dumps, loads
#from json import dumps, loads
from array import array
import sys
from random import randint

TCP_REQ = 0 
TCP_ACK = 1 
MAX_BODY_LENGTH = 131072 #128 * 1024 Bytes

HANDLERS = {}
_DEFAULT_PROXY = None

def load_all_handlers(root, module):
    _imported = []

    for f in listdir(root + module):
        if f.startswith('.') or f.startswith('_'):
            continue

        _subfix = ''
        if f.find('.pyc') > 0:
            _subfix = '.pyc'
        elif f.find('.pyo') > 0:
            _subfix = '.pyo'
        elif f.find('.py') > 0:
            _subfix = '.py'
        else:
            continue

        fname, _ = f.rsplit(_subfix, 1)
        if fname and fname not in _imported:
            _handlers_name = '%s.%s' % (module, fname)
            try:
                __import__(_handlers_name)
            except Exception, e:
                log.error('[ load_all_handlers ]Error when load handler:', root, f, _handlers_name, 'Detail:', str(e))
                traceback.print_exc()
                raise e
                break
            _imported.append(fname)

    log.info('All handler loaded.', _imported)

def route(**options):
    def decorator(handler):
        global _DEFAULT_PROXY

        msgid = options.pop('msgid', handler.__name__)
        if msgid == '*' and not _DEFAULT_PROXY:
            _DEFAULT_PROXY = handler
        elif not HANDLERS.has_key(msgid):
            HANDLERS[msgid] = handler
        else:
            raise Exception('[ ERROR ]Handler "%s" exists already!!' % msgid)
        return handler
    return decorator

#return: handler, need_proxy
def get_handler(msgid):
    if HANDLERS.has_key( msgid ):
        return HANDLERS[msgid], False
    elif _DEFAULT_PROXY:
        return _DEFAULT_PROXY, True
    else:
        return None, False

def inc_seq(seq):
    seq += 1
    if seq >= sys.maxint:
        seq = 1 
    return seq

class GeminiRPCProtocol(protocol.Protocol, TimeoutMixin):
    HEADER_FORMAT   = '!bii'
    HEADER_LENGTH   = struct.calcsize(HEADER_FORMAT)
    TIMEOUT         = 600

    def __init__(self, *args, **kwargs):
        self.seq = 0
        self.buff = ''
        #self.buff = array('c')
        self.deferreds = {}
        self.uid = 0
        self.nickname = ""
        self.session_key = ""
        self.lose_connect = True

    def timeoutConnection(self):
        #self.factory.onConnectionTimeout(self)
        for d in self.deferreds.itervalues():
            d.errback(Exception("timeout"))
        self.deferreds = {}

        self.transport.unregisterProducer()
        self.transport.loseConnection()
        log.warn("[ timeoutConnection ]peer:", self.transport.getPeer(), 'TIMEOUT:', self.TIMEOUT)

    def send(self, func, args=None):
        self.resetTimeout()
        if self.transport and func:
            obj = (func, args)
            data = dumps(obj)

            body_length = len(data)
            _header = struct.pack(self.HEADER_FORMAT, TCP_REQ, self.seq, body_length)
            try:
                self.transport.write(_header + data)
                log.debug("[ SEND ]:func:%s, body_length:%d, to:%s" % (func, body_length, self.transport.getPeer()))
            except:
                self.transport.loseConnection()
        else:
            log.warn("[ SEND ]:unknown args client:%s or func:%s." % (self.transport.getPeer(), func))

        self.resetTimeout()

    def call(self, func, args=None):
        self.resetTimeout()
        _d = defer.Deferred()

        if self.transport and func:
            obj = (func, args)
            data = dumps(obj)

            body_length = len(data)
            self.seq = inc_seq(self.seq)
            self.deferreds[self.seq]= _d

            _header = struct.pack(self.HEADER_FORMAT, TCP_REQ, self.seq, body_length)
            try:
                self.transport.write(_header + data)
                log.debug("[ CALL ]:ar_id:%d, func:%s, body_length:%d, to:%s" % (self.seq, func, body_length, self.transport.getPeer()))
            except:
                self.transport.loseConnection()
                _d.errback(Exception("call failed"))
        else:
            log.warn("[ CALL ]:unknown args client:%s or func:%s." % (self.transport.getPeer(), func))
            _d.errback(Exception("call failed"))

        self.resetTimeout()

        return _d

    def connectionMade(self):
        log.debug("[ connectionMade ]:", self.transport.getPeer())
        self.setTimeout(self.TIMEOUT)

    def dataReceived(self, data):
        #log.debug('[ dataReceived ]:', repr(data))
        self.buff += data
        #self.buff.extend( data )
        buff_length = len(self.buff)
        buff = self.buff

        while buff_length >= self.HEADER_LENGTH:
            try:
                ack, ar_id, body_length = struct.unpack(self.HEADER_FORMAT, buff[:self.HEADER_LENGTH])
                assert body_length <= MAX_BODY_LENGTH and body_length > 0, 'body length error. from %s.' % (body_length, self.transport.getPeer())
            except Exception, msg:
                log.warn('1. Un-supported message. buff_length:{0}, body_length: {1}, msg:{2}.'.format(buff_length, body_length, msg))
                self.buff = ''
                break

            _msg_end_pos = self.HEADER_LENGTH + body_length

            if buff_length >= _msg_end_pos:
                #log.debug("[ RECV ]:ar_id:%d, body_length:%d, buffer:%s, from:%s" % ( ar_id, body_length, repr(buff[self.HEADER_LENGTH:_msg_end_pos]), self.transport.getPeer()))
                log.debug("[ RECV ]:ar_id:%d, buff_length:%d, body_length:%d, from:%s" % ( ar_id, buff_length, body_length, self.transport.getPeer()))

                _body = loads(buff[self.HEADER_LENGTH:_msg_end_pos]) #, ensure_ascii=Falssee)
                #_body = loads(buff[self.HEADER_LENGTH:_msg_end_pos].tostring()) #, ensure_ascii=Falssee)

                self.buff = buff = buff[_msg_end_pos:]
                buff_length = len(self.buff)

                if ack:
                    _d = self.deferreds.pop(ar_id, None)
                    if _d:
                        _state, _body = _body
                        _result, _reason = _state
                        if not _reason:
                            _d.callback(_body)
                        else:
                            _d.errback(Exception("Error No:%s, Reason:%s." % (_result, _reason)))
                    else:
                        log.warn("Unknown ar_id: %d, body:%s, all:%s." % (ar_id, _body, self.deferreds.keys()))
                else:
                    self.process(ar_id, _body)
            else:
                break

        self.resetTimeout()

    def process(self, ar_id, body):
        self.resetTimeout()
        state = 1, 'unknown'
        result = state[1]

        try:
            request_data = None
            if len(body) == 1:
                _handler_name, = body
                _request       = None
            else:
                _handler_name, _request = body
                try:
                    request_data = str(_request)[0:100]
                except:
                    pass

            _handler, need_proxy = get_handler( _handler_name )

            log.debug("[ PROCESS ]:ar_id:%d, handler:%s, request:%s, H:%s, from:%s." % (ar_id, _handler_name,
                request_data, _handler, self.transport.getPeer()))

            if _handler:
                state = 0, ''
                if need_proxy:
                    _request = _handler_name, _request

                defer.maybeDeferred(_handler, self, _request).addBoth(self.ack, ar_id, state)
                return
            else:
                state = 1, ('No such handler: %s' % _handler_name) 
                log.warn('[ ALL handlers: ]', state, HANDLERS.keys())
                result = state[1]
        except Exception, msg:
            log.error('error body: {0}.'.format( body ))
            traceback.print_exc()
            state = 1, str(msg)[:128]
            result = state[1]

        if result is not None and ar_id:
            self.ack(result, ar_id, state)

    def ack(self, result, ar_id, state):
        self.resetTimeout()
        if result is None:
            #log.debug('[ ACK ]result is None, nothing need to ack.')
            return
        if isinstance(result, failure.Failure):
            result.printTraceback()
            state = 1, result.getErrorMessage()
            data = dumps((state, None))
            #data = dumps((state, None), ensure_ascii=False)
            ack_data = (state, None) 
        else:
            try:
                ack_data = (state, str(result)[:1000])
                data = dumps((state, result))
                #data = dumps((state, result), ensure_ascii=False)
            except Exception, e:
                traceback.print_exc()
                state = 2, str(e)
                data = dumps((state, None))
                #data = dumps((state, None), ensure_ascii=False)
                ack_data = (state, None) 

        body_length = len(data)
        _header = struct.pack(self.HEADER_FORMAT, TCP_ACK, ar_id, body_length)
        self.transport.write(_header + data)

        log.debug("[ ACK ]:ar_id:%d, body_length:%d, data:%s, to:%s." % (ar_id, body_length, ack_data, self.transport.getPeer()))

    def connectionLost(self, reason):
        log.debug('[ connectionLost ]lost from:', self.transport.getPeer(), reason.getErrorMessage())
        self.setTimeout(None)

        if hasattr(self.factory, 'onConnectionLost') and self.lose_connect:
            self.factory.onConnectionLost(self)


class GeminiRPCFactory(protocol.ServerFactory):
    protocol = GeminiRPCProtocol

class ConnectorCreator(protocol.ClientCreator):
    def __init__(self, service, *args, **kwargs):
        self.factory = service
        protocol.ClientCreator.__init__(self, reactor, GeminiRPCProtocol, *args, **kwargs)

    def connect(self, host, port, timeout = 30):
        return self.connectTCP(host, port, timeout = timeout).addCallbacks(self.callback, self.errback)

    def callback(self, p):
        p.factory = self.factory
        return p

    def errback(self, error):
        log.error("Can't connect Server!", error)

def main():
    f = GeminiRPCFactory()
    reactor.listenTCP(8888, f)
    reactor.run()


if __name__ == '__main__':main()
