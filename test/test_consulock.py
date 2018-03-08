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

class TestConsulLock:
    def construct( self, key, value = None ):
        consulClient = FakeObject( 'consulClient' )
        return consulock.ConsulLock( key, consulClient, value = value )

    @pytest.fixture
    def fakeTime( self ):
        fakeTime = FakeTime()
        consulock.time = fakeTime
        return fakeTime

    @pytest.fixture
    def key( self ):
        return random.choice( [ 'key1', 'key2', 'key3' ] )

    @pytest.fixture
    def value( self ):
        return random.choice( [ None, 'value1', 'value2' ] )

    @pytest.fixture
    def sessionId( self ):
        return str( uuid.uuid4() )

    def test_acquire_happy_flow( self, fakeTime, key, value, sessionId ):
        tested = self.construct( key, value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId ) <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )

            assert tested.acquire() == True

    def test_acquire_after_some_retries( self, fakeTime, key, value, sessionId ):
        tested = self.construct( key, value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId )
            for _ in range( 100 ):
                scenario <<\
                    Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                    Call( 'sleep', IgnoreArgument() )

            scenario <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )

            assert tested.acquire() == True

    def test_acquire_fails_due_to_timeout( self, fakeTime, key, value, sessionId ):
        tested = self.construct( key, value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId ) <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( fakeTime.set, 1 ) <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( fakeTime.set, 6 ) <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( False ) <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( fakeTime.set, 10 )

            assert tested.acquire( timeout = 9 ) == False

    def test_acquire_happy_flow( self, fakeTime, key, value, sessionId ):
        tested = self.construct( key, value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId ) <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True )

            assert tested.acquire() == True

    def test_acquire_and_release( self, fakeTime, key, value, sessionId ):
        tested = self.construct( key, value )
        with Scenario() as scenario:
            scenario <<\
                Call( 'consulClient.session.create', ttl = IgnoreArgument() ).returns( sessionId ) <<\
                Call( 'consulClient.kv.put', key, value, acquire = sessionId ).returns( True ) <<\
                Call( 'consulClient.kv.put', key, value, release = sessionId ).returns( 'whatever' ) <<\
                Call( 'consulClient.session.destroy', sessionId )

            assert tested.acquire() == True
            assert tested.release() == 'whatever'
