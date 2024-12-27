import subprocess
import time
from datetime import datetime, timedelta
import os


def start_script_daily(script_path, start_time=1218):
	# Extract hour and minute from the input time
	hour = start_time // 100
	minute = start_time % 100
	
	while True:
		# Get current time and calculate the next start time
		current_time = datetime.now()
		next_run = current_time.replace(
			hour=hour,
			minute=minute,
			second=0,
			microsecond=0
		)
		if current_time >= next_run:
			# If the time has already passed today, schedule for tomorrow
			next_run += timedelta(days=1)
		
		# Continuously update the remaining time until the next run
		while True:
			current_time = datetime.now()
			remaining_time = (next_run - current_time).total_seconds()
			if remaining_time <= 0:
				break
			wait_hours = int(remaining_time // 3600)
			wait_minutes = int((remaining_time % 3600) // 60)
			wait_seconds = int(remaining_time % 60)
			print(f"Next run at: {next_run}. Waiting {wait_hours} hours, {wait_minutes} minutes, and {wait_seconds} seconds...", end="\r")  # noqa: E501
			time.sleep(1)
		
		# Start the script in a new window
		try:
			print("\nStarting the script...")
			if os.name == 'nt':  # Windows
				subprocess.run(["start", "cmd.exe", "/k", f"python {script_path}"], shell=True)
			else:
				raise Exception("Unsupported operating system")
			
			print("Waiting for the next run...")
		except Exception as e:
			print(f"Error occurred while starting the script: {e}")
			
		# Wait for the next day's run
		print("Waiting for the next scheduled run...\n")


start_script_daily('bot.py')
