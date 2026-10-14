"""Unit tests for the global call timeline shared by all mock instances."""
import unittest
from unittest.mock import DEFAULT

from _mock_core import (
    build_recording_mock,
    CallInspectionMixin,
    GLOBAL_CALL_TIMELINE,
)
from MockCallOrder import MockCallOrder


class _Host(CallInspectionMixin):
    """Minimal host library keying mocks by the keyword name as written."""

    def __init__(self):
        self._mocks = {}


class TestGlobalCallOrder(unittest.TestCase):
    """Tests for get_global_call_order and reset_global_call_order."""

    def setUp(self):
        """Start every test from an empty timeline."""
        GLOBAL_CALL_TIMELINE.clear()
        self.host = _Host()
        self.order = MockCallOrder()

    def tearDown(self):
        """Leave no entries behind for the next test."""
        GLOBAL_CALL_TIMELINE.clear()

    def test_records_calls_across_separate_instances(self):
        """The whole point: ordering calls made through different instances."""
        alarm = build_recording_mock('alarm-handler.resource', 'Wait For Alarm')
        scale = build_recording_mock('kubelibrary.resource', 'Scale Deployment')
        alarm()
        scale()
        scale()
        alarm()
        self.assertEqual(
            self.order.get_global_call_order(),
            ['Wait For Alarm', 'Scale Deployment', 'Scale Deployment', 'Wait For Alarm'],
        )

    def test_qualified_names_carry_the_target(self):
        """Qualifying disambiguates one keyword name mocked on two targets."""
        first = build_recording_mock('a.resource', 'Run')
        second = build_recording_mock('b.resource', 'Run')
        first()
        second()
        self.assertEqual(self.order.get_global_call_order(qualified=True),
                         ['a.resource.Run', 'b.resource.Run'])
        self.assertEqual(self.order.get_global_call_order(), ['Run', 'Run'])

    def test_reading_the_order_does_not_consume_it(self):
        """The timeline is a record, not a queue."""
        build_recording_mock('lib', 'Kw')()
        self.assertEqual(self.order.get_global_call_order(), ['Kw'])
        self.assertEqual(self.order.get_global_call_order(), ['Kw'])

    def test_returned_list_is_a_copy(self):
        """A caller cannot corrupt the record by mutating what it was given."""
        build_recording_mock('lib', 'Kw')()
        self.order.get_global_call_order().append('Injected')
        self.assertEqual(self.order.get_global_call_order(), ['Kw'])

    def test_reset_clears_the_order(self):
        """Reset Global Call Order forgets everything recorded so far."""
        build_recording_mock('lib', 'Kw')()
        self.order.reset_global_call_order()
        self.assertEqual(self.order.get_global_call_order(), [])

    def test_uncalled_keywords_do_not_appear(self):
        """Mocking alone records nothing - only calls do."""
        build_recording_mock('lib', 'Never Called')
        self.assertEqual(self.order.get_global_call_order(), [])

    def test_per_instance_reset_does_not_clear_the_global_order(self):
        """Resetting one instance must not discard another instance's history.

        The timeline spans instances, so tying it to any single instance's
        Reset Mocks would make a two-instance assertion depend on reset order.
        """
        build_recording_mock('lib', 'Kw')()
        self.host._reset_call_order()  # pylint: disable=protected-access
        self.assertEqual(self.order.get_global_call_order(), ['Kw'])


class TestRecordingMockKeepsMockSemantics(unittest.TestCase):
    """The recording hook must not disturb any unittest.mock behaviour.

    These pin the behaviours that re-implementing side_effect inside a wrapper
    would have broken, and would catch a future change to the ``_mock_call``
    hook point.
    """

    def setUp(self):
        GLOBAL_CALL_TIMELINE.clear()
        self.host = _Host()
        self.order = MockCallOrder()

    def tearDown(self):
        GLOBAL_CALL_TIMELINE.clear()

    def test_return_value_is_returned(self):
        """A plain return_value still answers the call."""
        self.assertEqual(build_recording_mock('lib', 'Kw', return_value=42)(), 42)

    def test_side_effect_list_yields_one_value_per_call(self):
        """A list side_effect is consumed in order, as unittest.mock does."""
        mock = build_recording_mock('lib', 'Kw', side_effect=['first', 'second'])
        self.assertEqual([mock(), mock()], ['first', 'second'])
        self.assertEqual(self.order.get_global_call_order(), ['Kw', 'Kw'])

    def test_side_effect_exception_is_raised(self):
        """An exception in a side_effect list is raised, not returned."""
        mock = build_recording_mock('lib', 'Kw',
                                    side_effect=[RuntimeError('boom'), 'ok'])
        with self.assertRaisesRegex(RuntimeError, 'boom'):
            mock()
        self.assertEqual(mock(), 'ok')
        # The failed call is still a call, so it has to appear in the order.
        self.assertEqual(self.order.get_global_call_order(), ['Kw', 'Kw'])

    def test_side_effect_callable_result_is_returned(self):
        """A callable side_effect's result wins over return_value."""
        mock = build_recording_mock('lib', 'Kw', return_value='unused',
                                    side_effect=lambda *a, **k: 'from side effect')
        self.assertEqual(mock(), 'from side effect')

    def test_side_effect_callable_returning_default_falls_back(self):
        """Returning DEFAULT defers to return_value, as unittest.mock defines."""
        mock = build_recording_mock('lib', 'Kw', return_value='fallback',
                                    side_effect=lambda *a, **k: DEFAULT)
        self.assertEqual(mock(), 'fallback')

    def test_side_effect_callable_receives_the_arguments(self):
        """The call's arguments reach a callable side_effect untouched."""
        seen = {}

        def record(*args, **kwargs):
            seen['args'] = args
            seen['kwargs'] = kwargs

        build_recording_mock('lib', 'Kw', side_effect=record)('a', b='c')
        self.assertEqual(seen, {'args': ('a',), 'kwargs': {'b': 'c'}})

    def test_call_history_is_still_recorded(self):
        """The host's own inspection keywords keep working on the mock."""
        mock = build_recording_mock('lib', 'Kw')
        mock('arg', key='value')
        self.host._mocks['Kw'] = mock  # pylint: disable=protected-access
        self.assertEqual(self.host.get_keyword_call_count('Kw'), 1)
        self.assertEqual(self.host.get_keyword_call_args('Kw'), ['arg'])
        self.assertEqual(self.host.get_keyword_call_kwargs('Kw'), {'key': 'value'})

    def test_per_instance_order_still_works(self):
        """Attaching to the instance manager is unaffected by the hook."""
        first = build_recording_mock('lib', 'First')
        second = build_recording_mock('lib', 'Second')
        self.host._track_call_order('First', first)  # pylint: disable=protected-access
        self.host._track_call_order('Second', second)  # pylint: disable=protected-access
        second()
        first()
        self.assertEqual(self.host.get_keyword_call_order(), ['Second', 'First'])

    def test_is_not_a_descriptor(self):
        """Assigning it to a class attribute must not bind it as a method.

        MockLibrary installs the mock on the owning class. A plain function
        there would receive ``self`` as its first argument; a Mock instance
        does not.
        """
        mock = build_recording_mock('lib', 'Kw', return_value='value')
        owner_class = type('_Owner', (), {'method': mock})
        self.assertEqual(owner_class().method('only-arg'), 'value')
        self.assertEqual(mock.call_args_list[0].args, ('only-arg',))


if __name__ == '__main__':
    unittest.main()
