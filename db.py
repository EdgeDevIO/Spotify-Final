import pymysql.cursors
from logger import log
log = log(
	log_level="INFO",
	error_webhook="https://discord.com/api/webhooks/1312960982817050706/r5v3fYRBONjXulTyc0UGslear2PRB9qIcutg8INJsqHI_fPcO31fASwxIWg-AVSHpvBo",  # noqa: E501
	critical_webhook="https://discord.com/api/webhooks/1312960874889216083/vKxMcXl2Jx_zVfOn3X4uki90LxQHbenFeDyqgon1zYCkmcdYvx7Tm7Kcfi8es4YRDZrC",  # noqa: E501
)


class MySQL:
	def __init__(self, host, username, password, database):
		self.host = host
		self.username = username
		self.password = password
		self.database = database
		try:
			pymysql.connect(
				host=self.host,
				user=self.username,
				password=self.password,
				database=self.database,
				cursorclass=pymysql.cursors.DictCursor
			)
		except pymysql.err.OperationalError:
			log.critical("Error connecting to database. Exiting program.")
			exit()

	def GetSettings(self):
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = "SELECT * from settings"
				cursor.execute(sql)
				result = cursor.fetchone()
				connection.commit()
			return result

	def GetAccountsToRegister(self):
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = "SELECT * from emails WHERE registered IS NULL OR registered = 0"
				cursor.execute(sql)
				result = cursor.fetchall()
				connection.commit()
			return result

	def UpdateEmail(self, userId, data):
		string = ', '.join([f"{i} = %s" for i in data.keys()])
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = f"UPDATE emails SET {string} WHERE email=%s"
				newList = list(data.values())
				newList.append(userId)
				cursor.execute(sql, tuple(newList))
				connection.commit()

	def GetSongs(self):
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = "SELECT * from songs"
				cursor.execute(sql)
				result = cursor.fetchall()
				connection.commit()
			return result

	def GetAccounts(self):
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = "SELECT * from emails WHERE registered = 1"
				cursor.execute(sql)
				result = cursor.fetchall()
				connection.commit()
			return result

	def GetAccountForURL(self, url):
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = """
					SELECT e.*
					FROM emails e
					LEFT JOIN song_history sh ON e.email = sh.email AND sh.url = %s
					WHERE e.registered = 1 AND sh.email IS NULL
					ORDER BY e.last_action ASC
					LIMIT 1
				"""
				cursor.execute(sql, (url,))
				result = cursor.fetchone()
				connection.commit()
			return result

	def GetSongHistory(self, url, email):
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = "SELECT * from song_history WHERE url = %s AND email = %s"
				cursor.execute(sql, (url, email))
				result = cursor.fetchone()
				connection.commit()
			return result

	def Insert(self, table, insert):
		keys = ', '.join([f"{k}" for k in insert.keys()])
		values = ', '.join(["%s" for v in insert.values()])
		connection = pymysql.connect(
			host=self.host,
			user=self.username,
			password=self.password,
			database=self.database,
			cursorclass=pymysql.cursors.DictCursor
		)
		with connection:
			with connection.cursor() as cursor:
				sql = f"INSERT INTO {table} ({keys}) VALUES ({values})"
				valuesList = list(insert.values())
				cursor.execute(sql, tuple(valuesList))
				connection.commit()
				return cursor.lastrowid
