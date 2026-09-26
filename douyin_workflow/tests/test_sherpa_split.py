import pytest

np = pytest.importorskip("numpy")  # 属于可选依赖 .[lite]

from douyin_workflow.transcribe import split_points  # noqa: E402


def test_short_audio_not_split():
    assert split_points(np.zeros(16000 * 20, dtype=np.float32)) == [0, 16000 * 20]


def test_cut_lands_on_quiet_point():
    sr = 16000
    x = np.ones(sr * 70, dtype=np.float32)
    x[int(sr * 27.0): int(sr * 27.2)] = 0.0  # 唯一的安静段
    cuts = split_points(x, sr)
    assert cuts[0] == 0 and cuts[-1] == len(x)
    assert abs(cuts[1] / sr - 27.0) < 0.1
    assert all(b - a <= sr * 30 for a, b in zip(cuts, cuts[1:]))
