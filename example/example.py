import consulock.lock
import logging
import random
import time
import consul
import sys

logging.basicConfig( format = '{} %(message)s %(created)f'.format( sys.argv[1] ), level = logging.INFO )

c = consul.Consul( host='localhost' )
l = consulock.lock.Lock( 'xxx/lockme', c, value = sys.argv[1] )


result = None

for i in range( 10 ):
    try:
        time.sleep( random.random() * 2 )
        result = l.acquire( timeout = 1, interval = 0.3 )
        if result:
            logging.info( 'mine' )
        time.sleep( random.random() * 2 )
    finally:
        if result:
            l.release()
            logging.info( 'released' )
