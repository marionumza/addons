from .common import RequestCase, freeze_time


class TestDeadlineState(RequestCase):

    def test_deadline_state_1(self):
        self.request_1.deadline_date = '2020-03-17'

        with freeze_time('2020-03-16'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'ok')

        with freeze_time('2020-03-17'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'today')

        with freeze_time('2020-03-18'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'overdue')

    def test_deadline_state_2(self):
        self.request_1.deadline_date = '2020-03-17'

        with freeze_time('2020-03-16'):
            self.request_1.stage_id = self.stage_sent
            self.request_1.stage_id = self.stage_confirmed
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'ok')

        with freeze_time('2020-03-18'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'ok')

    def test_deadline_state_3(self):
        self.request_1.deadline_date = '2020-03-17'

        with freeze_time('2020-03-17'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'today')

            self.request_1.stage_id = self.stage_sent
            self.request_1.stage_id = self.stage_confirmed
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'ok')

        with freeze_time('2020-03-18'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'ok')

    def test_deadline_state_4(self):
        self.request_1.deadline_date = '2020-03-17'

        with freeze_time('2020-03-18'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'overdue')

            self.request_1.stage_id = self.stage_sent
            self.request_1.stage_id = self.stage_confirmed
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'overdue')

        with freeze_time('2020-03-19'):
            self.request_1.invalidate_cache()
            self.assertEqual(self.request_1.deadline_state, 'overdue')
