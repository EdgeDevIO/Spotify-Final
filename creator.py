import os
import time
import random
import pyotp
import configparser
import requests

from drivertools import SetupDriver
from drivertools import ClickByText
from drivertools import SendKeysBySelector
from drivertools import CheckPresenceByText
from drivertools import runner
from drivertools import WaitForLoading
from logger import log
from db import MySQL

import asyncio
from nodriver.cdp import fetch


log = log(
	log_level="DEBUG",
	error_webhook="https://discord.com/api/webhooks/1315498715078983691/D6Ef9MXpjzmcbjZ1yKuRjXPy6jVvwg_xc4kSd2yqc9CKAuaxyTl0pr5hF6Rpze6Po1lt",  # noqa: E501
	critical_webhook="https://discord.com/api/webhooks/1315498559885541476/4LFZiDhxHKmLsFSd23PxdWR1caBrUbNqWLVcUnozIX4YorH1GhWCjMvga5nH_0uE75uL",  # noqa: E501
)


# Load config
def GetConfig(file_path='config.ini'):
	config = configparser.ConfigParser()
	config.read(file_path)

	if 'mysql' not in config:
		log.critical(
			f"Section 'mysql' not found in the {file_path} file. Program closed."
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
			'super_debug': config['settings']['super_debug']
		}
	}


config = GetConfig()


# Settings
super_debug = config['settings']['super_debug']


# Load DB
db = MySQL(
	config['database']['host'],
	config['database']['user'],
	config['database']['password'],
	config['database']['database']
)

try:
	settings = db.GetSettings()
except Exception:
	log.critical('MySQL connection failed. Exiting program.')

# Spotify URL
spotify_signup_url = settings['spotify_signup_url']

# List of months
months = [
	"january",
	"february",
	"march",
	"april",
	"may",
	"june",
	"july",
	"august",
	"september",
	"october",
	"november",
	"december",
]

# List of genders
gender = ['Man', 'Woman', 'Something else', 'Prefer not to say']


async def SignupWithGoogle(tab, gmail_email, gmail_password, gmail_two_factor):
	log.debug('Clicking sign up with google')
	await tab.wait()
	await WaitForLoading(tab)
	await ClickByText(tab, "Sign up with Google")

	# Click use other account
	await tab.wait(5)
	await tab.reload(ignore_cache=True)
	await tab.wait()
	log.debug('Checking for use another account')
	if await CheckPresenceByText(tab, 'Choose an account', timeout=3):
		await ClickByText(tab, 'Use another account')

	# Send email
	log.debug('Insert email')
	await tab.wait()
	await SendKeysBySelector(tab, "input[type=email]", gmail_email)

	# Click Next
	log.debug('Clicking Next')
	await tab.wait()
	await ClickByText(tab, "Next")

	# Check for captcha
	log.debug('Check for captcha')
	await tab.wait()
	await CheckPresenceByText(tab, "Verify it’s youxxxx")
	# IMPLEMENT CAPTCHA HANDLING

	# Send password
	log.debug('Insert password')
	await tab.wait()
	await SendKeysBySelector(tab, "input[type=password]", gmail_password)

	# Click Next
	log.debug('Clicking Next')
	await tab.wait()
	await ClickByText(tab, "Next")

	# Check for 2FA
	log.debug('Checking for two step verification')

	await tab.wait()
	await Verify2FA(tab)

	await tab.wait()
	await Verify2FA(tab)

	if await CheckPresenceByText(tab, 'Install App', timeout=3):
		log.info('Already Registered. Skipping account.')
		return True

	# Click Continue
	log.debug('Clicking Continue')
	await tab.wait()
	await tab.sleep(2)
	await ClickByText(tab, "Continue")

	# Select Month
	log.debug('Selecting Month')
	await WaitForLoading(tab)
	await tab.wait()
	await tab.sleep(2)
	await SendKeysBySelector(
		tab,
		"select",
		months[random.randint(0, 11)].title()
	)

	# Select Day
	log.debug('Selecting Day')
	await tab.wait()
	await SendKeysBySelector(tab, "input[id=day]", str(random.randint(1, 27)))

	# Select Year
	log.debug('Selecting Year')
	await tab.wait()
	await SendKeysBySelector(
		tab,
		"input[id=year]",
		str(random.randint(1970, 2000))
	)

	# Click Man, Woman
	log.debug('Selecting Gender')
	await tab.wait()
	await ClickByText(tab, random.choice(gender))

	# Click Next
	log.debug('Clicking Next')
	await tab.wait()
	await tab.sleep(1)
	await ClickByText(tab, "Next")

	# Click Sign up
	log.debug('Clicking Sign up')
	await WaitForLoading(tab)
	await tab.wait()
	await tab.sleep(1)
	await ClickByText(tab, "Sign up")

	await tab.wait()
	proxy_service = await CheckPresenceByText(tab, 'You seem to be using a proxy service.', best_match=True)
	if proxy_service:
		log.critical(
			f'Proxy service detected. Skipping account: {gmail_email["email"]}| {settings["proxy_host"]}:{settings["proxy_port"]}:{settings["proxy_username"]}:{settings["proxy_password"]}')  # noqa: E501
	else:
		return True


def RotateProxy():
	r = requests.get('https://proxy-seller.com/api/proxy/reboot?token=6b6c6898-d724-4ab2-9459-2ec1c800cfde')
	match r.status_code:
		case 200:
			log.info("Proxy Rotated Successfully")
			time.sleep(5)
			return True
		case 429:
			log.error("Proxy Rotation Failed - Rate Limit Exceeded | Waiting 10 seconds.")
			return False
		case _:
			log.error(f"Proxy Rotation Failed - Status Code: {r.status_code}")
			return False


async def Verify2FA(tab):
	if await CheckPresenceByText(tab, "2-Step Verification") or await CheckPresenceByText(tab, "Verify it’s you"):  # noqa: E501
		# if await CheckPresenceByText(tab, "Verify it’s you"):
		while True:
			log.debug('Inserting two step verification')
			await tab.wait()
			code = get_2fa(gmail_two_factor)
			code_input = await tab.select("input[type=tel]")
			await code_input.send_keys(code)

			log.debug('Clicking Next')
			await tab.wait()
			await ClickByText(tab, "Next")

			if await CheckPresenceByText(tab, "Wrong code. Try again."):
				log.debug('Wrong code. Trying again.')
				continue

			else:
				log.debug('Code Accepted.')
				break


def get_2fa(secret):
	normalized_secret = secret.replace(" ", "")
	totp = pyotp.TOTP(normalized_secret)
	current_code = totp.now()
	return current_code


async def setup_proxy(username, password, tab):
	async def auth_challenge_handler(event: fetch.AuthRequired):
		# Respond to the authentication challenge
		await tab.send(
			fetch.continue_with_auth(
				request_id=event.request_id,
				auth_challenge_response=fetch.AuthChallengeResponse(
					response="ProvideCredentials",
					username=username,
					password=password,
				),
			)
		)

	async def req_paused(event: fetch.RequestPaused):
		# Continue with the request
		await tab.send(fetch.continue_request(request_id=event.request_id))

	# Add handlers for fetch events
	tab.add_handler(
		fetch.RequestPaused, lambda event: asyncio.create_task(req_paused(event))
	)
	tab.add_handler(
		fetch.AuthRequired,
		lambda event: asyncio.create_task(auth_challenge_handler(event)),
	)

	# Enable fetch domain with auth requests handling
	await tab.send(fetch.enable(handle_auth_requests=True))


async def main(gmail_email, gmail_password, gmail_two_factor):
	while True:
		if RotateProxy():
			break

		else:
			time.sleep(10)
			continue

	log.info(f'Starting registration for: {gmail_email}')

	# Setup Driver
	driver = await SetupDriver(
		f"{os.getcwd()}/profiles/{gmail_email.split('@')[0]}",
		settings=settings
	)

	# Set proxy
	main_tab = await driver.get("draft:,")
	await main_tab.wait(2)
	await setup_proxy(settings['proxy_username'], settings['proxy_password'], main_tab)
	await main_tab.wait()

	# tab = await driver.get("https://www.myexternalip.com/raw")
	# await asyncio.sleep(222)

	# Continue script
	tab = await driver.get(spotify_signup_url)
	await tab.wait()

	signup = await SignupWithGoogle(tab, gmail_email, gmail_password, gmail_two_factor)

	if signup:
		# Mark registered in database
		db.UpdateEmail(gmail_email, {'registered': 1})
		log.info(f'User Registered: {gmail_email}')

	# Close driver
	await tab.wait(5)
	await tab.close()
	driver.stop()
	return


if __name__ == '__main__':
	# Get users to register
	accounts_to_register = db.GetAccountsToRegister()

	# Ensure there are accounts to register
	if not accounts_to_register:
		log.critical('No accounts to register. Exiting program.')
		exit()

	# Loop through accounts to register
	for account in accounts_to_register:
		gmail_email = account['email']
		gmail_password = account['password']
		gmail_two_factor = account['two_factor']

		# Run main logic
		runner(main(gmail_email, gmail_password, gmail_two_factor))

	log.info('All users registered. Exiting program.')
	time.sleep(5)
	exit()
