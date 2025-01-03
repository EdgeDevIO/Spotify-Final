import subprocess
import time
from datetime import datetime, timedelta
import os
import configparser
from logger import log

log = log(
	log_level="INFO",
	error_webhook="https://discord.com/api/webhooks/1315498715078983691/D6Ef9MXpjzmcbjZ1yKuRjXPy6jVvwg_xc4kSd2yqc9CKAuaxyTl0pr5hF6Rpze6Po1lt",  # noqa: E501
	critical_webhook="https://discord.com/api/webhooks/1315498559885541476/4LFZiDhxHKmLsFSd23PxdWR1caBrUbNqWLVcUnozIX4YorH1GhWCjMvga5nH_0uE75uL",  # noqa: E501
)


def GetConfig(file_path='config.ini'):
	config = configparser.ConfigParser()
	config.read(file_path)

	if 'mysql' not in config:
		log.critical(
			f"Section 'mysql' not found in the {file_path} file. Program closed."
		)
		exit()

	if 'start_time' not in config['settings']:
		log.critical(
			f"'start_time' not found in the 'settings' section of the {file_path} file. Program closed."
		)
		exit()

	return {
		'database': {
			'host': config['mysql']['host'],
			'user': config['mysql']['user'],
			'password': config['mysql']['password'],
			'database': config['mysql']['database']
		},
		'settings': {
			'super_debug': config['settings']['super_debug'],
			'start_time': int(config['settings']['start_time'])
		}
	}


config = GetConfig()


def start_script_daily(script_path, start_time=500):
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


start_script_daily('bot.py', start_time=config['settings']['start_time'])
