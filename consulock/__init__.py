import time
import logging
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
        self._priority = priority

    def _putPriorityKey( self ):
        self._consul.kv.put( self._priorityKey(), None )

    def _deletePriorityKey( self ):
        self._consul.kv.delete( self._priorityKey() )

    def _priorityKey( self ):
        return '{}/{}/{}'.format( self._key, self._token, self._priority )

    @property
    def key( self ):
        return self._key

    def acquire( self, *, timeout = None, interval = 1 ):
        ONE_DAY = 24 * 3600
        self._sessionId = self._consul.session.create( ttl = ONE_DAY )
        self._putPriorityKey()
        start = time.time()
        while True:
            now = time.time()
            if timeout:
                if now - start > timeout:
                    self._cleanup()
                    return False

            if self._shouldYield():
                logging.debug( 'yielding to higher priority' )
                time.sleep( interval )
                continue

            logging.debug( 'try to get lock {} => {}'.format( self._key, self._value ) )
            result = self._consul.kv.put( self._key, self._value, acquire = self._sessionId )
            if result:
                return True

            time.sleep( interval )

    def _shouldYield( self ):
        _, keys = self._consul.kv.get( self._key, keys = True )
        higherPriority = lambda key: int( key.split( '/' )[ -1 ] ) > self._priority
        return any( [ higherPriority( key ) for key in keys ] )

    def _destroySession( self ):
        with contextlib.suppress( consul.base.ConsulException ):
            if self._sessionId is not None:
                self._consul.session.destroy( self._sessionId )
            self._sessionId = None

    def _cleanup( self ):
        self._deletePriorityKey()
        self._destroySession()

    def release( self ):
        result = self._consul.kv.put( self._key, self._value, release = self._sessionId )
        self._cleanup()
        return result
