import nodriver as uc
import os
import asyncio
from logger import log

log = log(
	log_level="INFO",
	error_webhook="https://discord.com/api/webhooks/1312960982817050706/r5v3fYRBONjXulTyc0UGslear2PRB9qIcutg8INJsqHI_fPcO31fASwxIWg-AVSHpvBo",  # noqa: E501
	critical_webhook="https://discord.com/api/webhooks/1312960874889216083/vKxMcXl2Jx_zVfOn3X4uki90LxQHbenFeDyqgon1zYCkmcdYvx7Tm7Kcfi8es4YRDZrC"  # noqa: E501
)

runner = uc.loop().run_until_complete


def create_folder(folder_path):
	if not os.path.exists(folder_path):
		os.mkdir(folder_path)


async def SetupDriver(folder_path=None, settings=False):
	browser_args = []

	browser_args.append(f'--proxy-server={settings["proxy_host"]}:{settings["proxy_port"]}')

	if folder_path:
		create_folder(folder_path)

	browser_args.append('--disable-session-crashed-bubble')

	log.debug(f'browser_args | {browser_args}')

	driver = await uc.start(
		user_data_dir=folder_path if folder_path else '',
		browser_args=browser_args
	)
	return driver


async def ClickByText(tab, text, best_match=True):
	try:
		await tab.wait_for(text=text)
		element = await tab.find(text, best_match=best_match)
		await element.mouse_move()
		await element.click()
	except Exception:
		log.debug(f'ERROR | ClickByText: {text}')


async def SendKeysBySelector(tab, selector, keys):
	try:
		await tab.wait_for(selector=selector)
		element = await tab.select(selector)
		await element.mouse_move()
		await element.send_keys(keys)
	except Exception:
		log.debug(f'ERROR | SendKeysBySelector: {selector}')


async def ClickBySelector(tab, selector):
	try:
		await tab.wait_for(selector=selector)
		element = await tab.select(selector)
		await element.mouse_move()
		await element.click()
	except Exception:
		log.debug(f'ERROR | ClickBySelector: {selector}')


async def CheckForLogin(tab):
	try:
		log.debug('Checking for login')
		await tab.wait(5)
		await tab.find('button[data-testid="login-button"]', timeout=5)
		return False
	except Exception:
		return True


async def CheckPresenceByText(tab, text, timeout=4, best_match=False):
	try:
		element = await tab.find(text, timeout=timeout, best_match=best_match)
		if element:
			return element

	except asyncio.exceptions.TimeoutError:
		return False


async def WaitForLoading(tab):
	while True:
		try:
			if await tab.find('div[data-testid="loading-overlay"]', timeout=1):
				log.debug('Loading found')
				await tab.wait(1)
			else:
				break
		except asyncio.TimeoutError:
			break
