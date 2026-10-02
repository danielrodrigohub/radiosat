"""Regression tests using actual PCM, without audio hardware or digit injection."""
import unittest
from types import SimpleNamespace

import numpy as np
from main import DTMFDetector, StreamDTMFDetector, DTMF_FREQS, MainWindow

SR = 44100
FREQUENCIES = {digit: pair for pair, digit in DTMF_FREQS.items()}


def tone(digit, duration=.070, amplitude=.08, offset=0):
    t = np.arange(round(SR * duration)) / SR
    row, col = FREQUENCIES[digit]
    return amplitude * (np.sin(2*np.pi*(row+offset)*t + .37)
                        + np.sin(2*np.pi*(col+offset)*t + 1.13))


def sequence(digits, prefix=0, duration=.070, gap=.040, amplitude=.08, offset=0):
    chunks = [np.zeros(prefix)]
    for digit in digits:
        chunks.extend((tone(digit, duration, amplitude, offset), np.zeros(round(SR*gap))))
    chunks.append(np.zeros(4410))
    return np.concatenate(chunks).astype(np.float32)


class DetectionTests(unittest.TestCase):
    def detect(self, pcm, remote, chunk_size=2048):
        detector = StreamDTMFDetector() if remote else DTMFDetector()
        detector.set_params(freq_tol=30, rms_threshold=.008)
        digits, actions = [], []
        detector.digit_detected.connect(digits.append)
        if remote:
            detector.arm(['420590', '609700'])
            detector.action_detected.connect(actions.append)
            feed = detector.feed_samples
        else:
            detector.start_external()
            feed = detector.feed_samples
        for start in range(0, len(pcm), chunk_size):
            feed(pcm[start:start+chunk_size])
        return ''.join(digits), actions

    def test_return_with_repeated_zero_at_every_block_alignment(self):
        for remote in (False, True):
            for prefix in range(0, 2048, 137):
                with self.subTest(remote=remote, prefix=prefix):
                    digits, actions = self.detect(sequence('609700', prefix), remote)
                    self.assertEqual(digits, '609700')
                    if remote:
                        self.assertEqual(actions, ['609700'])

    def test_chunk_boundaries_levels_noise_and_frequency_shift(self):
        rng = np.random.default_rng(19)
        for remote in (False, True):
            for chunk in (257, 1024, 2048, 4096):
                pcm = sequence('420590609700', 911, amplitude=.016, offset=13)
                pcm += rng.normal(0, .002, len(pcm)).astype(np.float32)
                with self.subTest(remote=remote, chunk=chunk):
                    digits, actions = self.detect(pcm, remote, chunk)
                    self.assertEqual(digits, '420590609700')
                    if remote:
                        self.assertEqual(actions, ['420590', '609700'])

    def test_all_digits_with_short_tones_and_gaps(self):
        expected = '123A456B789C*0#D'
        for remote in (False, True):
            for prefix in (0, 529, 1637):
                with self.subTest(remote=remote, prefix=prefix):
                    pcm = sequence(expected, prefix, duration=.060, gap=.030)
                    self.assertEqual(self.detect(pcm, remote)[0], expected)

    def test_tones_mixed_with_louder_program_audio(self):
        pcm = sequence('609700', 713, duration=.100, amplitude=.025)
        t = np.arange(len(pcm)) / SR
        # A strong low-frequency component must not hide the DTMF pair.
        pcm += (.1 * np.sin(2*np.pi*110*t)).astype(np.float32)
        for remote in (False, True):
            with self.subTest(remote=remote):
                digits, actions = self.detect(pcm, remote)
                self.assertEqual(digits, '609700')
                if remote:
                    self.assertEqual(actions, ['609700'])

    def test_long_tone_with_short_dropout_is_one_digit(self):
        pcm = tone('0', .5).astype(np.float32)
        pcm[8000:8220] = 0  # 5 ms input dropout
        pcm = np.concatenate((pcm, np.zeros(4410))).astype(np.float32)
        for remote in (False, True):
            self.assertEqual(self.detect(pcm, remote)[0], '0')

    def test_noise_and_single_frequency_do_not_trigger(self):
        rng = np.random.default_rng(7)
        noise = rng.normal(0, .02, SR).astype(np.float32)
        single = (.1*np.sin(2*np.pi*697*np.arange(SR)/SR)).astype(np.float32)
        for remote in (False, True):
            self.assertEqual(self.detect(noise, remote)[0], '')
            self.assertEqual(self.detect(single, remote)[0], '')

    def test_exact_sequence_and_overlapping_prefix(self):
        for received, target, expected in (
            ('6097A00', '609700', ''),
            ('6097700', '609700', ''),
            ('1212123', '12123', '12123'),
        ):
            detector = StreamDTMFDetector()
            detector.arm(target)
            actions = []
            detector.action_detected.connect(actions.append)
            local = SimpleNamespace(_dtmf_seq_progress={})
            matches = []
            for digit in received:
                detector.feed_digit(digit)
                matched = MainWindow._matched_dtmf_sequence(local, digit, [target])
                if matched:
                    matches.append(matched)
            self.assertEqual(actions, [expected] if expected else [])
            self.assertEqual(matches, actions)

    def test_only_configured_return_can_restore_remote(self):
        returns = []
        window = SimpleNamespace(
            _dtmf_log=[], _remote_break_active=True,
            _remote_break_return_seq='609700', _remote_break_start_seq='420590',
            _return_to_remote_from_dtmf=lambda: returns.append(True),
        )
        MainWindow._remote_dtmf_action(window, '123456')
        MainWindow._remote_dtmf_action(window, '420590')
        self.assertEqual(returns, [])
        MainWindow._remote_dtmf_action(window, '609700')
        self.assertEqual(returns, [True])


if __name__ == '__main__':
    unittest.main()
