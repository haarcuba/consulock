import uuid
import time

class SharedQueuedResource:
    def __init__( self, sharedList, priority ):
        self._sharedList = sharedList
        self._priority = priority
        self._token = uuid.uuid4()

    def waitMyTurn( self ):
        now = time.time()
        self._sharedList.append( { 'token': self._token, 'priority': self._priority, 'timestamp': now } )
        while True:
            queue = self._sharedList.acquire()
            queue = self._sharedList.get()
            if queue[ 0 ][ 'token' ] == self._token:
                return
            queue = self._sharedList.release()
            time.sleep( 1 )
