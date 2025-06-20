import pandas as pd
import json
import time
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_and_filter_data():
    """Load CSV data and filter by time range"""
    logger.info("Loading and filtering market data...")
    
    # Load the CSV file
    df = pd.read_csv(
        'l1_day.csv',
        dtype={
            'publisher_id': int,       
            'ask_px_00': float,
            'ask_sz_00': float      
        },
        parse_dates=['ts_event'],
        na_values=['NA', 'N/A', '-', '']
    )
    
    # Filter by time range (13:36:32 to 13:45:14 UTC)
    start_time = pd.Timestamp('2024-08-01T13:36:32Z')
    end_time = pd.Timestamp('2024-08-01T13:45:14Z')
    
    df_filtered = df[
        (df['ts_event'] >= start_time) & 
        (df['ts_event'] <= end_time)
    ].copy()
    
    logger.info(f"Filtered data: {len(df_filtered)} rows from {len(df)} total")
    return df_filtered

def create_venue_snapshots(df):
    """Group data by timestamp to create venue snapshots"""
    logger.info("Creating venue snapshots...")
    
    # Group by timestamp and create venue snapshots
    snapshots = []
    
    for timestamp, group in df.groupby('ts_event'):
        venues = []
        
        # Get unique venues for this timestamp
        for venue_id in group['publisher_id'].unique():
            venue_data = group[group['publisher_id'] == venue_id].iloc[0]
            
            venue_snapshot = {
                'publisher_id': int(venue_data['publisher_id']),
                'ask_px_00': float(venue_data['ask_px_00']),
                'ask_sz_00': float(venue_data['ask_sz_00'])
            }
            venues.append(venue_snapshot)
        
        snapshots.append({
            'timestamp': timestamp.isoformat(),
            'venues': venues
        })
    
    # print("snapshots", snapshots)
    logger.info(f"Created {len(snapshots)} venue snapshots")
    return snapshots

def setup_kafka_producer():
    """Set up Kafka producer"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        logger.info("Kafka producer connected successfully")
        return producer
    except KafkaError as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        return None

def simulate_real_time_streaming(snapshots, producer):
    """Simulate real-time streaming with time delays"""
    logger.info("Starting real-time simulation...")
    
    topic = 'mock_l1_stream'
    
    for i, snapshot in enumerate(snapshots):
        try:
            # Send snapshot to Kafka
            future = producer.send(
                topic=topic,
                key=snapshot['timestamp'],
                value=snapshot
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            logger.info(f"Sent snapshot {i+1}/{len(snapshots)} to {record_metadata.topic} "
                       f"[{record_metadata.partition}] at offset {record_metadata.offset}")
            
            # Simulate real-time delays
            if i < len(snapshots) - 1:
                # Calculate time difference to next snapshot
                current_time = pd.Timestamp(snapshot['timestamp'])
                next_time = pd.Timestamp(snapshots[i+1]['timestamp'])
                time_delta = (next_time - current_time).total_seconds()
                
                # Cap the delay to reasonable bounds (0.1 to 1 second)
                time_delta = max(0.1, min(1.0, time_delta))
                
                logger.info(f"Sleeping for {time_delta:.3f} seconds...")
                time.sleep(time_delta)
                
        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
            break
    
    # Flush and close producer
    producer.flush()
    producer.close()
    logger.info("Streaming completed")

def main():
    """Main function to run the Kafka producer"""
    logger.info("Starting Kafka producer for SOR backtesting...")
    
    # Step 1: Load and filter data
    df = load_and_filter_data()
    
    # Step 2: Create venue snapshots
    snapshots = create_venue_snapshots(df)
    
    # Step 3: Set up Kafka producer
    producer = setup_kafka_producer()
    if not producer:
        logger.error("Failed to set up Kafka producer. Exiting.")
        return
    
    # Step 4: Simulate real-time streaming
    simulate_real_time_streaming(snapshots, producer)
    
    logger.info("Kafka producer completed successfully!")

if __name__ == "__main__":
    main()
