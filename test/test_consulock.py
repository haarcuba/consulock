import pytest
import uuid
from testix.frequentlyused import *
import random
import consulock

class FakeTime:
    def __init__( self ):
        self._time = 0
        self.sleep = FakeObject( 'sleep' )

    def set( self, time ):
        self._time = time

    def time( self ):
        return self._time

consulock.uuid = FakeObject( 'uuid' )

def getTuple( ** properties ):
    return random.randint( 10000, 200000 ), properties

class TestConsulLock:
    def construct( self, key, token, *, value = None, priority = 0 ):
        consulClient = FakeObject( 'consulClient' )
        with Scenario() as scenario:
            scenario <<\
                Call( 'uuid.uuid4' ).returns( token )
            tested = consulock.ConsulLock( key, consulClient, priority = priority, value = value )

        return tested

    @pytest.fixture
    def fakeTime( self ):
        fakeTime = FakeTime()
        consulock.time = fakeTime
        return fakeTime

    @pytest.fixture
    def key( self ):
        return random.choice( [ 'key1', 'key2', 'key3' ] )

    @pytest.fixture( params = [ None, 'value1', 'value2' ] )
    def value( self, request ):
        return request.param

    @pytest.fixture( params = ( 0, 1, 3, 5 ) )
    def zeroPriorityKeys( self, request, key ):
        length = request.param
        return [ key ] + [ self.priorityKey( key, uuid.uuid4(), 0 ) for _ in range( length ) ]

    @pytest.fixture
    def sessionId( self ):
        return str( uuid.uuid4() )

    @pytest.fixture
    def token( self ):
        return uuid.uuid4()

    def priorityKey( self, key, token, priority ):
        return '{key}/{token}/{priority}'.format( key = key, token = token, priority = priority )

    def scanPrioritiesScenario( self, scenario, key, myPriorityKey, priorityKeys ):
        SOME_INDEX = 239432
        priorityKeys.append( myPriorityKey )
        scenario <<\
            Call( 'consulClient.kv.get', key, keys = True ).returns( ( SOME_INDEX, priorityKeys ) )

    def putPriorityKeyScenario( self, scenario, key, token, priority ):
        priorityKey = self.priorityKey( key, token, priority )
        scenario <<\
            Call( 'consulClient.kv.put', priorityKey, None ).returns( True )
        return scenario

    def test_acquire_happy_flow( self, fakeTime, key, value, sessionId, token, zeroPriorityKeys ):
        tested = self.construct( key, token, value = value )
        priorityKey = self.priorityKey( key, token, 0 )
        with Scenario() as scenario:
            self.queryLockScenario( scenario, key, None )
            assert tested.locked() == False

            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId )
            self.putPriorityKeyScenario( scenario, key, token, 0 )

            self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )

            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )
            self.deletePriorityKeyScenario( scenario, key, token, 0 )

            assert tested.acquire() == True
            self.queryLockScenario( scenario, key, sessionId )
            assert tested.locked() == True

    def queryLockScenario( self, scenario, key, sessionId ):
        if sessionId:
            scenario <<\
                Call( 'consulClient.kv.get', key ).returns( getTuple( Key = key, Session = sessionId ) )
        else:
            scenario <<\
                Call( 'consulClient.kv.get', key ).returns( getTuple( Key = key ) )

    def test_acquire_after_some_retries( self, fakeTime, key, value, sessionId, token, zeroPriorityKeys ):
        tested = self.construct( key, token, value = value )
        priorityKey = self.priorityKey( key, token, 0 )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId )
            self.putPriorityKeyScenario( scenario, key, token, 0 )
            for _ in range( 100 ):
                self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )
                scenario <<\
                    Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                    Call( 'sleep', IgnoreArgument() )

            self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )
            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )
            self.deletePriorityKeyScenario( scenario, key, token, 0 )

            assert tested.acquire() == True

    def test_acquire_yield_to_higher_priority( self, fakeTime, key, value, sessionId, token, zeroPriorityKeys ):
        tested = self.construct( key, token, value = value )
        priorityKey = self.priorityKey( key, token, 0 )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId )
            self.putPriorityKeyScenario( scenario, key, token, 0 )
            for _ in range( 100 ):
                self.scanPrioritiesScenario( scenario, key, priorityKey, [ '{}/tokenA/1'.format( key ) ] + zeroPriorityKeys )
                scenario <<\
                    Call( 'sleep', IgnoreArgument() )

            self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )
            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )
            self.deletePriorityKeyScenario( scenario, key, token, 0 )

            assert tested.acquire() == True

    def deletePriorityKeyScenario( self, scenario, key, token, priority ):
        priorityKey = self.priorityKey( key, token, priority )
        scenario <<\
            Call( 'consulClient.kv.delete', priorityKey ).returns( True )

    def test_acquire_yields_to_higher_priority_and_fails_due_to_timeout( self, fakeTime, key, value, sessionId, token, zeroPriorityKeys ):
        tested = self.construct( key, token, value = value )
        priorityKey = self.priorityKey( key, token, 0 )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId )
            self.putPriorityKeyScenario( scenario, key, token, 0 )
            self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )
            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( fakeTime.set, 1 )
            self.scanPrioritiesScenario( scenario, key, priorityKey, [ '{}/tokenA/1'.format( key ) ] + zeroPriorityKeys )
            scenario <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( fakeTime.set, 6 )
            self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )
            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( fakeTime.set, 10 )
            self.deletePriorityKeyScenario( scenario, key, token, 0 )
            scenario <<\
                Call( 'consulClient.session.destroy', sessionId )

            assert tested.acquire( timeout = 9 ) == False

    def test_get_info_api( self, key, value, token  ):
        tested = self.construct( key, token, value = value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.kv.get', key ).returns( getTuple( Key = key, Session = 'some-session-uuid', Value = b'Some Value' ) )

            assert tested.value() == b'Some Value'

    def test_get_info_and_locked_api_if_key_not_exist( self, key, value, token  ):
        tested = self.construct( key, token, value = value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.kv.get', key ).returns( ( 10934890, None ) )

            assert tested.locked() == False

            scenario <<\
                Call( 'consulClient.kv.get', key ).returns( ( 10934890, None ) )
            assert tested.value() is None

    def test_acquire_and_release( self, fakeTime, key, value, sessionId, token, zeroPriorityKeys ):
        tested = self.construct( key, token, value = value )
        priorityKey = self.priorityKey( key, token, 0 )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId )
            self.putPriorityKeyScenario( scenario, key, token, 0 )
            self.scanPrioritiesScenario( scenario, key, priorityKey, zeroPriorityKeys )
            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )
            self.deletePriorityKeyScenario( scenario, key, token, 0 )

            assert tested.acquire() == True

            scenario <<\
                Call( 'consulClient.kv.put', key, value, release = sessionId ).returns( 'whatever' )
            self.deletePriorityKeyScenario( scenario, key, token, 0 )
            scenario <<\
                Call( 'consulClient.session.destroy', sessionId )

            assert tested.release() == 'whatever'
