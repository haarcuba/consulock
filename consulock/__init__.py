import time

class ConsulLock:
    def __init__( self, key, consulClient, *, value = None ):
        self._key = key
        self._consul = consulClient
        self._value = value
        self._status = 'unlocked'
        self._sessionId = None

    @property
    def key( self ):
        return self._key

    @property
    def status( self ):
        return self._status

    def acquire( self, *, timeout = None, interval = 1 ):
        ONE_DAY = 24 * 3600
        self._sessionId = self._consul.session.create( ttl = ONE_DAY )
        start = time.time()
        while True:
            result = self._consul.kv.put( self._key, self._value, acquire = self._sessionId )
            if result:
                self._status = 'locked'
                return True

            now = time.time()
            if timeout:
                if now - start > timeout:
                    return False

            time.sleep( interval )


    def release( self ):
        result = self._consul.kv.put( self._key, self._value, release = self._sessionId )
        self._consul.session.destroy( self._sessionId )
        self._sessionId = None
        self._status = 'unlocked'
        return result
