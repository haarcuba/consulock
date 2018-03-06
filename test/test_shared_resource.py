import pytest
import json
import random
from testix.frequentlyused import *
import consulock.shared_resource

consulock.shared_resource.lock = FakeObject( 'lock' )

class TestSharedResource:
    def construct( self, key, initialQueue ):
        with Scenario() as scenario:
            scenario <<\
                Call( 'lock.Lock', self.lockKey( key ), FakeObject( 'consulClient' ) ).returns( FakeObject( 'aLock' ) )
            self.checkQueueExistsScenario( scenario, key, initialQueue )
            result = consulock.shared_resource.SharedResource( FakeObject( 'consulClient' ), key )
        return result

    @pytest.fixture
    def key( self ):
        return random.choice( 'abcdefghijklmnopqrstuvwxyz' )

    def lockKey( self, key ):
        return '{}/lock'.format( key )

    def queueKey( self, key ):
        return '{}/queue'.format( key )

    def checkQueueExistsScenario( self, scenario, key, initialQueue ):
        scenario <<\
            Call( 'aLock.acquire', timeout = IgnoreArgument() ).returns( True ) <<\
            Call( 'consulClient.kv.get', self.queueKey( key ) ).returns( ( 1, initialQueue ) )
        if initialQueue is None:
            scenario << Call( 'consulClient.kv.put', self.queueKey( key ), value = json.dumps( [] ) ).returns( ( 1, None ) )
        scenario << Call( 'aLock.release' )

    @pytest.fixture( params = [ None, json.dumps( [ ( 'a', 0 ), ( 'b', 0 ) ] ) ] )
    def initialQueue( self, request ):
        return request.param

    def test_construct_check_queue_exists_create_if_not( self, key, initialQueue ):
        tested = self.construct( key, initialQueue )
