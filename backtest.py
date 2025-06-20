import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple
import pandas as pd
from kafka import KafkaConsumer
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Venue:
    """Represents a trading venue with its current state"""
    publisher_id: int
    ask: float        # ask_px_00
    ask_size: float   # ask_sz_00
    fee: float = 0.0  # Exchange fee (could be negative for rebates)
    rebate: float = 0.0

class ContKukanovAllocator:
    """Implementation of the Cont-Kukanov static allocation strategy"""
    
    def __init__(self, lambda_over: float, lambda_under: float, theta_queue: float):
        self.lambda_over = lambda_over    # Cost penalty per extra share bought
        self.lambda_under = lambda_under  # Cost penalty per unfilled share
        self.theta_queue = theta_queue    # Queue-risk penalty
        self.step = 100                  # Search in 100-share chunks
    
    def compute_cost(self, split: List[int], venues: List[Venue], order_size: int) -> float:
        """Compute the total expected cost for a given split"""
        executed = 0
        cash_spent = 0.0
        
        # Calculate execution costs and maker rebates
        for i, shares in enumerate(split):
            # How many shares we can actually execute at this venue
            exe = min(shares, venues[i].ask_size)
            executed += exe
            
            # Cost of executed shares including fees
            cash_spent += exe * (venues[i].ask + venues[i].fee)
            
            # Maker rebates for unfilled shares
            maker_rebate = max(shares - exe, 0) * venues[i].rebate
            cash_spent -= maker_rebate
        
        # Calculate penalties
        underfill = max(order_size - executed, 0)
        overfill = max(executed - order_size, 0)
        
        # Risk penalty for total mis-execution
        risk_penalty = self.theta_queue * (underfill + overfill)
        
        # Cost penalties for under/over-filling
        cost_penalty = (self.lambda_under * underfill + 
                       self.lambda_over * overfill)
        
        return cash_spent + risk_penalty + cost_penalty
    
    def allocate(self, order_size: int, venues: List[Venue]) -> Tuple[List[int], float]:
        """
        Allocate order across venues to minimize total expected cost
        Returns: (best_split, best_cost)
        """
        splits = [[]]  # Start with empty allocation
        
        # For each venue, try different allocation sizes
        for v in range(len(venues)):
            new_splits = []
            for alloc in splits:
                used = sum(alloc)
                max_v = min(order_size - used, venues[v].ask_size)
                
                # Try different quantities in steps
                for q in range(0, int(max_v) + 1, self.step):
                    new_splits.append(alloc + [q])
            splits = new_splits
        
        # Find best split
        best_cost = float('inf')
        best_split = []
        
        for split in splits:
            if sum(split) != order_size:
                continue
                
            cost = self.compute_cost(split, venues, order_size)
            if cost < best_cost:
                best_cost = cost
                best_split = split
        
        return best_split, best_cost

class BaselineStrategies:
    """Implements baseline execution strategies for comparison"""
    
    @staticmethod
    def best_ask(venues: List[Venue], order_size: int) -> Dict:
        """Always execute at the lowest ask price"""
        best_venue = min(venues, key=lambda v: v.ask)
        executed = min(order_size, best_venue.ask_size)
        total_cost = executed * best_venue.ask
        return {
            "total_cash": total_cost,
            "avg_fill_px": best_venue.ask if executed > 0 else 0
        }
    
    @staticmethod
    def twap(venues: List[Venue], order_size: int, interval_seconds: int = 60) -> Dict:
        """Time-Weighted Average Price - split order equally over time"""
        shares_per_interval = order_size / (interval_seconds / 60)  # Shares per minute
        total_cost = 0
        total_executed = 0
        
        # Simulate simple TWAP by taking best ask at each interval
        best_venue = min(venues, key=lambda v: v.ask)
        executed = min(shares_per_interval, best_venue.ask_size)
        total_cost += executed * best_venue.ask
        total_executed += executed
        
        return {
            "total_cash": total_cost,
            "avg_fill_px": total_cost / total_executed if total_executed > 0 else 0
        }
    
    @staticmethod
    def vwap(venues: List[Venue], order_size: int) -> Dict:
        """Volume-Weighted Average Price - split based on displayed size"""
        total_size = sum(v.ask_size for v in venues)
        total_cost = 0
        total_executed = 0
        
        for venue in venues:
            size_ratio = venue.ask_size / total_size
            shares_to_execute = min(order_size * size_ratio, venue.ask_size)
            total_cost += shares_to_execute * venue.ask
            total_executed += shares_to_execute
        
        return {
            "total_cash": total_cost,
            "avg_fill_px": total_cost / total_executed if total_executed > 0 else 0
        }

class SORBacktester:
    """Main backtesting engine for Smart Order Router"""
    
    def __init__(self):
        self.order_size = 5000  # Target shares to execute
        self.remaining_shares = self.order_size
        self.total_cost = 0.0
        self.total_executed = 0
        
        # Track baseline performance
        self.baseline_results = defaultdict(lambda: {"total_cash": 0, "avg_fill_px": 0})
        
        # Initialize Kafka consumer
        self.consumer = KafkaConsumer(
            'mock_l1_stream',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='sor_backtester'
        )
        
        # Initialize allocator with default parameters
        self.allocator = ContKukanovAllocator(
            lambda_over=0.5,
            lambda_under=0.5,
            theta_queue=0.3
        )
    
    def process_snapshot(self, snapshot: Dict) -> None:
        """Process a single market data snapshot"""
        # Convert snapshot to venue objects
        venues = [
            Venue(
                publisher_id=v['publisher_id'],
                ask=v['ask_px_00'],
                ask_size=v['ask_sz_00']
            )
            for v in snapshot['venues']
        ]
        
        # Skip if no remaining shares to execute
        if self.remaining_shares <= 0:
            return
        
        # Get allocation from Cont-Kukanov
        split, cost = self.allocator.allocate(
            self.remaining_shares, venues
        )
        
        # Execute the split
        for i, shares in enumerate(split):
            if shares > 0:
                executed = min(shares, venues[i].ask_size)
                self.total_cost += executed * venues[i].ask
                self.total_executed += executed
                self.remaining_shares -= executed
        
        # Track baseline performance
        self._update_baselines(venues)
    
    def _update_baselines(self, venues: List[Venue]) -> None:
        """Update baseline strategy results"""
        baselines = BaselineStrategies()
        
        # Best Ask
        best_ask = baselines.best_ask(venues, self.order_size)
        self.baseline_results['best_ask'] = best_ask
        
        # TWAP (60-second intervals)
        twap = baselines.twap(venues, self.order_size)
        self.baseline_results['twap'] = twap
        
        # VWAP
        vwap = baselines.vwap(venues, self.order_size)
        self.baseline_results['vwap'] = vwap
    
    def calculate_savings_bps(self) -> Dict:
        """Calculate savings vs baselines in basis points"""
        our_avg_px = self.total_cost / self.total_executed if self.total_executed > 0 else 0
        savings = {}
        
        for strategy, result in self.baseline_results.items():
            if result['avg_fill_px'] > 0:
                savings[strategy] = (
                    (result['avg_fill_px'] - our_avg_px) / 
                    result['avg_fill_px'] * 10000  # Convert to basis points
                )
            else:
                savings[strategy] = 0
        
        return savings
    
    def run(self) -> Dict:
        """Run the backtesting simulation"""
        logger.info("Starting SOR backtest...")
        
        try:
            for message in self.consumer:
                snapshot = message.value
                self.process_snapshot(snapshot)
                
                # Stop if we've filled the entire order
                if self.remaining_shares <= 0:
                    break
            
            # Calculate final results
            avg_fill_px = self.total_cost / self.total_executed if self.total_executed > 0 else 0
            savings = self.calculate_savings_bps()
            
            results = {
                "best_parameters": {
                    "lambda_over": self.allocator.lambda_over,
                    "lambda_under": self.allocator.lambda_under,
                    "theta_queue": self.allocator.theta_queue
                },
                "optimized": {
                    "total_cash": self.total_cost,
                    "avg_fill_px": avg_fill_px
                },
                "baselines": self.baseline_results,
                "savings_vs_baselines_bps": savings
            }
            
            logger.info("Backtest completed successfully!")
            return results
            
        except Exception as e:
            logger.error(f"Error during backtest: {e}")
            raise
        finally:
            self.consumer.close()

def main():
    """Main function to run the backtest"""
    backtester = SORBacktester()
    results = backtester.run()
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
