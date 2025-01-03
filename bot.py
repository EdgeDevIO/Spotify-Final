import os
import time
import random
import pyotp
import configparser
import requests
from pprint import pprint

from urllib.parse import urlparse

from drivertools import SetupDriver
from drivertools import ClickByText
from drivertools import SendKeysBySelector
from drivertools import ClickBySelector
from drivertools import CheckPresenceByText
from drivertools import WaitForLoading
from drivertools import CheckForLogin
from drivertools import runner
from datetime import datetime
import traceback

import asyncio
from nodriver.cdp import fetch
import shutil

from logger import log
from db import MySQL

from email_fetcher import fetch_confirmation_code

save_song = True
follow_artist = True

account_manager = []
action_list = []


# Load config
def GetConfig(file_path='config.ini'):
	config = configparser.ConfigParser()
	config.read(file_path)

	if 'mysql' not in config:
		print(
			f"Section 'mysql' not found in the {file_path} file. Program closed."
		)
		exit()

	return {
		'database': {
			'host': config['mysql']['host'],
			'user': config['mysql']['user'],
			'password': config['mysql']['password'],
			'database': config['mysql']['database']
		}
	}


config = GetConfig()


db = MySQL(
	config['database']['host'],
	config['database']['user'],
	config['database']['password'],
	config['database']['database']
)
settings = db.GetSettings()

log = log(
	log_level=settings['log_level'].upper(),
	error_webhook="https://discord.com/api/webhooks/1315498715078983691/D6Ef9MXpjzmcbjZ1yKuRjXPy6jVvwg_xc4kSd2yqc9CKAuaxyTl0pr5hF6Rpze6Po1lt",  # noqa: E501
	critical_webhook="https://discord.com/api/webhooks/1315498559885541476/4LFZiDhxHKmLsFSd23PxdWR1caBrUbNqWLVcUnozIX4YorH1GhWCjMvga5nH_0uE75uL",  # noqa: E501
)


async def main(account, song):
	email = account['email']
	# Setup Driver
	try:
		driver = await SetupDriver(
			folder_path=f"{os.getcwd()}/profiles/{email.split('@')[0]}",
			settings=settings
		)
	except Exception as e:
		log.error(f'Error setting up driver for {email}. Skipping song: {song["url"]}')
		print(traceback.format_exc())
		try:
			account_manager.remove(account['email'])
		except Exception:
			pass
		return

	try:
		# Set proxy
		main_tab = await driver.get("draft:,")
		await main_tab.wait(2)
		await setup_proxy(settings['proxy_username'], settings['proxy_password'], main_tab)
		await main_tab.wait()

		tab = await driver.get(song['url'])
		# tab = await driver.get('https://www.myexternalip.com/raw')
		# await tab.sleep(999)
	except RuntimeError:
		log.error(f'Error getting song: {song["url"]}. Skipping song. | {email}')
		try:
			account_manager.remove(account['email'])
		except Exception:
			pass
		return
	except ConnectionRefusedError as e:
		log.error(f'Connection refused while getting song: {song["url"]}. Skipping song. | {email} | Error: {e}')
		try:
			account_manager.remove(account['email'])
		except Exception as inner_e:
			log.warning(f"Failed to remove account {account['email']} | Error: {inner_e}")
		return
	except Exception:
		print(traceback.format_exc())
		try:
			account_manager.remove(account['email'])
		except Exception:
			pass
		return
	await tab.wait()

	# Check if logged in
	await WaitForLoading(tab)
	if not await CheckForLogin(tab):
		log.info('Not logged in. Logging in now.')

		# Log in
		await Login(tab, account, song)

	await tab.wait()
	await WaitForLoading(tab)

	try:
		added, saved, followed = await SaveToPlaylist(tab, account, song)
	except Exception:
		log.error(f'Error saving song: {song["url"]}. Skipping song. | {email}')
		try:
			account_manager.remove(account['email'])
		except Exception:
			pass
		driver.stop()
		return
	await tab.wait(2)

	if not account['verified']:
		while True:
			try:
				verified = await VerifyEmail(driver, account)
				if verified:
					db.UpdateEmail(account['email'], {'verified': 1, 'app_password': verified})
					log.success(f'{account["email"]} verified.')
					break
				else:
					break
			except ConnectionRefusedError:
				log.error('Error verifying email. Retrying.')
				tab.wait(5)
				continue
			except Exception:
				verified = False
				break

	db.Insert('song_history', {
		'email': email,
		'url': song['url'],
		'saved': saved,
		'followed': followed,
		'added': added,
		'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	})

	try:
		action_list.remove(song)
	except Exception as e:
		log.critical('failed to remove song from list.')
		print(str(e))

	driver.stop()


async def VerifyEmail(driver, account):
	if not account['app_password']:
		log.info(f'Attempting to verify account. {account["email"]}')
		tab = await driver.get('https://myaccount.google.com/apppasswords', new_tab=True)
	
		# Entering Password
		log.debug('EMAIL | Entering password confirmation.')
		await tab.wait()
		await SendKeysBySelector(tab, 'input[type="password"]', account['password'])
		await tab.sleep(2)
	
		log.debug('EMAIL | Clicking Next')
		await tab.wait()
		await ClickByText(tab, "Next")
	
		log.debug('EMAIL | Checking for 2FA')
		await tab.wait(2)
		await Verify2FAEmail(tab, account)
	
		log.debug('EMAIL | Clicking #i6')
		await tab.wait()
		await SendKeysBySelector(tab, '#i6', 'Spotify')
	
		await tab.wait(2)
		await ClickByText(tab, 'Create')
	
		app_password = await tab.select('div[dir="ltr"]')
		combined_text = ''.join(str(child.text) for child in app_password.children).replace('<span>', '').replace('</span>', '')
	else:
		combined_text = account['app_password']

	confirmation_code = fetch_confirmation_code(account['email'], combined_text, log)
	if not confirmation_code:
		log.error('EMAIL | Failed to get confirmation code. Account not verified.')
		db.UpdateEmail(account['email'], {'app_password': combined_text})
		await tab.close()
		return False
	await tab.get(confirmation_code)
	await tab.wait(10)
	await tab.close()
	return combined_text


async def Login(tab, account, song):
	# Retrieve the current URL
	if '/en/login' not in tab.url:
		try:
			await ClickByText(tab, "Log in")
		except Exception:
			try:
				account_manager.remove(account['email'])
			except Exception:
				pass
			tab.get('https://accounts.spotify.com/en/login?continue=' + song['url'])
	else:
		try:
			tab.get('https://accounts.spotify.com/en/login?continue=' + song['url'])
		except Exception:
			try:
				account_manager.remove(account['email'])
			except Exception:
				pass
			log.error('Error logging in. Skipping account.')

	# Click login with google
	log.debug('Clicking sign in with google')
	await tab.wait()
	await WaitForLoading(tab)
	await ClickByText(tab, "Continue with Google")

	# Click use other account
	log.debug('Checking for use another account')
	if await CheckPresenceByText(tab, 'Choose an account', timeout=3):
		await ClickByText(tab, 'Use another account')

	# Send email
	log.debug('Insert email')
	await tab.wait(3)
	await SendKeysBySelector(tab, "input[type=email]", account['email'])

	# Click Next
	log.debug('Clicking Next')
	await tab.wait()
	await ClickByText(tab, "Next")

	# Check for captcha
	log.debug('Check for captcha')
	await tab.wait(3)
	await CheckPresenceByText(tab, "Verify it’s you")
	# IMPLEMENT CAPTCHA HANDLING

	# Send password
	log.debug('Insert password')
	await tab.wait(5)
	await SendKeysBySelector(tab, "input[type=password]", account['password'])

	# Click Next
	log.debug('Clicking Next')
	await tab.wait()
	await ClickByText(tab, "Next")

	# Check for 2FA
	log.debug('Checking for two step verification')

	await tab.wait()
	await Verify2FA(tab, account)

	await tab.wait()
	await Verify2FA(tab, account)

	if await CheckPresenceByText(tab, 'Install App', timeout=3):
		log.info(f'{account["email"]} logged in.')
		try:
			account_manager.remove(account['email'])
		except Exception:
			pass
		return


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


def get_2fa(secret):
	normalized_secret = secret.replace(" ", "")
	totp = pyotp.TOTP(normalized_secret)
	current_code = totp.now()
	return current_code


async def Verify2FA(tab, account):
	if await CheckPresenceByText(tab, "2-Step Verification") or await CheckPresenceByText(tab, "Verify it’s you"):  # noqa: E501
		# if await CheckPresenceByText(tab, "Verify it’s you"):
		while True:
			log.debug('Inserting two step verification')
			await tab.wait()
			code = get_2fa(account['two_factor'])
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


async def Verify2FAEmail(tab, account):
	if await CheckPresenceByText(tab, "Verify that it’s you") or await CheckPresenceByText(tab, 'More ways to verify') or await CheckPresenceByText(tab, 'Try another way'):  # noqa: E501
		# if await CheckPresenceByText(tab, "Verify it’s you"):
		while True:
			log.debug('Inserting two step verification')
			await tab.wait()
			code = get_2fa(account['two_factor'])
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


async def SaveToPlaylist(tab, account, song):
	added = False
	saved = False
	followed = False

	log.debug('Attempting to add to playlist')
	await tab.wait()
	try:
		song_title = (await tab.select('h1')).text
		artist_title = (await tab.select('a[data-testid="creator-link"]')).text
	except asyncio.exceptions.TimeoutError:
		log.error(f'Error getting song title. Skipping song. | {account["email"]} | {song["url"]}')
		return
	except Exception:
		log.error(f'Error getting song title. Skipping song. | {account["email"]} | {song["url"]}')
		return
	url = song['url']
	email = account['email']
	# Check if already added
	song_history = db.GetSongHistory(url, email)
	if song_history:
		log.error('Song already added to users playlist. Skipping song.')
		return

	# Check if already added
	await tab.wait_for(selector='button[data-testid="more-button"]')
	dropdown = await tab.select('button[data-testid="more-button"]')
	await dropdown.mouse_move()
	await dropdown.click()
	add_to_playlist = await tab.select('button[role="menuitem"]')
	await add_to_playlist.mouse_move()
	await tab.wait(2)
	await ClickByText(tab, 'New playlist')
	await tab.wait(2)
	added = True
	log.success(f'{account["email"]} | Added song to playlist: {song_title}')

	# Save song
	if RandomChance(settings['save_chance']):
		log.debug('Attempting to save song')
		await tab.wait()
		button = await tab.select('button[data-testid="add-button"]')
		await button.mouse_move()

		# Check if already saved
		if not song_history or not song_history['saved']:
			# Save song
			await ClickBySelector(tab, 'button[data-testid="add-button"]')
			saved = True
			log.success(f'{account["email"]} | Saved song: {song_title}')
		else:
			log.info(f'{account["email"]} | Already saved song: {song_title}')

	# Follow artist
	if RandomChance(settings['follow_chance']):
		log.debug('Attempting to follow artist')
		await tab.wait()
		artist_title = await tab.select('a[data-testid="creator-link"]')
		await artist_title.mouse_click(button='right')
		await tab.wait()
		# Check if already followed
		if not song_history or not song_history['followed']:
			# Follow
			await ClickByText(tab, "Follow")
			followed = True
			log.success(f'{account["email"]} | Followed artist: {artist_title.text}')
		else:
			log.info(f'{account["email"]} | Already follows: {artist_title.text}')

	await tab.wait(2)

	return added, saved, followed


# Function to safely increment and fetch a shared counter
def get_next_browser_id(counter, lock):
	with lock:
		counter.value += 1
		return counter.value


def GetSongs():
	song_list = db.GetSongs()
	if not song_list:
		log.critical('No songs found in the database. Exiting program.')
		exit()
	log.info(f'Loaded {len(song_list)} songs.')
	return song_list


def GetAccounts():
	account_list = db.GetAccounts()
	if not account_list:
		log.critical('No accounts found in the database. Exiting program.')
		exit()
	log.info(f'Loaded {len(account_list)} accounts.')
	return account_list


def GetActions(songs):
	song_list = []  # Initialize the list to store results
	total_sum = 0       # Initialize the total sum of all random actions
	initial_action_list = []
	
	for song in songs:
		# Extract the range for the current song
		range_low = song['range_low']
		range_high = song['range_high']
		
		# Generate a random number within the range
		random_number = random.randint(range_low, range_high)
		
		# Add the random number to the total sum
		total_sum += random_number

		# Add the action to the list
		for i in range(random_number):
			initial_action_list.append({
				'id': song['id'],
				'url': CleanLink(song['url'])
			})
		
		# Add the result to the list
		song_list.append({
			'id': song['id'],  # Include the song ID for reference
			'url': CleanLink(song['url']),  # Include the song link for reference
			'random_action': random_number  # The generated random number
		})

	log.info(f'Loaded {len(initial_action_list)} actions.')

	return song_list, total_sum, initial_action_list


def RandomChance(percentage):
	"""
	Returns True with the given percentage chance.
	
	:param percentage: A number between 0 and 100 indicating the chance for True.
	:return: True with the given probability, otherwise False.
	"""
	if not 0 <= percentage <= 100:
		raise ValueError("Percentage must be between 0 and 100.")
	return random.uniform(0, 100) < percentage


def Title(text):
	os.system(f'title {text}')


def clear_folder(folder_path):
	for item in os.listdir(folder_path):
		item_path = os.path.join(folder_path, item)
		if os.path.isfile(item_path) or os.path.islink(item_path):
			os.remove(item_path)  # Remove file or symlink
		elif os.path.isdir(item_path):
			shutil.rmtree(item_path)  # Remove directory


def CleanLink(link):
	parsed_url = urlparse(link)
	cleaned_link = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
	return cleaned_link


def GetAccountForActions(url):
	while True:
		account = db.GetAccountForURL(url)
		if not account:
			log.error(f'No accounts found for song: {url}. Skipping song.')
			return False

		if account['email'] in account_manager:
			log.error(f'Account already in use for song: {url}. Trying next account.')
			pass
		return account


def StartBot():
	global action_list
	while action_list:
		log.debug(f'Action list: {len(action_list)}')
		log.debug(action_list[0])
		# Get Account Logic (Check if its already been used for this song)
		account = GetAccountForActions(action_list[0]['url'])

		# If no account available, skip song
		if not account:
			break

		time.sleep(3)

		log.info(f'Loaded account: {account["email"]}')

		account_manager.append(account['email'])

		# Rotate proxy
		while True:
			if RotateProxy():
				break
	
			else:
				time.sleep(10)
				continue

		# Run main function
		runner(main(account, action_list[0]))

		# Update account last action
		db.UpdateEmail(
			account['email'], 
			{
				'last_action': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			}
		)

		sleep_time = random.randint(
			settings['action_range_low'],
			settings['action_range_high']
		)

		# Wait for next action
		log.info(f'Waiting {sleep_time}s for next action.\n\n')
		time.sleep(sleep_time)


def RotateProxy():
	r = requests.get(settings['proxy_rotate_url'])
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


if __name__ == '__main__':
	# Get song list
	songs = GetSongs()
	if not songs:
		log.critical(
			'No songs found in the database. Exiting program.'
		)
		exit()

	# Check for registered accounts
	all_accounts = db.GetAccounts()
	if not all_accounts:
		log.critical(
			'No registered accounts found in the database. Exiting program.'
		)
		exit()

	# Returns the song list, total actions, and list of total urls
	song_list, total_actions, initial_action_list = GetActions(songs)

	# Randomizes the list of urls so the same urls aren't used one after another
	random_action_list = sorted(initial_action_list, key=lambda x: random.random())
	action_list = random_action_list

	# Send accounts and actions to the bot
	StartBot()

	log.debug('Program Finished.')
