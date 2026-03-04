# Research Database
import logging
import sqlite3
import pandas as pd
import json
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    strategy_id: str
    features_used: List[str]
    hyperparameters: Dict
    pnl: float
    sharpe: float
    drawdown: float
    win_rate: float
    total_trades: int
    market_regime: str
    timestamp: datetime
    fitness: float = 0.0

@dataclass
class Experiment:
    experiment_id: str
    strategy_name: str
    variant_id: str
    features: List[str]
    parameters: Dict
    status: str  # 'backtest', 'walk_forward', 'paper', 'live'
    results: Optional[BacktestResult] = None

class ResearchDatabase:
    """
    Research database for AI-driven strategy optimization.
    
    Stores every experiment for meta-optimization:
    - Backtest results
    - Walk-forward performance
    - Live trading metrics
    - Regime-specific performance
    """
    
    def __init__(self, db_path: str = "data/research.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        self._create_tables()
        
        logger.info(f"ResearchDatabase initialized: {self.db_path}")
    
    def _create_tables(self):
        """Create schema for research data"""
        cursor = self.conn.cursor()
        
        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                variant_id TEXT NOT NULL,
                features TEXT,  -- JSON list
                parameters TEXT,  -- JSON dict
                status TEXT DEFAULT 'backtest',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                promoted_at TIMESTAMP,
                UNIQUE(strategy_name, variant_id)
            )
        ''')
        
        # Backtest results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                pnl_pct REAL,
                sharpe_ratio REAL,
                max_drawdown_pct REAL,
                win_rate_pct REAL,
                total_trades INTEGER,
                market_regime TEXT,
                fitness_score REAL,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_end_date TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Live performance metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS live_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                timestamp TIMESTAMP,
                realized_pnl REAL,
                unrealized_pnl REAL,
                sharpe_24h REAL,
                drawdown_current REAL,
                exposure REAL,
                num_positions INTEGER,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Feature importance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feature_importance (
                importance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                importance_score REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Regime detection history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regime_history (
                regime_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                regime_type TEXT,  -- trend, mean_reversion, high_vol, low_liq
                regime_score REAL,
                vol_regime REAL,
                trend_regime REAL,
                liquidity_regime REAL
            )
        ''')
        
        self.conn.commit()
        logger.info("Research database schema created")
    
    def log_experiment(self, experiment: Experiment) -> str:
        """Log a new experiment to the database"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO experiments 
                (experiment_id, strategy_name, variant_id, features, parameters, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment.experiment_id,
                experiment.strategy_name,
                experiment.variant_id,
                json.dumps(experiment.features),
                json.dumps(experiment.parameters),
                experiment.status,
                datetime.now().isoformat()
            ))
            
            self.conn.commit()
            logger.info(f"Logged experiment: {experiment.experiment_id}")
            return experiment.experiment_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to log experiment: {e}")
            return None
    
    def log_backtest_result(self, result: BacktestResult) -> bool:
        """Log backtest results with fitness calculation"""
        cursor = self.conn.cursor()
        
        # Calculate fitness: maximize sharpe, minimize drawdown
        fitness = result.sharpe - 0.5 * result.drawdown
        
        try:
            cursor.execute('''
                INSERT INTO backtest_results 
                (experiment_id, pnl_pct, sharpe_ratio, max_drawdown_pct, 
                 win_rate_pct, total_trades, market_regime, fitness_score, data_end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.strategy_id,
                result.pnl,
                result.sharpe,
                result.drawdown,
                result.win_rate,
                result.total_trades,
                result.market_regime,
                fitness,
                result.timestamp.isoformat()
            ))
            
            self.conn.commit()
            logger.info(f"Logged backtest for {result.strategy_id}: fitness={fitness:.3f}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to log backtest result: {e}")
            return False
    
    def log_live_metrics(self, experiment_id: str, metrics: Dict) -> bool:
        """Log real-time trading metrics"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO live_metrics 
                (experiment_id, timestamp, realized_pnl, unrealized_pnl,
                 sharpe_24h, drawdown_current, exposure, num_positions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment_id,
                datetime.now().isoformat(),
                metrics.get('realized_pnl', 0),
                metrics.get('unrealized_pnl', 0),
                metrics.get('sharpe_24h', 0),
                metrics.get('drawdown_current', 0),
                metrics.get('exposure', 0),
                metrics.get('num_positions', 0)
            ))
            
            self.conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to log live metrics: {e}")
            return False
    
    def log_regime(self, symbol: str, regime: str, scores: Dict) -> bool:
        """Log market regime detection"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO regime_history 
                (symbol, regime_type, regime_score, vol_regime, trend_regime, liquidity_regime)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                regime,
                scores.get('overall', 0),
                scores.get('volatility', 0),
                scores.get('trend', 0),
                scores.get('liquidity', 0)
            ))
            
            self.conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to log regime: {e}")
            return False
    
    def get_top_experiments(self, n: int = 10, 
                         regime: str = None) -> pd.DataFrame:
        """Get top performing experiments for meta-optimization"""
        query = '''
            SELECT e.experiment_id, e.strategy_name, e.features, e.parameters,
                   b.sharpe_ratio, b.max_drawdown_pct, b.win_rate_pct,
                   b.fitness_score, b.total_trades, b.market_regime,
                   b.pnl_pct
            FROM experiments e
            JOIN backtest_results b ON e.experiment_id = b.experiment_id
            WHERE b.run_at = (
                SELECT MAX(run_at) FROM backtest_results WHERE experiment_id = e.experiment_id
            )
        '''
        
        if regime:
            query += f" AND b.market_regime = '{regime}'"
        
        query += " ORDER BY b.fitness_score DESC LIMIT ?"
        
        df = pd.read_sql_query(query, self.conn, params=(n,))
        
        # Parse JSON columns
        df['features'] = df['features'].apply(json.loads)
        df['parameters'] = df['parameters'].apply(json.loads)
        
        return df
    
    def get_strategy_evolution(self, strategy_name: str) -> pd.DataFrame:
        """Get evolution of a strategy over time"""
        query = '''
            SELECT b.*, e.variant_id
            FROM backtest_results b
            JOIN experiments e ON b.experiment_id = e.experiment_id
            WHERE e.strategy_name = ?
            ORDER BY b.run_at ASC
        '''
        
        return pd.read_sql_query(query, self.conn, params=(strategy_name,))
    
    def promote_to_paper(self, experiment_id: str) -> bool:
        """Promote experiment from backtest to paper trading"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE experiments 
                SET status = 'paper', promoted_at = ?
                WHERE experiment_id = ?
            ''', (datetime.now().isoformat(), experiment_id))
            
            self.conn.commit()
            logger.info(f"Promoted {experiment_id} to paper trading")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to promote experiment: {e}")
            return False
    
    def get_promotion_candidates(self, min_sharpe: float = 1.0,
                                max_drawdown: float = 0.2) -> pd.DataFrame:
        """Get experiments ready for promotion to next stage"""
        query = '''
            SELECT e.*, b.sharpe_ratio, b.max_drawdown_pct, b.fitness_score
            FROM experiments e
            JOIN backtest_results b ON e.experiment_id = b.experiment_id
            WHERE e.status = 'backtest'
            AND b.sharpe_ratio >= ?
            AND b.max_drawdown_pct <= ?
            ORDER BY b.fitness_score DESC
        '''
        
        return pd.read_sql_query(query, self.conn, 
                                params=(min_sharpe, max_drawdown))
    
    def close(self):
        self.conn.close()


if __name__ == "__main__":
    db = ResearchDatabase("data/research_test.db")
    
    # Example experiment
    experiment = Experiment(
        experiment_id="mm_imb_001",
        strategy_name="market_making",
        variant_id="imbalance_v1",
        features=["ob_imbalance", "volatility", "trade_toxicity"],
        parameters={"spread_bps": 50, "skew_factor": 0.5},
        status="backtest"
    )
    
    db.log_experiment(experiment)
    
    # Example backtest result
    result = BacktestResult(
        strategy_id="mm_imb_001",
        features_used=["ob_imbalance", "volatility"],
        hyperparameters={"spread_bps": 50},
        pnl=15.3,
        sharpe=1.45,
        drawdown=0.08,
        win_rate=0.62,
        total_trades=150,
        market_regime="mean_reversion",
        timestamp=datetime.now()
    )
    
    db.log_backtest_result(result)
    
    # Get top experiments
    top = db.get_top_experiments(n=5)
    print("\nTop Experiments:")
    print(top[['experiment_id', 'sharpe_ratio', 'fitness_score']].head())
    
    db.close()
