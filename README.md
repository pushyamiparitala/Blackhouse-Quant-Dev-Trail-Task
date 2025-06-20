Smart Order Router (SOR) Backtesting System

A real-time Smart Order Router backtesting system that implements the Cont-Kukanov cost model for optimal order execution across multiple trading venues.

🎯 Project Overview

This system simulates a production Smart Order Router by:
- Streaming market data via Kafka to simulate real-time market feeds
- Implementing Cont-Kukanov algorithm for optimal order splitting
- Backtesting execution strategies against baseline methods
- Deploying on AWS EC2 for production-like testing

 📊 System Architecture

<img width="576" alt="Screenshot 2025-06-19 at 5 45 00 PM" src="https://github.com/user-attachments/assets/8dd826b4-d721-4569-8b72-04661418aaad" />



🚀 Quick Start (Local Development)

 Prerequisites
- Python 3.8+
- Java 11+ (for Kafka)
- Kafka & Zookeeper

Installation

1. Install dependencies:
bash
pip install -r requirements.txt


2. Start Kafka & Zookeeper:
bash
 On macOS with Homebrew
brew services start zookeeper
brew services start kafka

 Create topic
kafka-topics --create --topic mock_l1_stream --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1


3. Run the system:
bash
 Terminal 1: Start producer
python kafka_producer.py

 Terminal 2: Run backtest
python backtest.py


 ☁️ AWS EC2 Deployment

 EC2 Instance Configuration

Instance Type Used: `t3.micro` (Free Tier Eligible)
- vCPUs: 2
- Memory: 1 GiB
- Storage: 8 GB gp2
- Architecture: x86_64
- AMI: Amazon Linux 2023

 Step 1: Launch EC2 Instance

1. Launch Instance:
   - AMI: Amazon Linux 2023 (x86)
   - Instance Type: `t3.micro` - Free tier eligible
   - Storage: 8 GB gp2 (default)
   - Security Group: Allow SSH (port 22) from your IP

2. Create Key Pair:
   - Download the `.pem` key file
   - Set permissions: `chmod 400 your-key.pem`


Update system and install dependencies:
bash
 Update system packages
sudo yum update -y

 Install Java (required for Kafka)
sudo yum install -y java-11-amazon-corretto

 Install Python 3 and pip
sudo yum install -y python3 python3-pip

 Install Git
sudo yum install -y git


Create application directory:
bash
mkdir -p /home/ec2-user/sor-backtest
cd /home/ec2-user/sor-backtest


Step 2: Install Kafka & Zookeeper

Download and install Kafka:
bash
 Download Kafka
KAFKA_VERSION="3.6.1"
wget https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_2.13-${KAFKA_VERSION}.tgz
tar -xzf kafka_2.13-${KAFKA_VERSION}.tgz
ln -s kafka_2.13-${KAFKA_VERSION} kafka
rm kafka_2.13-${KAFKA_VERSION}.tgz

- Create data directories
mkdir -p /home/ec2-user/kafka-data
mkdir -p /home/ec2-user/zookeeper-data


- Configure Kafka:
bash
 Configure Kafka server
cat > kafka/config/server.properties << EOF
broker.id=0
listeners=PLAINTEXT://localhost:9092
log.dirs=/home/ec2-user/kafka-data
num.partitions=1
default.replication.factor=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=localhost:2181
EOF

- Configure Zookeeper
cat > kafka/config/zookeeper.properties << EOF
dataDir=/home/ec2-user/zookeeper-data
clientPort=2181
maxClientCnxns=0
admin.enableServer=false
EOF


Install Python dependencies:
bash
pip3 install pandas numpy kafka-python matplotlib seaborn


Step 3: Upload Application Files

From your local machine, upload files:
bash
 Upload all application files
scp -i your-key.pem -r . ec2-user@<EC2_IP>:/home/ec2-user/sor-backtest/


Step 4: Start Kafka & Zookeeper

SSH to EC2 and start services:
bash
ssh -i your-key.pem ec2-user@<EC2_IP>
cd /home/ec2-user/sor-backtest

 Start Zookeeper
./kafka/bin/zookeeper-server-start.sh -daemon ./kafka/config/zookeeper.properties

 Wait for Zookeeper to start
sleep 10

 Start Kafka
./kafka/bin/kafka-server-start.sh -daemon ./kafka/config/server.properties

 Wait for Kafka to start
sleep 10

 Create topic
./kafka/bin/kafka-topics.sh --create --topic mock_l1_stream --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1


Step 5: Run the Full Pipeline

Commands to run producer & backtest:

Terminal 1 - Run Producer:
bash
 SSH to EC2
ssh -i your-key.pem ec2-user@<EC2_IP>
cd /home/ec2-user/sor-backtest

Run Kafka producer
python3 kafka_producer.py


Terminal 2 - Run Backtest:
bash
 SSH to EC2 (new terminal)
ssh -i your-key.pem ec2-user@<EC2_IP>
cd /home/ec2-user/sor-backtest

Run SOR backtest
python3 backtest.py


Expected Output:
json
{
  "best_parameters": {
    "lambda_over": 0.5,
    "lambda_under": 0.5,
    "theta_queue": 0.3
  },
  "optimized": {
    "total_cash": 1234567.89,
    "avg_fill_px": 123.45
  },
  "baselines": {
    "best_ask": {"total_cash": 1235000, "avg_fill_px": 123.50},
    "twap": {"total_cash": 1236000, "avg_fill_px": 123.60},
    "vwap": {"total_cash": 1235500, "avg_fill_px": 123.55}
  },
  "savings_vs_baselines_bps": {
    "best_ask": 4.0,
    "twap": 12.1,
    "vwap": 8.1
  }
}


 📸 Screenshots 

Screenshot 1: Kafka + Backtest Running on local


- Shows Kafka producer running in one terminal
- Shows SOR backtest running in another terminal
- Display real-time log output
<img width="753" alt="Screenshot 2025-06-19 at 5 49 39 PM" src="https://github.com/user-attachments/assets/837a753d-d07d-4043-9ea1-10cd57abdf32" />

Screenshot 2: Stdout JSON Result

- Shows the final JSON output from backtest.py
- Highlight the savings vs baselines
- Display the optimized parameters
<img width="517" alt="Screenshot 2025-06-19 at 5 50 09 PM" src="https://github.com/user-attachments/assets/41f534e0-19f9-4f33-a534-a303f00a15c2" />



Screenshot 3: System Information
bash
 Commands to run for screenshots:
uptime
uname -a
systemctl status kafka zookeeper
./kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
![image](https://github.com/user-attachments/assets/979958b2-4646-44b4-bb9c-df8b8f32fdc2)


📄 Output Files

 output_json.png
The system generates a complete result dump in JSON format:

 🔧 System Components

 1. Kafka Producer (`kafka_producer.py`)
- Loads and filters `l1_day.csv` data
- Creates venue snapshots per timestamp
- Streams data to Kafka topic `mock_l1_stream`
- Simulates real-time market data flow

 2. SOR Backtester (`backtest.py`)
- Cont-Kukanov Allocator: Implements optimal order splitting
- Baseline Strategies: Best Ask, TWAP, VWAP comparison
- Real-time Processing: Consumes Kafka stream
- Performance Tracking: Calculates execution costs and savings

 3. Cont-Kukanov Algorithm
- Input: Order size, venue states, penalty parameters
- Output: Optimal split across venues
- Optimization: Minimizes total expected cost
- Parameters: `lambda_over`, `lambda_under`, `theta_queue`

 📊 Data Format

 Market Data Snapshot
json
{
  "timestamp": "2024-08-01T13:36:32.491911683Z",
  "venues": [
    {
      "publisher_id": 2,
      "ask_px_00": 222.83,
      "ask_sz_00": 36
    }
  ]
}


 Venue Object
python
@dataclass
class Venue:
    publisher_id: int     Exchange identifier
    ask: float           Best ask price
    ask_size: float      Available shares
    fee: float = 0.0     Exchange fees
    rebate: float = 0.0  Maker rebates


 🎛️ Configuration

 Cont-Kukanov Parameters
- `lambda_over`: Penalty for over-filling (default: 0.5)
- `lambda_under`: Penalty for under-filling (default: 0.5)
- `theta_queue`: Queue risk penalty (default: 0.3)

 Order Configuration
- Order Size: 5,000 shares (configurable in `SORBacktester`)
- Time Window: 13:36:32 to 13:45:14 UTC
- Step Size: 100 shares (allocation granularity)

 🔍 Monitoring & Debugging

 Kafka Commands
bash
 List topics
./kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

 View messages
./kafka/bin/kafka-console-consumer.sh --topic mock_l1_stream --bootstrap-server localhost:9092 --from-beginning

 Check consumer groups
./kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list


 System Monitoring
bash
 Check service status
systemctl status kafka zookeeper

 View logs
journalctl -u kafka -f
journalctl -u zookeeper -f

 Monitor resources
htop
df -h


 🐛 Troubleshooting

 Common Issues

1. Kafka Connection Failed
   bash
    Check if Kafka is running
   ps aux | grep kafka
   
    Restart services
   ./kafka/bin/kafka-server-stop.sh
   ./kafka/bin/zookeeper-server-stop.sh
   ./kafka/bin/zookeeper-server-start.sh -daemon ./kafka/config/zookeeper.properties
   sleep 10
   ./kafka/bin/kafka-server-start.sh -daemon ./kafka/config/server.properties
   

2. Topic Not Found
   bash
    Create topic manually
   ./kafka/bin/kafka-topics.sh --create --topic mock_l1_stream --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   

3. Memory Issues (t3.micro)
   bash
    Check memory usage
   free -h
   
    Reduce Kafka memory if needed
    Edit kafka/config/server.properties
    Add: heap.opts=-Xmx512m -Xms512m
   

4. Python Import Errors
   bash
    Reinstall dependencies
   pip3 install -r requirements.txt --force-reinstall
   

 Performance Optimization

1. For t3.micro instances:
   - Monitor CPU credits: `watch -n 1 'cat /proc/cpuinfo | grep "cpu MHz" | head -1'`
   - Use ARM-based t4g.micro for better performance if available

2. Kafka Tuning:
   - Reduce log retention: `log.retention.hours=24`
   - Optimize memory: `heap.opts=-Xmx512m -Xms512m`

 📈 Performance Metrics

 Key Performance Indicators
- Execution Cost: Total cash spent on order
- Average Fill Price: Weighted average execution price
- Savings vs Baselines: Performance improvement in basis points
- Fill Rate: Percentage of order executed

 Baseline Comparisons
- Best Ask: Always execute at lowest available price
- TWAP: Time-weighted average price over 60-second intervals
- VWAP: Volume-weighted average price based on displayed size

 🔒 Security Considerations

 EC2 Security
- Use IAM roles for AWS service access
- Restrict security group to necessary ports only
- Regularly update system packages
- Use key-based SSH authentication

 Data Security
- Market data is processed locally (no external transmission)
- Kafka runs on localhost only
- No sensitive data stored in logs

 📚 Technical Details

 Algorithm Implementation
The Cont-Kukanov allocator implements:
1. Cost Function: Execution cost + penalties + risk
2. Optimization: Exhaustive search over allocation space
3. Constraints: Respect venue size limits
4. Penalties: Over/under-fill and queue risk penalties

 Real-time Simulation
- Time Delays: Based on actual `ts_event` differences
- No Look-ahead: Only current market state available
- Sequential Processing: Snapshots processed in order
- State Tracking: Maintains order execution state

