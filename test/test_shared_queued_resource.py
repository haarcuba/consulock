import pytest
import random
from testix.frequentlyused import *
import consulock.shared_queued_resource

consulock.shared_queued_resource.uuid = FakeObject( 'uuid' )

class FakeTime:
    def __init__( self ):
        self._time = 0
        self.sleep = FakeObject( 'sleep' )

    def set( self, time ):
        self._time = time

    def time( self ):
        return self._time

class TestSharedQueuedResource:
    def construct( self, priority, token ):
        with Scenario() as scenario:
            scenario <<\
                Call( 'uuid.uuid4' ).returns( token )
            result = consulock.shared_queued_resource.SharedQueuedResource( FakeObject( 'sharedList' ), priority )
            return result

    @pytest.fixture
    def fakeTime( self ):
        fakeTime = FakeTime()
        consulock.shared_queued_resource.time = fakeTime
        return fakeTime

    @pytest.fixture
    def token( self ):
        return random.choice( 'abcdefghijklmnopqrstuvwxyz' )

    def pollUntilMyTurnScenario( self, scenario, sharedList ):
        for _ in range( len( sharedList ) - 1 ):
            scenario <<\
                Call( 'sharedList.acquire' ).returns( sharedList ) <<\
                Call( 'sharedList.get' ).returns( sharedList ) <<\
                Call( 'sharedList.release' ).returns( sharedList ) <<\
                Call( 'sleep', IgnoreArgument() ) <<\
                Hook( sharedList.pop, 0 )

        scenario <<\
            Call( 'sharedList.acquire' ).returns( sharedList ) <<\
            Call( 'sharedList.get' ).returns( sharedList )
            # Call( 'sharedList.acquire' )
            # Call( 'sharedList.put' ).returns( sharedList[ 1: ] )
            # Call( 'sharedList.release' ) <<\

    def test_wait_my_turn_some_before_me( self, fakeTime, token ):
        tested = self.construct( 0, token )
        fakeTime.set( 120 )
        with Scenario() as scenario:
            scenario <<\
                Call( 'sharedList.append', { 'token': token, 'priority': 0, 'timestamp': 120 } )

            self.pollUntilMyTurnScenario( scenario, [ { 'token': '1', 'priority': 0, 'timestamp': 50 },
                                                      { 'token': '2', 'priority': 0, 'timestamp': 70 },
                                                      { 'token': '3', 'priority': 0, 'timestamp': 100 },
                                                      { 'token': token, 'priority': 0, 'timestamp': 120 } ] )
            tested.waitMyTurn()
