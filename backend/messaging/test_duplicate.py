from backend.messaging.duplicate import DuplicateDetector


def test_duplicate_detection():
    detector = DuplicateDetector()

    assert detector.check_and_mark("msg-1") is False
    assert detector.check_and_mark("msg-1") is True
    assert detector.check_and_mark("msg-2") is False