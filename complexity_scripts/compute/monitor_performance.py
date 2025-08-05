#!/usr/bin/env python3
"""
Performance Monitoring for Complexity Analysis
Monitors CPU utilization, memory usage, and processing speed.
"""

import os
import time
import psutil
import threading
from datetime import datetime

class PerformanceMonitor:
    def __init__(self, log_file="performance_monitor.log"):
        self.log_file = log_file
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start performance monitoring in background thread."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"Performance monitoring started. Log: {self.log_file}")
        
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("Performance monitoring stopped.")
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        with open(self.log_file, 'w') as f:
            f.write("Timestamp,CPU_Percent,Memory_Percent,Memory_GB,Disk_IO_Read,Disk_IO_Write\n")
            
            while self.monitoring:
                try:
                    # Get system metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    disk_io = psutil.disk_io_counters()
                    
                    # Format timestamp
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Write to log
                    log_line = f"{timestamp},{cpu_percent:.1f},{memory.percent:.1f},{memory.used/1024**3:.2f},{disk_io.read_bytes/1024**2:.1f},{disk_io.write_bytes/1024**2:.1f}\n"
                    f.write(log_line)
                    f.flush()
                    
                    # Print to console every 30 seconds
                    if int(time.time()) % 30 == 0:
                        print(f"[{timestamp}] CPU: {cpu_percent:.1f}% | Memory: {memory.percent:.1f}% ({memory.used/1024**3:.2f}GB)")
                        
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    
                time.sleep(5)  # Sample every 5 seconds
                
    def get_summary(self):
        """Get performance summary from log file."""
        if not os.path.exists(self.log_file):
            return "No performance data available."
            
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                
            if len(lines) < 2:
                return "Insufficient data for summary."
                
            # Parse data (skip header)
            data = []
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    data.append({
                        'cpu': float(parts[1]),
                        'memory': float(parts[2]),
                        'memory_gb': float(parts[3])
                    })
                    
            if not data:
                return "No valid data found."
                
            # Calculate statistics
            cpu_values = [d['cpu'] for d in data]
            memory_values = [d['memory'] for d in data]
            memory_gb_values = [d['memory_gb'] for d in data]
            
            summary = f"""
Performance Summary:
==================
Samples: {len(data)}
Duration: {len(data) * 5} seconds

CPU Usage:
  Average: {sum(cpu_values)/len(cpu_values):.1f}%
  Max: {max(cpu_values):.1f}%
  Min: {min(cpu_values):.1f}%

Memory Usage:
  Average: {sum(memory_values)/len(memory_values):.1f}%
  Max: {max(memory_values):.1f}%
  Min: {min(memory_values):.1f}%
  Average GB: {sum(memory_gb_values)/len(memory_gb_values):.2f}GB
"""
            return summary
            
        except Exception as e:
            return f"Error generating summary: {e}"

def main():
    """Main function for standalone performance monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor system performance")
    parser.add_argument("--duration", type=int, default=3600, help="Monitoring duration in seconds")
    parser.add_argument("--log-file", type=str, default="performance_monitor.log", help="Log file path")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.log_file)
    
    print(f"Starting performance monitoring for {args.duration} seconds...")
    monitor.start_monitoring()
    
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user.")
    finally:
        monitor.stop_monitoring()
        print("\n" + monitor.get_summary())

if __name__ == "__main__":
    main() 