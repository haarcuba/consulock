import time
import uuid
import contextlib
import consul.base

class ConsulLock:
    def __init__( self, key, consulClient, *, value = None, priority = 0 ):
        self._key = key
        self._consul = consulClient
        self._value = value
        self._sessionId = None
        self._token = uuid.uuid4()
        self._priorityKey = '{}/{}/{}'.format( key, self._token, priority )
        self._consul.kv.put( self._priorityKey, None )

    @property
    def key( self ):
        return self._key

    def acquire( self, *, timeout = None, interval = 1 ):
        ONE_DAY = 24 * 3600
        self._sessionId = self._consul.session.create( ttl = ONE_DAY )
        start = time.time()
        while True:
            now = time.time()
            if timeout:
                if now - start > timeout:
                    return False

            self._consul.kv.get( self._key, keys = True )
            result = self._consul.kv.put( self._key, self._value, acquire = self._sessionId )
            if result:
                return True

            time.sleep( interval )

    def _destroySession( self ):
        with contextlib.suppress( consul.base.ConsulException ):
            if self._sessionId is not None:
                self._consul.session.destroy( self._sessionId )
            self._sessionId = None

    def release( self ):
        result = self._consul.kv.put( self._key, self._value, release = self._sessionId )
        self._destroySession()
        return result
