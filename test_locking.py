
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import threading
import time

# Mock the waveshare library before importing tracker
sys.modules['spidev'] = MagicMock()
sys.modules['gpiozero'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

# Add project root to path
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import tracker

class TestHabitTrackerLocking(unittest.TestCase):
    @patch('tracker.epd2in13_V4.EPD')
    @patch('tracker.database')
    def test_concurrent_updates_locked(self, mock_db, mock_epd_class):
        mock_epd = mock_epd_class.return_value
        ht = tracker.HabitTracker()
        
        # Track if multiple calls are active
        active_calls = 0
        max_active = 0
        lock_count = 0
        
        def slow_draw(epd):
            nonlocal active_calls, max_active, lock_count
            active_calls += 1
            lock_count += 1
            max_active = max(max_active, active_calls)
            time.sleep(0.1)
            active_calls -= 1

        # Replace draw_stats with our slow version
        with patch('tracker.draw_stats', side_effect=slow_draw):
            threads = []
            for _ in range(3):
                t = threading.Thread(target=ht.update)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
        
        # If locked correctly, active_calls should never have been > 1
        self.assertEqual(max_active, 1)
        self.assertEqual(lock_count, 3)
        # Verify init and sleep called 3 times each
        self.assertEqual(mock_epd.init.call_count, 3)
        self.assertEqual(mock_epd.sleep.call_count, 3)

if __name__ == '__main__':
    unittest.main()
