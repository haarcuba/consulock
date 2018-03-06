from . import lock
import json

class SharedResource:
    def __init__( self, consulClient, key ):
        self._key = key
        self._consul = consulClient
        lockKey = '{}/lock'.format( key )
        self._queueKey = '{}/queue'.format( key )
        self._lock = lock.Lock( lockKey, consulClient )
        self._ensureQueueExists()

    def _ensureQueueExists( self ):
        self._lock.acquire( timeout = 3 * 60 )
        _, value = self._consul.kv.get( self._queueKey )
        if value is None:
            self._consul.kv.put( self._queueKey, value = json.dumps( [] ) )
        self._lock.release()
