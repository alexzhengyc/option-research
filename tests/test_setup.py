"""
Basic setup tests to verify installation and configuration
"""
import os
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))


def test_imports():
    """Test that all modules can be imported"""
    import finnhub_client
    import polygon_client
    import supabase_client
    import scoring
    import config
    
    assert finnhub_client is not None
    assert polygon_client is not None
    assert supabase_client is not None
    assert scoring is not None
    assert config is not None


def test_directories_exist():
    """Test that all required directories exist"""
    project_root = Path(__file__).parent.parent
    
    assert (project_root / "lib").exists()
    assert (project_root / "jobs").exists()
    assert (project_root / "config").exists()
    assert (project_root / "db").exists()
    assert (project_root / "out").exists()


def test_config_loads():
    """Test that config module loads without errors"""
    import config
    
    # Check that paths are set
    assert config.PROJECT_ROOT is not None
    assert config.DB_DIR is not None
    assert config.OUT_DIR is not None


def test_scorer_initialization():
    """Test that DirectionalScorer can be initialized"""
    from scoring import DirectionalScorer
    
    scorer = DirectionalScorer()
    assert scorer is not None
    assert scorer.WEIGHTS['d1'] == 0.32
    assert scorer.WEIGHTS['d2'] == 0.28


def test_compute_simple_score():
    """Test basic score computation"""
    from scoring import DirectionalScorer
    
    scorer = DirectionalScorer()
    
    # Test bullish scenario
    score = scorer.compute_score(
        ticker="TEST",
        d1=1.0,
        d2=1.0,
        d3=0.5,
        d4=0.3,
        d5=0.2,
        p1=0.3,
        p2=0.1,
    )
    
    assert score.ticker == "TEST"
    assert score.dir_score > 0  # Should be positive (bullish)
    assert score.direction == "CALL"
    
    # Test bearish scenario
    score = scorer.compute_score(
        ticker="TEST",
        d1=-1.0,
        d2=-1.0,
        d3=-0.5,
        d4=-0.3,
        d5=-0.2,
        p1=0.3,
        p2=0.1,
    )
    
    assert score.dir_score < 0  # Should be negative (bearish)
    assert score.direction == "PUT"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

