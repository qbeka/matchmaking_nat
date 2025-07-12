import pytest

from app.scoring.bayes import SkillPosterior


def test_initialization():
    posterior = SkillPosterior()
    assert posterior.alpha == 1.0
    assert posterior.beta == 1.0
    assert posterior.mean == 0.5
    assert posterior.std_dev == pytest.approx(0.288, abs=1e-3)

    with pytest.raises(ValueError):
        SkillPosterior(alpha=0)
    with pytest.raises(ValueError):
        SkillPosterior(beta=-1)


def test_update():
    posterior = SkillPosterior()
    posterior.update(3, 2)
    assert posterior.alpha == 4.0
    assert posterior.beta == 3.0
    assert posterior.mean == pytest.approx(0.571, abs=1e-3)

    with pytest.raises(ValueError):
        posterior.update(-1, 0)


def test_update_from_self_rating():
    posterior = SkillPosterior()
    posterior.update_from_self_rating(4)
    assert posterior.alpha == 5.0
    assert posterior.beta == 2.0
    assert posterior.mean == pytest.approx(0.714, abs=1e-3)

    with pytest.raises(ValueError):
        posterior.update_from_self_rating(6)


def test_posterior_convergence():
    posterior = SkillPosterior()
    initial_std_dev = posterior.std_dev
    posterior.update(10, 2)
    assert posterior.std_dev < initial_std_dev
    posterior.update(10, 2)
    assert posterior.std_dev < initial_std_dev
    assert posterior.mean > 0.8


def test_contradictory_evidence():
    posterior = SkillPosterior()
    posterior.update(10, 0)
    high_confidence_mean = posterior.mean
    posterior.update(0, 10)
    assert posterior.mean < high_confidence_mean
    assert posterior.mean == pytest.approx(0.5)


def test_no_evidence():
    posterior = SkillPosterior()
    posterior.update(0, 0)
    assert posterior.mean == 0.5
    assert posterior.std_dev == pytest.approx(0.288, abs=1e-3) 